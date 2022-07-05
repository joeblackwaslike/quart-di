import dataclasses
import asyncio
from collections import defaultdict
from enum import Enum
from pathlib import PurePath
import inspect
from types import GeneratorType
from typing import Optional, Any, Tuple, Type, NamedTuple, Callable, Dict, List, Set, Union

from di.dependant import Marker
from pydantic import BaseModel, BaseConfig
from pydantic.json import ENCODERS_BY_TYPE
from pydantic.fields import ModelField

from quart_di.compat import get_args, _AnnotatedAlias

SetIntStr = Set[Union[int, str]]
DictIntStrAny = Dict[Union[int, str], Any]

__all__ = (
    "resolve_name",
    "TypeProperties",
    "inspect_annotation",
    "model_field_from_param",
    "get_task_id",
)


def resolve_name(param_name, alias=None, convert_underscores=False):
    if alias is not None:
        name = alias
    elif convert_underscores:
        name = param_name.replace("_", "-")
    else:
        name = param_name
    return name


class TypeProperties(NamedTuple):
    args: Tuple[Any, ...]
    origin: Type
    markers: Tuple[Marker, ...]
    is_scalar: bool
    is_pydantic: bool
    is_dataclass: bool
    is_model: bool
    is_parameterized: bool


def inspect_annotation(annotation: _AnnotatedAlias):
    from quart_di.markers import T

    scalar_types = (str, bytes, int, float, bool, complex, None)
    args = get_args(annotation)
    origin = getattr(annotation, "__origin__", None)
    return TypeProperties(
        args=args,
        origin=origin,
        markers=tuple(arg for arg in args if isinstance(arg, Marker)),
        is_scalar=hasattr(annotation, "__origin__") and origin in scalar_types,
        is_pydantic=(inspect.isclass(origin) and issubclass(origin, BaseModel))
        or (inspect.isclass(annotation) and issubclass(annotation, BaseModel)),
        is_dataclass=hasattr(origin, "__dataclass_fields__"),
        is_model=(inspect.isclass(origin) and issubclass(origin, BaseModel))
        or hasattr(origin, "__dataclass_fields__"),
        is_parameterized=origin is not T,
    )


def model_field_from_param(
    param: inspect.Parameter,
    alias: Optional[str] = None,
    arbitrary_types_allowed: bool = False,
) -> ModelField:

    Config = BaseConfig
    if arbitrary_types_allowed:

        class _Config(BaseConfig):
            arbitrary_types_allowed = True

        Config = _Config

    return ModelField.infer(
        name=alias or param.name,
        value=param.default if param.default is not param.empty else ...,
        annotation=param.annotation,
        class_validators={},
        config=Config,
    )


def generate_encoders_by_class_tuples(
    type_encoder_map: Dict[Any, Callable[[Any], Any]]
) -> Dict[Callable[[Any], Any], Tuple[Any, ...]]:
    encoders_by_class_tuples: Dict[Callable[[Any], Any], Tuple[Any, ...]] = defaultdict(tuple)
    for type_, encoder in type_encoder_map.items():
        encoders_by_class_tuples[encoder] += (type_,)
    return encoders_by_class_tuples


encoders_by_class_tuples = generate_encoders_by_class_tuples(ENCODERS_BY_TYPE)


def jsonable_encoder(
    obj: Any,
    include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
    exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
    by_alias: bool = True,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    custom_encoder: Optional[Dict[Any, Callable[[Any], Any]]] = None,
    sqlalchemy_safe: bool = True,
) -> Any:
    custom_encoder = custom_encoder or {}
    if custom_encoder:
        if type(obj) in custom_encoder:
            return custom_encoder[type(obj)](obj)
        else:
            for encoder_type, encoder_instance in custom_encoder.items():
                if isinstance(obj, encoder_type):
                    return encoder_instance(obj)
    if include is not None and not isinstance(include, (set, dict)):
        include = set(include)
    if exclude is not None and not isinstance(exclude, (set, dict)):
        exclude = set(exclude)
    if isinstance(obj, BaseModel):
        encoder = getattr(obj.__config__, "json_encoders", {})
        if custom_encoder:
            encoder.update(custom_encoder)
        obj_dict = obj.dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
        )
        if "__root__" in obj_dict:
            obj_dict = obj_dict["__root__"]
        return jsonable_encoder(
            obj_dict,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            custom_encoder=encoder,
            sqlalchemy_safe=sqlalchemy_safe,
        )
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, PurePath):
        return str(obj)
    if isinstance(obj, (str, int, float, type(None))):
        return obj
    if isinstance(obj, dict):
        encoded_dict = {}
        for key, value in obj.items():
            if (
                (not sqlalchemy_safe or (not isinstance(key, str)) or (not key.startswith("_sa")))
                and (value is not None or not exclude_none)
                and ((include and key in include) or not exclude or key not in exclude)
            ):
                encoded_key = jsonable_encoder(
                    key,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_none=exclude_none,
                    custom_encoder=custom_encoder,
                    sqlalchemy_safe=sqlalchemy_safe,
                )
                encoded_value = jsonable_encoder(
                    value,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_none=exclude_none,
                    custom_encoder=custom_encoder,
                    sqlalchemy_safe=sqlalchemy_safe,
                )
                encoded_dict[encoded_key] = encoded_value
        return encoded_dict
    if isinstance(obj, (list, set, frozenset, GeneratorType, tuple)):
        encoded_list = []
        for item in obj:
            encoded_list.append(
                jsonable_encoder(
                    item,
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    custom_encoder=custom_encoder,
                    sqlalchemy_safe=sqlalchemy_safe,
                )
            )
        return encoded_list

    if type(obj) in ENCODERS_BY_TYPE:
        return ENCODERS_BY_TYPE[type(obj)](obj)
    for encoder, classes_tuple in encoders_by_class_tuples.items():
        if isinstance(obj, classes_tuple):
            return encoder(obj)

    errors: List[Exception] = []
    try:
        data = dict(obj)
    except Exception as e:
        errors.append(e)
        try:
            data = vars(obj)
        except Exception as e:
            errors.append(e)
            raise ValueError(errors)
    return jsonable_encoder(
        data,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        custom_encoder=custom_encoder,
        sqlalchemy_safe=sqlalchemy_safe,
    )


def get_task_id():
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return

    return id(task)
