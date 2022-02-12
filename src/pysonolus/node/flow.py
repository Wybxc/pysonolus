"""This module defines the CFG nodes.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple, TypeVar, Union, final

from pysonolus.typings import Numbers, TNodeFunctionName

T = TypeVar('T')


@dataclass(init=True, eq=True, frozen=True)
class Expr():
    """CFG node. """

    def __init__(self):
        raise NotImplementedError

    def apply(self, func: Callable[[T], T]) -> Expr:
        return self

    def __add__(self, other: Expr) -> Expr:
        return F.Add(self, other)

    def __sub__(self, other: Expr) -> Expr:
        return F.Subtract(self, other)

    def __mul__(self, other: Expr) -> Expr:
        return F.Multiply(self, other)

    def __truediv__(self, other: Expr) -> Expr:
        return F.Divide(self, other)

    def __floordiv__(self, other: Expr) -> Expr:
        return F.Floor(self / other)

    def __mod__(self, other: Expr) -> Expr:
        return F.Mod(self, other)

    def __pow__(self, other: Expr) -> Expr:
        return F.Power(self, other)

    def __neg__(self) -> Expr:
        return F.Value(0) - self

    def __pos__(self) -> Expr:
        return self

    def __lt__(self, other: Expr) -> Expr:
        return F.Less(self, other)

    def __le__(self, other: Expr) -> Expr:
        return F.LessOr(self, other)

    # No __eq__ and __ne__, because they are implemented by dataclasses to
    # compare the fields.

    # def __eq__(self, other: Block) -> Block:
    #     return F.Equal(self, other)

    # def __ne__(self, other: Block) -> Block:
    #     return F.NotEqual(self, other)

    def __gt__(self, other: Expr) -> Expr:
        return F.Greater(self, other)

    def __ge__(self, other: Expr) -> Expr:
        return F.GreaterOr(self, other)


@dataclass(init=True, eq=True, frozen=True)
@final
class ValueExpr(Expr):
    """Value. """
    value: float

    @staticmethod
    def true(node: Expr) -> bool:
        return isinstance(node, ValueExpr) and node.value != 0

    @staticmethod
    def false(node: Expr) -> bool:
        return isinstance(node, ValueExpr) and node.value == 0

    def __str__(self) -> str:
        return str(self.value)


@dataclass(init=True, eq=True, frozen=True)
@final
class FunctionExpr(Expr):
    """Function call. """
    name: TNodeFunctionName
    args: List[Expr]

    def __str__(self) -> str:
        args = ', '.join(map(str, self.args))
        return f"{self.name}({args})"

    def apply(self, func: Callable[[T], T]) -> Expr:
        return FunctionExpr(self.name, [func(arg) for arg in self.args])


@dataclass(init=True, eq=True, frozen=True)
@final
class RefExpr(Expr):
    """Variable reference."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(init=True, eq=True, frozen=True)
@final
class GetExpr(Expr):
    """Get pointer value. """
    block: int
    index: int
    offset: Expr

    def __str__(self) -> str:
        return f"Get({self.block}, {self.index}, {self.offset})"

    def apply(self, func: Callable[[T], T]) -> Expr:
        return GetExpr(self.block, self.index, func(self.offset))


@dataclass(init=True, eq=True, frozen=True)
class Statement():
    """Statement. """

    def __init__(self):
        raise NotImplementedError

    def apply(self, func: Callable[[T], T]) -> Statement:
        raise NotImplementedError


@dataclass(init=True, eq=True, frozen=True)
@final
class AssignStatement(Statement):
    """Variable assignment."""
    name: str
    value: Expr
    mutable: bool = True

    def __str__(self) -> str:
        if self.mutable:
            return f"{self.name} := {self.value}"
        return f"{self.name} = {self.value}"

    def apply(self, func: Callable[[T], T]) -> AssignStatement:
        return AssignStatement(self.name, func(self.value))


@dataclass(init=True, eq=True, frozen=True)
@final
class SetStatement(Statement):
    """Set pointer value. """
    block: int
    index: int
    offset: Expr
    value: Expr

    def __str__(self) -> str:
        return f"Set({self.block}, {self.index}, {self.offset}, {self.value})"

    def apply(self, func: Callable[[T], T]) -> SetStatement:
        return SetStatement(
            self.block, self.index, func(self.offset), func(self.value)
        )


@dataclass(eq=True, frozen=True)
class Flow():
    """Control flow. """

    def inner(self) -> str:
        return str(self)

    def attach(self, flow: Flow) -> Flow:
        raise NotImplementedError

    def set_result(self, result: str) -> Flow:
        raise NotImplementedError

    def apply(self, func: Callable[[T], T]) -> Flow:
        raise NotImplementedError


