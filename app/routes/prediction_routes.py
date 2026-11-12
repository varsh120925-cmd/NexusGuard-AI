"""
Risk Prediction REST API Routes
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.shipment import Shipment
from app.models.prediction import RiskPrediction
from app.models.weather import WeatherRecord
from app.models.anomaly import AnomalyRecord
from app.schemas.prediction_schemas import PredictRequest, PredictResponse
from app.services.weather_service import WeatherService
from app.services.risk_scoring_service import MultiFactorRiskEngine
from app.services.recommendation_service import RecommendationEngine
from app.ml.predictor import get_predictor

router = APIRouter(prefix="/api", tags=["Risk Prediction"])

@router.post("/predict-risk", response_model=PredictResponse)
def predict_shipment_risk(payload: PredictRequest, db: Session = Depends(get_db)):
    # 1. Coordinate & Distance handling
    o_coords = WeatherService.resolve_coordinates(payload.origin) or {"lat": 40.7128, "lng": -74.0060, "city": payload.origin}
    d_coords = WeatherService.resolve_coordinates(payload.destination) or {"lat": 51.9244, "lng": 4.4777, "city": payload.destination}

    dist = payload.distance_km
    if not dist or dist <= 0:
        from app.routes.shipment_routes import calc_haversine
        dist = calc_haversine(o_coords["lat"], o_coords["lng"], d_coords["lat"], d_coords["lng"])
        if dist < 50:
            dist = 500.0

    # 2. Live Weather API from Open-Meteo
    weather_info = WeatherService.get_live_weather(payload.origin)
    temp_c = weather_info.get("temperature_c") or 20.0
    precip_mm = weather_info.get("precipitation_mm") or 0.0
    wind_kmh = weather_info.get("wind_speed_kmh") or 12.0
    w_severity = weather_info.get("severity_index", 0.05)

    # 3. ML Inference
    predictor = get_predictor()
    ml_input = {
        "origin": payload.origin,
        "destination": payload.destination,
        "distance_km": dist,
        "transport_mode": payload.transport_mode,
        "cargo_type": payload.cargo_type,
        "shipment_value_usd": payload.shipment_value_usd,
        "weight_kg": payload.weight_kg,
        "priority": payload.priority,
        "is_fragile": 1 if payload.is_fragile else 0,
        "is_perishable": 1 if payload.is_perishable else 0,
        "transit_stops": payload.transit_stops,
        "carrier_historical_delay_rate": payload.carrier_historical_delay_rate or 0.12,
        "origin_temp_c": temp_c,
        "origin_precip_mm": precip_mm,
        "origin_wind_kmh": wind_kmh,
        "weather_severity_index": w_severity,
        "route_risk_index": 0.15
    }

    ml_result = predictor.predict_risk(ml_input)
    anom_result = predictor.detect_anomaly(ml_input)

    # 4. Multi-Factor Risk Calculation
    risk_assessment = MultiFactorRiskEngine.calculate_composite_risk(
        ml_probability=ml_result["ml_probability"],
        weather_severity=w_severity,
        distance_km=dist,
        transit_stops=payload.transit_stops,
        carrier_historical_delay_rate=payload.carrier_historical_delay_rate or 0.12,
        anomaly_score=anom_result["anomaly_score"],
        is_suspicious=anom_result["is_suspicious"]
    )

    # 5. AI Recommendations
    recs = RecommendationEngine.generate_recommendations(
        risk_category=risk_assessment["risk_category"],
        overall_risk_score=risk_assessment["overall_risk_score"],
        weather_info=weather_info,
        anomaly_info=anom_result,
        shipment_data=ml_input
    )

    trk = payload.tracking_number or f"SIM-{int(dist)}-{payload.transport_mode[:3].upper()}"
    shipment_id = None

    return PredictResponse(
        shipment_id=shipment_id,
        tracking_number=trk,
        origin=payload.origin,
        destination=payload.destination,
        distance_km=dist,
        transport_mode=payload.transport_mode,
        cargo_type=payload.cargo_type,
        ml_probability=ml_result["ml_probability"],
        overall_risk_score=risk_assessment["overall_risk_score"],
        risk_category=risk_assessment["risk_category"],
        badge_class=risk_assessment["badge_class"],
        weather=weather_info,
        anomaly=anom_result,
        factor_breakdown=risk_assessment["factor_breakdown"],
        recommendations=recs,
        model_version="GradientBoosting-v1.0"
    )

@router.get("/predictions")
def get_prediction_history(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    preds = db.query(RiskPrediction).order_by(desc(RiskPrediction.prediction_date)).offset(skip).limit(limit).all()
    out = []
    for p in preds:
        shipment = p.shipment
        out.append({
            "id": p.id,
            "shipment_id": p.shipment_id,
            "tracking_number": shipment.tracking_number if shipment else "N/A",
            "origin": shipment.origin if shipment else "N/A",
            "destination": shipment.destination if shipment else "N/A",
            "overall_risk_score": p.overall_risk_score,
            "risk_category": p.risk_category,
            "ml_probability": p.ml_probability,
            "prediction_date": p.prediction_date.strftime("%Y-%m-%d %H:%M")
        })
    return out
