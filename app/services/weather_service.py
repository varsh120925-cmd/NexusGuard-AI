"""
Real-Time Weather Service
Integrates with Open-Meteo API for live atmospheric data, location geocoding,
in-memory caching with TTL, and weather risk calculation.
"""

import time
import requests
import urllib3
from typing import Dict, Any, Optional
from app.config import settings

# Suppress insecure request warnings if corporate SSL inspection is present
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Pre-indexed international logistics hubs with exact GPS coordinates
GLOBAL_HUB_COORDINATES = {
    "New York": {"lat": 40.7128, "lng": -74.0060, "country": "United States"},
    "Los Angeles": {"lat": 34.0522, "lng": -118.2437, "country": "United States"},
    "Chicago": {"lat": 41.8781, "lng": -87.6298, "country": "United States"},
    "Houston": {"lat": 29.7604, "lng": -95.3698, "country": "United States"},
    "Miami": {"lat": 25.7617, "lng": -80.1918, "country": "United States"},
    "Toronto": {"lat": 43.6532, "lng": -79.3832, "country": "Canada"},
    "Rotterdam": {"lat": 51.9244, "lng": 4.4777, "country": "Netherlands"},
    "Frankfurt": {"lat": 50.1109, "lng": 8.6821, "country": "Germany"},
    "London": {"lat": 51.5074, "lng": -0.1278, "country": "United Kingdom"},
    "Antwerp": {"lat": 51.2194, "lng": 4.4025, "country": "Belgium"},
    "Hamburg": {"lat": 53.5511, "lng": 9.9937, "country": "Germany"},
    "Shanghai": {"lat": 31.2304, "lng": 121.4737, "country": "China"},
    "Singapore": {"lat": 1.3521, "lng": 103.8198, "country": "Singapore"},
    "Tokyo": {"lat": 35.6762, "lng": 139.6503, "country": "Japan"},
    "Hong Kong": {"lat": 22.3193, "lng": 114.1694, "country": "Hong Kong"},
    "Busan": {"lat": 35.1796, "lng": 129.0756, "country": "South Korea"},
    "Dubai": {"lat": 25.2048, "lng": 55.2708, "country": "United Arab Emirates"},
    "Sydney": {"lat": -33.8688, "lng": 151.2093, "country": "Australia"},
    "Mumbai": {"lat": 19.0760, "lng": 72.8777, "country": "India"},
    "São Paulo": {"lat": -23.5505, "lng": -46.6333, "country": "Brazil"}
}

# WMO Weather interpretation codes
WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900 # 15 minutes

def _safe_get(url: str, params: dict, timeout: int = 4):
    """Executes request with certificate verification fallback."""
    try:
        return requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.SSLError:
        return requests.get(url, params=params, timeout=timeout, verify=False)

