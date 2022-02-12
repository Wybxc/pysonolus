from __future__ import annotations
from pysonolus.pointer.core import Struct


class LevelMemory(Struct, block=0):

    def __init_subclass__(cls):
        Struct.init_block(cls, 0)


class LevelData(Struct, block=1):
    """Level Data block contains level wide information that are updated
    by Sonolus each frame. """
    time: float
    delta_time: float
    screen_aspect_ratio: float
    audio_offset: float
    input_offset: float
    render_scale: float
    anti_aliasing: float
