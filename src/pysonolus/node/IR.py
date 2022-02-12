"""This module defines the IR nodes.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import (
    Any, Callable, Dict, Iterable, List, Optional, Sequence, Union, cast,
    final, overload
)

from pysonolus.inspect import QualifiedName
# from pysonolus.pointer.core import Pointer
from pysonolus.typings import Numbers, TNodeFunctionName


@dataclass(init=True, eq=True, frozen=True)
class Node():
    """IR node. """

    def __init__(self):
        raise NotImplementedError

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return self

    def __add__(self, other: Node) -> Node:
        return F.Add(self, other)

    def __sub__(self, other: Node) -> Node:
        return F.Subtract(self, other)

    def __mul__(self, other: Node) -> Node:
        return F.Multiply(self, other)

    def __truediv__(self, other: Node) -> Node:
        return F.Divide(self, other)

    def __floordiv__(self, other: Node) -> Node:
        return F.Floor(self / other)

    def __mod__(self, other: Node) -> Node:
        return F.Mod(self, other)

    def __pow__(self, other: Node) -> Node:
        return F.Power(self, other)

    def __neg__(self) -> Node:
        return F.Value(0) - self

    def __pos__(self) -> Node:
        return self

    def __lt__(self, other: Node) -> Node:
        return F.Less(self, other)

    def __le__(self, other: Node) -> Node:
        return F.LessOr(self, other)

    # No __eq__ and __ne__, because they are implemented by dataclasses to
    # compare the fields.

    # def __eq__(self, other: Node) -> Node:
    #     return F.Equal(self, other)

    # def __ne__(self, other: Node) -> Node:
    #     return F.NotEqual(self, other)

    def __gt__(self, other: Node) -> Node:
        return F.Greater(self, other)

    def __ge__(self, other: Node) -> Node:
        return F.GreaterOr(self, other)


@dataclass(init=True, eq=True, frozen=True)
@final
class ValueNode(Node):
    """Value. """
    value: float

    @staticmethod
    def true(node: Node) -> bool:
        return isinstance(node, ValueNode) and node.value != 0

    @staticmethod
    def false(node: Node) -> bool:
        return isinstance(node, ValueNode) and node.value == 0

    def __str__(self) -> str:
        return str(self.value)


@dataclass(init=True, eq=True, frozen=True)
@final
class FunctionNode(Node):
    """Function call. """
    name: TNodeFunctionName
    args: List[Node]

    def __str__(self) -> str:
        args = ', '.join(map(str, self.args))
        return f"{self.name}({args})"

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return FunctionNode(self.name, [func(arg) for arg in self.args])


@dataclass(init=True, eq=True, frozen=True)
@final
class RefNode(Node):
    """Variable reference."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(init=True, eq=True, frozen=True)
@final
class AssignNode(Node):
    """Variable assignment."""
    name: str
    value: Node

    def __str__(self) -> str:
        return f"{self.name} := {self.value}"

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return F.Assign(self.name, func(self.value))


@dataclass(init=True, eq=True, frozen=True)
@final
class GetNode(Node):
    """Get pointer value. """
    block: int
    index: int
    offset: Node


@dataclass(init=True, eq=True, frozen=True)
@final
class SetNode(Node):
    """Set pointer value. """
    block: int
    index: int
    offset: Node
    value: Node


@dataclass(init=True, eq=True, frozen=True)
@final
class ExecuteNode(Node):
    """Execute a sequence of nodes. """
    nodes: Sequence[Node]

    @staticmethod
    def empty(node: Node) -> bool:
        return isinstance(node, ExecuteNode) and len(node.nodes) == 0

    def __str__(self) -> str:
        return '[\n' + textwrap.indent(
            ', \n'.join(map(str, self.nodes)), ' ' * 4
        ) + '\n]'

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return F.Execute(func(node) for node in self.nodes)


@dataclass(init=True, eq=True, frozen=True)
@final
class CallNode(Node):
    """Call a Python defined function, which will be inlined when linking. """
    name: QualifiedName
    """Name of the called function, written as is."""
    args: List[Node]
    kwargs: Dict[str, Node]

    def __str__(self) -> str:
        args = ', '.join(map(str, self.args))
        if self.kwargs:
            kwargs = ', '.join(f"{k}={v}" for k, v in self.kwargs.items())
            return f"{self.name}({args}, {kwargs})"
        return f"{self.name}({args})"

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return F.Call(
            self.name,
            [func(arg) for arg in self.args],
            {k: func(v)
             for k, v in self.kwargs.items()},
        )