class WeatherService:
    @staticmethod
    def resolve_coordinates(city_name: str) -> Optional[Dict[str, float]]:
        """Resolves city to latitude and longitude using local lookup or Open-Meteo Geocoding."""
        city_clean = city_name.strip()
        for known_city, info in GLOBAL_HUB_COORDINATES.items():
            if known_city.lower() == city_clean.lower():
                return {"lat": info["lat"], "lng": info["lng"], "city": known_city}

        try:
            resp = _safe_get(
                settings.OPEN_METEO_GEO_URL,
                params={"name": city_clean, "count": 1, "language": "en", "format": "json"},
                timeout=settings.WEATHER_REQUEST_TIMEOUT_SECONDS
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    best = results[0]
                    return {
                        "lat": round(float(best["latitude"]), 4),
                        "lng": round(float(best["longitude"]), 4),
                        "city": best.get("name", city_clean)
                    }
        except Exception:
            pass

        return None

    @classmethod
    def get_live_weather(cls, city_or_lat: Any, lng: Optional[float] = None) -> Dict[str, Any]:
        """
        Retrieves real-time atmospheric observation from Open-Meteo API.
        Includes error handling, timeouts, caching, and risk factor derivation.
        """
        location_label = ""
        if isinstance(city_or_lat, str):
            location_label = city_or_lat
            coords = cls.resolve_coordinates(city_or_lat)
            if not coords:
                return {
                    "is_live": False,
                    "location_name": city_or_lat,
                    "error": f"Coordinates could not be resolved for location: '{city_or_lat}'",
                    "temperature_c": None,
                    "precipitation_mm": None,
                    "wind_speed_kmh": None,
                    "weather_description": "Data Unavailable",
                    "severity_index": 0.15,
                    "risk_warnings": ["Live weather information could not be retrieved for this corridor."]
                }
            lat = coords["lat"]
            lon = coords["lng"]
        else:
            lat = round(float(city_or_lat), 4)
            lon = round(float(lng), 4)
            location_label = f"{lat:.2f}, {lon:.2f}"

        cache_key = f"{lat:.3f}_{lon:.3f}"
        now = time.time()

        if cache_key in _WEATHER_CACHE:
            entry = _WEATHER_CACHE[cache_key]
            if now < entry["expires_at"]:
                cached_copy = entry["data"].copy()
                cached_copy["is_cached"] = True
                return cached_copy

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "timezone": "auto"
        }

        try:
            response = _safe_get(
                settings.OPEN_METEO_BASE_URL,
                params=params,
                timeout=settings.WEATHER_REQUEST_TIMEOUT_SECONDS
            )

            if response.status_code != 200:
                return {
                    "is_live": False,
                    "location_name": location_label,
                    "latitude": lat,
                    "longitude": lon,
                    "error": f"Open-Meteo API returned HTTP {response.status_code}",
                    "temperature_c": None,
                    "precipitation_mm": None,
                    "wind_speed_kmh": None,
                    "weather_description": "Live weather API unavailable",
                    "severity_index": 0.10,
                    "risk_warnings": ["Live atmospheric data unavailable; evaluated with historical weather baseline."]
                }

            data = response.json()
            current = data.get("current", {})

            temp_c = current.get("temperature_2m", 18.0)
            precip_mm = current.get("precipitation", 0.0)
            wind_kmh = current.get("wind_speed_10m", 12.0)
            weather_code = current.get("weather_code", 0)
            humidity = current.get("relative_humidity_2m", 50)
            weather_desc = WMO_DESCRIPTIONS.get(weather_code, f"Weather Code {weather_code}")

            severity = 0.05
            warnings = []

            if temp_c < -5:
                severity += 0.35
                warnings.append(f"Sub-zero conditions ({temp_c}°C): freezing threat for cold-chain and diesel fuel gelation.")
            elif temp_c > 35:
                severity += 0.30
                warnings.append(f"Extreme heat ({temp_c}°C): thermal degradation hazard for perishables and electronics.")

            if precip_mm > 15:
                severity += 0.45
                warnings.append(f"Torrential precipitation ({precip_mm} mm): flash flood risk and roadway visibility degradation.")
            elif precip_mm > 4:
                severity += 0.20
                warnings.append(f"Moderate precipitation ({precip_mm} mm): surface slickness and braking distance increase.")

            if wind_kmh > 65:
                severity += 0.50
                warnings.append(f"Gale-force winds ({wind_kmh} km/h): critical flight delay risk and high-profile freight roll-over hazard.")
            elif wind_kmh > 40:
                severity += 0.25
                warnings.append(f"High crosswinds ({wind_kmh} km/h): speed restrictions active for heavy road transports.")

            if weather_code in [95, 96, 99]:
                severity += 0.40
                warnings.append("Severe thunderstorm alert: lightning ground-stop procedures likely active.")
            elif weather_code in [71, 73, 75, 85, 86]:
                severity += 0.35
                warnings.append("Active snowfall: de-icing delays and mountain pass restrictions.")

            severity = round(min(1.0, max(0.05, severity)), 3)

            weather_result = {
                "is_live": True,
                "is_cached": False,
                "location_name": location_label,
                "latitude": lat,
                "longitude": lon,
                "temperature_c": round(float(temp_c), 1),
                "precipitation_mm": round(float(precip_mm), 1),
                "wind_speed_kmh": round(float(wind_kmh), 1),
                "humidity_percent": humidity,
                "weather_code": weather_code,
                "weather_description": weather_desc,
                "severity_index": severity,
                "risk_warnings": warnings if warnings else ["Atmospheric conditions are within normal operational limits."],
                "retrieved_at": current.get("time", "")
            }

            _WEATHER_CACHE[cache_key] = {
                "data": weather_result,
                "expires_at": now + CACHE_TTL_SECONDS
            }

            return weather_result

        except Exception as e:
            return {
                "is_live": False,
                "location_name": location_label,
                "latitude": lat,
                "longitude": lon,
                "error": f"Live weather API connection failed: {str(e)}",
                "temperature_c": None,
                "precipitation_mm": None,
                "wind_speed_kmh": None,
                "weather_description": "Live weather API unavailable",
                "severity_index": 0.10,
                "risk_warnings": ["Live weather information could not be retrieved. Fallback to operational baseline."]
            }
