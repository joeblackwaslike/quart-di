import pytest

from tests.shared.base import IntegrationTestBase
from tests.shared import extension as extension_data

from tests.apps.example import app


class TestExtension(IntegrationTestBase):
    user_id = extension_data.user_id
    kitchen_sink_request = extension_data.kitchen_sink_request
    kitchen_sink_urls = extension_data.kitchen_sink_urls

    @pytest.fixture
    def _app(self):
        return app

    @pytest.fixture
    def kitchen_sink_request_params(self):
        return self.kitchen_sink_request.copy()

    @pytest.mark.parametrize("path", kitchen_sink_urls)
    async def test_kitchen_sink_endpoint_integration(self, path, kitchen_sink_request_params):
        method = kitchen_sink_request_params.pop("method")
        kitchen_sink_request_params["path"] = path.format(user_id=self.user_id)

        async with self.test_client(app) as test_client:
            test_client_method = getattr(test_client, method.lower())

            response = await test_client_method(**kitchen_sink_request_params)
            payload = await response.get_json()

        assert response.status_code == 200
        extension_data.validate_kitchen_sink_payload(
            payload, kitchen_sink_request_params, user_id=self.user_id
        )
