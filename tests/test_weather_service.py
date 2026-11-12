"""
Open-Meteo Weather Service Tests
"""

from app.services.weather_service import WeatherService

def test_resolve_coordinates_known_hub():
    coords = WeatherService.resolve_coordinates("New York")
    assert coords is not None
    assert "lat" in coords and "lng" in coords
    assert round(coords["lat"], 2) == 40.71

def test_get_live_weather_known_city():
    w = WeatherService.get_live_weather("London")
    assert "location_name" in w
    assert "severity_index" in w
    assert 0.0 <= w["severity_index"] <= 1.0
    assert "weather_description" in w
    if w["is_live"]:
        assert w["temperature_c"] is not None
        assert w["wind_speed_kmh"] is not None

def test_get_live_weather_caching():
    # Calling twice should return cached data on second call
    w1 = WeatherService.get_live_weather("Chicago")
    w2 = WeatherService.get_live_weather("Chicago")
    assert w2.get("is_cached") is True

def test_weather_fallback_unknown_location():
    w = WeatherService.get_live_weather("NonExistentCityXYZ12345")
    assert w["is_live"] is False
    assert "could not be resolved" in w["error"].lower()
