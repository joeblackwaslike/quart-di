import inspect
import logging
from functools import partial
from functools import wraps
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union

from di.api.dependencies import DependantBase
from di.container import bind_by_type
from di.container import Container
from di.container import ContainerState
from di.dependant import Dependant
from di.executors import AsyncExecutor
from quart import current_app
from quart import Quart
from quart import request
from quart import signals
from quart.wrappers import Request

from quart_di.override import DependencyOverrideManager
from quart_di.state_context import app_states
from quart_di.state_context import create_and_push_app_context
from quart_di.state_context import create_and_push_req_context
from quart_di.state_context import req_states
from quart_di.util import jsonable_encoder


__all__ = ("inject", "QuartDI")

INJECTED_MARKER_ATTRIBUTE = "__quart_di_solved__"

BindByTypeType = Tuple[Type, DependantBase[Any]]
BindCallableType = Callable[
    [Optional[inspect.Parameter], DependantBase[Any]], Optional[DependantBase[Any]]
]
DependencyType = Union[BindByTypeType, BindCallableType]

logger = logging.getLogger(__name__)


def inject(view: Callable) -> Callable:
    @wraps(view)
    async def wrapper(*args, **kwargs):
        extension = current_app.extensions[QuartDI.EXTENSION_KEY]

        result = await current_app.ensure_async(extension._inject)(
            Dependant(partial(view, *args, **kwargs), scope="request"),
        )

        if extension.encode_view_result:
            result = extension.view_result_encoder(
                result,
                **extension.view_result_encoder_options,
            )
        return result

    setattr(wrapper, INJECTED_MARKER_ATTRIBUTE, True)
    return wrapper


class QuartDI:
    EXTENSION_KEY = "QuartDI"

    default_scopes = ("app", "request")

    app: Optional[Quart]
    container: Container
    dependency_overrides: DependencyOverrideManager
    decorate_views: bool
    encode_view_result: bool
    view_result_encoder: Callable[[Any], Any]
    view_result_encoder_options: Dict[str, Any]
    _binds: Sequence[DependencyType]
    _container_state: ContainerState
    _executor: AsyncExecutor

    class DefaultConfig:
        app = None
        container = None
        container_state = None
        binds = None
        decorate_views = False
        encode_view_result = True
        view_result_encoder = jsonable_encoder
        view_result_encoder_options = None

    def __init__(
        self,
        app=DefaultConfig.app,
        container=DefaultConfig.container,
        container_state=DefaultConfig.container_state,
        binds=DefaultConfig.binds,
        decorate_views=DefaultConfig.decorate_views,
        encode_view_result=DefaultConfig.encode_view_result,
        view_result_encoder=DefaultConfig.view_result_encoder,
        view_result_encoder_options=DefaultConfig.view_result_encoder_options,
    ):
        self.container = container or Container()
        self._binds = list(binds or ())
        self._container_state = container_state or ContainerState()
        self.decorate_views = decorate_views
        self.encode_view_result = encode_view_result
        self.view_result_encoder = view_result_encoder
        self.view_result_encoder_options = view_result_encoder_options or {}

        self._executor = AsyncExecutor()
        self.dependency_overrides = DependencyOverrideManager(self.container)

        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Quart) -> None:
        self.app = app
        app.extensions[self.EXTENSION_KEY] = self
        self._init_app_config(app)

        if self.decorate_views:
            self._decorate_views()

        for scope in self.default_scopes:
            self._register_dependencies(scope)

        @app.before_request
        async def handle_request_started():
            await create_and_push_req_context(
                app,
                self.container,
            )

        @app.teardown_request
        async def handle_request_ended(*args):
            await req_states.pop_context()

        @signals.appcontext_pushed.connect_via(app)
        async def handle_appcontext_pushed(app):
            await create_and_push_app_context(
                app,
                self.container,
                self._container_state,
            )

        @signals.appcontext_popped.connect_via(app)
        async def handle_appcontext_popped(app):
            await app_states.pop_context()

    def _init_app_config(self, app: Quart):
        self.decorate_views = app.config.get("QUART_DI_DECORATE_VIEWS", self.decorate_views)
        self.encode_view_result = app.config.get(
            "QUART_DI_ENCODE_VIEW_RESULT", self.encode_view_result
        )
        self.view_result_encoder = app.config.get(
            "QUART_DI_VIEW_RESULT_ENCODER", self.view_result_encoder
        )
        self.view_result_encoder_options = app.config.get(
            "QUART_DI_VIEW_RESULT_ENCODER_OPTIONS", self.view_result_encoder_options
        )

        for bind in app.config.get("QUART_DI_BINDS", []):
            self._binds.append(bind)

    def _decorate_views(self):
        if self.app is None:
            raise RuntimeError("app is not initialized")

        for rule in self.app.url_map.iter_rules():
            if rule.endpoint is not None:
                view = self.app.view_functions[rule.endpoint]

                if getattr(view, INJECTED_MARKER_ATTRIBUTE, False) is False:
                    decorated_view = inject(view)
                    self.app.view_functions[rule.endpoint] = decorated_view

    def get_di_execute_values(self):
        return {
            Request: request._get_current_object(),
            Quart: current_app._get_current_object(),
        }

    def _register_dependencies(self, scope: str):
        if scope == "app":
            self.container.bind(
                bind_by_type(Dependant(lambda: self.container, scope="app"), Container)
            )
            self.container.bind(
                bind_by_type(
                    Dependant(lambda: current_app._get_current_object(), scope="app"), Quart
                )
            )
        elif scope == "request":
            self.container.bind(
                bind_by_type(
                    Dependant(lambda: request._get_current_object(), scope="request"), Request
                )
            )

        if self._binds:
            for bind in self._binds:
                if isinstance(bind, (list, tuple)) and bind[1].scope == scope:
                    self.container.bind(bind_by_type(*reversed(bind)))
                elif callable(bind):
                    self.container.bind(bind)

    async def _inject(self, dependant: DependantBase):
        logger.info(f"injecting {dependant!r}")

        req_ctx = req_states.get_context()
        if req_ctx is None:
            raise RuntimeError("request context is not initialized")

        req_state = req_ctx.state

        solved = self.container.solve(
            dependant,
            scopes=self.default_scopes,
        )

        try:
            result = await self.container.execute_async(
                solved,
                executor=self._executor,
                state=req_state,
                values=self.get_di_execute_values(),
            )
        except Exception as err:
            logger.exception(
                "! Exception caught while injecting dependencies",
                extra=dict(dependant=dependant, exception_type=type(err).__name__),
            )
            raise

        return result
