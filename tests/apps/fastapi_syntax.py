from typing import Dict, Any, Union
import logging

from di.dependant import Marker
from quart import Blueprint

from sqlmodel import create_engine
from sqlmodel import Session

from sqlmodel.ext.asyncio.session import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from quart_di.compat import Annotated
from quart_di import QuartDI

from shared import setup_logging
from .common import create_app

logger = logging.getLogger(__name__)
setup_logging("quart_di", "tests")

sync_url = "sqlite://"
async_url = "sqlite+aiosqlite://"

sync_engine = create_engine(sync_url)
async_engine = AsyncEngine(create_engine(async_url))


# FastAPI Style dependencies
async def get_async_session():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


def get_sync_session():
    with Session(sync_engine) as session:
        yield session


# async def common_parameters(query: Optional[str] = None, offset: int = 0, limit: int = 100):
#     return {"q": query, "offset": offset, "limit": limit}


async def common_parameters(
    query: Union[str, None] = None, offset: int = 0, limit: int = 100
) -> Dict[str, Any]:
    return {"query": query, "offset": offset, "limit": limit}


# Annotations
AsyncDBSession = Annotated[AsyncSession, Marker(get_async_session, scope="request")]
SyncDBSession = Annotated[Session, Marker(get_sync_session, scope="request")]
CommonParams = Annotated[Dict[str, Any], Marker(common_parameters, scope="request")]


base = Blueprint("base", __name__)


@base.route("/db/async/session", methods=["POST"])
async def db_async_session(session: AsyncDBSession):
    return dict(
        session_type=type(session).__name__,
        engine_url=str(session.bind.url),
        is_active=session.is_active,
    )


@base.route("/db/sync/session", methods=["POST"])
async def db_sync_session(session: SyncDBSession, common: CommonParams):
    return dict(
        session_type=type(session).__name__,
        engine_url=str(session.bind.url),
        is_active=session.is_active,
    )


@base.route("/commons", methods=["POST"])
async def commons(common: CommonParams):
    return dict(common=common)


di = QuartDI(decorate_views=True)
app = create_app(base, di)
