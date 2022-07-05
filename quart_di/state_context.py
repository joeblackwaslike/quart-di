import logging
import threading
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from di.container import Container
from di.container import ContainerState
from pydantic import BaseModel
from pydantic import Field
from quart import Quart
from werkzeug.local import LocalProxy

from quart_di.datastructures import ThreadLocalStack
from quart_di.util import get_task_id


logger = logging.getLogger(__name__)

_app_state_stack = ThreadLocalStack()
_req_state_stack = ThreadLocalStack()

current_app_state = LocalProxy(lambda: _ctx_lookup([_app_state_stack]))
current_req_state = LocalProxy(lambda: _ctx_lookup([_req_state_stack]))

__all__ = (
    "ContainerStateContext",
    "ContainerStateController",
    "app_states",
    "req_states",
    "create_and_push_app_context",
    "create_and_push_req_context",
)


def _ctx_lookup(ctx_stacks: List[ThreadLocalStack], name: Optional[str] = None) -> Any:
    top = None
    for ctx_stack in ctx_stacks:
        top = ctx_stack.top
        if top is not None:
            break
    if top is None:
        raise RuntimeError(f"Attempt to access {name} outside of a relevant context")
    if name is not None:
        return getattr(top, name)
    return top


class ContainerStateContext(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    meta: Dict[str, Any] = Field(default_factory=dict)
    container: Container
    scope: str
    scope_cm: Optional[Any] = None
    state: ContainerState
    app: Quart

    @classmethod
    def with_metadata(cls, **kwargs):
        kwargs.setdefault("meta", {})
        kwargs["meta"].setdefault("task_id", get_task_id())
        kwargs["meta"].setdefault("thread_id", threading.get_ident())
        return cls(**kwargs)


class ContainerStateController:
    def __init__(self, scope, stack):
        self.scope = scope
        self.stack = stack

    async def create_context(
        self,
        current_state,
        container,
        app,
    ):
        scope_cm = current_state.enter_scope(self.scope)
        state = await scope_cm.__aenter__()

        return ContainerStateContext.with_metadata(
            container=container,
            scope=self.scope,
            scope_cm=scope_cm,
            state=state,
            app=app,
        )

    def push_context(self, state_ctx):
        self.stack.push(state_ctx)

    def get_context(self):
        return self.stack.top

    async def pop_context(self):
        ctx = self.get_context()
        if ctx is None:
            logger.warning(f"{self.scope} context popped handler nothing to do, stack is empty")
            return

        try:
            await ctx.scope_cm.__aexit__(None, None, None)
        except Exception:
            logger.exception("error raised while tearing down app context")

        self.stack.pop()


app_states = ContainerStateController("app", _app_state_stack)
req_states = ContainerStateController("request", _req_state_stack)


async def create_and_push_app_context(app, container, container_state):
    app_ctx = await app_states.create_context(
        current_state=container_state,
        container=container,
        app=app,
    )
    app_states.push_context(app_ctx)


async def create_and_push_req_context(app, container):
    app_ctx = app_states.get_context()
    if app_ctx is None:
        raise RuntimeError("Cannot open request state context without app state context")

    req_ctx = await req_states.create_context(
        current_state=app_ctx.state,
        container=container,
        app=app,
    )
    req_states.push_context(req_ctx)
