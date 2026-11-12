"""
Shipment Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ShipmentCreate(BaseModel):
    tracking_number: Optional[str] = None
    origin: str = Field(..., example="New York")
    destination: str = Field(..., example="Rotterdam")
    distance_km: Optional[float] = None
    shipment_value_usd: float = Field(..., ge=1.0, example=25000.0)
    weight_kg: float = Field(..., ge=0.1, example=450.0)
    transport_mode: str = Field("Road", example="Sea")
    cargo_type: str = Field("Electronics", example="Electronics")
    priority: str = Field("Standard", example="Express")
    is_fragile: bool = False
    is_perishable: bool = False
    transit_stops: int = Field(1, ge=0, le=10)
    carrier_name: Optional[str] = "Nexus Express Global"
    carrier_historical_delay_rate: Optional[float] = Field(0.12, ge=0.0, le=1.0)
    expected_delivery_days: Optional[int] = 5

class ShipmentResponse(BaseModel):
    id: int
    tracking_number: str
    origin: str
    destination: str
    distance_km: float
    shipment_value_usd: float
    weight_kg: float
    transport_mode: str
    cargo_type: str
    priority: str
    is_fragile: bool
    is_perishable: bool
    transit_stops: int
    carrier_name: str
    carrier_historical_delay_rate: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
