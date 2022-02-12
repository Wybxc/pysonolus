from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class FlattenedNode():
    """Flattened Sonolus node, for engine data. """


@dataclass
class FlattenedValueNode(FlattenedNode):
    """Flattened value node, for engine data. """
    value: float


@dataclass
class FlattenedFunctionNode(FlattenedNode):
    """Flattened function calling node, for engine data. """
    func: str
    args: List[int]
