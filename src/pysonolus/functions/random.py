"""Here provide random functions uses in Node functions.
"""
import math
import random as R


def random(a: float, b: float) -> float:
    return a + (b-a) * R.random()


def random_integer(a: float, b: float) -> int:
    return R.randrange(math.floor(a), math.ceil(b))


def randint(a: int, b: int) -> int:
    return random_integer(a, b)
