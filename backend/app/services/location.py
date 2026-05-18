import math

EARTH_RADIUS_KM = 6371.0
FALLBACK_DISTANCE_KM = 50.0


def parse_location(value: str) -> tuple[float, float]:
    left, right = value.split(",", maxsplit=1)
    latitude = float(left.strip())
    longitude = float(right.strip())
    if not -90 <= latitude <= 90:
        raise ValueError("Latitud fuera de rango")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitud fuera de rango")
    return latitude, longitude


def simulated_distance(origin: str, destination: str) -> float:
    try:
        origin_lat, origin_lng = parse_location(origin)
        destination_lat, destination_lng = parse_location(destination)
    except (ValueError, AttributeError):
        return FALLBACK_DISTANCE_KM

    origin_lat_rad = math.radians(origin_lat)
    destination_lat_rad = math.radians(destination_lat)
    delta_lat = math.radians(destination_lat - origin_lat)
    delta_lng = math.radians(destination_lng - origin_lng)

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(origin_lat_rad) * math.cos(destination_lat_rad) * math.sin(delta_lng / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return EARTH_RADIUS_KM * central_angle
