import logging

from quart import Blueprint
from di.dependant import Dependant

from quart_di.compat import Protocol
from quart_di import QuartDI

from .common import create_app
from shared import setup_logging

logger = logging.getLogger(__name__)
setup_logging("quart_di", "tests")


class DBProtocol(Protocol):
    async def execute(self, sql: str) -> None:
        ...


class Postgres(DBProtocol):
    async def execute(self, sql: str) -> None:
        print(sql)


class MySQL(DBProtocol):
    async def execute(self, sql: str) -> None:
        print(sql)


class SecurityBase(Protocol):
    async def authorize(self, token: str) -> bool:
        ...


class ApiKeySecurity(SecurityBase):
    async def authorize(self, token: str) -> bool:
        return token == "secret"


class BearerTokenSecurity(SecurityBase):
    async def authorize(self, token: str) -> bool:
        return token == "secret"


base = Blueprint("base", __name__)


@base.post("/app")
async def app_scope(db: DBProtocol):
    return dict(type=type(db).__name__)


@base.post("/request")
async def request_scope(security: SecurityBase):
    return dict(type=type(security).__name__)


di = QuartDI(
    binds=[
        (DBProtocol, Dependant(Postgres, scope="app")),
        (SecurityBase, Dependant(ApiKeySecurity, scope="request")),
    ],
    decorate_views=True,
)
app = create_app(base, di)
di.init_app(app)
