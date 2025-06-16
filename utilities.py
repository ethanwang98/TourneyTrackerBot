from math import log, floor, ceil


def calculate_upset_factor(seed_1: int, seed_2: int) -> int:
    """Uses the upset factor formula used on PGStats"""
    return abs(_calculate_losers_rounds_to_victory(seed_1) - _calculate_losers_rounds_to_victory(seed_2))


def _calculate_losers_rounds_to_victory(seed: int) -> int:
    if seed == 1:
        return 0

    return floor(log(seed - 1, 2)) + ceil(log(seed * (2 / 3), 2))