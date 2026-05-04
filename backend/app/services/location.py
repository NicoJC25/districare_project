import math


def parse_location(value: str) -> tuple[float, float]:
    left, right = value.split(",", maxsplit=1)
    return float(left.strip()), float(right.strip())


def simulated_distance(origin: str, destination: str) -> float:
    try:
        ox, oy = parse_location(origin)
        dx, dy = parse_location(destination)
    except (ValueError, AttributeError):
        return 50.0
    return math.hypot(ox - dx, oy - dy)