@dataclass(init=True, eq=True, frozen=True)
@final
class ExecuteFlow(Flow):
    """Execute block. """
    nodes: List[Union[Expr, Statement]]
    next: Optional[Flow] = None

    def inner(self) -> str:
        inner = '\n'.join(map(str, self.nodes)) + ';'
        if self.next:
            inner += '\n' + self.next.inner()
        return inner

    def __str__(self):
        return '{\n' + textwrap.indent(self.inner(), ' ' * 4) + '\n}'

    def attach(self, flow: Flow) -> Flow:
        if self.next:
            next = self.next.attach(flow)
        else:
            if isinstance(flow, ExecuteFlow):
                return ExecuteFlow(self.nodes + flow.nodes, flow.next)
            next = flow
        return ExecuteFlow(self.nodes, next)

    def set_result(self, result: str) -> Flow:
        if self.next:
            return ExecuteFlow(self.nodes, self.next.set_result(result))
        last = self.nodes[-1]
        if isinstance(last, Statement):
            return ExecuteFlow(
                self.nodes + [F.Assign(result, F.Value(0))], None
            )
        return ExecuteFlow(self.nodes[:-1] + [F.Assign(result, last)])

    def apply(self, func: Callable[[T], T]) -> ExecuteFlow:
        return ExecuteFlow(
            [func(node) for node in self.nodes],
            self.next and func(self.next),
        )


@dataclass(init=True, eq=True, frozen=True)
@final
class SwitchFlow(Flow):
    result: str
    """Name of the variable that stores the result. """
    condition: Expr
    cases: List[Tuple[Expr, Flow]]
    default: Optional[Flow] = None
    next: Optional[Flow] = None

    def __str__(self):
        cases = textwrap.indent(
            '\n'.join(f"{case} -> {body}" for case, body in self.cases),
            ' ' * 4
        )
        default = textwrap.indent(
            f"default -> {self.default}" if self.default else '', ' ' * 4
        )
        return f"{self.result} = switch {self.condition} {{\n{cases}\n{default}\n}};" + (
            f'\n{self.next.inner()}' if self.next else ''
        )

    def attach(self, flow: Flow) -> Flow:
        if self.next:
            next = self.next.attach(flow)
        else:
            next = flow
        return SwitchFlow(
            self.result, self.condition, self.cases, self.default, next
        )

    def set_result(self, result: str) -> Flow:
        if self.next:
            return SwitchFlow(
                self.result, self.condition, self.cases, self.default,
                self.next.set_result(result)
            )
        return self.attach(
            ExecuteFlow([F.Assign(result, RefExpr(self.result))])
        )

    def apply(self, func: Callable[[T], T]) -> SwitchFlow:
        cases = [func(case) for case, _ in self.cases]
        return SwitchFlow(
            self.result,
            func(self.condition),
            [(case, func(body)) for case, (_, body) in zip(cases, self.cases)],
            func(self.default) if self.default else None,
            self.next and func(self.next),
        )


@dataclass(init=True, eq=True, frozen=True)
@final
class LoopFlow(Flow):
    condition: Expr
    body: Flow
    next: Optional[Flow] = None

    def __str__(self):
        return f"while {self.condition} do {self.body};" + (
            f'\n{self.next.inner()}' if self.next else ''
        )

    def attach(self, flow: Flow) -> Flow:
        if self.next:
            next = self.next.attach(flow)
        else:
            next = flow
        return LoopFlow(self.condition, self.body, next)

    def set_result(self, result: str) -> Flow:
        return self

    def apply(self, func: Callable[[T], T]) -> LoopFlow:
        return LoopFlow(
            func(self.condition),
            func(self.body),
            self.next and func(self.next),
        )


class FunctionMetaClass(type):
    """Metaclass for Functions."""

    def __getattr__(cls, name: TNodeFunctionName) -> Callable[..., Expr]:

        def create_function_node(*nodes: Expr) -> FunctionExpr:
            return FunctionExpr(name, list(nodes))

        return create_function_node


@final
class Functions(metaclass=FunctionMetaClass):
    """Functions to build node."""

    @staticmethod
    def Value(value: Any) -> ValueExpr:
        if isinstance(value, Numbers):
            return ValueExpr(float(value))
        else:
            raise TypeError(f"Unsupported constant type: {type(value)}")

    true = ValueExpr(1.)

    false = ValueExpr(0.)

    @staticmethod
    def Ref(name: str) -> RefExpr:
        return RefExpr(name)

    @staticmethod
    def Assign(
        name: str, value: Expr, mutable: bool = True
    ) -> AssignStatement:
        return AssignStatement(name, value, mutable)

    @staticmethod
    def Get(block: int, index: int, offset: Optional[Expr] = None) -> GetExpr:
        return GetExpr(block, index, offset or F.Value(0))

    @staticmethod
    def Set(
        block: int,
        index: int,
        offset: Optional[Expr] = None,
        *,
        value: Expr
    ) -> SetStatement:
        return SetStatement(block, index, offset or F.Value(0), value)


F = Functions

__all__ = [
    'Expr',
    'ValueExpr',
    'FunctionExpr',
    'RefExpr',
    'Statement',
    'AssignStatement',
    'GetExpr',
    'SetStatement',
    'Flow',
    'ExecuteFlow',
    'SwitchFlow',
    'LoopFlow',
    'Functions',
]