@dataclass(init=True, eq=True, frozen=True)
@final
class StarredNode(Node):
    """Placeholder for *args.

    StarredNode can only appear as an single argument of a CallNode.
    """
    nested: bool = True

    def __str__(self) -> str:
        return "..."


@dataclass(init=True, eq=True, frozen=True)
@final
class IfNode(Node):
    """Conditional node. """
    condition: Node
    then: Node
    orelse: Node

    def __str__(self) -> str:
        return f"If({self.condition}, {self.then}, {self.orelse})"

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return F.If(func(self.condition), func(self.then), func(self.orelse))


@dataclass(init=True, eq=True, frozen=True)
@final
class WhileNode(Node):
    """Conditional node. """
    condition: Node
    body: Node

    def __str__(self) -> str:
        return f"While({self.condition}, {self.body})"

    def apply(self, func: Callable[[Node], Node]) -> Node:
        return F.While(func(self.condition), func(self.body))


class FunctionMetaClass(type):
    """Metaclass for Functions."""

    def __getattr__(cls, name: TNodeFunctionName) -> Callable[..., Node]:

        def create_function_node(*nodes: Node) -> FunctionNode:
            if any(ExecuteNode.empty(node) for node in nodes):
                raise ValueError(
                    f"Cannot create a function node with empty node in arguments"
                )
            return FunctionNode(name, list(nodes))

        return create_function_node


@final
class Functions(metaclass=FunctionMetaClass):
    """Functions to build node."""

    empty = ExecuteNode([])

    @staticmethod
    def Value(value: Any) -> ValueNode:
        if isinstance(value, Numbers):
            return ValueNode(float(value))
        else:
            raise TypeError(f"Unsupported constant type: {type(value)}")

    true = ValueNode(1.)

    false = ValueNode(0.)

    @staticmethod
    def Ref(name: str) -> RefNode:
        return RefNode(name)

    @staticmethod
    def Assign(name: str, value: Node) -> Node:
        if isinstance(value, ExecuteNode):
            return F.Execute(
                *value.nodes[:-1], F.Assign(name, value.nodes[-1])
            )
        return AssignNode(name, value)

    @staticmethod
    def Call(
        name: QualifiedName,
        args: Iterable[Node],
        kwargs: Optional[Dict[str, Node]] = None
    ) -> CallNode:
        return CallNode(name, list(args), kwargs or {})

    @staticmethod
    def Starred(nested: bool = True) -> StarredNode:
        return StarredNode(nested)

    @staticmethod
    def If(condition: Node, then: Node, orelse: Node) -> Node:
        if ExecuteNode.empty(then):
            then = F.true
        elif ExecuteNode.empty(orelse):
            orelse = F.false
        return IfNode(condition, then, orelse)

    @overload
    @staticmethod
    def Execute(*node: Node) -> Node:
        ...

    @overload
    @staticmethod
    def Execute(nodes: Iterable[Node]) -> Node:
        ...

    @staticmethod
    def Execute(*nodes: Union[Node, Iterable[Node]]) -> Node:
        if len(nodes) == 1:
            if isinstance(nodes[0], Node):
                return nodes[0]
            else:
                return F.Execute(*nodes[0])
        result: List[Node] = []
        for node in nodes:
            node = cast(Node, node)
            if ExecuteNode.empty(node):
                continue
            elif isinstance(node, ExecuteNode):
                result.extend(node.nodes)
            else:
                result.append(node)
        return ExecuteNode(result)

    @staticmethod
    def While(condition: Node, body: Node) -> WhileNode:
        return WhileNode(condition, body)

    @staticmethod
    def And(condition: Node, *args: Node) -> Node:
        if not args:
            return condition
        return F.If(condition, F.And(*args), F.false)

    @staticmethod
    def Or(condition: Node, *args: Node) -> Node:
        if not args:
            return condition
        return F.If(condition, F.true, F.Or(*args))


F = Functions

__all__ = [
    'Node',
    'ValueNode',
    'RefNode',
    'AssignNode',
    'GetNode',
    'SetNode',
    'ExecuteNode',
    'FunctionNode',
    'IfNode',
    'WhileNode',
    'CallNode',
    'StarredNode',
    'Functions',
]
