from typing import TypeVar

from quart_di.compat import Annotated
from quart_di.extractors import (
    RequestBody,
    JsonBody,
    HeaderParam,
    QueryParam,
    PathParam,
    CookieParam,
    JsonParam,
)

__all__ = (
    "T",
    "Body",
    "Json",
    "FromPath",
    "FromHeader",
    "FromJson",
    "FromQuery",
    "FromCookie",
)

T = TypeVar("T")

Body = Annotated[T, RequestBody()]
Json = Annotated[T, JsonBody()]
FromPath = Annotated[T, PathParam()]
FromHeader = Annotated[T, HeaderParam(convert_underscores=True)]
FromJson = Annotated[T, JsonParam(convert_underscores=True)]
FromQuery = Annotated[T, QueryParam(convert_underscores=True)]
FromCookie = Annotated[T, CookieParam(convert_underscores=True)]
