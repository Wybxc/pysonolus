"""This module implements pre-compiled functions.

Pre-compiled functions have more features than normal functions,
such as directly use of FunctionNode, and *args and overloading support.
"""
from __future__ import annotations

import ast
import math
from typing import Callable, Dict

from pysonolus.compiler.context import Context
from pysonolus.compiler.core import Compiler
from pysonolus.compiler.function import (
    CompiledFunction, CompiledOverloadedFunction, ParameterList
)
from pysonolus.inspect import QualifiedName
from pysonolus.node.IR import Functions as F
from pysonolus.node.IR import Node, RefNode, StarredNode

_compiled: Dict[QualifiedName, CompiledFunction] = {}


def pre_compile(name: str):
    """Define a pre-compiled function.

    Pre-compiled functions has signature like Python function,
    but only has one return statement, whose value is the compiled node.

    Pre-compiled functions accepts all kinds of parameters except `**kwargs`.
    A special rule is applied to `*args`: use `*args` in code to leave a
    `StarredNode` placeholder, which will be replaced by arguments when inlining,
    while `...` in code will be expanded to nested function calls.

    Overloading is supported. Currently overloaded functions are dispatched by
    number of arguments.
    """
    qualname = QualifiedName(name)

    def wrapper(func: Callable[..., Node]):
        func_def = Compiler.parse(func)
        params = Compiler.analyze_parameters(func_def.args, Context())

        if (
            len(func_def.body) != 1
            or not isinstance(func_def.body[0], ast.Return)
            or not func_def.body[0].value
        ):
            raise TypeError(f"Function {name} must have exactly one statement")

        node_ast = ParamTransformer(qualname,
                                    params).visit(func_def.body[0].value)
        code = compile(
            ast.fix_missing_locations(ast.Expression(node_ast)),
            filename=__name__,
            mode='eval'
        )
        node = eval(
            code, globals(), {
                'RefNode': RefNode,
                'StarredNode': StarredNode
            }
        )

        if qualname not in _compiled:
            _compiled[qualname] = CompiledFunction(qualname, params, node)
        else:  # overload
            overload = CompiledOverloadedFunction.overload(
                _compiled[qualname], CompiledFunction(qualname, params, node)
            )
            _compiled[qualname] = overload
        return func

    return wrapper


def compiled() -> Dict[QualifiedName, CompiledFunction]:
    return _compiled.copy()


class ParamTransformer(ast.NodeTransformer):
    """Walk AST of a node delcaration, transform names to RefNode. """

    def __init__(self, func_name: QualifiedName, params: ParameterList):
        self.func_name = func_name
        self.param_names = {param.name for param in params.params}
        self.va_args_name = params.va_args

    def visit_Name(self, node: ast.Name):
        if node.id in self.param_names:
            return ast.Call(
                func=ast.Name(id='RefNode', ctx=ast.Load()),
                args=[ast.Constant(self.func_name.var(node.id))],
                keywords=[]
            )
        return node

    def visit_Starred(self, node: ast.Starred):
        if isinstance(
            node.value, ast.Name
        ) and node.value.id == self.va_args_name:
            return ast.Call(
                func=ast.Name(id='StarredNode', ctx=ast.Load()),
                args=[ast.Constant(False)],
                keywords=[]
            )
        return node

    def visit_Constant(self, node: ast.Constant):
        if node.value is ...:
            return ast.Call(
                func=ast.Name(id='StarredNode', ctx=ast.Load()),
                args=[ast.Constant(True)],
                keywords=[]
            )
        return node


# region Math


@pre_compile('pysonolus.functions.math.frac')
def pysonolus_math_frac(x: Node) -> Node:
    return F.Frac(x)


@pre_compile('pysonolus.functions.math.sign')
def pysonolus_math_sign(x: Node) -> Node:
    return F.Sign(x)


@pre_compile('pysonolus.functions.math.clamp')
def pysonolus_math_clamp(x: Node, a: Node, b: Node) -> Node:
    return F.Clamp(x, a, b)


