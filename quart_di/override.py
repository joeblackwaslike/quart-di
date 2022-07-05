import inspect
from contextlib import ExitStack
from types import TracebackType
from typing import Any, List, Optional, Type

from di.container import Container
from di.dependant import Dependant
from di.api.providers import DependencyProvider
from di.api.dependencies import DependantBase

from quart_di.compat import get_type


__all__ = ("DependencyOverrideManager",)


class DependencyOverrideManager:
    _stacks: List[ExitStack]

    def __init__(self, container: Container) -> None:
        self._container = container
        self._stacks = []

    def __setitem__(self, target: DependencyProvider, replacement: DependencyProvider) -> None:
        def hook(
            param: Optional[inspect.Parameter],
            dependant: DependantBase[Any],
        ) -> Optional[DependantBase[Any]]:
            if not isinstance(dependant, Dependant):
                return None
            scope = dependant.scope
            dep = Dependant(
                replacement,
                scope=scope,
                use_cache=dependant.use_cache,
                wire=dependant.wire,
                sync_to_thread=dependant.sync_to_thread,
            )
            if param is not None and param.annotation is not param.empty:
                type_ = get_type(param)
                if type_ is target:
                    return dep
            if dependant.call is not None and dependant.call is target:
                return dep
            return None

        cm = self._container.bind(hook)
        if self._stacks:
            self._stacks[-1].enter_context(cm)

    def __enter__(self) -> "DependencyOverrideManager":
        self._stacks.append(ExitStack().__enter__())
        return self

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        return self._stacks.pop().__exit__(__exc_type, __exc_value, __traceback)
