import pytest
from di.dependant import Dependant

from tests.shared.base import UnitTestBase
from tests.apps.override import (
    app,
    DBProtocol,
    Postgres,
    MySQL,
    SecurityBase,
    ApiKeySecurity,
    BearerTokenSecurity,
)


class TestOverrides(UnitTestBase):
    @pytest.fixture
    def _app(self):
        return app

    async def test_interface_resolution(self, app, extension):
        async with self.test_contexts(app, path="/request"):
            security = await extension._inject(Dependant(SecurityBase, scope="request"))

        assert isinstance(security, ApiKeySecurity)

    async def test_interface_overrides_request_scope(self, app, extension):
        async with self.test_contexts(app, path="/request"):
            security = await extension._inject(Dependant(SecurityBase, scope="request"))

        assert isinstance(security, ApiKeySecurity)

        async with self.test_contexts(app, path="/request"):
            with extension.dependency_overrides as overrides:
                overrides[ApiKeySecurity] = BearerTokenSecurity

                security2 = await extension._inject(Dependant(SecurityBase, scope="request"))

        assert isinstance(security2, BearerTokenSecurity)

    async def test_interface_overrides_app_scope(self, app, extension):
        async with self.test_contexts(app, path="/request"):
            db = await extension._inject(Dependant(DBProtocol, scope="app"))

        assert isinstance(db, Postgres)

        async with self.test_contexts(app, path="/request"):
            with extension.dependency_overrides as overrides:
                overrides[Postgres] = MySQL

                db2 = await extension._inject(Dependant(DBProtocol, scope="app"))

        assert isinstance(db2, MySQL)
