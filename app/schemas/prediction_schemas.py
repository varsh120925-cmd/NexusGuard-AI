"""
Risk Prediction and Assessment Pydantic Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class PredictRequest(BaseModel):
    origin: str
    destination: str
    distance_km: Optional[float] = None
    transport_mode: str = "Road"
    cargo_type: str = "Electronics"
    shipment_value_usd: float = 15000.0
    weight_kg: float = 250.0
    priority: str = "Standard"
    is_fragile: bool = False
    is_perishable: bool = False
    transit_stops: int = 1
    carrier_historical_delay_rate: Optional[float] = 0.12
    save_to_database: bool = True
    tracking_number: Optional[str] = None

class FactorContribution(BaseModel):
    dimension: str
    weight_percent: int
    score_contribution: float
    raw_value: str
    status: str

class RecommendationItem(BaseModel):
    type: str
    priority: str
    action: str
    description: str

class PredictResponse(BaseModel):
    shipment_id: Optional[int] = None
    tracking_number: str
    origin: str
    destination: str
    distance_km: float
    transport_mode: str
    cargo_type: str
    ml_probability: float
    overall_risk_score: float
    risk_category: str
    badge_class: str
    weather: Dict[str, Any]
    anomaly: Dict[str, Any]
    factor_breakdown: List[FactorContribution]
    recommendations: List[RecommendationItem]
    model_version: str
