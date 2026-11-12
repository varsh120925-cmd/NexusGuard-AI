"""
Anomaly & Weather Schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class AnomalyUpdateStatus(BaseModel):
    investigation_status: str # Pending Review, Under Investigation, Verified Legitimate, Confirmed Irregularity
    resolution_notes: Optional[str] = None

class WeatherQuery(BaseModel):
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class WeatherResponse(BaseModel):
    is_live: bool
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    weather_description: str
    severity_index: float
    risk_warnings: List[str]
    retrieved_at: Optional[str] = None

class DashboardSummaryResponse(BaseModel):
    total_shipments: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    suspicious_alerts_count: int
    average_risk_score: float
    recent_shipments: List[Dict[str, Any]]
    risk_distribution: Dict[str, int]
    transport_mode_breakdown: Dict[str, int]
    anomaly_status_breakdown: Dict[str, int]
