"""
Report Generation & PDF Download REST API Routes
"""

import os
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.shipment import Shipment
from app.models.prediction import RiskPrediction
from app.models.weather import WeatherRecord
from app.models.anomaly import AnomalyRecord
from app.models.report import Report
from app.services.report_service import ReportService
from app.services.recommendation_service import RecommendationEngine

router = APIRouter(prefix="/api/reports", tags=["Shipment Reports"])

@router.get("")
def list_reports(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(desc(Report.generated_date)).offset(skip).limit(limit).all()
    results = []
    for r in reports:
        shipment = r.shipment
        results.append({
            "id": r.id,
            "shipment_id": r.shipment_id,
            "tracking_number": shipment.tracking_number if shipment else "N/A",
            "report_title": r.report_title,
            "file_path": r.file_path,
            "generated_date": r.generated_date.strftime("%Y-%m-%d %H:%M")
        })
    return results

@router.post("/generate/{shipment_id}")
def generate_report(shipment_id: int, db: Session = Depends(get_db)):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found.")

    pred = db.query(RiskPrediction).filter(RiskPrediction.shipment_id == shipment_id)\
        .order_by(desc(RiskPrediction.prediction_date)).first()
    weather = db.query(WeatherRecord).filter(WeatherRecord.shipment_id == shipment_id)\
        .order_by(desc(WeatherRecord.weather_retrieval_time)).first()
    anom = db.query(AnomalyRecord).filter(AnomalyRecord.shipment_id == shipment_id)\
        .order_by(desc(AnomalyRecord.created_at)).first()

    # Weather payload
    weather_dict = {
        "location_name": weather.location_name if weather else shipment.origin,
        "temperature_c": weather.temperature_c if weather else 20.0,
        "precipitation_mm": weather.precipitation_mm if weather else 0.0,
        "wind_speed_kmh": weather.wind_speed_kmh if weather else 12.0,
        "weather_description": weather.weather_description if weather else "Clear",
        "severity_index": weather.severity_index if weather else 0.05,
        "is_live": True
    }

    # Anomaly payload
    reasons = []
    actions = []
    if anom:
        if anom.explanation_json:
            try:
                reasons = json.loads(anom.explanation_json)
            except Exception:
                pass
        if anom.recommended_actions_json:
            try:
                actions = json.loads(anom.recommended_actions_json)
            except Exception:
                pass

    anomaly_dict = {
        "anomaly_score": anom.anomaly_score if anom else 0.0,
        "is_suspicious": anom.is_suspicious if anom else False,
        "status_label": anom.detection_result if anom else "Normal Operating Pattern",
        "detected_reasons": reasons if reasons else ["Parameters within baseline."],
        "recommended_actions": actions
    }

    # Recommendation payload
    recs = RecommendationEngine.generate_recommendations(
        risk_category=pred.risk_category if pred else "Low Risk",
        overall_risk_score=pred.overall_risk_score if pred else 25.0,
        weather_info=weather_dict,
        anomaly_info=anomaly_dict,
        shipment_data={
            "transport_mode": shipment.transport_mode,
            "cargo_type": shipment.cargo_type,
            "is_perishable": shipment.is_perishable,
            "transit_stops": shipment.transit_stops,
            "carrier_historical_delay_rate": shipment.carrier_historical_delay_rate
        }
    )

    pdf_path = ReportService.generate_pdf_report(
        shipment=shipment,
        prediction=pred,
        weather_info=weather_dict,
        anomaly_info=anomaly_dict,
        recommendations=recs
    )

    # Persist Report in DB
    report_entry = Report(
        shipment_id=shipment.id,
        report_title=f"Risk Assessment Report - {shipment.tracking_number}",
        file_path=pdf_path,
        generated_date=datetime.utcnow()
    )
    db.add(report_entry)
    db.commit()
    db.refresh(report_entry)

    return {
        "success": True,
        "report_id": report_entry.id,
        "report_title": report_entry.report_title,
        "file_path": report_entry.file_path,
        "download_url": f"/api/reports/{report_entry.id}/pdf"
    }

@router.get("/{id}")
def get_report(id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    return {
        "id": report.id,
        "shipment_id": report.shipment_id,
        "report_title": report.report_title,
        "file_path": report.file_path,
        "download_url": f"/api/reports/{report.id}/pdf",
        "generated_date": report.generated_date.strftime("%Y-%m-%d %H:%M")
    }

@router.get("/{id}/pdf")
def download_pdf(id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == id).first()
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="PDF report file not found on disk.")

    filename = os.path.basename(report.file_path)
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=filename
    )