@pre_compile('pysonolus.functions.math.lerp')
def pysonolus_math_lerp(a: Node, b: Node, x: Node) -> Node:
    return F.Lerp(a, b, x)


@pre_compile('pysonolus.functions.math.lerp_clamped')
def pysonolus_math_lerp_clamped(a: Node, b: Node, x: Node) -> Node:
    return F.LerpClamped(a, b, x)


@pre_compile('pysonolus.functions.math.unlerp')
def pysonolus_math_unlerp(a: Node, b: Node, x: Node) -> Node:
    return F.Unlerp(a, b, x)


@pre_compile('pysonolus.functions.math.unlerp_clamped')
def pysonolus_math_unlerp_clamped(a: Node, b: Node, x: Node) -> Node:
    return F.UnlerpClamped(a, b, x)


@pre_compile('pysonolus.functions.math.remap')
def pysonolus_math_remap(a: Node, b: Node, c: Node, d: Node, x: Node) -> Node:
    return F.Remap(a, b, c, d, x)


@pre_compile('pysonolus.functions.math.remap_clamped')
def pysonolus_math_remap_clamped(
    a: Node, b: Node, c: Node, d: Node, x: Node
) -> Node:
    return F.RemapClamped(a, b, c, d, x)


@pre_compile('pysonolus.functions.math.smooth_step')
def pysonolus_math_smooth_step(a: Node, b: Node, x: Node) -> Node:
    return F.SmoothStep(a, b, x)


# endregion


# region Random
@pre_compile('pysonolus.functions.random.random')
def pysonolus_random_random(a: Node, b: Node) -> Node:
    return F.Random(a, b)


@pre_compile('pysonolus.functions.random.random_integer')
def pysonolus_random_random_integer(a: Node, b: Node) -> Node:
    return F.RandomInteger(a, b)


@pre_compile('random.Random.random')
def random_random() -> Node:
    return F.Random(F.Value(0), F.Value(1))


@pre_compile('random.Random.randint')
def random_randint(a: Node, b: Node) -> Node:
    return F.RandomInteger(a, b + F.Value(1))


@pre_compile('random.Random.randrange')
def random_randrange(a: Node, b: Node) -> Node:
    return F.RandomInteger(a, b)


@pre_compile('random.Random.randrange')
def random_randrange_3(a: Node, b: Node, c: Node) -> Node:
    return F.RandomInteger(0, F.Floor((b-a) / c) * c) + a


#endregion


# region Engine
@pre_compile('pysonolus.functions.engine.draw')
def pysonolus_engine_draw(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node
) -> Node:
    return F.Draw(id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity)


@pre_compile('pysonolus.functions.engine.draw_curved_left')
def pysonolus_engine_draw_curved_left(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node, n: Node, cxl: Node, cyl: Node
) -> Node:
    return F.DrawCurvedLeft(
        id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity, n, cxl, cyl
    )


@pre_compile('pysonolus.functions.engine.draw_curved_right')
def pysonolus_engine_draw_curved_right(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node, n: Node, cxr: Node, cyr: Node
) -> Node:
    return F.DrawCurvedRight(
        id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity, n, cxr, cyr
    )


@pre_compile('pysonolus.functions.engine.draw_curved_left_right')
def pysonolus_engine_draw_curved_left_right(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node, n: Node, cxl: Node, cyl: Node,
    cxr: Node, cyr: Node
) -> Node:
    return F.DrawCurvedLeftRight(
        id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity, n, cxl, cyl, cxr, cyr
    )


@pre_compile('pysonolus.functions.engine.draw_curved_bottom')
def pysonolus_engine_draw_curved_bottom(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node, n: Node, cxb: Node, cyb: Node
) -> Node:
    return F.DrawCurvedBottom(
        id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity, n, cxb, cyb
    )


@pre_compile('pysonolus.functions.engine.draw_curved_top')
def pysonolus_engine_draw_curved_top(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node, n: Node, cxt: Node, cyt: Node
) -> Node:
    return F.DrawCurvedTop(
        id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity, n, cxt, cyt
    )


