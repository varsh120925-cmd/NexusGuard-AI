"""
Fraud & Anomaly Detection REST API Routes
"""

import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.shipment import Shipment
from app.models.anomaly import AnomalyRecord
from app.schemas.anomaly_schemas import AnomalyUpdateStatus
from app.ml.predictor import get_predictor

router = APIRouter(prefix="/api/anomalies", tags=["Fraud & Anomaly Detection"])

@router.get("")
def list_anomalies(
    status_filter: Optional[str] = None,
    suspicious_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(AnomalyRecord).order_by(desc(AnomalyRecord.created_at))

    if suspicious_only:
        query = query.filter(AnomalyRecord.is_suspicious == True)

    if status_filter and status_filter != "All":
        query = query.filter(AnomalyRecord.investigation_status == status_filter)

    anomalies = query.offset(skip).limit(limit).all()

    results = []
    for a in anomalies:
        shipment = a.shipment
        reasons = []
        if a.explanation_json:
            try:
                reasons = json.loads(a.explanation_json)
            except Exception:
                reasons = []

        actions = []
        if a.recommended_actions_json:
            try:
                actions = json.loads(a.recommended_actions_json)
            except Exception:
                actions = []

        results.append({
            "id": a.id,
            "shipment_id": a.shipment_id,
            "tracking_number": shipment.tracking_number if shipment else "N/A",
            "origin": shipment.origin if shipment else "N/A",
            "destination": shipment.destination if shipment else "N/A",
            "transport_mode": shipment.transport_mode if shipment else "N/A",
            "cargo_type": shipment.cargo_type if shipment else "N/A",
            "shipment_value_usd": shipment.shipment_value_usd if shipment else 0.0,
            "weight_kg": shipment.weight_kg if shipment else 0.0,
            "anomaly_score": a.anomaly_score,
            "is_suspicious": a.is_suspicious,
            "detection_result": a.detection_result,
            "investigation_status": a.investigation_status,
            "reasons": reasons,
            "recommended_actions": actions,
            "resolution_notes": a.resolution_notes,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
            "reviewed_at": a.reviewed_at.strftime("%Y-%m-%d %H:%M") if a.reviewed_at else None
        })

    return results

@router.patch("/{id}/status")
def update_anomaly_status(id: int, payload: AnomalyUpdateStatus, db: Session = Depends(get_db)):
    record = db.query(AnomalyRecord).filter(AnomalyRecord.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Anomaly record not found.")

    record.investigation_status = payload.investigation_status
    if payload.resolution_notes:
        record.resolution_notes = payload.resolution_notes
    record.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "id": record.id,
        "investigation_status": record.investigation_status,
        "resolution_notes": record.resolution_notes,
        "reviewed_at": record.reviewed_at.strftime("%Y-%m-%d %H:%M")
    }
