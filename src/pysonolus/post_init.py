from typing import Callable, List

_init: List[Callable[[], None]] = []


def post_init(func: Callable[[], None]):
    _init.append(func)


def init():
    global _init
    for func in _init:
        func()
    _init = []
