"""
NexusGuard Database Seeding Script
Populates SQLite database with default operator accounts, realistic multi-modal consignments,
multi-factor predictions, weather records, anomaly flags, and sample reports.
"""

import sys
import os
import json
import random
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.shipment import Shipment
from app.models.prediction import RiskPrediction
from app.models.weather import WeatherRecord
from app.models.anomaly import AnomalyRecord
from app.models.alert import RiskAlert
from app.models.report import Report
from app.services.auth_service import get_password_hash
from app.services.weather_service import WeatherService, GLOBAL_HUB_COORDINATES
from app.services.risk_scoring_service import MultiFactorRiskEngine
from app.services.recommendation_service import RecommendationEngine
from app.services.report_service import ReportService
from app.ml.predictor import get_predictor

SAMPLE_SHIPMENTS_DATA = [
    {
        "trk": "NXG-882104", "orig": "Shanghai", "dest": "Rotterdam", "dist": 10500.0,
        "mode": "Sea", "cargo": "Electronics", "val": 240000.0, "wt": 2400.0,
        "priority": "Standard", "fragile": True, "perish": False, "stops": 2, "delay_rate": 0.22
    },
    {
        "trk": "NXG-910482", "orig": "Frankfurt", "dest": "New York", "dist": 6200.0,
        "mode": "Air", "cargo": "Pharmaceuticals", "val": 450000.0, "wt": 320.0,
        "priority": "Express", "fragile": True, "perish": True, "stops": 1, "delay_rate": 0.08
    },
    {
        "trk": "NXG-339102", "orig": "Los Angeles", "dest": "Chicago", "dist": 2800.0,
        "mode": "Road", "cargo": "Automotive Parts", "val": 42000.0, "wt": 1850.0,
        "priority": "Standard", "fragile": False, "perish": False, "stops": 1, "delay_rate": 0.14
    },
    {
        "trk": "NXG-774192", "orig": "Dubai", "dest": "London", "dist": 5500.0,
        "mode": "Air", "cargo": "Apparel & Textiles", "val": 350000.0, "wt": 15.0, # Suspicious: High value low weight
        "priority": "Standard", "fragile": False, "perish": False, "stops": 1, "delay_rate": 0.11
    },
    {
        "trk": "NXG-102934", "orig": "Singapore", "dest": "Sydney", "dist": 6300.0,
        "mode": "Sea", "cargo": "Heavy Machinery", "val": 95000.0, "wt": 8500.0,
        "priority": "Standard", "fragile": False, "perish": False, "stops": 2, "delay_rate": 0.16
    },
    {
        "trk": "NXG-551029", "orig": "Tokyo", "dest": "Hong Kong", "dist": 2900.0,
        "mode": "Air", "cargo": "Electronics", "val": 180000.0, "wt": 420.0,
        "priority": "Express", "fragile": True, "perish": False, "stops": 0, "delay_rate": 0.06
    },
    {
        "trk": "NXG-660192", "orig": "Antwerp", "dest": "Hamburg", "dist": 480.0,
        "mode": "Road", "cargo": "Chemicals", "val": 75000.0, "wt": 3400.0,
        "priority": "Standard", "fragile": True, "perish": False, "stops": 0, "delay_rate": 0.09
    },
    {
        "trk": "NXG-440182", "orig": "Miami", "dest": "Houston", "dist": 1600.0,
        "mode": "Road", "cargo": "Perishables & Food", "val": 32000.0, "wt": 2800.0,
        "priority": "Express", "fragile": False, "perish": True, "stops": 1, "delay_rate": 0.28 # High delay
    },
    {
        "trk": "NXG-209481", "orig": "Mumbai", "dest": "Dubai", "dist": 1950.0,
        "mode": "Sea", "cargo": "Apparel & Textiles", "val": 28000.0, "wt": 1200.0,
        "priority": "Overnight", # Suspicious: overnight maritime freight
        "fragile": False, "perish": False, "stops": 1, "delay_rate": 0.18
    },
    {
        "trk": "NXG-119823", "orig": "Toronto", "dest": "Chicago", "dist": 720.0,
        "mode": "Rail", "cargo": "Automotive Parts", "val": 56000.0, "wt": 4100.0,
        "priority": "Standard", "fragile": False, "perish": False, "stops": 0, "delay_rate": 0.10
    },
    {
        "trk": "NXG-881290", "orig": "Busan", "dest": "Rotterdam", "dist": 11200.0,
        "mode": "Sea", "cargo": "Heavy Machinery", "val": 310000.0, "wt": 12500.0,
        "priority": "Standard", "fragile": False, "perish": False, "stops": 3, "delay_rate": 0.32
    },
    {
        "trk": "NXG-448102", "orig": "London", "dest": "Frankfurt", "dist": 650.0,
        "mode": "Air", "cargo": "Pharmaceuticals", "val": 190000.0, "wt": 95.0,
        "priority": "Overnight", "fragile": True, "perish": True, "stops": 0, "delay_rate": 0.05
    }
]

