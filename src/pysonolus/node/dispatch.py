from __future__ import annotations

import functools
from typing import (
    TYPE_CHECKING, Any, Callable, Dict, Generic, Protocol, Type, TypeVar
)

from typing_extensions import Self

T = TypeVar('T')


class Node(Protocol):
    def apply(self, func: Callable[[T], T]) -> Self:
        ...


TNode = TypeVar("TNode", bound=Node)
DispatchFunction = Callable[..., TNode]


def _dispatch(func: DispatchFunction[TNode]) -> DispatchFunction[TNode]:
    """Decorator to make a single-dispatch method that depends on the type
    of the node."""

    registry: Dict[Type[TNode], DispatchFunction[TNode]] = {}

    def register(node_type: Type[TNode]):
        def wrapper(wrapped: DispatchFunction[TNode]):
            registry[node_type] = wrapped
            return wrapped

        return wrapper

    def auto_dispatch(self: Any, node: TNode, *args: Any, **kwargs: Any):
        return node.apply(lambda x: wrapped(self, x, *args, **kwargs))

    def dispatch(node: TNode) -> DispatchFunction[TNode]:
        return registry.get(node.__class__) or auto_dispatch

    def wrapped(self: Any, node: TNode, *args: Any, **kwargs: Any) -> TNode:
        return dispatch(node)(self, node, *args, **kwargs)

    wrapped.register = register  # type: ignore
    functools.update_wrapper(wrapped, func)
    return wrapped


if TYPE_CHECKING:

    class Dispatcher(Generic[TNode]):
        """Dispatcher function, for type check only."""
        def register(
            self, node_type: Type[TNode]
        ) -> Callable[[DispatchFunction[TNode]], DispatchFunction[TNode]]:
            ...

        def __call__(self, node: TNode, *args: Any, **kwargs: Any) -> TNode:
            ...

    def dispatch(func: DispatchFunction[TNode]) -> Dispatcher[TNode]:
        ...
else:
    dispatch = _dispatch

__all__ = ['dispatch']
