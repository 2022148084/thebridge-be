from sqlalchemy import func

from app.models import Gathering


def haversine_km(user_lat: float, user_lng: float):
    """SQLAlchemy expression for great-circle distance in km between user and Gathering."""
    lat1 = func.radians(user_lat)
    lat2 = func.radians(Gathering.lat)
    dlat = func.radians(Gathering.lat - user_lat)
    dlng = func.radians(Gathering.lng - user_lng)
    sin_dlat = func.sin(dlat / 2)
    sin_dlng = func.sin(dlng / 2)
    a = sin_dlat * sin_dlat + func.cos(lat1) * func.cos(lat2) * sin_dlng * sin_dlng
    return 6371 * 2 * func.asin(func.sqrt(a))
