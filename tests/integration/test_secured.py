import pytest

from tests.shared.base import IntegrationTestBase
from tests.apps.secured import app, NO_KEYS_ERROR_MSG, BOTH_KEYS_ERROR_MSG


class TestSecured(IntegrationTestBase):
    @pytest.fixture
    def _app(self):
        return app

    @pytest.mark.parametrize(
        "headers", [{"x-public-api-key": "12345"}, {"x-secret-api-key": "12345"}]
    )
    async def test_happy_path(self, headers, app):
        async with self.test_client(app) as test_client:
            response = await test_client.post(
                "/secured",
                headers=headers,
            )
            data = await response.get_json()

        expected = dict(
            api_keys=dict(
                public=headers.get("x-public-api-key"),
                secret=headers.get("x-secret-api-key"),
            ),
        )

        assert data == expected

    @pytest.mark.parametrize(
        "headers", [{}, {"x-secret-api-key": "12345", "x-public-api-key": "12345"}]
    )
    async def test_raises_exception_when_not_authenticated(self, headers, app):
        async with self.test_client(app) as test_client:
            response = await test_client.post(
                "/secured",
                headers=headers,
            )
            data = await response.get_json()

        assert response.status_code == 401

        if not headers:
            error_msg = NO_KEYS_ERROR_MSG
        else:
            error_msg = BOTH_KEYS_ERROR_MSG

        expected_data = dict(error=f"401 Unauthorized: {error_msg}")

        assert data == expected_data
