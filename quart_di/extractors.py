import inspect
import json
from typing import Any, Optional, Callable

from di.dependant import Dependant, Marker
from pydantic import BaseModel, ValidationError
from quart.wrappers import Request

from quart_di.compat import Annotated
from quart_di.util import resolve_name, inspect_annotation, model_field_from_param


__all__ = (
    "HeaderParam",
    "RequestBody",
    "JsonBody",
    "QueryParam",
    "PathParam",
    "CookieParam",
    "JsonParam",
)


class HeaderParam(Marker):
    alias: Optional[str] = None
    convert_underscores: bool = False

    def __init__(self, alias=None, convert_underscores=True):
        self.alias = alias
        self.convert_underscores = convert_underscores
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        name = resolve_name(param.name, self.alias, self.convert_underscores)
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param, alias=self.alias)

        def get_header(request: Annotated[Request, Marker()]) -> Any:
            headers = {key.lower(): val for key, val in request.headers.items()}

            if info.is_pydantic:
                return field.type_.parse_obj(headers)
            elif name.lower() in headers and info.is_parameterized:
                return field.validate(headers[name.lower()], {}, loc="en_US")[0]
            else:
                return headers

        return Dependant(get_header, scope="request")


class RequestBody(Marker):
    encoding: str
    decode: bool

    def __init__(self, encoding="utf-8", decode=True):
        self.encoding = encoding
        self.decode = decode
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param)

        async def get_body(request: Annotated[Request, Marker()]) -> Any:
            body = await request.get_data()
            if self.decode:
                body = body.decode(self.encoding)

            if info.origin and info.is_parameterized:
                if isinstance(body, str) and issubclass(info.origin, bytes):
                    body = body.encode(self.encoding)
                elif isinstance(body, bytes) and issubclass(info.origin, str):
                    body = body.decode(self.encoding)
                else:
                    body = field.validate(body, {}, loc="en_US")[0]

            return body

        return Dependant(get_body, scope="request")


class JsonBody(Marker):
    decoder: Callable

    def __init__(self, decoder=json.loads):
        self.decoder = decoder
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param)

        async def get_json(request: Annotated[Request, Marker()]) -> Any:
            data = await request.get_data()
            if self.decoder:
                data = self.decoder(data)

            if info.is_pydantic:
                return field.type_.parse_obj(data)
            else:
                return data

        return Dependant(get_json, scope="request")


class JsonParam(Marker):
    decoder: Callable
    alias: Optional[str]
    convert_underscores: bool

    def __init__(self, decoder=json.loads, alias=None, convert_underscores=False):
        self.decoder = decoder
        self.alias = alias
        self.convert_underscores = convert_underscores
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        name = resolve_name(param.name, self.alias, self.convert_underscores)
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param, alias=self.alias)

        async def get_json(request: Annotated[Request, Marker()]) -> Any:
            data = await request.get_data()
            if self.decoder:
                data = self.decoder(data)

            if info.is_pydantic:
                return field.type_.parse_obj(data)

            return field.validate(data[name], {}, loc="en_US")[0]

        return Dependant(get_json, scope="request")


class QueryParam(Marker):
    alias: Optional[str]
    convert_underscores: bool

    def __init__(self, alias=None, convert_underscores=False):
        self.alias = alias
        self.convert_underscores = convert_underscores
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        name = resolve_name(param.name, self.alias, self.convert_underscores)
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param, alias=self.alias)

        def get_query_args(request: Annotated[Request, Marker()]) -> Any:
            args = request.args

            if info.is_pydantic:
                return field.type_.parse_obj(args)
            elif name in args and info.is_parameterized:
                return field.validate(args[name], {}, loc="en_US")[0]
            else:
                return args

        return Dependant(get_query_args, scope="request")


class PathParam(Marker):
    def __init__(self):
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param)

        def get_path_args(request: Annotated[Request, Marker()]) -> Any:
            args = request.view_args

            if args is None and field.required:
                _, error = field.validate(None, {}, loc="en_US")
                if isinstance(error.exc, Exception):
                    raise ValidationError([error], model=BaseModel())

            if info.is_pydantic:
                return field.type_.parse_obj(args)
            elif param.name in args and info.is_parameterized:
                return field.validate(args[param.name], {}, loc="en_US")[0]
            else:
                return args

        return Dependant(get_path_args, scope="request")


class CookieParam(Marker):
    alias: Optional[str]
    convert_underscores: bool

    def __init__(self, alias=None, convert_underscores=False):
        self.alias = alias
        self.convert_underscores = convert_underscores
        super().__init__(call=None, scope="request", use_cache=False)

    def register_parameter(self, param: inspect.Parameter) -> Dependant[Any]:
        name = resolve_name(param.name, self.alias, self.convert_underscores)
        info = inspect_annotation(param.annotation)
        field = model_field_from_param(param, alias=self.alias)

        def get_cookies(request: Annotated[Request, Marker()]) -> Any:
            cookies = request.cookies

            if info.is_pydantic:
                return field.type_.parse_obj(cookies)
            elif name in cookies and info.is_parameterized:
                return field.validate(cookies[param.name], {}, loc="en_US")[0]
            else:
                return cookies

        return Dependant(get_cookies, scope="request")
