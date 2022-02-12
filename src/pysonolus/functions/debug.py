def is_debug() -> bool:
    raise NotImplementedError


def debug_pause() -> None:
    raise NotImplementedError


def debug_log(value: float) -> None:
    print(value)
