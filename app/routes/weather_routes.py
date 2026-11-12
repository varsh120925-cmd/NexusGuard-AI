"""
Live Weather REST API Routes
"""

from typing import Optional
from fastapi import APIRouter, Query
from app.services.weather_service import WeatherService, GLOBAL_HUB_COORDINATES

router = APIRouter(prefix="/api/weather", tags=["Live Weather Monitoring"])

@router.get("")
def get_weather(
    location: Optional[str] = Query(None, description="City name or logistics hub"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lng: Optional[float] = Query(None, description="Longitude")
):
    if lat is not None and lng is not None:
        return WeatherService.get_live_weather(lat, lng)
    elif location:
        return WeatherService.get_live_weather(location)
    else:
        # Default to New York
        return WeatherService.get_live_weather("New York")

@router.get("/hubs")
def get_logistics_hubs():
    """Returns all supported international logistics hubs with live atmospheric data."""
    hub_list = []
    for hub_name, info in GLOBAL_HUB_COORDINATES.items():
        w = WeatherService.get_live_weather(hub_name)
        hub_list.append({
            "name": hub_name,
            "country": info["country"],
            "lat": info["lat"],
            "lng": info["lng"],
            "temperature_c": w.get("temperature_c"),
            "precipitation_mm": w.get("precipitation_mm"),
            "wind_speed_kmh": w.get("wind_speed_kmh"),
            "weather_description": w.get("weather_description", "Fair"),
            "severity_index": w.get("severity_index", 0.05),
            "is_live": w.get("is_live", False)
        })
    return hub_list
