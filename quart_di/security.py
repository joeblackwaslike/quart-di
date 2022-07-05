import inspect
from abc import abstractmethod
from typing import AbstractSet
from typing import Any
from typing import ClassVar
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import TypeVar

from di.dependant import Dependant
from di.dependant import Injectable
from pydantic import BaseModel
from quart.wrappers import Request
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Unauthorized

from quart_di.compat import Protocol


__all__ = (
    "AlternativeSecuritySchemes",
    "APIKeyHeader",
    "OAuth2AuthorizationCodeBearer",
    "RequiredSecuritySchemes",
)

T = TypeVar("T")
UNAUTHORIZED_EXC = Unauthorized("Not authenticated")
UNAUTHORIZED_CHALLANGE_EXC = Unauthorized(
    "Not authenticated", www_authenticate=WWWAuthenticate("Bearer")
)


class SecurityScheme(Protocol):
    __slots__ = ()

    @classmethod
    def __di_dependency__(cls, param: inspect.Parameter) -> Dependant[Any]:
        return Dependant(cls.extract, scope="request")

    @classmethod
    @abstractmethod
    async def extract(cls, request: Request) -> "Optional[SecuritySchemeType]":
        raise NotImplementedError

    def __init_subclass__(cls) -> None:
        # https://bugs.python.org/issue44807
        init = getattr(cls, "__init__")
        super().__init_subclass__()
        if init is not object.__init__:
            setattr(cls, "__init__", init)


SecuritySchemeType = TypeVar("SecuritySchemeType", bound=SecurityScheme)


class _APIKeyBase(SecurityScheme, Protocol):
    name: ClassVar[str]
    unauthorized_error: ClassVar[Optional[Exception]] = UNAUTHORIZED_EXC

    __slots__ = ("api_key",)

    api_key: str

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key


class APIKeyHeader(_APIKeyBase, Protocol):
    __slots__ = ()

    @classmethod
    async def extract(cls, request: Request) -> "Optional[APIKeyHeader]":
        api_key = request.headers.get(cls.name)
        if not api_key:
            if cls.unauthorized_error:
                raise cls.unauthorized_error
            else:
                return None
        return cls(api_key=api_key)


class _OAuth2Base(SecurityScheme, Protocol):
    unauthorized_error: ClassVar[Optional[Exception]] = UNAUTHORIZED_EXC


def get_authorization_scheme_param(authorization_header_value: str) -> Tuple[str, str]:
    if not authorization_header_value:
        return "", ""
    scheme, _, param = authorization_header_value.partition(" ")
    return scheme, param


class OAuth2AuthorizationCodeBearer(_OAuth2Base, Protocol):
    unauthorized_error: ClassVar[Optional[Exception]] = UNAUTHORIZED_CHALLANGE_EXC
    authorization_url: ClassVar[str]
    token_url: ClassVar[str]
    refresh_url: ClassVar[Optional[str]] = None
    scopes: ClassVar[Optional[Mapping[str, str]]] = None
    required_scopes: ClassVar[Optional[AbstractSet[str]]] = None

    token: str

    def __init__(self, token: str) -> None:
        self.token = token

    @classmethod
    async def extract(cls, request: Request) -> "Optional[OAuth2AuthorizationCodeBearer]":
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if cls.unauthorized_error:
                raise cls.unauthorized_error
            else:
                return None
        return cls(param)


class RequiredSecuritySchemes(BaseModel, Injectable):
    def __init_subclass__(cls) -> None:
        return super().__init_subclass__(call=cls.extract, scope="request")

    @classmethod
    async def extract(cls, request: Request) -> Any:
        data = {}
        for field in cls.__fields__.values():
            data[field.name] = await field.type_.extract(request)
        return cls(**data)

    class Config:
        arbitrary_types_allowed = True


class AlternativeSecuritySchemes(BaseModel, Injectable):
    def __init_subclass__(cls) -> None:
        return super().__init_subclass__(call=cls.extract, scope="request")

    @classmethod
    async def extract(cls, request: Request) -> Any:
        data = {}
        err = None
        for field in cls.__fields__.values():
            try:
                data[field.name] = await field.type_.extract(request)
            except Exception as e:
                err = e
                data[field.name] = None
        if not any(data.values()) and err:
            raise err
        return cls(**data)

    class Config:
        arbitrary_types_allowed = True
