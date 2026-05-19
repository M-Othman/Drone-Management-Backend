from app.models import Location

DRONE_SPEED_KMH = 50
ETA_BUFFER = 1.15


def estimate_eta_minutes(loc1: Location, loc2: Location) -> float:
    dlat = (loc2.lat - loc1.lat) * 111
    dlng = (loc2.lng - loc1.lng) * 111
    distance_km = (dlat ** 2 + dlng ** 2) ** 0.5
    return (distance_km / DRONE_SPEED_KMH) * ETA_BUFFER * 60