def seed_database():
    print("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Operators
        admin = db.query(User).filter(User.email == "admin@nexusguard.io").first()
        if not admin:
            print("Creating default administrator account: admin@nexusguard.io")
            admin = User(
                name="Admin Lead",
                email="admin@nexusguard.io",
                hashed_password=get_password_hash("admin123"),
                role="Logistics Operations Lead",
                created_at=datetime.utcnow()
            )
            db.add(admin)

        sec_officer = db.query(User).filter(User.email == "security@nexusguard.io").first()
        if not sec_officer:
            print("Creating security officer account: security@nexusguard.io")
            sec_officer = User(
                name="Sarah Vance",
                email="security@nexusguard.io",
                hashed_password=get_password_hash("security123"),
                role="Supply Chain Security Officer",
                created_at=datetime.utcnow()
            )
            db.add(sec_officer)

        db.commit()

        # Check existing shipments
        existing_count = db.query(Shipment).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} shipments. Skipping demo seed.")
            return

        print("Seeding demo consignments with live weather and ML predictions...")
        predictor = get_predictor()

        first_shipment_obj = None
        first_pred_obj = None
        first_weather_dict = None
        first_anom_dict = None
        first_recs = None

        for item in SAMPLE_SHIPMENTS_DATA:
            o_info = GLOBAL_HUB_COORDINATES.get(item["orig"], {"lat": 40.7128, "lng": -74.0060})
            d_info = GLOBAL_HUB_COORDINATES.get(item["dest"], {"lat": 51.9244, "lng": 4.4777})

            # Live Weather
            w = WeatherService.get_live_weather(item["orig"])
            temp_c = w.get("temperature_c") or 18.0
            precip_mm = w.get("precipitation_mm") or 0.0
            wind_kmh = w.get("wind_speed_kmh") or 12.0
            w_severity = w.get("severity_index", 0.05)

            # ML Predict & Anomaly
            ml_input = {
                "origin": item["orig"],
                "destination": item["dest"],
                "distance_km": item["dist"],
                "transport_mode": item["mode"],
                "cargo_type": item["cargo"],
                "shipment_value_usd": item["val"],
                "weight_kg": item["wt"],
                "priority": item["priority"],
                "is_fragile": 1 if item["fragile"] else 0,
                "is_perishable": 1 if item["perish"] else 0,
                "transit_stops": item["stops"],
                "carrier_historical_delay_rate": item["delay_rate"],
                "origin_temp_c": temp_c,
                "origin_precip_mm": precip_mm,
                "origin_wind_kmh": wind_kmh,
                "weather_severity_index": w_severity,
                "route_risk_index": 0.15
            }

            ml_res = predictor.predict_risk(ml_input)
            anom_res = predictor.detect_anomaly(ml_input)

            # Multi-factor score
            risk_res = MultiFactorRiskEngine.calculate_composite_risk(
                ml_probability=ml_res["ml_probability"],
                weather_severity=w_severity,
                distance_km=item["dist"],
                transit_stops=item["stops"],
                carrier_historical_delay_rate=item["delay_rate"],
                anomaly_score=anom_res["anomaly_score"],
                is_suspicious=anom_res["is_suspicious"]
            )

            # Recommendations
            recs = RecommendationEngine.generate_recommendations(
                risk_category=risk_res["risk_category"],
                overall_risk_score=risk_res["overall_risk_score"],
                weather_info=w,
                anomaly_info=anom_res,
                shipment_data=ml_input
            )

            now = datetime.utcnow() - timedelta(hours=random.randint(1, 48))
            exp_date = now + timedelta(days=random.randint(2, 10))

            shipment = Shipment(
                tracking_number=item["trk"],
                origin=item["orig"],
                destination=item["dest"],
                origin_lat=o_info["lat"],
                origin_lng=o_info["lng"],
                dest_lat=d_info["lat"],
                dest_lng=d_info["lng"],
                distance_km=item["dist"],
                shipment_value_usd=item["val"],
                weight_kg=item["wt"],
                transport_mode=item["mode"],
                cargo_type=item["cargo"],
                priority=item["priority"],
                is_fragile=item["fragile"],
                is_perishable=item["perish"],
                transit_stops=item["stops"],
                carrier_name="Nexus Express Global",
                carrier_historical_delay_rate=item["delay_rate"],
                status="In Transit",
                shipment_date=now,
                expected_delivery_date=exp_date,
                created_at=now,
                user_id=admin.id
            )
            db.add(shipment)
            db.commit()
            db.refresh(shipment)

            pred = RiskPrediction(
                shipment_id=shipment.id,
                ml_probability=ml_res["ml_probability"],
                overall_risk_score=risk_res["overall_risk_score"],
                risk_category=risk_res["risk_category"],
                contributing_factors_json=json.dumps(risk_res["factor_breakdown"]),
                weather_risk_score=risk_res["components"]["weather_component"],
                anomaly_factor_score=risk_res["components"]["anomaly_component"],
                model_version="GradientBoosting-v1.0",
                prediction_date=now
            )
            db.add(pred)

            weather_rec = WeatherRecord(
                shipment_id=shipment.id,
                location_name=item["orig"],
                latitude=o_info["lat"],
                longitude=o_info["lng"],
                temperature_c=temp_c,
                precipitation_mm=precip_mm,
                wind_speed_kmh=wind_kmh,
                weather_code=w.get("weather_code", 0),
                weather_description=w.get("weather_description", "Fair"),
                severity_index=w_severity,
                weather_retrieval_time=now
            )
            db.add(weather_rec)

            anom_rec = AnomalyRecord(
                shipment_id=shipment.id,
                anomaly_score=anom_res["anomaly_score"],
                is_suspicious=anom_res["is_suspicious"],
                detection_result=anom_res["status_label"],
                explanation_json=json.dumps(anom_res["detected_reasons"]),
                recommended_actions_json=json.dumps(anom_res["recommended_actions"]),
                investigation_status="Under Review" if anom_res["is_suspicious"] else "Normal Operating Pattern",
                created_at=now
            )
            db.add(anom_rec)

            if risk_res["risk_category"] == "High Risk" or anom_res["is_suspicious"]:
                alert = RiskAlert(
                    shipment_id=shipment.id,
                    alert_level="Critical" if anom_res["is_suspicious"] else "Warning",
                    title=f"Elevated Risk Warning - Consignment {shipment.tracking_number}",
                    message=f"Consignment {shipment.tracking_number} ({item['orig']} → {item['dest']}) registered composite risk {risk_res['overall_risk_score']}/100. {anom_res['detected_reasons'][0]}",
                    is_read=False,
                    created_at=now
                )
                db.add(alert)

            db.commit()

            if first_shipment_obj is None:
                first_shipment_obj = shipment
                first_pred_obj = pred
                first_weather_dict = w
                first_anom_dict = anom_res
                first_recs = recs

        # Generate sample PDF report for the first shipment
        if first_shipment_obj:
            print("Compiling sample demonstration PDF report...")
            pdf_path = ReportService.generate_pdf_report(
                shipment=first_shipment_obj,
                prediction=first_pred_obj,
                weather_info=first_weather_dict,
                anomaly_info=first_anom_dict,
                recommendations=first_recs
            )
            rep = Report(
                shipment_id=first_shipment_obj.id,
                report_title=f"Initial Risk Certification - {first_shipment_obj.tracking_number}",
                file_path=pdf_path,
                generated_date=datetime.utcnow()
            )
            db.add(rep)
            db.commit()

        print("Database successfully seeded with realistic logistics data!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
