"""
RiskPrediction Model storing multi-factor risk calculations and ML probabilities
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    ml_probability = Column(Float, nullable=False)
    overall_risk_score = Column(Float, nullable=False) # 0 to 100
    risk_category = Column(String(50), nullable=False) # Low, Medium, High
    contributing_factors_json = Column(Text, nullable=True) # JSON serialized list of factors
    weather_risk_score = Column(Float, default=0.0)
    anomaly_factor_score = Column(Float, default=0.0)
    model_version = Column(String(50), default="GradientBoosting-v1.0")
    prediction_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    shipment = relationship("Shipment", back_populates="predictions")
