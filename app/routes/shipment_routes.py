"""
Shipment Management REST API Routes
"""

import json
import math
import random
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.shipment import Shipment
from app.models.prediction import RiskPrediction
from app.models.weather import WeatherRecord
from app.models.anomaly import AnomalyRecord
from app.models.alert import RiskAlert
from app.schemas.shipment_schemas import ShipmentCreate, ShipmentResponse
from app.services.weather_service import WeatherService, GLOBAL_HUB_COORDINATES
from app.services.risk_scoring_service import MultiFactorRiskEngine
from app.services.recommendation_service import RecommendationEngine
from app.ml.predictor import get_predictor

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])

def calc_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

@router.get("", response_model=List[dict])
def list_shipments(
    skip: int = 0,
    limit: int = 100,
    transport_mode: Optional[str] = None,
    risk_category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Shipment).order_by(desc(Shipment.created_at))

    if transport_mode and transport_mode != "All":
        query = query.filter(Shipment.transport_mode == transport_mode)
    if status and status != "All":
        query = query.filter(Shipment.status == status)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Shipment.tracking_number.ilike(search_filter)) |
            (Shipment.origin.ilike(search_filter)) |
            (Shipment.destination.ilike(search_filter)) |
            (Shipment.cargo_type.ilike(search_filter))
        )

    shipments = query.offset(skip).limit(limit).all()

    results = []
    for s in shipments:
        latest_pred = db.query(RiskPrediction).filter(RiskPrediction.shipment_id == s.id).order_by(desc(RiskPrediction.prediction_date)).first()
        latest_anom = db.query(AnomalyRecord).filter(AnomalyRecord.shipment_id == s.id).order_by(desc(AnomalyRecord.created_at)).first()

        item = {
            "id": s.id,
            "tracking_number": s.tracking_number,
            "origin": s.origin,
            "destination": s.destination,
            "distance_km": s.distance_km,
            "shipment_value_usd": s.shipment_value_usd,
            "weight_kg": s.weight_kg,
            "transport_mode": s.transport_mode,
            "cargo_type": s.cargo_type,
            "priority": s.priority,
            "status": s.status,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "risk_score": latest_pred.overall_risk_score if latest_pred else 25.0,
            "risk_category": latest_pred.risk_category if latest_pred else "Low Risk",
            "is_suspicious": latest_anom.is_suspicious if latest_anom else False,
            "anomaly_score": latest_anom.anomaly_score if latest_anom else 0.0,
            "investigation_status": latest_anom.investigation_status if latest_anom else "Normal"
        }

        if risk_category and risk_category != "All":
            if item["risk_category"] != risk_category:
                continue

        results.append(item)

    return results

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_shipment(payload: ShipmentCreate, db: Session = Depends(get_db)):
    # 1. Resolve coordinates
    o_coords = WeatherService.resolve_coordinates(payload.origin) or {"lat": 40.7128, "lng": -74.0060, "city": payload.origin}
    d_coords = WeatherService.resolve_coordinates(payload.destination) or {"lat": 51.9244, "lng": 4.4777, "city": payload.destination}

    # 2. Distance calculation
    dist = payload.distance_km
    if not dist or dist <= 0:
        dist = calc_haversine(o_coords["lat"], o_coords["lng"], d_coords["lat"], d_coords["lng"])
        if dist < 50:
            dist = 450.0 # sensible minimum

    # 3. Tracking number
    trk = payload.tracking_number
    if not trk:
        trk = f"NXG-{random.randint(100000, 999999)}"

    # Check uniqueness
    existing = db.query(Shipment).filter(Shipment.tracking_number == trk).first()
    if existing:
        trk = f"NXG-{random.randint(100000, 999999)}"

    # 4. Fetch real-time weather from Open-Meteo
    weather_info = WeatherService.get_live_weather(payload.origin)
    temp_c = weather_info.get("temperature_c") or 20.0
    precip_mm = weather_info.get("precipitation_mm") or 0.0
    wind_kmh = weather_info.get("wind_speed_kmh") or 12.0
    w_severity = weather_info.get("severity_index", 0.05)

    # 5. ML Predictor & Anomaly Detection
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

    # 6. Multi-Factor Risk Engine
    risk_assessment = MultiFactorRiskEngine.calculate_composite_risk(
        ml_probability=ml_result["ml_probability"],
        weather_severity=w_severity,
        distance_km=dist,
        transit_stops=payload.transit_stops,
        carrier_historical_delay_rate=payload.carrier_historical_delay_rate or 0.12,
        anomaly_score=anom_result["anomaly_score"],
        is_suspicious=anom_result["is_suspicious"]
    )

    # 7. AI Recommendations
    recs = RecommendationEngine.generate_recommendations(
        risk_category=risk_assessment["risk_category"],
        overall_risk_score=risk_assessment["overall_risk_score"],
        weather_info=weather_info,
        anomaly_info=anom_result,
        shipment_data=ml_input
    )

    # 8. Persist Shipment in Database
    now = datetime.utcnow()
    exp_date = now + timedelta(days=payload.expected_delivery_days or 4)

    new_shipment = Shipment(
        tracking_number=trk,
        origin=payload.origin,
        destination=payload.destination,
        origin_lat=o_coords["lat"],
        origin_lng=o_coords["lng"],
        dest_lat=d_coords["lat"],
        dest_lng=d_coords["lng"],
        distance_km=dist,
        shipment_value_usd=payload.shipment_value_usd,
        weight_kg=payload.weight_kg,
        transport_mode=payload.transport_mode,
        cargo_type=payload.cargo_type,
        priority=payload.priority,
        is_fragile=payload.is_fragile,
        is_perishable=payload.is_perishable,
        transit_stops=payload.transit_stops,
        carrier_name=payload.carrier_name or "Nexus Express Global",
        carrier_historical_delay_rate=payload.carrier_historical_delay_rate or 0.12,
        status="In Transit",
        shipment_date=now,
        expected_delivery_date=exp_date,
        created_at=now
    )
    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)

    # Persist Prediction
    pred_record = RiskPrediction(
        shipment_id=new_shipment.id,
        ml_probability=ml_result["ml_probability"],
        overall_risk_score=risk_assessment["overall_risk_score"],
        risk_category=risk_assessment["risk_category"],
        contributing_factors_json=json.dumps(risk_assessment["factor_breakdown"]),
        weather_risk_score=risk_assessment["components"]["weather_component"],
        anomaly_factor_score=risk_assessment["components"]["anomaly_component"],
        model_version="GradientBoosting-v1.0",
        prediction_date=now
    )
    db.add(pred_record)

    # Persist Weather Record
    weather_record = WeatherRecord(
        shipment_id=new_shipment.id,
        location_name=payload.origin,
        latitude=o_coords["lat"],
        longitude=o_coords["lng"],
        temperature_c=temp_c,
        precipitation_mm=precip_mm,
        wind_speed_kmh=wind_kmh,
        weather_code=weather_info.get("weather_code", 0),
        weather_description=weather_info.get("weather_description", "Fair"),
        severity_index=w_severity,
        weather_retrieval_time=now
    )
    db.add(weather_record)

    # Persist Anomaly Record
    anom_record = AnomalyRecord(
        shipment_id=new_shipment.id,
        anomaly_score=anom_result["anomaly_score"],
        is_suspicious=anom_result["is_suspicious"],
        detection_result=anom_result["status_label"],
        explanation_json=json.dumps(anom_result["detected_reasons"]),
        recommended_actions_json=json.dumps(anom_result["recommended_actions"]),
        investigation_status="Under Review" if anom_result["is_suspicious"] else "Normal Operating Pattern",
        created_at=now
    )
    db.add(anom_record)

    # Proactive Risk Alert if High Risk or Suspicious
    if risk_assessment["risk_category"] == "High Risk" or anom_result["is_suspicious"]:
        alert = RiskAlert(
            shipment_id=new_shipment.id,
            alert_level="Critical" if anom_result["is_suspicious"] else "Warning",
            title=f"High Risk Alert for Shipment {trk}",
            message=f"Shipment {trk} from {payload.origin} to {payload.destination} triggered an elevated risk assessment ({risk_assessment['overall_risk_score']}/100). {anom_result['detected_reasons'][0]}",
            is_read=False,
            created_at=now
        )
        db.add(alert)

    db.commit()

    return {
        "success": True,
        "shipment_id": new_shipment.id,
        "tracking_number": new_shipment.tracking_number,
        "overall_risk_score": risk_assessment["overall_risk_score"],
        "risk_category": risk_assessment["risk_category"],
        "badge_class": risk_assessment["badge_class"],
        "ml_probability": ml_result["ml_probability"],
        "weather": weather_info,
        "anomaly": anom_result,
        "factor_breakdown": risk_assessment["factor_breakdown"],
        "recommendations": recs
    }

