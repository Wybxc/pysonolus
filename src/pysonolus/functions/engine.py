"""Here are the Node functions implemented by Sonolus engine.

Directly call functions here will cause an error.
"""
from sonolus_core.typings import EffectClip, ParticleEffect, SkinSprite

from pysonolus.typings import ParticleEffectId


def draw(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
) -> None:
    raise NotImplementedError


def draw_curved_left(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
    n: int,
    cxl: float,
    cyl: float,
) -> None:
    raise NotImplementedError


def draw_curved_right(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
    n: int,
    cxr: float,
    cyr: float,
) -> None:
    raise NotImplementedError


def draw_curved_left_right(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
    n: int,
    cxl: float,
    cyl: float,
    cxr: float,
    cyr: float,
) -> None:
    raise NotImplementedError


def draw_curved_bottom(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
    n: int,
    cxb: float,
    cyb: float,
) -> None:
    raise NotImplementedError


def draw_curved_top(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
    n: int,
    cxt: float,
    cyt: float,
) -> None:
    raise NotImplementedError


def draw_curved_bottom_top(
    id: SkinSprite,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    z: float,
    opacity: float,
    n: int,
    cxb: float,
    cyb: float,
    cxt: float,
    cyt: float,
) -> None:
    raise NotImplementedError


def play(id: EffectClip, dist: float) -> None:
    raise NotImplementedError


def play_scheduled(id: EffectClip, time: float, dist: float) -> None:
    raise NotImplementedError


def spawn(id: int, *data: float) -> None:
    raise NotImplementedError


def spawn_particle_effect(
    id: ParticleEffect,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
    time: float,
    loop: bool,
) -> ParticleEffectId:
    raise NotImplementedError


def move_particle_effect(
    id: ParticleEffectId,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
) -> None:
    raise NotImplementedError


def destroy_particle_effect(id: ParticleEffectId) -> None:
    raise NotImplementedError
