import pytest

from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.shared.base import IntegrationTestBase
from tests.apps.fastapi_syntax import app, AsyncDBSession, sync_url, async_url


class TestFastAPISyntax(IntegrationTestBase):
    @pytest.fixture
    def _app(self):
        return app

    async def test_fastapi_syntax_async_dbsession(self, app):
        async with self.test_client(app) as test_client:
            response = await test_client.post("/db/async/session")
            data = await response.get_json()

        assert data["session_type"] == AsyncSession.__name__
        assert data["engine_url"] == async_url
        assert data["is_active"] is True

    async def test_fastapi_syntax_sync_dbsession(self, app):
        async with self.test_client(app) as test_client:
            response = await test_client.post("/db/sync/session")
            data = await response.get_json()

        assert data["session_type"] == Session.__name__
        assert data["engine_url"] == sync_url
        assert data["is_active"] is True

    @pytest.mark.xfail(reason="Not currently working")
    async def test_fastapi_syntax_commons(self, app):
        commons = dict(query="search", limit=50)

        async with self.test_client(app) as test_client:
            response = await test_client.post("/commons", query_string=commons)
            data = await response.get_json()

        assert data["common"] == dict(offset=0, **commons)

    # async def test_interface_overrides_request_scope(self, app, deps):
    #     async with self.test_client(app) as test_client:
    #         response = await test_client.post("/request")
    #         data = await response.get_json()

    #     assert data["type"] == "ApiKeySecurity"

    #     async with self.test_client(app) as test_client:
    #         with deps.dependency_overrides as overrides:
    #             overrides[ApiKeySecurity] = BearerTokenSecurity

    #             response = await test_client.post("/request")
    #             data = await response.get_json()

    #     assert data["type"] == "BearerTokenSecurity"

    # async def test_interface_overrides_app_scope(self, app, deps):
    #     async with self.test_client(app) as test_client:
    #         response = await test_client.post("/app")
    #         data = await response.get_json()

    #     assert data["type"] == "Postgres"

    #     async with self.test_client(app) as test_client:
    #         with deps.dependency_overrides as overrides:
    #             overrides[Postgres] = MySQL

    #             response = await test_client.post("/app")
    #             data = await response.get_json()

    #     assert data["type"] == "MySQL"