@pre_compile('pysonolus.functions.engine.draw_curved_bottom_top')
def pysonolus_engine_draw_curved_bottom_top(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, z: Node, opacity: Node, n: Node, cxb: Node, cyb: Node,
    cxt: Node, cyt: Node
) -> Node:
    return F.DrawCurvedBottomTop(
        id, x1, y1, x2, y2, x3, y3, x4, y4, z, opacity, n, cxb, cyb, cxt, cyt
    )


@pre_compile('pysonolus.functions.engine.play')
def pysonolus_engine_play(id: Node, dist: Node) -> Node:
    return F.Play(id, dist)


@pre_compile('pysonolus.functions.engine.play_scheduled')
def pysonolus_engine_play_scheduled(id: Node, time: Node, dist: Node) -> Node:
    return F.PlayScheduled(id, time, dist)


@pre_compile('pysonolus.functions.engine.spawn')
def pysonolus_engine_spawn(id: Node, *data: Node) -> Node:
    return F.Spawn(id, *data)


@pre_compile('pysonolus.functions.engine.spawn_particle_effect')
def pysonolus_engine_spawn_particle_effect(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node, time: Node, loop: Node
) -> Node:
    return F.SpawnParticleEffect(
        id, x1, y1, x2, y2, x3, y3, x4, y4, time, loop
    )


@pre_compile('pysonolus.functions.engine.move_particle_effect')
def pysonolus_engine_move_particle_effect(
    id: Node, x1: Node, y1: Node, x2: Node, y2: Node, x3: Node, y3: Node,
    x4: Node, y4: Node
) -> Node:
    return F.MoveParticleEffect(id, x1, y1, x2, y2, x3, y3, x4, y4)


@pre_compile('pysonolus.functions.engine.destroy_particle_effect')
def pysonolus_engine_destroy_particle_effect(id: Node) -> Node:
    return F.DestroyParticleEffect(id)


# endregion


# region Easing
@pre_compile('pysonolus.functions.easing.in_quad')
def pysonolus_easing_in_quad(x: Node) -> Node:
    return F.InQuad(x)


@pre_compile('pysonolus.functions.easing.out_quad')
def pysonolus_easing_out_quad(x: Node) -> Node:
    return F.OutQuad(x)


@pre_compile('pysonolus.functions.easing.in_out_quad')
def pysonolus_easing_in_out_quad(x: Node) -> Node:
    return F.InOutQuad(x)


@pre_compile('pysonolus.functions.easing.in_cubic')
def pysonolus_easing_in_cubic(x: Node) -> Node:
    return F.InCubic(x)


@pre_compile('pysonolus.functions.easing.out_cubic')
def pysonolus_easing_out_cubic(x: Node) -> Node:
    return F.OutCubic(x)


@pre_compile('pysonolus.functions.easing.in_out_cubic')
def pysonolus_easing_in_out_cubic(x: Node) -> Node:
    return F.InOutCubic(x)


@pre_compile('pysonolus.functions.easing.in_quart')
def pysonolus_easing_in_quart(x: Node) -> Node:
    return F.InQuart(x)


@pre_compile('pysonolus.functions.easing.out_quart')
def pysonolus_easing_out_quart(x: Node) -> Node:
    return F.OutQuart(x)


@pre_compile('pysonolus.functions.easing.in_out_quart')
def pysonolus_easing_in_out_quart(x: Node) -> Node:
    return F.InOutQuart(x)


@pre_compile('pysonolus.functions.easing.in_quint')
def pysonolus_easing_in_quint(x: Node) -> Node:
    return F.InQuint(x)


@pre_compile('pysonolus.functions.easing.out_quint')
def pysonolus_easing_out_quint(x: Node) -> Node:
    return F.OutQuint(x)


@pre_compile('pysonolus.functions.easing.in_out_quint')
def pysonolus_easing_in_out_quint(x: Node) -> Node:
    return F.InOutQuint(x)


@pre_compile('pysonolus.functions.easing.in_sine')
def pysonolus_easing_in_sine(x: Node) -> Node:
    return F.InSine(x)


@pre_compile('pysonolus.functions.easing.out_sine')
def pysonolus_easing_out_sine(x: Node) -> Node:
    return F.OutSine(x)


