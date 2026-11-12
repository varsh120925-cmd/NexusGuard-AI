"""
Dashboard & Analytics REST API Routes
Calculates live aggregation metrics and real chart distributions directly from the SQLite database.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.shipment import Shipment
from app.models.prediction import RiskPrediction
from app.models.anomaly import AnomalyRecord
from app.models.alert import RiskAlert
from app.models.weather import WeatherRecord

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Aggregations"])

@router.get("")
def get_dashboard_summary(db: Session = Depends(get_db)):
    # 1. Total Shipments
    total_shipments = db.query(func.count(Shipment.id)).scalar() or 0

    # 2. Risk Categories breakdown
    risk_counts = {
        "High Risk": 0,
        "Medium Risk": 0,
        "Low Risk": 0
    }
    risk_rows = db.query(RiskPrediction.risk_category, func.count(RiskPrediction.id))\
        .group_by(RiskPrediction.risk_category).all()
    for cat, count in risk_rows:
        if cat in risk_counts:
            risk_counts[cat] = count

    # 3. Average Risk Score
    avg_score = db.query(func.avg(RiskPrediction.overall_risk_score)).scalar() or 0.0

    # 4. Suspicious Anomalies
    suspicious_count = db.query(func.count(AnomalyRecord.id))\
        .filter(AnomalyRecord.is_suspicious == True).scalar() or 0

    # 5. Transport Mode Breakdown
    mode_counts = {}
    mode_rows = db.query(Shipment.transport_mode, func.count(Shipment.id))\
        .group_by(Shipment.transport_mode).all()
    for mode, count in mode_rows:
        mode_counts[mode] = count

    # 6. Status Breakdown
    status_counts = {}
    status_rows = db.query(Shipment.status, func.count(Shipment.id))\
        .group_by(Shipment.status).all()
    for st, count in status_rows:
        status_counts[st] = count

    # 7. Anomaly Investigation Status Breakdown
    anomaly_status_counts = {
        "Pending Review": 0,
        "Under Investigation": 0,
        "Verified Legitimate": 0,
        "Confirmed Irregularity": 0
    }
    anom_rows = db.query(AnomalyRecord.investigation_status, func.count(AnomalyRecord.id))\
        .filter(AnomalyRecord.is_suspicious == True)\
        .group_by(AnomalyRecord.investigation_status).all()
    for st, count in anom_rows:
        anomaly_status_counts[st] = count

    # 8. Weather Severity Distribution (0-20, 21-40, 41-60, 61-80, 81-100)
    weather_tiers = {"Normal (0-20%)": 0, "Moderate (21-40%)": 0, "Severe (41-70%)": 0, "Extreme (>70%)": 0}
    w_records = db.query(WeatherRecord.severity_index).all()
    for (sev,) in w_records:
        val = (sev or 0.0) * 100
        if val <= 20:
            weather_tiers["Normal (0-20%)"] += 1
        elif val <= 40:
            weather_tiers["Moderate (21-40%)"] += 1
        elif val <= 70:
            weather_tiers["Severe (41-70%)"] += 1
        else:
            weather_tiers["Extreme (>70%)"] += 1

    # 9. Recent Shipments
    recent_shipments = []
    latest_shipments = db.query(Shipment).order_by(desc(Shipment.created_at)).limit(6).all()
    for s in latest_shipments:
        pred = db.query(RiskPrediction).filter(RiskPrediction.shipment_id == s.id)\
            .order_by(desc(RiskPrediction.prediction_date)).first()
        anom = db.query(AnomalyRecord).filter(AnomalyRecord.shipment_id == s.id)\
            .order_by(desc(AnomalyRecord.created_at)).first()

        recent_shipments.append({
            "id": s.id,
            "tracking_number": s.tracking_number,
            "origin": s.origin,
            "destination": s.destination,
            "transport_mode": s.transport_mode,
            "cargo_type": s.cargo_type,
            "shipment_value_usd": s.shipment_value_usd,
            "status": s.status,
            "risk_score": pred.overall_risk_score if pred else 25.0,
            "risk_category": pred.risk_category if pred else "Low Risk",
            "is_suspicious": anom.is_suspicious if anom else False,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M")
        })

    # 10. Risk Trend series (last 7 recorded shipments)
    risk_trend_labels = []
    risk_trend_values = []
    trend_rows = db.query(Shipment.tracking_number, RiskPrediction.overall_risk_score)\
        .join(RiskPrediction, Shipment.id == RiskPrediction.shipment_id)\
        .order_by(desc(Shipment.created_at)).limit(10).all()
    for trk, score in reversed(trend_rows):
        risk_trend_labels.append(trk)
        risk_trend_values.append(round(score, 1))

    return {
        "kpis": {
            "total_shipments": total_shipments,
            "high_risk_count": risk_counts["High Risk"],
            "medium_risk_count": risk_counts["Medium Risk"],
            "low_risk_count": risk_counts["Low Risk"],
            "suspicious_alerts_count": suspicious_count,
            "average_risk_score": round(float(avg_score), 1)
        },
        "charts": {
            "risk_distribution": risk_counts,
            "transport_modes": mode_counts,
            "shipment_status": status_counts,
            "anomaly_statuses": anomaly_status_counts,
            "weather_distribution": weather_tiers,
            "risk_trend": {
                "labels": risk_trend_labels,
                "values": risk_trend_values
            }
        },
        "recent_activity": recent_shipments
    }
