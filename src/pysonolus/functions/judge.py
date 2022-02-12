from pysonolus.typings import JudgeResult


def judge(
    src: float,
    dst: float,
    min_perfect: float,
    max_perfect: float,
    min_great: float,
    max_great: float,
    min_good: float,
    max_good: float,
) -> JudgeResult:
    diff = src - dst
    if min_perfect <= diff <= max_perfect:
        return JudgeResult.Perfect
    elif min_great <= diff <= max_great:
        return JudgeResult.Great
    elif min_good <= diff <= max_good:
        return JudgeResult.Good
    else:
        return JudgeResult.Miss


def judge_simple(
    src: float, dst: float, max_perfect: float, max_great: float,
    max_good: float
) -> JudgeResult:
    return judge(
        src,
        dst,
        -max_perfect,
        max_perfect,
        -max_great,
        max_great,
        -max_good,
        max_good,
    )
