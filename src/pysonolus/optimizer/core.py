from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import (
    ClassVar, Iterable, List, Optional, Set, Type, TypeVar, Union
)

from pysonolus.node.flow import *
from pysonolus.post_init import post_init


@lru_cache(maxsize=None)
def depend_on(a: Type[Optimizer], b: Type[Optimizer]) -> bool:
    """If a depends on b directly or indirectly."""
    if a == b:
        return True

    for dep in a.dependencies:
        if depend_on(dep, b):
            return True

    return False


@post_init
def clear_depend_cache():
    depend_on.cache_clear()


T = TypeVar('T', bound=Union[Flow, Statement, Expr])


class Optimizer():
    """Base class for optimizers.

    Resolve dependencies between optimizers, and demtermine the order of
    optimizers being applied.
    """
    dependencies: ClassVar[Set[Type[Optimizer]]] = set()
    """Optimizers that this optimizer depends on. """
    topological_order: ClassVar[List[Type[Optimizer]]] = []
    """Optimizers in topological order. """

    def __init_subclass__(
        cls,
        dependencies: Optional[Iterable[Type[Optimizer]]] = None,
    ):
        """Register optimizer class. Only subclasses with dependencies
        should be registered.
        """

        if dependencies is not None:
            cls.dependencies = set(dependencies)
            l = -1
            for i, c in enumerate(cls.topological_order):
                if depend_on(cls, c):
                    l = i
            cls.topological_order.insert(l + 1, cls)

    def __init__(self, node: Flow):
        pass

    def optimize(self, node: T) -> T:
        """Optimize a flow. """
        node_type = node.__class__.__name__
        optimizer = getattr(self, f"optimize_{node_type}", None)
        if optimizer:
            return optimizer(node)
        else:
            return node.apply(self.optimize)


class OptimizerWithContext(Optimizer):
    """Base class for optimizers that need a context."""

    @dataclass(frozen=False)
    class Context():
        """Context of the optimizer.

        For optimizer with a context, optimize function has typed `(Flow,
        Context) -> (Flow, Context)` and `(Block, Context) -> (Block,
        Context)`. However, to make it compatible with `Flow.apply`, context
        is mutable, and its changes are made directly by modifying the context
        object.
        """

    def optimize(self, node: T, context: Optional[Context] = None) -> T:
        """Optimize a flow. """
        context = context or self.Context()
        node_type = node.__class__.__name__
        optimizer = getattr(self, f"optimize_{node_type}", None)
        if optimizer:
            return optimizer(node, context)
        else:
            return node.apply(lambda b: self.optimize(b, context))

    # optimize function for a specific flow type need to be implemented in
    # subclasses, because they need to know how to pass context through
    # the flow.


def optimize(flow: Flow):
    while True:
        optimized = flow
        for optimizer in Optimizer.topological_order:
            optimized = optimizer(optimized).optimize(optimized)
        if optimized == flow:
            break
        flow = optimized
        yield flow


__all__ = ['Optimizer', 'optimize']
