"""
Shipment Model storing primary logistics consignments and metadata
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(60), unique=True, index=True, nullable=False)
    origin = Column(String(120), nullable=False)
    destination = Column(String(120), nullable=False)
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    dest_lat = Column(Float, nullable=True)
    dest_lng = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=False)
    shipment_value_usd = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    transport_mode = Column(String(50), nullable=False, default="Road")
    cargo_type = Column(String(100), nullable=False, default="General Freight")
    priority = Column(String(50), nullable=False, default="Standard")
    is_fragile = Column(Boolean, default=False)
    is_perishable = Column(Boolean, default=False)
    transit_stops = Column(Integer, default=1)
    carrier_name = Column(String(120), default="Nexus Express Global")
    carrier_historical_delay_rate = Column(Float, default=0.12)
    status = Column(String(50), default="In Transit") # In Transit, Delivered, On Hold, Cancelled
    shipment_date = Column(DateTime, default=datetime.utcnow)
    expected_delivery_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="shipments")
    predictions = relationship("RiskPrediction", back_populates="shipment", cascade="all, delete-orphan")
    weather_records = relationship("WeatherRecord", back_populates="shipment", cascade="all, delete-orphan")
    anomaly_records = relationship("AnomalyRecord", back_populates="shipment", cascade="all, delete-orphan")
    alerts = relationship("RiskAlert", back_populates="shipment", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="shipment", cascade="all, delete-orphan")
