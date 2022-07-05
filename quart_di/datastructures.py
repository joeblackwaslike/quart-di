import threading
from typing import Any
from typing import Iterator
from typing import Tuple

from werkzeug.local import LocalProxy


__all__ = ("ThreadLocal", "ThreadLocalStack")


class ThreadLocal:
    def __init__(self):
        object.__setattr__(self, "_storage", threading.local())

    def __iter__(self) -> Iterator[Tuple[int, Any]]:
        return iter(self._storage.__dict__.items())

    def __call__(self, proxy: str) -> LocalProxy:
        """Create a proxy for a name."""
        return LocalProxy(self, proxy)

    def __release_local__(self) -> None:
        self._storage.__dict__.clear()

    def __getattr__(self, name: str) -> Any:
        values = self._storage.__dict__
        try:
            return values[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value: Any) -> None:
        values = self._storage.__dict__
        values[name] = value

    def __delattr__(self, name: str) -> None:
        values = self._storage.__dict__
        try:
            del values[name]
        except KeyError as e:
            raise AttributeError(name) from e


class ThreadLocalStack:
    def __init__(self):
        self._local = ThreadLocal()
        self._local.stack = []

    def __release_local__(self) -> None:
        self._local.__release_local__()
        self._local.stack = []

    def __call__(self) -> LocalProxy:
        def _lookup() -> Any:
            rv = self.top
            if rv is None:
                raise RuntimeError("object unbound")
            return rv

        return LocalProxy(_lookup)

    def push(self, obj: Any) -> None:
        """Pushes a new item to the stack."""
        self._local.stack.append(obj)

    def pop(self) -> Any:
        """Removes the topmost item from the stack.

        This will return the old value or `None` if thestack was already empty.
        """
        if not self._local.stack:
            return None
        else:
            return self._local.stack.pop()

    @property
    def top(self) -> Any:
        """The topmost item on the stack.

        If the stack is empty,  `None` is returned."""
        try:
            return self._local.stack[-1]
        except (AttributeError, IndexError):
            return None
