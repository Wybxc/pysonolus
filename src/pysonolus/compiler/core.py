from __future__ import annotations

import ast
from typing import Any, Callable, Dict, List, Optional, cast

from pysonolus.anonymous import anonymous
from pysonolus.compiler.context import (
    BinOpContext, BlockContext, BlockLevel, Context, UnaryOpContext
)
from pysonolus.compiler.function import Parameter, ParameterList
from pysonolus.inspect import RelativeName, getsource
from pysonolus.node.IR import ExecuteNode
from pysonolus.node.IR import Functions as F
from pysonolus.node.IR import Node
from pysonolus.pointer.core import Pointer, StructMetaclass
from pysonolus.typings import Numbers


class Compiler():
    """Compiler, convert Python AST to Sonolus node. """

    @staticmethod
    def parse(func: Callable[..., Any]) -> ast.FunctionDef:
        source = getsource(func)
        return cast(ast.FunctionDef, ast.parse(source).body[0])

    @staticmethod
    def compile(node: ast.AST, context: Context) -> Node:
        """Compile an AST into a Sonolus node.

        Dispatches to the appropriate __compile_*__ method.
        """
        if not node:
            raise ValueError("Node is None")
        compile_func = cast(
            Optional[Callable[[ast.AST, Context], Node]],
            getattr(Compiler, f'__compile_{node.__class__.__name__}__', None)
        )
        if compile_func:
            return compile_func(node, context)

        raise NotImplementedError(
            f'Unsupported node type: {node.__class__.__name__}'
        )

    @staticmethod
    def analyze_parameters(
        args: ast.arguments, context: Context
    ) -> ParameterList:
        if args.kwarg:
            raise NotImplementedError("*kwargs not supported")

        params: List[Parameter] = []
        for arg in args.posonlyargs:
            params.append(Parameter(arg.arg))
        defaults = len(args.defaults)
        if defaults == 0:
            for arg in args.args:
                params.append(Parameter(arg.arg))
        else:
            for arg in args.args[:-defaults]:
                params.append(Parameter(arg.arg))
            for arg, default in zip(args.args[-defaults:], args.defaults):
                params.append(
                    Parameter(arg.arg, Compiler.compile(default, context))
                )
        if len(args.kwonlyargs) != len(args.kw_defaults):
            raise RuntimeError()
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            params.append(
                Parameter(
                    arg.arg,
                    Compiler.compile(default, context) if default else None
                )
            )

        if args.vararg:
            return ParameterList(params, args.vararg.arg)
        else:
            return ParameterList(params)

    @staticmethod
    def __compile_FunctionDef__(
        func_def: ast.FunctionDef, context: Context
    ) -> Node:
        with context.use(BlockContext):
            return Compiler._compile_block(
                func_def.body, context, 'Returnable'
            )

    @staticmethod
    def __compile_Expr__(expr: ast.Expr, context: Context) -> Node:
        return Compiler.compile(expr.value, context)

    @staticmethod
    def __compile_Pass__(_: ast.Pass, context: Context) -> Node:
        return F.empty

    @staticmethod
    def _may_return(c: BlockContext, node: Node, context: Context) -> Node:
        if c.may_return:
            if not c.return_flag:
                raise ValueError("No return flag")
            return_flag = F.Ref(c.return_flag)
            if c.return_value:
                return_value = F.Ref(c.return_value)
            else:
                return_value = F.empty
            result = anonymous()
            if not ExecuteNode.empty(node):
                return F.Execute(
                    F.Assign(result, node),
                    F.If(return_flag, return_value, F.Ref(result))
                )
            else:
                return F.And(return_flag, return_value)
        else:
            return node

    @staticmethod
    def _compile_block(
        body: List[ast.stmt], context: Context, level: BlockLevel
    ) -> Node:
        c = context.enter(BlockContext)
        nodes: List[Node] = []
        for i, stat in enumerate(body):
            nodes.append(Compiler.compile(stat, context))
            if c.may_return:
                with context.use(BlockContext):
                    after = Compiler._compile_block(
                        body[i + 1:], context, 'None'
                    )
                nodes.append(Compiler._may_return(c, after, context))
                break
        context.exit(BlockContext)

        if c.may_return and level != 'Returnable':
            context.may_return = True
            context.return_flag = c.return_flag
            context.return_value = c.return_value

        return F.Execute(*nodes)

    @staticmethod
    def __compile_Return__(ret: ast.Return, context: Context) -> Node:
        """Return statements are not allowed in Node IR,
        so they are compiled into an `If` that wraps the following nodes
        and decides whether to return or continue executing.

        When compiler meets a return statement, it sets the `may_return`,
        which will indicate the upper frame compiler to wrap following
        statements in an `If`. The return statement is compiled into setting
        the `return_flag` and `return_value` variables, and the `If `can read
        them to make decision.
        """
        context.may_return = True
        if ret.value:
            flag_name = anonymous()
            context.return_flag = flag_name
            var_name = anonymous()
            context.return_value = var_name
            return F.Execute(
                F.Assign(var_name, Compiler.compile(ret.value, context)),
                F.Assign(flag_name, F.true),
            )
        else:
            flag_name = anonymous()
            context.return_flag = flag_name
            return F.Assign(flag_name, F.true)

    @staticmethod
    def __compile_If__(if_: ast.If, context: Context) -> Node:
        test = Compiler.compile(if_.test, context)

        may_return = False
        return_flag_then = F.false
        return_flag_else = F.false
        return_value_then = F.empty
        return_value_else = F.empty
        with context.use(BlockContext) as c:
            body = Compiler._compile_block(if_.body, context, 'None')
            body = Compiler._may_return(c, body, context)
            if c.may_return:
                if not c.return_flag:
                    raise ValueError("No return flag")
                may_return = True
                return_flag_then = F.Ref(c.return_flag)
                if c.return_value:
                    return_value_then = F.Ref(c.return_value)

        with context.use(BlockContext) as c:
            orelse = Compiler._compile_block(if_.orelse, context, 'None')
            orelse = Compiler._may_return(c, orelse, context)
            if c.may_return:
                if not c.return_flag:
                    raise ValueError("No return flag")
                may_return = True
                return_flag_else = F.Ref(c.return_flag)
                if c.return_value:
                    return_value_else = F.Ref(c.return_value)

        if may_return:
            context.may_return = True
            flag_name = anonymous()
            context.return_flag = flag_name
            value_name = anonymous()
            context.return_value = value_name
            return F.Execute(
                F.Assign(flag_name, F.false), F.Assign(value_name, F.false),
                F.If(
                    test,
                    F.Execute(
                        F.Assign(value_name, body),
                        F.Assign(flag_name, return_flag_then),
                        F.And(
                            return_flag_then,
                            F.Assign(value_name, return_value_then)
                        ),
                    ) if not ExecuteNode.empty(body) else F.empty,
                    F.Execute(
                        F.Assign(value_name, orelse),
                        F.Assign(flag_name, return_flag_else),
                        F.And(
                            return_flag_else,
                            F.Assign(value_name, return_value_else)
                        ),
                    ) if not ExecuteNode.empty(orelse) else F.empty,
                )
            )

        return F.If(test, body, orelse)

    @staticmethod
    def __compile_BinOp__(bin_op: ast.BinOp, context: Context) -> Node:
        left = Compiler.compile(bin_op.left, context)
        right = Compiler.compile(bin_op.right, context)
        with context.use(BinOpContext) as c:
            c.left = left
            c.right = right
            return Compiler.compile(bin_op.op, context)

    @staticmethod
    def __compile_Add__(_: ast.Add, context: Context) -> Node:
        return F.Add(context.left, context.right)

    @staticmethod
    def __compile_Sub__(_: ast.Sub, context: Context) -> Node:
        return F.Subtract(context.left, context.right)

    @staticmethod
    def __compile_Mult__(_: ast.Mult, context: Context) -> Node:
        return F.Multiply(context.left, context.right)

    @staticmethod
    def __compile_Div__(_: ast.Div, context: Context) -> Node:
        return F.Divide(context.left, context.right)

    @staticmethod
    def __compile_Mod__(_: ast.Mod, context: Context) -> Node:
        return F.Mod(context.left, context.right)

    @staticmethod
    def __compile_Pow__(_: ast.Pow, context: Context) -> Node:
        """Caution: the Power node is left associative."""
        return F.Power(context.left, context.right)

    @staticmethod
    def __compile_UnaryOp__(unary_op: ast.UnaryOp, context: Context) -> Node:
        operand = Compiler.compile(unary_op.operand, context)
        with context.use(UnaryOpContext) as c:
            c.operand = operand
            return Compiler.compile(unary_op.op, context)

    @staticmethod
    def __compile_UAdd__(_: ast.UAdd, context: Context) -> Node:
        return F.Value(context.operand)

    @staticmethod
    def __compile_USub__(_: ast.USub, context: Context) -> Node:
        return F.Subtract(F.Value(0), context.operand)

    @staticmethod
    def __compile_Not__(_: ast.Not, context: Context) -> Node:
        return F.Not(context.operand)

    @staticmethod
    def __compile_IfExp__(if_exp: ast.IfExp, context: Context) -> Node:
        test = Compiler.compile(if_exp.test, context)
        body = Compiler.compile(if_exp.body, context)
        orelse = Compiler.compile(if_exp.orelse, context)
        return F.If(test, body, orelse)

    @staticmethod
    def __compile_Compare__(compare: ast.Compare, context: Context) -> Node:
        """Expand nested comparisons, like 2 < 3 < 4.

        Calculation order is important. Expressions in nested comparisons are
        evaluated from left to right, and won't be evaluated if the left-most
        comparison is false. Each expression will only be evaluated once.
        """
        left = compare.left
        result = F.true
        for op, right in zip(compare.ops, compare.comparators):
            left_alias = anonymous()
            left_assign = F.Assign(left_alias, Compiler.compile(left, context))
            right_alias = anonymous()
            right_assign = F.Assign(
                right_alias, Compiler.compile(right, context)
            )
            with context.use(BinOpContext) as c:
                c.left = F.Ref(left_alias)
                c.right = F.Ref(right_alias)
                result = F.And(
                    result,
                    F.Execute(
                        left_assign,
                        right_assign,
                        Compiler.compile(op, context),
                    )
                )
                left = right
        return result

    @staticmethod
    def __compile_Eq__(_: ast.Eq, context: Context) -> Node:
        return F.Equal(context.left, context.right)

    @staticmethod
    def __compile_NotEq__(_: ast.NotEq, context: Context) -> Node:
        return F.NotEqual(context.left, context.right)

    @staticmethod
    def __compile_Lt__(_: ast.Lt, context: Context) -> Node:
        return F.Less(context.left, context.right)

    @staticmethod
    def __compile_LtE__(_: ast.LtE, context: Context) -> Node:
        return F.LessOr(context.left, context.right)

    @staticmethod
    def __compile_Gt__(_: ast.Gt, context: Context) -> Node:
        return F.Greater(context.left, context.right)

    @staticmethod
    def __compile_GtE__(_: ast.GtE, context: Context) -> Node:
        return F.GreaterOr(context.left, context.right)

    @staticmethod
    def _resolve_expr(name: ast.expr, context: Context):
        if not context.module:
            raise RuntimeError("Attribute not in context")
        return RelativeName(context.module, name).eval()

    @staticmethod
    def _resolve_pointer(name: ast.expr,
                         context: Context) -> Optional[Pointer]:
        if isinstance(name, ast.Name):
            obj = Compiler._resolve_expr(name, context)
            if isinstance(obj, Pointer):
                return obj
            elif isinstance(obj, StructMetaclass):
                return obj.base_ptr()
        elif isinstance(name, ast.Attribute):
            obj = Compiler._resolve_pointer(name.value, context)
            return getattr(obj, name.attr)
        elif isinstance(name, ast.Subscript):
            if obj := Compiler._resolve_pointer(name.value, context):
                if not isinstance(name.slice, ast.Index):
                    raise TypeError("Only integer indexing is supported")
                index = Compiler.compile(name.slice.value, context)
                return obj.of(index)

    @staticmethod
    def _assign(target: ast.expr, value: Node, context: Context) -> Node:
        if context.name is None:
            raise RuntimeError("Assignment outside of function")
        if isinstance(target, ast.Name):
            return F.Assign(context.name.var(target.id), value)
        elif isinstance(target, ast.Attribute):
            pointer = Compiler._resolve_pointer(target, context)
            if not pointer:
                raise TypeError("Attribute not supported")
            return pointer.set(value)
        raise TypeError("Assignment to non-name not supported")

    @staticmethod
    def __compile_Assign__(assign: ast.Assign, context: Context) -> Node:
        if len(assign.targets) > 1:
            raise TypeError("Multiple assignment not supported")
        target = assign.targets[0]
        value = Compiler.compile(assign.value, context)
        return Compiler._assign(target, value, context)

    @staticmethod
    def __compile_AugAssign__(assign: ast.AugAssign, context: Context) -> Node:
        target = assign.target
        value = Compiler.compile(assign.value, context)
        with context.use(BinOpContext) as c:
            c.left = Compiler.compile(target, context)
            c.right = value
            return Compiler._assign(
                target, Compiler.compile(assign.op, context), context
            )

    @staticmethod
    def __compile_AnnAssign__(assign: ast.AnnAssign, context: Context) -> Node:
        if not assign.value:
            raise TypeError("Value required for annotation assignment")
        target = assign.target
        value = Compiler.compile(assign.value, context)
        return Compiler._assign(target, value, context)

    @staticmethod
    def __compile_Name__(name: ast.Name, context: Context) -> Node:
        if not context.name:
            raise RuntimeError("Name not in context")
        ref = name.id
        return F.Ref(context.name.var(ref))

    @staticmethod
    def __compile_Attribute__(name: ast.Attribute, context: Context) -> Node:
        pointer = Compiler._resolve_pointer(name, context)
        if not pointer:
            raise TypeError("Attribute not supported")
        return pointer.get()

    @staticmethod
    def __compile_Constant__(constant: ast.Constant, _: Context) -> Node:
        if isinstance(constant.value, Numbers):
            return F.Value(float(constant.value))
        else:
            raise TypeError(
                f"Unsupported constant type: {type(constant.value)}"
            )

    @staticmethod
    def __compile_Call__(call: ast.Call, context: Context) -> Node:
        if not isinstance(call.func, (ast.Name, ast.Attribute)):
            raise TypeError("Call to non-name not supported")
        if not context.module:
            raise RuntimeError("Module not in context")
        name = RelativeName(context.module, call.func)
        args = [Compiler.compile(arg, context) for arg in call.args]
        kwargs = {
            kw.arg: Compiler.compile(kw.value, context)
            for kw in call.keywords
        }
        if None in kwargs:
            raise TypeError("**kwargs is not supported")
        context.calls.add(name)
        return F.Call(name.as_qualified(), args, cast(Dict[str, Node], kwargs))
