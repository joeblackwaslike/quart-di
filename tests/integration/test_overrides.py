import pytest

from tests.shared.base import IntegrationTestBase
from tests.apps.override import app, ApiKeySecurity, BearerTokenSecurity, Postgres, MySQL


class TestOverrides(IntegrationTestBase):
    @pytest.fixture
    def _app(self):
        return app

    async def test_interface_resolution(self, app):
        async with self.test_client(app) as test_client:
            response = await test_client.post("/request")
            data = await response.get_json()

        assert data["type"] == "ApiKeySecurity"

    async def test_interface_overrides_request_scope(self, app, extension):
        async with self.test_client(app) as test_client:
            response = await test_client.post("/request")
            data = await response.get_json()

        assert data["type"] == "ApiKeySecurity"

        async with self.test_client(app) as test_client:
            with extension.dependency_overrides as overrides:
                overrides[ApiKeySecurity] = BearerTokenSecurity

                response = await test_client.post("/request")
                data = await response.get_json()

        assert data["type"] == "BearerTokenSecurity"

    async def test_interface_overrides_app_scope(self, app, extension):
        async with self.test_client(app) as test_client:
            response = await test_client.post("/app")
            data = await response.get_json()

        assert data["type"] == "Postgres"

        async with self.test_client(app) as test_client:
            with extension.dependency_overrides as overrides:
                overrides[Postgres] = MySQL

                response = await test_client.post("/app")
                data = await response.get_json()

        assert data["type"] == "MySQL"
