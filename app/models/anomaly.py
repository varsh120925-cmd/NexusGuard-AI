"""
AnomalyRecord Model tracking flagged fraud indicators and operational discrepancies
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False) # 0 to 100
    is_suspicious = Column(Boolean, default=False)
    detection_result = Column(String(100), default="Suspicious Pattern Requiring Verification")
    explanation_json = Column(Text, nullable=True) # JSON list of reasons
    recommended_actions_json = Column(Text, nullable=True) # JSON list of actions
    investigation_status = Column(String(50), default="Pending Review") # Pending Review, Under Investigation, Verified Legitimate, Confirmed Irregularity
    resolution_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    shipment = relationship("Shipment", back_populates="anomaly_records")