@router.get("/{id}", response_model=dict)
def get_shipment_details(id: int, db: Session = Depends(get_db)):
    shipment = db.query(Shipment).filter(Shipment.id == id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found.")

    latest_pred = db.query(RiskPrediction).filter(RiskPrediction.shipment_id == id).order_by(desc(RiskPrediction.prediction_date)).first()
    latest_weather = db.query(WeatherRecord).filter(WeatherRecord.shipment_id == id).order_by(desc(WeatherRecord.weather_retrieval_time)).first()
    latest_anom = db.query(AnomalyRecord).filter(AnomalyRecord.shipment_id == id).order_by(desc(AnomalyRecord.created_at)).first()

    factors = []
    if latest_pred and latest_pred.contributing_factors_json:
        try:
            factors = json.loads(latest_pred.contributing_factors_json)
        except Exception:
            factors = []

    anom_reasons = []
    anom_actions = []
    if latest_anom:
        if latest_anom.explanation_json:
            try:
                anom_reasons = json.loads(latest_anom.explanation_json)
            except Exception:
                pass
        if latest_anom.recommended_actions_json:
            try:
                anom_actions = json.loads(latest_anom.recommended_actions_json)
            except Exception:
                pass

    return {
        "shipment": {
            "id": shipment.id,
            "tracking_number": shipment.tracking_number,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "origin_lat": shipment.origin_lat,
            "origin_lng": shipment.origin_lng,
            "dest_lat": shipment.dest_lat,
            "dest_lng": shipment.dest_lng,
            "distance_km": shipment.distance_km,
            "shipment_value_usd": shipment.shipment_value_usd,
            "weight_kg": shipment.weight_kg,
            "transport_mode": shipment.transport_mode,
            "cargo_type": shipment.cargo_type,
            "priority": shipment.priority,
            "is_fragile": shipment.is_fragile,
            "is_perishable": shipment.is_perishable,
            "transit_stops": shipment.transit_stops,
            "carrier_name": shipment.carrier_name,
            "carrier_historical_delay_rate": shipment.carrier_historical_delay_rate,
            "status": shipment.status,
            "shipment_date": shipment.shipment_date.strftime("%Y-%m-%d %H:%M") if shipment.shipment_date else "",
            "expected_delivery_date": shipment.expected_delivery_date.strftime("%Y-%m-%d %H:%M") if shipment.expected_delivery_date else "",
            "created_at": shipment.created_at.strftime("%Y-%m-%d %H:%M")
        },
        "prediction": {
            "overall_risk_score": latest_pred.overall_risk_score if latest_pred else 25.0,
            "risk_category": latest_pred.risk_category if latest_pred else "Low Risk",
            "ml_probability": latest_pred.ml_probability if latest_pred else 0.15,
            "factor_breakdown": factors
        },
        "weather": {
            "location_name": latest_weather.location_name if latest_weather else shipment.origin,
            "temperature_c": latest_weather.temperature_c if latest_weather else 20.0,
            "precipitation_mm": latest_weather.precipitation_mm if latest_weather else 0.0,
            "wind_speed_kmh": latest_weather.wind_speed_kmh if latest_weather else 10.0,
            "weather_description": latest_weather.weather_description if latest_weather else "Clear",
            "severity_index": latest_weather.severity_index if latest_weather else 0.05
        },
        "anomaly": {
            "anomaly_score": latest_anom.anomaly_score if latest_anom else 0.0,
            "is_suspicious": latest_anom.is_suspicious if latest_anom else False,
            "detection_result": latest_anom.detection_result if latest_anom else "Normal",
            "investigation_status": latest_anom.investigation_status if latest_anom else "Normal",
            "detected_reasons": anom_reasons,
            "recommended_actions": anom_actions
        }
    }
