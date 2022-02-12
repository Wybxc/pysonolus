"""Here defines the math functions uses in Node functions.
"""
import math


def sign(x: float) -> float:
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def frac(x: float) -> float:
    return x - math.floor(x)


def clamp(x: float, a: float, b: float) -> float:
    if x < a:
        return a
    elif x > b:
        return b
    else:
        return x


def lerp(a: float, b: float, x: float) -> float:
    return a + (b-a) * x


def lerp_clamped(a: float, b: float, x: float) -> float:
    return a + (b-a) * clamp(x, 0, 1)


def unlerp(a: float, b: float, x: float) -> float:
    return (x-a) / (b-a)


def unlerp_clamped(a: float, b: float, x: float) -> float:
    return clamp((x-a) / (b-a), 0, 1)


def remap(
    x_min: float,
    x_max: float,
    target_min: float,
    target_max: float,
    x: float,
) -> float:
    return lerp(target_min, target_max, unlerp(x_min, x_max, x))


def remap_clamped(
    x_min: float,
    x_max: float,
    target_min: float,
    target_max: float,
    x: float,
) -> float:
    return lerp(target_min, target_max, unlerp_clamped(x_min, x_max, x))


def smooth_step(a: float, b: float, x: float) -> float:
    t = unlerp_clamped(a, b, x)
    return t * t * (3 - 2*t)
