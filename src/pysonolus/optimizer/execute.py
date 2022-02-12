from dataclasses import replace

from pysonolus.node.flow import *
from pysonolus.optimizer.core import Optimizer
from pysonolus.optimizer.switch import SwitchElimination


class MergeExecute(Optimizer, dependencies=[SwitchElimination]):
    """Merge two adjacent `ExecuteFlow`s."""
    def optimize_ExecuteFlow(self, flow: ExecuteFlow) -> Flow:
        if isinstance(flow.next, ExecuteFlow):
            return ExecuteFlow(
                flow.nodes + flow.next.nodes, flow.next.next
                and self.optimize(flow.next.next)
            )
        return replace(flow, next=flow.next and self.optimize(flow.next))


class RemoveEmptyExecute(Optimizer, dependencies=[SwitchElimination]):
    """Remove empty flows."""
    def optimize_ExecuteFlow(self, flow: ExecuteFlow) -> Flow:
        if not flow.nodes:
            if flow.next:
                return self.optimize(flow.next)
        if flow.next and isinstance(
            flow.next, ExecuteFlow
        ) and not flow.next.nodes:
            return ExecuteFlow(
                flow.nodes,
                flow.next.next and self.optimize(flow.next.next),
            )
        return replace(flow, next=flow.next and self.optimize(flow.next))

    def optimize_SwitchFlow(self, flow: SwitchFlow) -> Flow:
        if flow.next and isinstance(
            flow.next, ExecuteFlow
        ) and not flow.next.nodes:
            return SwitchFlow(
                flow.result,
                flow.condition,
                [(case, self.optimize(body)) for case, body in flow.cases],
                flow.default and self.optimize(flow.default),
                flow.next.next and self.optimize(flow.next.next),
            )
        return replace(flow, next=flow.next and self.optimize(flow.next))

    def optimize_LoopFlow(self, flow: LoopFlow) -> Flow:
        if flow.next and isinstance(
            flow.next, ExecuteFlow
        ) and not flow.next.nodes:
            return LoopFlow(
                flow.condition,
                self.optimize(flow.body),
                flow.next.next and self.optimize(flow.next.next),
            )
        return replace(flow, next=flow.next and self.optimize(flow.next))
