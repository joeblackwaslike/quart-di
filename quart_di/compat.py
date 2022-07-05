import inspect
import typing

try:
    from typing import get_args
except ImportError:
    from typing_extensions import get_args

try:
    from typing import _AnnotatedAlias
except ImportError:
    from typing_extensions import _AnnotatedAlias

try:
    # 3.9+
    from typing import _BaseGenericAlias
except ImportError:
    _BaseGenericAlias = typing._GenericAlias
try:
    # 3.9+
    from typing import GenericAlias
except ImportError:
    GenericAlias = typing._GenericAlias

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol

from di.typing import Annotated


# Python 3.10+ has PEP 612
if hasattr(typing, "ParamSpecArgs"):
    ParamSpecArgs = typing.ParamSpecArgs
    ParamSpecKwargs = typing.ParamSpecKwargs
# 3.6-3.9
else:

    class _Immutable:
        """Mixin to indicate that object should not be copied."""

        __slots__ = ()

        def __copy__(self):
            return self

        def __deepcopy__(self, memo):
            return self

    class ParamSpecArgs(_Immutable):
        """The args for a ParamSpec object.

        Given a ParamSpec object P, P.args is an instance of ParamSpecArgs.

        ParamSpecArgs objects have a reference back to their ParamSpec:

        P.args.__origin__ is P

        This type is meant for runtime introspection and has no special meaning to
        static type checkers.
        """

        def __init__(self, origin):
            self.__origin__ = origin

        def __repr__(self):
            return f"{self.__origin__.__name__}.args"

        def __eq__(self, other):
            if not isinstance(other, ParamSpecArgs):
                return NotImplemented
            return self.__origin__ == other.__origin__

    class ParamSpecKwargs(_Immutable):
        """The kwargs for a ParamSpec object.

        Given a ParamSpec object P, P.kwargs is an instance of ParamSpecKwargs.

        ParamSpecKwargs objects have a reference back to their ParamSpec:

        P.kwargs.__origin__ is P

        This type is meant for runtime introspection and has no special meaning to
        static type checkers.
        """

        def __init__(self, origin):
            self.__origin__ = origin

        def __repr__(self):
            return f"{self.__origin__.__name__}.kwargs"

        def __eq__(self, other):
            if not isinstance(other, ParamSpecKwargs):
                return NotImplemented
            return self.__origin__ == other.__origin__


__all__ = (
    "_AnnotatedAlias",
    "Annotated",
    "_BaseGenericAlias",
    "GenericAlias",
    "ParamSpecArgs",
    "ParamSpecKwargs",
    "get_origin",
    "get_type",
    "get_args",
    "Protocol",
)


def get_origin(tp):
    """Get the unsubscripted version of a type.

    This supports generic types, Callable, Tuple, Union, Literal, Final, ClassVar
    and Annotated. Return None for unsupported types. Examples::

        get_origin(Literal[42]) is Literal
        get_origin(int) is None
        get_origin(ClassVar[int]) is ClassVar
        get_origin(Generic) is Generic
        get_origin(Generic[T]) is Generic
        get_origin(Union[T, int]) is Union
        get_origin(List[Tuple[T, T]][int]) == list
        get_origin(P.args) is P
    """
    if isinstance(tp, _AnnotatedAlias):
        return Annotated
    if isinstance(tp, (GenericAlias, _BaseGenericAlias, ParamSpecArgs, ParamSpecKwargs)):
        return tp.__origin__
    if tp is typing.Generic:
        return typing.Generic
    return None


def get_type(param: inspect.Parameter) -> type:
    if get_origin(param.annotation) is Annotated:
        return next(iter(get_args(param.annotation)))
    return param.annotation
