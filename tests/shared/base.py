from contextlib import asynccontextmanager, AsyncExitStack

import pytest
from quart_di import QuartDI


class BaseTestClass:
    @pytest.fixture
    def _app(self):
        return None

    @pytest.fixture
    def app(self, _app, monkeypatch):
        if _app is None:
            raise ValueError("Must provide an `_app` fixture when using BaseTestClass")
        monkeypatch.setitem(_app.config, "TESTING", True)
        yield _app

    @pytest.fixture
    def extension(self, app):
        yield app.extensions[QuartDI.EXTENSION_KEY]

    @asynccontextmanager
    async def test_contexts(
        self,
        app,
        test_app_context=True,
        app_context=False,
        request_context=False,
        preprocess_request=False,
        *request_context_args,
        **request_context_kwargs,
    ):
        async with AsyncExitStack() as stack:
            if test_app_context:
                await stack.enter_async_context(app.test_app())
            if app_context:
                await stack.enter_async_context(app.app_context())
            if request_context:
                await stack.enter_async_context(
                    app.test_request_context(
                        *request_context_args,
                        **request_context_kwargs,
                    )
                )
            if preprocess_request:
                await app.preprocess_request()

            yield


class UnitTestBase(BaseTestClass):
    @asynccontextmanager
    async def test_contexts(
        self,
        app,
        test_app_context=True,
        app_context=True,
        request_context=True,
        preprocess_request=True,
        *request_context_args,
        **request_context_kwargs,
    ):
        async with super().test_contexts(
            app,
            *request_context_args,
            test_app_context=test_app_context,
            app_context=app_context,
            request_context=request_context,
            preprocess_request=preprocess_request,
            **request_context_kwargs,
        ):
            yield


class IntegrationTestBase(BaseTestClass):
    @asynccontextmanager
    async def test_client(self, app):
        async with self.test_contexts(app):
            yield app.test_client()
