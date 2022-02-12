"""Transform IR nodes into control-flow graph. """

from typing import Iterable, List, Optional, Union

from pysonolus.anonymous import anonymous
from pysonolus.node.flow import *
from pysonolus.node.IR import Functions as F
from pysonolus.node.IR import *


def transform(node: Node) -> Flow:
    """Transform IR nodes into control-flow graph. """
    return Transformer(node).flow


class Transformer():
    root: Node
    flow: Flow

    def __init__(self, root: Node):
        self.root = root
        self.flow = ExecuteFlow([])
        block = self.transform(ExecuteNode([root]))
        if block:
            self.append([block])

    def append(self, blocks: Union[Iterable[Union[Statement, Expr]], Flow]):
        if isinstance(blocks, Flow):
            self.flow = self.flow.attach(blocks)
        else:
            self.flow = self.flow.attach(ExecuteFlow(list(blocks)))

    def lift(self, value: Expr) -> RefExpr:
        """Lift a value to ensure evaluation order. """
        name = anonymous()
        self.append([AssignStatement(name, value)])
        return RefExpr(name)

    def transform(self, node: Node) -> Optional[Expr]:
        node_type = node.__class__.__name__
        method = getattr(self, f'transform_{node_type}', None)
        if method:
            return method(node)
        else:
            raise NotImplementedError(f'{node_type} is not supported.')

    def transform_ValueNode(self, node: ValueNode) -> Expr:
        return ValueExpr(node.value)

    def transform_RefNode(self, node: RefNode) -> Expr:
        return RefExpr(node.name)

    def transform_AssignNode(self, node: AssignNode) -> None:
        value = self.transform(node.value)
        if not value:
            raise TypeError(f'{node.value} returns None.')
        self.append([AssignStatement(node.name, value)])

    def transform_GetNode(self, node: GetNode) -> Expr:
        offset = self.transform(node.offset)
        if not offset:
            raise TypeError(f'{node.offset} returns None.')
        return GetExpr(node.block, node.index, self.lift(offset))

    def transform_SetNode(self, node: SetNode) -> Statement:
        value = self.transform(node.value)
        if not value:
            raise TypeError(f'{node.value} returns None.')
        offset = self.transform(node.offset)
        if not offset:
            raise TypeError(f'{node.offset} returns None.')
        return SetStatement(
            node.block, node.index, self.lift(offset), self.lift(value)
        )

    def transform_ExecuteNode(
        self,
        execute_node: ExecuteNode,
    ) -> Optional[Expr]:
        result = None
        for node in execute_node.nodes:
            if result:
                self.append([result])
            result = self.transform(node)
        return result

    def transform_FunctionNode(self, node: FunctionNode) -> Expr:
        args: List[Expr] = []
        for arg in node.args:
            value = self.transform(arg)
            if not value:
                raise TypeError(f'{arg} returns None.')
            args.append(self.lift(value))
        return FunctionExpr(node.name, args)

    def transform_IfNode(self, node: IfNode) -> Expr:
        cond = self.transform(node.condition)
        if not cond:
            raise TypeError(f'{node.condition} returns None.')
        result = anonymous()
        then = transform(node.then)
        orelse = transform(node.orelse)
        self.append(SwitchFlow(result, cond, [(ValueExpr(0.), orelse)], then))
        return RefExpr(result)

    def transform_WhileNode(self, node: WhileNode) -> None:
        cond = anonymous()
        condition = transform(F.Assign(cond, node.condition))
        body = transform(node.body).attach(condition)
        self.append(condition)
        self.append(LoopFlow(RefExpr(cond), body))
