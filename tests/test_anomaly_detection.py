"""
Fraud and Outlier Anomaly Detection Tests
"""

from app.ml.predictor import get_predictor

def test_anomaly_detection_normal_shipment():
    predictor = get_predictor()
    normal_shipment = {
        "shipment_value_usd": 25000.0,
        "weight_kg": 450.0,
        "distance_km": 1200.0,
        "transit_stops": 1,
        "transport_mode": "Road",
        "cargo_type": "Automotive Parts",
        "priority": "Standard",
        "carrier_historical_delay_rate": 0.12,
        "weather_severity_index": 0.10
    }
    anom = predictor.detect_anomaly(normal_shipment)
    assert "anomaly_score" in anom
    assert "is_suspicious" in anom
    assert "status_label" in anom
    assert anom["is_suspicious"] is False

def test_anomaly_detection_suspicious_patterns():
    predictor = get_predictor()

    # Pattern A: Extremely high value for tiny weight in Apparel
    suspicious_val_weight = {
        "shipment_value_usd": 400000.0,
        "weight_kg": 5.0,
        "distance_km": 1200.0,
        "transit_stops": 1,
        "transport_mode": "Road",
        "cargo_type": "Apparel & Textiles",
        "priority": "Standard",
        "carrier_historical_delay_rate": 0.12,
        "weather_severity_index": 0.10
    }
    anom_a = predictor.detect_anomaly(suspicious_val_weight)
    assert anom_a["is_suspicious"] is True
    assert any("suspicious declared value" in r.lower() or "declared cargo value" in r.lower() or "value" in r.lower() for r in anom_a["detected_reasons"])
    assert len(anom_a["recommended_actions"]) > 0

    # Pattern B: Overnight Sea freight
    suspicious_mode_priority = {
        "shipment_value_usd": 15000.0,
        "weight_kg": 500.0,
        "distance_km": 3000.0,
        "transit_stops": 1,
        "transport_mode": "Sea",
        "cargo_type": "General",
        "priority": "Overnight",
        "carrier_historical_delay_rate": 0.10,
        "weather_severity_index": 0.10
    }
    anom_b = predictor.detect_anomaly(suspicious_mode_priority)
    assert anom_b["is_suspicious"] is True
    assert any("incompatible" in r.lower() or "overnight" in r.lower() for r in anom_b["detected_reasons"])
