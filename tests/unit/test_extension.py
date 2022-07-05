import pytest

from tests.shared.base import UnitTestBase
from tests.shared import extension as extension_data

from tests.apps.example import app


class TestExtension(UnitTestBase):
    user_id = extension_data.user_id
    kitchen_sink_request = extension_data.kitchen_sink_request
    kitchen_sink_endpoints = extension_data.kitchen_sink_endpoints
    kitchen_sink_urls = extension_data.kitchen_sink_urls

    @pytest.fixture
    def _app(self):
        return app

    @pytest.fixture
    def kitchen_sink_request_params(self):
        return self.kitchen_sink_request.copy()

    @pytest.mark.parametrize(
        "endpoint_name, endpoint_url", zip(kitchen_sink_endpoints, kitchen_sink_urls)
    )
    async def test_endpoints_unit(
        self,
        endpoint_name,
        endpoint_url,
        kitchen_sink_request_params,
        app,
    ):
        kitchen_sink_request_params["path"] = endpoint_url.format(user_id=self.user_id)

        async with self.test_contexts(app, **kitchen_sink_request_params):
            payload = await app.view_functions[endpoint_name]()

        extension_data.validate_kitchen_sink_payload(
            payload, kitchen_sink_request_params, user_id=self.user_id
        )
