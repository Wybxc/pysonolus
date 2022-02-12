from pysonolus.node.flow import *
from pysonolus.optimizer.constant import ConstantFold
from pysonolus.optimizer.core import Optimizer


class SwitchElimination(Optimizer, dependencies=[ConstantFold]):
    """Eliminate switches whose condition is constant."""

    def optimize_SwitchFlow(self, flow: SwitchFlow) -> Flow:
        if isinstance(flow.condition, ValueExpr):
            static = True  # whether the switch can be statically evaluated
            result = None
            for case, body in flow.cases:
                if isinstance(case, ValueExpr):
                    if case.value == flow.condition.value:
                        result = body.set_result(flow.result)
                        break
                else:
                    static = False
            else:
                # static, but no match
                if static and flow.default:
                    result = flow.default.set_result(flow.result)
            if result:
                if flow.next:
                    next = self.optimize(flow.next)
                    result = result.attach(next)
                return result
        return flow.apply(self.optimize)


class BranchMerge(Optimizer, dependencies=[ConstantFold]):
    """Merge branches with the same body. """

    def optimize_SwitchFlow(self, flow: SwitchFlow) -> Flow:
        result = None
        if len(flow.cases) == 0:
            if not flow.default:
                raise ValueError("Empty switch")
            result = flow.default
        else:
            first = flow.cases[0][1]
            for _, body in flow.cases[1:]:
                if first != body:
                    break
            else:
                if not flow.default or flow.default == first:
                    result = first.set_result(flow.result)
        if result:
            if flow.next:
                next = self.optimize(flow.next)
                result = result.attach(next)
            return result
        return flow.apply(self.optimize)


class SwitchFold(Optimizer, dependencies=[ConstantFold]):
    """Eliminate switch not necessary, like `If(a, 1, 0)`. """

    def optimize_SwitchFlow(self, flow: SwitchFlow) -> Flow:
        if len(flow.cases) == 1:
            case, body = flow.cases[0]
            if isinstance(case, ValueExpr) and case.value == 0:
                if (
                    isinstance(body, ExecuteFlow) and len(body.nodes) == 1
                    and body.next is None
                ):
                    value = body.nodes[0]
                    if isinstance(value, ValueExpr) and value == 0:
                        pass

        return flow.apply(self.optimize)