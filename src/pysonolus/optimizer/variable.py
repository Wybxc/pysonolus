from collections import defaultdict
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Set, TypeVar, Union

from pysonolus.anonymous import anonymous
from pysonolus.node.flow import Functions as F
from pysonolus.node.flow import *
from pysonolus.optimizer.core import Optimizer, OptimizerWithContext
from pysonolus.optimizer.elimination import UnusedVariableElimination
from pysonolus.utils import union

T = TypeVar('T', bound=Union[Flow, Statement, Expr])


class SingleAssignTransform(OptimizerWithContext, dependencies=[]):
    """Rename variables to possibly transform program into single-assign style."""

    @dataclass(frozen=False)
    class Context(OptimizerWithContext.Context):
        alias: Dict[str, str] = field(default_factory=dict)

    def optimize_ExecuteFlow(
        self, flow: ExecuteFlow, context: Context
    ) -> Flow:
        blocks: List[Union[Statement, Expr]] = []
        for block in flow.nodes:
            block = self.optimize(block, context)

            if isinstance(block, AssignStatement):
                if block.name not in context.alias:
                    context.alias[block.name] = block.name
                else:
                    alias = anonymous()
                    context.alias[block.name] = alias
                    block = F.Assign(alias, block.value)

            blocks.append(block)

        return ExecuteFlow(
            blocks, flow.next and self.optimize(flow.next, context)
        )

    def optimize_RefExpr(self, expr: RefExpr, context: Context) -> Expr:
        if expr.name in context.alias:
            return F.Ref(context.alias[expr.name])
        return expr

    def optimize_SwitchFlow(self, flow: SwitchFlow, context: Context) -> Flow:
        condition = self.optimize(flow.condition, context)
        cases = [self.optimize(case, context) for case, _ in flow.cases]
        flows = [body for _, body in flow.cases]
        if flow.default:
            flows.append(flow.default)
        bodies: List[Flow] = []
        contexts: List[SingleAssignTransform.Context] = []
        for node in flows:
            context_new = copy.deepcopy(context)
            node = self.optimize(node, context_new)
            contexts.append(context_new)
            bodies.append(node)
        # For newly added names and modified names, use phi function to determine the value.
        modified = union(set(c.alias.items())
                         for c in contexts) - set(context.alias.items())
        phi = set(name for name, alias in modified if name != alias)
        for name, alias in modified:
            if name == alias:
                context.alias[name] = name
        # phi[name] = [c.alias.get(name, name) for c in contexts]
        result = SwitchFlow(
            flow.result,
            condition,
            list(zip(cases, bodies)),
            bodies[-1] if flow.default else None,
        )
        if phi:
            cond = anonymous()
            result = ExecuteFlow(
                [F.Assign(cond, condition)],
                SwitchFlow(
                    flow.result,
                    F.Ref(cond),
                    list(zip(cases, bodies)),
                    bodies[-1] if flow.default else None,
                )
            )
            for name in phi:
                alias = anonymous()
                values = [F.Ref(c.alias.get(name, name)) for c in contexts]
                result = result.attach(
                    SwitchFlow(
                        alias,
                        F.Ref(cond),
                        [
                            (case, ExecuteFlow([value]))
                            for case, value in zip(cases, values)
                        ],
                        ExecuteFlow(
                            [F.Ref(contexts[-1].alias.get(name, name))]
                        ) if flow.default else None,
                    )
                )
                context.alias[name] = alias

        if flow.next:
            return result.attach(self.optimize(flow.next, context))
        else:
            return result


def is_pure(block: Expr, pure: Set[str]) -> bool:
    if isinstance(block, ValueExpr):
        return True
    elif isinstance(block, RefExpr):
        return block.name in pure
    elif isinstance(block, FunctionExpr):
        if block.name in (
            "Random", "RandomInteger", "Draw", "DrawCurvedL", "DrawCurvedR",
            "DrawCurvedLR", "DrawCurvedB", "DrawCurvedT", "DrawCurvedBT",
            "Play", "PlayScheduled", "Spawn", "SpawnParticleEffect",
            "MoveParticleEffect", "DestroyParticleEffect", "DebugPause",
            "DebugLog"
        ):
            return False
        return all(is_pure(arg, pure) for arg in block.args)
    elif isinstance(block, GetExpr):
        return False
    else:
        raise NotImplementedError(f"{block}")


class VariableInline(
    Optimizer, dependencies=[UnusedVariableElimination, SingleAssignTransform]
):
    """Inline variables into RefExpr. Only variables that be assigned
    once and reference once will be inlined."""
    assign_count: Dict[str, int]
    """Number of times a variable is assigned."""
    ref_count: Dict[str, int]
    """Number of times a variable is referenced."""
    values: Dict[str, Expr]
    """Values of variables."""

    def __init__(self, flow: Flow):
        self.assign_count = defaultdict(int)
        self.ref_count = defaultdict(int)
        self.values = {}
        self.analyze(flow)

    def analyze(self, node: T) -> T:
        if isinstance(node, AssignStatement):
            self.assign_count[node.name] += 1
        elif isinstance(node, RefExpr):
            self.ref_count[node.name] += 1
        elif isinstance(node, SwitchFlow):
            self.assign_count[node.result] += 1
        node.apply(self.analyze)
        return node

    def optimize_AssignStatement(
        self, assign: AssignStatement
    ) -> AssignStatement:
        if (
            self.assign_count[assign.name] == 1
            and self.ref_count[assign.name] == 1
        ):
            self.values[assign.name] = assign.value
        return assign.apply(self.optimize)

    def optimize_RefExpr(self, expr: RefExpr) -> Expr:
        if expr.name in self.values:
            return self.values[expr.name].apply(self.optimize)
        return expr


class AssignmentStaticization(Optimizer, dependencies=[SingleAssignTransform]):
    """Make assignments immutable, if possible. """

    count: Dict[str, int]
    """Number of times the variable has been assigned. """
    pure: Set[str]
    """Whether a name is an immutable variable referring to a pure function. """

    def __init__(self, flow: Flow):
        self.count = {}
        self.pure = set()
        self.analyze(flow)

    def analyze(self, node: T) -> T:
        if isinstance(node, AssignStatement):
            if node.name in self.count:
                self.count[node.name] += 1
            else:
                self.count[node.name] = 1
        node.apply(self.analyze)
        return node

    def optimize_AssignStatement(
        self, assign: AssignStatement
    ) -> AssignStatement:
        if not assign.mutable:
            self.pure.add(assign.name)
            return assign
        if self.count[assign.name] == 1:
            if is_pure(assign.value, self.pure):
                self.pure.add(assign.name)
                return F.Assign(assign.name, assign.value, mutable=False)
        return assign
