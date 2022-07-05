from typing import Optional, List, Dict, Any
import logging

from di.dependant import Marker, Injectable, Dependant
from pydantic import BaseModel, Field, validator
from quart import Blueprint

from quart_di.compat import Annotated
from quart_di import (
    FromHeader,
    FromQuery,
    FromCookie,
    FromJson,
    FromPath,
    Json,
    Body,
    QuartDI,
    inject,
)

from .common import create_app
from shared import setup_logging

logger = logging.getLogger(__name__)
setup_logging("quart_di", "tests")


# FastAPI Style dependencies
async def common_parameters(q: Optional[str] = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


# Annotations
CommonParams = Annotated[Dict, Marker(common_parameters, scope="request")]


class Config(BaseModel):
    db_uri: str = "sqlite:///:memory:"


class Database(Injectable, scope="request"):
    def __init__(self, config: Config):
        self.db_uri = config.db_uri
        self.closed = False
        print(f"Initializing db {self}")

    async def execute(self, sql: str) -> None:
        print(sql)

    def close(self):
        if self.closed is True:
            raise RuntimeError("Database already closed")
        self.closed = True
        print(f"Closing db {self}")

    def __repr__(self):
        return f"{type(self).__name__}(uri={self.db_uri!r}, closed={self.closed!r})"


# Deps
class Postgres(Database):
    pass


# Schemas
class HeadersModel(BaseModel):
    x_header_one: Optional[str] = Field(None, alias="x-header-one")
    x_header_two: Optional[int] = Field(None, alias="x-header-two")


class RequestItem(BaseModel):
    id: int
    name: str
    tags: List[str]


class StyleParams(BaseModel):
    color: str = "default"
    theme: str = "default"
    logo: str = "default.png"


class AuthCookies(BaseModel):
    session: Optional[str] = None
    csrf: Optional[str] = None


class Response(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            Database: lambda v: vars(v),
        }

    db: Database
    x_header_one: str
    headers_model: HeadersModel
    headers: Dict[str, Any]
    commons: Dict[str, Any]
    body: RequestItem
    item: RequestItem
    name: str
    tags: List[str]
    style_params: StyleParams
    color: str
    query: Dict[str, Any]
    session: str
    auth: AuthCookies
    cookies: Dict[str, Any]
    raw_body: str
    bytes_body: bytes
    str_body: str
    user_id: int
    extra: Optional[Any] = None

    @validator("db")
    def deserialize_db(cls, v):
        if isinstance(v, dict):
            return Database(Config(db_uri=v["db_uri"]))
        return v


# Endpoints
async def endpoint(
    db: Database,
    x_header_one: FromHeader[str],
    headers_model: FromHeader[HeadersModel],
    headers: FromHeader,
    commons: CommonParams,
    body: Json[RequestItem],
    item: FromJson[RequestItem],
    name: FromJson[str],
    tags: FromJson[List[str]],
    style_params: FromQuery[StyleParams],
    color: FromQuery[str],
    query: FromQuery,
    session: FromCookie[str],
    auth: FromCookie[AuthCookies],
    cookies: FromCookie,
    raw_body: Body,
    bytes_body: Body[bytes],
    str_body: Body[str],
    user_id: FromPath[int],
    extra: Optional[Any] = None,
) -> Response:
    return Response(
        commons=commons,
        db=db,
        x_header_one=x_header_one,
        headers_model=headers_model,
        headers=dict(headers),
        body=body,
        item=item,
        name=name,
        tags=tags,
        style_params=style_params,
        color=color,
        query=dict(query),
        session=session,
        auth=auth,
        cookies=dict(cookies),
        raw_body=raw_body,
        bytes_body=bytes_body,
        str_body=str_body,
        user_id=user_id,
        extra=extra,
    )


base = Blueprint("base", __name__)

decorated_kitchen_sink = base.post(
    "/kitchen-sink/decorated/<user_id>/", endpoint="decorated_kitchen_sink"
)(inject(endpoint))
undecorated_kitchen_sink = base.post(
    "/kitchen-sink/undecorated/<user_id>/", endpoint="undecorated_kitchen_sink"
)(endpoint)


di = QuartDI(
    binds=[(Database, Dependant(Postgres, scope="app"))],
    decorate_views=True,
)
app = create_app(base, di)