@pre_compile('pysonolus.functions.easing.in_out_sine')
def pysonolus_easing_in_out_sine(x: Node) -> Node:
    return F.InOutSine(x)


@pre_compile('pysonolus.functions.easing.in_circ')
def pysonolus_easing_in_circ(x: Node) -> Node:
    return F.InCirc(x)


@pre_compile('pysonolus.functions.easing.out_circ')
def pysonolus_easing_out_circ(x: Node) -> Node:
    return F.OutCirc(x)


@pre_compile('pysonolus.functions.easing.in_out_circ')
def pysonolus_easing_in_out_circ(x: Node) -> Node:
    return F.InOutCirc(x)


@pre_compile('pysonolus.functions.easing.in_expo')
def pysonolus_easing_in_expo(x: Node) -> Node:
    return F.InExpo(x)


@pre_compile('pysonolus.functions.easing.out_expo')
def pysonolus_easing_out_expo(x: Node) -> Node:
    return F.OutExpo(x)


@pre_compile('pysonolus.functions.easing.in_out_expo')
def pysonolus_easing_in_out_expo(x: Node) -> Node:
    return F.InOutExpo(x)


@pre_compile('pysonolus.functions.easing.in_back')
def pysonolus_easing_in_back(x: Node) -> Node:
    return F.InBack(x)


@pre_compile('pysonolus.functions.easing.out_back')
def pysonolus_easing_out_back(x: Node) -> Node:
    return F.OutBack(x)


@pre_compile('pysonolus.functions.easing.in_out_back')
def pysonolus_easing_in_out_back(x: Node) -> Node:
    return F.InOutBack(x)


@pre_compile('pysonolus.functions.easing.in_elastic')
def pysonolus_easing_in_elastic(x: Node) -> Node:
    return F.InElastic(x)


@pre_compile('pysonolus.functions.easing.out_elastic')
def pysonolus_easing_out_elastic(x: Node) -> Node:
    return F.OutElastic(x)


@pre_compile('pysonolus.functions.easing.in_out_elastic')
def pysonolus_easing_in_out_elastic(x: Node) -> Node:
    return F.InOutElastic(x)


@pre_compile('pysonolus.functions.easing.in_bounce')
def pysonolus_easing_in_bounce(x: Node) -> Node:
    return F.InBounce(x)


@pre_compile('pysonolus.functions.easing.out_bounce')
def pysonolus_easing_out_bounce(x: Node) -> Node:
    return F.OutBounce(x)


@pre_compile('pysonolus.functions.easing.in_out_bounce')
def pysonolus_easing_in_out_bounce(x: Node) -> Node:
    return F.InOutBounce(x)


# endregion


# region Debug
@pre_compile('pysonolus.functions.debug.is_debug')
def pysonolus_debug_is_debug() -> Node:
    return F.IsDebug()


@pre_compile('pysonolus.functions.debug.debug_pause')
def pysonolus_debug_debug_pause() -> Node:
    return F.DebugPause()


@pre_compile('pysonolus.functions.debug.debug_log')
def pysonolus_debug_debug_log(message: Node) -> Node:
    return F.DebugLog(message)


# endregion


# region Python Math
@pre_compile('math.ceil')
def math_ceil(x: Node) -> Node:
    return F.Ceil(x)


@pre_compile('math.floor')
def math_floor(x: Node) -> Node:
    return F.Floor(x)


@pre_compile('math.trunc')
def math_trunc(x: Node) -> Node:
    return F.Trunc(x)


@pre_compile('math.degrees')
def math_degrees(x: Node) -> Node:
    return F.Degree(x)


@pre_compile('math.radians')
def math_radians(x: Node) -> Node:
    return F.Radian(x)


@pre_compile('math.sin')
def math_sin(x: Node) -> Node:
    return F.Sin(x)


@pre_compile('math.cos')
def math_cos(x: Node) -> Node:
    return F.Cos(x)


@pre_compile('math.tan')
def math_tan(x: Node) -> Node:
    return F.Tan(x)


