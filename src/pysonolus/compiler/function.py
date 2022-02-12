from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Callable, Dict, List, Optional

from pysonolus.inspect import QualifiedName
from pysonolus.node.dispatch import dispatch
from pysonolus.node.IR import Functions as F
from pysonolus.node.IR import *


@dataclass
class CompiledFunction():
    """Compiled function. """
    name: QualifiedName
    """Name of the function, written as `{module}.{function}`. Additionally,
    when module name is `__main__`, it won't be included."""
    params: ParameterList
    """Parameters."""
    node: Node
    """Compiled node."""
    def param(self, name: str) -> str:
        """Get parameter name from function name and parameter name
        when calling the function.

        When calling, arguments are passed by name in the format:
        `{func_name}${param_name}`, with all `.` replaced with `$`.
        As for `*args`, they will be named as `{func_name}$args$1`,
        `{func_name}$args$2`, etc.
        """
        return f"{self.name}${name}".replace('.', '$')

    def call(self, args: List[Node], kwargs: Dict[str, Node]) -> Node:
        """Call this function with given arguments, while calling is
        just inlining.

        Calling convention can be found in `CompiledFunction.param`.
        """
        kwargs = kwargs.copy()
        for param, arg in zip(self.params.params, args):
            kwargs[param.name] = arg
        if len(args) > len(self.params.params):
            if self.params.va_args:
                for i, arg in enumerate(args[len(self.params.params):]):
                    kwargs[f"{self.params.va_args}${i+1}"] = arg
            else:
                raise TypeError(f"Too many arguments for {self.name}")
        for param in self.params.params:
            if param.name not in kwargs:
                if param.default:
                    kwargs[param.name] = param.default
                else:
                    raise TypeError(
                        f"Function {self.name} missing parameter {param.name}"
                    )
        if len(args) > len(self.params.params):
            node = self._resolve_starred(
                self.node,
                len(args) - len(self.params.params)
            )
        else:
            node = self.node
        return F.Execute(
            *[
                F.Assign(self.param(name), value)
                for name, value in kwargs.items()
            ], node
        )

    @dispatch
    def _resolve_starred(self, node: Node, arg_count: int) -> Node:
        """Resolve StarredNode.

        `StarredNode(nested=False)`, compiled from `*args`, will be replaced by
        listing arguments in the order they are passed.

        `StarredNode(nested=True)`, compiled from `...`, will be replaced by
        nested function call, e.g. `f(a, f(b, c))`.
        """
        ...

    def _resolve_nested(
        self, arg_count: int, unit: Callable[[Node, Node], Node]
    ) -> Node:
        return reduce(
            lambda a, b: unit(b, a), (
                F.Ref(self.param(f"{self.params.va_args}${i+1}"))
                for i in reversed(range(arg_count))
            )
        )

    @_resolve_starred.register(FunctionNode)
    def _resolve_starred_FunctionNode(
        self, node: FunctionNode, arg_count: int
    ) -> Node:
        if len(node.args) == 0:
            return node
        star = node.args[-1]
        if isinstance(star, StarredNode):
            if star.nested:
                nested = self._resolve_nested(
                    arg_count,
                    lambda left, right: FunctionNode(node.name, [left, right])
                )
                if len(node.args) == 1:
                    return nested
                else:
                    return FunctionNode(node.name, [node.args[0], nested])
            else:
                return FunctionNode(
                    node.name, node.args[:-1] + [
                        F.Ref(self.param(f"{self.params.va_args}${i+1}"))
                        for i in range(arg_count)
                    ]
                )
        else:
            return FunctionNode(
                node.name,
                [self._resolve_starred(arg, arg_count) for arg in node.args]
            )

    @_resolve_starred.register(CallNode)
    def _resolve_starred_CallNode(
        self, node: CallNode, arg_count: int
    ) -> Node:
        if len(node.args) == 0:
            return node
        star = node.args[-1]
        if isinstance(star, StarredNode):
            if star.nested:
                nested = self._resolve_nested(
                    arg_count, lambda left, right: F.
                    Call(node.name, [left, right], node.kwargs)
                )
                if len(node.args) == 1:
                    return nested
                else:
                    return F.Call(
                        node.name, [node.args[0], nested], node.kwargs
                    )
            else:
                return F.Call(
                    node.name, node.args[:-1] + [
                        F.Ref(self.param(f"{self.params.va_args}${i+1}"))
                        for i in range(arg_count)
                    ], node.kwargs
                )
        else:
            return F.Call(
                node.name,
                [self._resolve_starred(arg, arg_count) for arg in node.args],
                node.kwargs
            )

    @_resolve_starred.register(StarredNode)
    def _resolve_starred_StarredNode(
        self, node: StarredNode, arg_count: int
    ) -> Node:
        raise TypeError(f"StarredNode not resolved")

    def __str__(self) -> str:
        return f"({self.params}) -> {self.node}"


@dataclass
class CompiledOverloadedFunction(CompiledFunction):
    """Compiled overloaded function.

    This is a list of compiled functions.
    """
    overloads: List[CompiledFunction]

    @staticmethod
    def overload(func: CompiledFunction, overloaded: CompiledFunction):
        """Create an overloaded function.

        The first function will be used as the base function.
        """
        if isinstance(func, CompiledOverloadedFunction):
            func.overloads.append(overloaded)
            return func
        else:
            return CompiledOverloadedFunction(
                func.name, func.params, func.node, [overloaded]
            )

    def call(self, args: List[Node], kwargs: Dict[str, Node]) -> Node:
        try:
            return super().call(args, kwargs)
        except TypeError as err:
            for overload in self.overloads:
                try:
                    return overload.call(args, kwargs)
                except TypeError as e:
                    err = e
            raise err from None


@dataclass
class Parameter():
    """Parameter. """
    name: str
    default: Optional[Node] = None

    def __str__(self) -> str:
        if self.default:
            return f"{self.name} = {self.default}"
        return self.name


@dataclass
class ParameterList():
    """Parameter list. """
    params: List[Parameter]
    va_args: Optional[str] = None

    def __str__(self) -> str:
        return ', '.join(str(param) for param in self.params
                         ) + (f", *{self.va_args}" if self.va_args else "")


__all__ = ["CompiledFunction", "Parameter"]
