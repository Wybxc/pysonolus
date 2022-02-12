from __future__ import annotations
from enum import Enum
from typing import Any, ClassVar, Literal, NewType, Tuple, TypeVar, Union, get_origin

T = TypeVar('T')

TNodeFunctionName = Literal[
    "Add", "Subtract", "Multiply", "Divide", "Mod", "Power", "Log", "Equal",
    "NotEqual", "Greater", "GreaterOr", "Less", "LessOr", "Not", "Abs", "Sign",
    "Min", "Max", "Ceil", "Floor", "Round", "Frac", "Trunc", "Degree",
    "Radian", "Sin", "Cos", "Tan", "Sinh", "Cosh", "Tanh", "Arcsin", "Arccos",
    "Arctan", "Arctan2", "Clamp", "Lerp", "LerpClamped", "Unlerp",
    "UnlerpClamped", "Remap", "RemapClamped", "Smoothstep", "Random",
    "RandomInteger", "Draw", "DrawCurvedL", "DrawCurvedR", "DrawCurvedLR",
    "DrawCurvedB", "DrawCurvedT", "DrawCurvedBT", "Play", "PlayScheduled",
    "Spawn", "SpawnParticleEffect", "MoveParticleEffect",
    "DestroyParticleEffect", "HasSkinSprite", "HasEffectClip",
    "HasParticleEffect", "Judge", "JudgeSimple", "InSine", "InQuad", "InCubic",
    "InQuart", "InQuint", "InExpo", "InCirc", "InBack", "InElastic", "OutSine",
    "OutQuad", "OutCubic", "OutQuart", "OutQuint", "OutExpo", "OutCirc",
    "OutBack", "OutElastic", "InOutSine", "InOutQuad", "InOutCubic",
    "InOutQuart", "InOutQuint", "InOutExpo", "InOutCirc", "InOutBack",
    "InOutElastic", "OutInSine", "OutInQuad", "OutInCubic", "OutInQuart",
    "OutInQuint", "OutInExpo", "OutInCirc", "OutInBack", "OutInElastic",
    "IsDebug", "DebugPause", "DebugLog"]
"""IR Node Functions name."""

ParticleEffectId = NewType('ParticleEffectId', int)
"""id of a particle effect spawned by `spawn_particle_effect`."""

Number = Union[float, int]
"""Python definition of JavaScript Number."""
Numbers = (float, int)
"""`Number` type used in `isinstance`."""


class JudgeResult(int, Enum):
    """Judge result of `judge` function."""
    Perfect = 1
    Great = 2
    Good = 3
    Miss = 0


def is_class_var(anno: Any) -> bool:
    """Check if `anno` is `ClassVar`."""
    return anno is ClassVar or get_origin(anno) is ClassVar


class Array():
    """Fixed length array type, used in structs. """

    def __init__(self, type: type, length: int):
        self.type = type
        self.length = length

    def __class_getitem__(cls, t: Tuple[type, int]):
        type, length = t
        return Array(type, length)

    def __getitem__(self, index: int) -> Any:
        raise NotImplementedError