@pre_compile('math.sinh')
def math_sinh(x: Node) -> Node:
    return F.Sinh(x)


@pre_compile('math.cosh')
def math_cosh(x: Node) -> Node:
    return F.Cosh(x)


@pre_compile('math.tanh')
def math_tanh(x: Node) -> Node:
    return F.Tanh(x)


@pre_compile('math.asin')
def math_asin(x: Node) -> Node:
    return F.Arcsin(x)


@pre_compile('math.acos')
def math_acos(x: Node) -> Node:
    return F.Arccos(x)


@pre_compile('math.atan')
def math_atan(x: Node) -> Node:
    return F.Arctan(x)


@pre_compile('math.atan2')
def math_atan2(y: Node, x: Node) -> Node:
    return F.Arctan2(y, x)


@pre_compile('math.log')
def math_log(x: Node) -> Node:
    return F.Log(x)


@pre_compile('math.log')
def math_log_2(x: Node, base: Node) -> Node:
    return F.Divide(F.Log(x), F.Log(base))


@pre_compile('math.fmod')
def math_fmod(x: Node, y: Node) -> Node:
    return F.Mod(x, y)


@pre_compile('math.fabs')
def math_fabs(x: Node) -> Node:
    return F.Abs(x)


@pre_compile('math.copysign')
def math_copysign(x: Node, y: Node) -> Node:
    return F.Abs(x) * F.Sign(y)


@pre_compile('math.isclose')
def math_isclose(a: Node, b: Node, rel_tol: Node, abs_tol: Node) -> Node:
    return F.Abs(a - b) <= F.Max(rel_tol * F.Max(F.Abs(a), F.Abs(b)), abs_tol)


@pre_compile('math.isqrt')
def math_isqrt(x: Node) -> Node:
    return F.Floor(F.Sqrt(x))


@pre_compile('math.ldexp')
def math_ldexp(x: Node, i: Node) -> Node:
    return x * F.Value(2)**i


@pre_compile('math.remainder')
def math_remainder(x: Node, y: Node) -> Node:
    return x - F.Round(x / y) * y


@pre_compile('math.exp')
def math_exp(x: Node) -> Node:
    return F.Value(math.e)**x


@pre_compile('math.expm1')
def math_expm1(x: Node) -> Node:
    return F.Value(math.e)**x - F.Value(1)


@pre_compile('math.log1p')
def math_log1p(x: Node) -> Node:
    return F.Log(x + F.Value(1))


@pre_compile('math.log2')
def math_log2(x: Node) -> Node:
    return F.Log(x) / F.Value(math.log(2))


@pre_compile('math.log10')
def math_log10(x: Node) -> Node:
    return F.Log(x) / F.Value(math.log(10))


@pre_compile('math.pow')
def math_pow(x: Node, y: Node) -> Node:
    return x**y


@pre_compile('math.sqrt')
def math_sqrt(x: Node) -> Node:
    return x**F.Value(0.5)


@pre_compile('math.hypot')
def math_hypot(x: Node, y: Node) -> Node:
    return F.Sqrt(x*x + y*y)


#endregion


# region Python Builtins
@pre_compile('builtins.round')
def buildins_round(x: Node) -> Node:
    return F.Round(x)


@pre_compile('builtins.min')
def buildins_min(*x: Node) -> Node:
    return F.Min(...)


@pre_compile('builtins.max')
def buildins_max(*x: Node) -> Node:
    return F.Max(...)


@pre_compile('builtins.abs')
def buildins_abs(x: Node) -> Node:
    return F.Abs(x)


@pre_compile('builtins.bool')
def builtins_bool(x: Node) -> Node:
    return x


@pre_compile('builtins.float')
def builtins_float(x: Node) -> Node:
    return x


@pre_compile('builtins.int')
def builtins_int(x: Node) -> Node:
    return F.Trunc(x)


@pre_compile('builtins.pow')
def builtins_pow(x: Node, y: Node) -> Node:
    return F.Power(x, y)


@pre_compile('builtins.print')
def buildins_print(x: Node) -> Node:
    return F.DebugLog(x)


# endregion
