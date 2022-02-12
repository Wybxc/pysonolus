import copy
import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Union

from pysonolus.functions.math import sign
from pysonolus.node.flow import Functions as F
from pysonolus.node.flow import *
from pysonolus.optimizer.core import Optimizer, OptimizerWithContext
from pysonolus.utils import intersection


class ConstantPropagation(OptimizerWithContext, dependencies=[]):
    """Constant propagation optimizer.

    This optimizer will find variables that are assigned to a constant value
    and replace their references with the value.
    """
    @dataclass(frozen=False)
    class Context(OptimizerWithContext.Context):
        constants: Dict[str, float] = field(default_factory=dict)

    def optimize_ExecuteFlow(
        self, flow: ExecuteFlow, context: Context
    ) -> Flow:
        blocks: List[Union[Statement, Expr]] = []
        for node in flow.nodes:
            node = self.optimize(node, context)

            if isinstance(node, AssignStatement):
                if isinstance(node.value, ValueExpr):
                    context.constants[node.name] = node.value.value
                elif node.name in context.constants:
                    if node.mutable:
                        del context.constants[node.name]
                    else:
                        raise TypeError(
                            f'Cannot assign to immutable variable {node.name}.'
                        )

            blocks.append(node)
        return ExecuteFlow(
            blocks, flow.next and self.optimize(flow.next, context)
        )

    def optimize_RefExpr(self, block: RefExpr, context: Context) -> Expr:
        if block.name in context.constants:
            return ValueExpr(context.constants[block.name])
        return block

    def optimize_SwitchFlow(self, flow: SwitchFlow, context: Context) -> Flow:
        condition = self.optimize(flow.condition, context)
        cases = [self.optimize(case, context) for case, _ in flow.cases]
        flows = [body for _, body in flow.cases]
        if flow.default:
            flows.append(flow.default)
        bodies: List[Flow] = []
        contexts: List[ConstantPropagation.Context] = []
        for node in flows:
            context_new = copy.deepcopy(context)
            node = self.optimize(node, context_new)
            contexts.append(context_new)
            bodies.append(node)
        # Those values are same after each branches can be considered as constants.
        context.constants = dict(
            intersection(set(c.constants.items()) for c in contexts)
        )
        return SwitchFlow(
            flow.result,
            condition,
            list(zip(cases, bodies)),
            bodies[-1] if flow.default else None,
            flow.next and self.optimize(flow.next, context),
        )


class ConstantFold(Optimizer, dependencies=[ConstantPropagation]):
    """Constant fold optimizer.

    This optimizer recognizes and evaluates constant expressions to
    minify Block tree.
    """
    def optimize_FunctionExpr(self, block: FunctionExpr) -> Expr:
        args = [self.optimize(arg) for arg in block.args]
        fold = getattr(self, f"fold_{block.name}", None)
        if fold:
            return fold(*args)
        else:
            return FunctionExpr(block.name, args)

    def _fold_quad(
        self,
        *nodes: Expr,
        fold: Literal["Add", "Multiply"],
    ) -> List[Expr]:
        """Fold constants in Quadratic arithmetic.
        Constant (if any) is put to the first of the result.
        """
        constant = 0. if fold == "Add" else 1.
        result: List[Expr] = []
        for node in nodes:
            if isinstance(node, ValueExpr):
                if fold == "Add":
                    constant += node.value
                else:
                    constant *= node.value
            else:
                result.append(node)
        if constant:
            result.insert(0, F.Value(constant))
        return result or [F.Value(0.) if fold == "Add" else F.Value(1.)]

    def fold_Add(self, *nodes: Expr) -> Expr:
        result = self._fold_quad(*nodes, fold="Add")
        if len(result) == 1:
            return result[0]
        return F.Add(*result)

    def fold_Subtract(self, *nodes: Expr) -> Expr:
        head = nodes[0]
        if len(nodes) == 1:
            return head
        tail = self._fold_quad(*nodes[1:], fold="Add")
        if isinstance(head, ValueExpr) and isinstance(tail[0], ValueExpr):
            head = F.Value(head.value - tail[0].value)
            tail = tail[1:]
            if len(tail) == 0:
                return head
        return F.Sub(head, *tail)

    def fold_Multiply(self, *nodes: Expr) -> Expr:
        result = self._fold_quad(*nodes, fold="Multiply")
        if len(result) == 1:
            return result[0]
        return F.Multiply(*result)

    def fold_Divide(self, *nodes: Expr) -> Expr:
        head = nodes[0]
        if len(nodes) == 1:
            return head
        tail = self._fold_quad(*nodes[1:], fold="Multiply")
        if isinstance(head, ValueExpr) and isinstance(tail[0], ValueExpr):
            head = F.Value(head.value / tail[0].value)
            tail = tail[1:]
            if len(tail) == 0:
                return head
        return F.Divide(head, *tail)

    def fold_Min(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(min(a.value, b.value))
        return F.Min(a, b)

    def fold_Max(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(max(a.value, b.value))
        return F.Max(a, b)

    def fold_Less(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(a.value < b.value)
        return a < b

    def fold_LessOr(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(a.value <= b.value)
        return a <= b

    def fold_Greater(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(a.value > b.value)
        return a > b

    def fold_GreaterOr(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(a.value >= b.value)
        return a >= b

    def fold_Equal(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(a.value == b.value)
        return F.Equal(a, b)

    def fold_NotEqual(self, a: Expr, b: Expr) -> Expr:
        if isinstance(a, ValueExpr) and isinstance(b, ValueExpr):
            return F.Value(a.value != b.value)
        return F.NotEqual(a, b)

    def fold_Not(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(not node.value)
        return F.Not(node)

    def fold_Negate(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(-node.value)
        return -node

    def fold_Abs(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(abs(node.value))
        return F.Abs(node)

    def fold_Sign(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(sign(node.value))
        return F.Sign(node)

    def fold_Floor(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(math.floor(node.value))
        return F.Floor(node)

    def fold_Ceil(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(math.ceil(node.value))
        return F.Ceil(node)

    def fold_Round(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(round(node.value))
        return F.Round(node)

    def fold_Trunc(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(math.trunc(node.value))
        return F.Trunc(node)

    def fold_Exp(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(math.exp(node.value))
        return F.Exp(node)

    def fold_Log(self, node: Expr) -> Expr:
        if isinstance(node, ValueExpr):
            return F.Value(math.log(node.value))
        return F.Log(node)

    def fold_If(self, condition: Expr, then: Expr, orelse: Expr) -> Expr:
        if ValueExpr.true(condition):
            return then
        elif ValueExpr.false(condition):
            return orelse
        return F.If(condition, then, orelse)

    def fold_And(self, *args: Expr) -> Expr:
        nodes: List[Expr] = []
        for node in args:
            if ValueExpr.true(node):
                continue
            if ValueExpr.false(node):
                break
            nodes.append(node)
        else:
            if len(nodes) == 0:
                return F.true
            return F.And(*nodes)
        if len(args) == 0:
            return F.false
        return F.And(*args)

    def fold_Or(self, *args: Expr) -> Expr:
        nodes: List[Expr] = []
        for node in args:
            if ValueExpr.false(node):
                continue
            if ValueExpr.true(node):
                break
            nodes.append(node)
        else:
            if len(nodes) == 0:
                return F.false
            return F.Or(*nodes)
        if len(args) == 0:
            return F.true
        return F.Or(*args)
