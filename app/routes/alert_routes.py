"""
Risk Alerts & Notifications REST API Routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.alert import RiskAlert

router = APIRouter(prefix="/api/alerts", tags=["Risk Alerts"])

@router.get("")
def list_alerts(unread_only: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(RiskAlert).order_by(desc(RiskAlert.created_at))
    if unread_only:
        query = query.filter(RiskAlert.is_read == False)

    alerts = query.limit(limit).all()
    results = []
    for a in alerts:
        results.append({
            "id": a.id,
            "shipment_id": a.shipment_id,
            "tracking_number": a.shipment.tracking_number if a.shipment else None,
            "alert_level": a.alert_level,
            "title": a.title,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return results

@router.patch("/{id}/read")
def mark_alert_read(id: int, db: Session = Depends(get_db)):
    alert = db.query(RiskAlert).filter(RiskAlert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.is_read = True
    db.commit()
    return {"success": True, "id": id, "is_read": True}

@router.post("/mark-all-read")
def mark_all_alerts_read(db: Session = Depends(get_db)):
    db.query(RiskAlert).filter(RiskAlert.is_read == False).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "All alerts marked as read."}
