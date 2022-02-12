"""
From https://easings.net/.
"""
import math

c1 = 1.70158
c2 = c1 * 1.525
c3 = c1 + 1
c4 = (2 * math.pi) / 3
c5 = (2 * math.pi) / 4.5


def _bounce_out(x: float) -> float:
    n1 = 7.5625
    d1 = 2.75

    if x < 1 / d1:
        return n1 * x * x
    elif x < 2 / d1:
        x -= 1.5 / d1
        return n1*x*x + 0.75
    elif x < 2.5 / d1:
        x -= 2.25 / d1
        return n1*x*x + 0.9375
    else:
        x -= 2.625 / d1
        return n1*x*x + 0.984375


def in_quad(x: float) -> float:
    return x * x


def out_quad(x: float) -> float:
    return 1 - (1-x) * (1-x)


def in_out_quad(x: float) -> float:
    if x < 0.5:
        return 2 * x * x
    else:
        return 1 - (-2 * x + 2)**2 / 2


def in_cubic(x: float) -> float:
    return x * x * x


def out_cubic(x: float) -> float:
    return 1 - (1 - x)**3


def in_out_cubic(x: float) -> float:
    if x < 0.5:
        return 4 * x * x * x
    else:
        return 1 - (-2 * x + 2)**3 / 2


def in_quart(x: float) -> float:
    return x * x * x * x


def out_quart(x: float) -> float:
    return 1 - (1 - x)**4


def in_out_quart(x: float) -> float:
    if x < 0.5:
        return 8 * x * x * x * x
    else:
        return 1 - (-2 * x + 2)**4 / 2


def in_quint(x: float) -> float:
    return x * x * x * x * x


def out_quint(x: float) -> float:
    return 1 - (1 - x)**5


def in_out_quint(x: float) -> float:
    if x < 0.5:
        return 16 * x * x * x * x * x
    else:
        return 1 - (-2 * x + 2)**5 / 2


def in_sine(x: float) -> float:
    return 1 - math.cos((x * math.pi) / 2)


def out_sine(x: float) -> float:
    return math.sin((x * math.pi) / 2)


def in_out_sine(x: float) -> float:
    return -(math.cos(math.pi * x) - 1) / 2


def in_expo(x: float) -> float:
    return 0 if x == 0 else 2**(10*x - 10)


def out_expo(x: float) -> float:
    return 1 if x == 1 else 1 - 2**(-10 * x)


def in_out_expo(x: float) -> float:
    if x == 0:
        return 0
    elif x == 1:
        return 1
    elif x < 0.5:
        return 2**(20*x - 10) / 2
    else:
        return (2 - 2**(-20 * x + 10)) / 2


def in_circ(x: float) -> float:
    return 1 - math.sqrt(1 - (x)**2)


def out_circ(x: float) -> float:
    return math.sqrt(1 - (x - 1)**2)


def in_out_circ(x: float) -> float:
    if x < 0.5:
        return (1 - math.sqrt(1 - (2 * x)**2)) / 2
    else:
        return (math.sqrt(1 - (-2 * x + 2)**2) + 1) / 2


def in_back(x: float) -> float:
    return c3*x*x*x - c1*x*x


def out_back(x: float) -> float:
    return 1 + c3 * (x - 1)**3 + c1 * (x - 1)**2


def in_out_back(x: float) -> float:
    if x < 0.5:
        return ((2 * x)**2 * ((c2+1) * 2 * x - c2)) / 2
    else:
        return ((2*x - 2)**2 * ((c2+1) * (x*2 - 2) + c2) + 2) / 2


def in_elastic(x: float) -> float:
    if x == 0:
        return 0
    elif x == 1:
        return 1
    else:
        return -2**(10*x - 10) * math.sin((x*10 - 10.75) * c4)


def out_elastic(x: float) -> float:
    if x == 0:
        return 0
    elif x == 1:
        return 1
    else:
        return 2**(-10 * x) * math.sin((x*10 - 0.75) * c4) + 1


def in_out_elastic(x: float) -> float:
    if x == 0:
        return 0
    elif x == 1:
        return 1
    elif x < 0.5:
        return -(2**(20*x - 10) * math.sin((20*x - 11.125) * c5)) / 2
    else:
        return (2**(-20 * x + 10) * math.sin((20*x - 11.125) * c5)) / 2 + 1


def in_bounce(x: float) -> float:
    return 1 - _bounce_out(1 - x)


def out_bounce(x: float) -> float:
    return _bounce_out(x)


def in_out_bounce(x: float) -> float:
    if x < 0.5:
        return (1 - _bounce_out(1 - 2*x)) / 2
    else:
        return (1 + _bounce_out(2*x - 1)) / 2
