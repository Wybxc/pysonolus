from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from types import ModuleType
from typing import (
    TYPE_CHECKING, List, Literal, Optional, Set, Type, TypeVar, cast
)

from pysonolus.inspect import QualifiedName, RelativeName
from pysonolus.node.IR import Node

TContextFrame = TypeVar("TContextFrame", bound='ContextFrame')


class Context():
    """Context for compiling.

    Context manages:
        1. Context frames
    """
    def __init__(self):
        self._frames: List[ContextFrame] = []

    def enter(self, frame: Type[TContextFrame]) -> TContextFrame:
        """Enter a new context frame."""
        new_frame = frame()
        self._frames.append(new_frame)
        return new_frame

    def exit(self, frame: Type[TContextFrame]) -> TContextFrame:
        """Exit a context frame."""
        if len(self._frames) == 0:
            raise RuntimeError("No context frame to exit")
        if isinstance(self._frames[-1], frame):
            return cast(TContextFrame, self._frames.pop())
        else:
            raise RuntimeError(
                f"Expected to exit {frame} but got {type(self._frames[-1])}"
            )

    @contextlib.contextmanager
    def use(self, frame: Type[TContextFrame]):
        """Enter and exit a context frame, by context manager."""
        yield self.enter(frame)
        self.exit(frame)

    def __setattr__(self, name: str, value: object):
        if name.startswith("_"):
            return super().__setattr__(name, value)
        for frame in reversed(self._frames):
            if hasattr(frame, name):
                setattr(frame, name, value)
                return
        else:
            raise AttributeError(f"Option {name} not found in context")

    def __getattr__(self, name: str) -> object:
        for frame in reversed(self._frames):
            if hasattr(frame, name):
                return getattr(frame, name)
        else:
            raise AttributeError(f"Option {name} not found in context")

    if TYPE_CHECKING:
        calls: Set[RelativeName] = field(default_factory=set)
        """Names of functions called in this function.
        Names here are written as is."""
        name: Optional[QualifiedName] = None
        """Name of this function."""
        module: Optional[ModuleType] = None
        params: Set[str] = field(default_factory=set)
        """Names of parameters."""
        may_break: bool = False
        break_flag: Optional[str] = None
        may_return: bool = False
        return_flag: Optional[str] = None
        return_value: Optional[str] = None
        left: Optional[Node] = None
        right: Optional[Node] = None
        operand: Optional[Node] = None


@dataclass
class ContextFrame():
    """Context frame. """


@dataclass
class FunctionContext(ContextFrame):
    """Context frame for a compiling Python function. """
    calls: Set[RelativeName] = field(default_factory=set)
    """Names of functions called in this function.
    Names here are written as is."""
    name: Optional[QualifiedName] = None
    """Name of this function."""
    module: Optional[ModuleType] = None
    params: Set[str] = field(default_factory=set)
    """Names of parameters."""


BlockLevel = Literal['Returnable', 'Breakable', 'None']


@dataclass
class BlockContext(ContextFrame):
    """Context for a code block. """
    may_break: bool = False
    break_flag: Optional[str] = None
    may_return: bool = False
    return_flag: Optional[str] = None
    return_value: Optional[str] = None


@dataclass
class BinOpContext(ContextFrame):
    """Context for binary operation. """
    left: Optional[Node] = None
    right: Optional[Node] = None


@dataclass
class UnaryOpContext(ContextFrame):
    """Context for unitary operation. """
    operand: Optional[Node] = None
