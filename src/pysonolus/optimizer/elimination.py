from typing import List, Set, TypeVar, Union

from pysonolus.node.flow import *
from pysonolus.optimizer.constant import ConstantFold
from pysonolus.optimizer.core import Optimizer

T = TypeVar('T', bound=Union[Flow, Statement, Expr])


class UnusedVariableElimination(Optimizer, dependencies=[ConstantFold]):
    """Eliminate unused variables. """

    refs: Set[str]

    def __init__(self, flow: Flow):
        self.refs = set()
        self.detect_refs(flow)

    def detect_refs(self, node: T) -> T:
        if isinstance(node, RefExpr):
            self.refs.add(node.name)
        else:
            node.apply(self.detect_refs)
        return node

    def optimize_ExecuteFlow(self, flow: ExecuteFlow) -> Flow:
        blocks: List[Union[Statement, Expr]] = []
        for block in flow.nodes:
            if isinstance(
                block, AssignStatement
            ) and block.name not in self.refs:
                pass
            else:
                blocks.append(block)
        return ExecuteFlow(blocks, flow.next and self.optimize(flow.next))


class UselessValueElimination(
    Optimizer, dependencies=[UnusedVariableElimination]
):
    """Eliminate useless values and references. """
    def optimize_ExecuteFlow(self, flow: ExecuteFlow) -> Flow:
        if not flow.nodes:
            return flow.apply(self.optimize)

        blocks: List[Union[Statement, Expr]] = []
        for i, block in enumerate(flow.nodes):
            if flow.next is None and i == len(flow.nodes) - 1:
                pass
            elif isinstance(block, (ValueExpr, RefExpr)):
                continue
            blocks.append(block)
        return ExecuteFlow(blocks, flow.next and self.optimize(flow.next))
