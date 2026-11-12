"""
Machine Learning Preprocessing and Inference Tests
"""

import pandas as pd
from app.ml.preprocessor import prepare_features_df, build_preprocessor_pipeline, LogisticsFeatureEngineer
from app.ml.predictor import get_predictor

def test_feature_engineering_and_preprocessing():
    sample_data = {
        "distance_km": 1500.0,
        "shipment_value_usd": 75000.0,
        "weight_kg": 250.0,
        "transport_mode": "Road",
        "cargo_type": "Electronics",
        "priority": "Standard",
        "is_fragile": 1,
        "is_perishable": 0,
        "transit_stops": 2,
        "carrier_historical_delay_rate": 0.15,
        "origin_temp_c": 18.0,
        "origin_precip_mm": 2.5,
        "origin_wind_kmh": 15.0,
        "weather_severity_index": 0.12,
        "route_risk_index": 0.20
    }
    raw_df = prepare_features_df(sample_data)
    assert "distance_km" in raw_df.columns
    assert "shipment_value_usd" in raw_df.columns

    # Verify Feature Engineering transformer
    fe = LogisticsFeatureEngineer()
    fe_df = fe.transform(raw_df)
    assert "val_weight_ratio" in fe_df.columns
    assert "stop_density" in fe_df.columns
    assert fe_df["val_weight_ratio"].iloc[0] == 75000.0 / 250.0

    # Verify Complete Pipeline
    pipeline = build_preprocessor_pipeline()
    transformed = pipeline.fit_transform(raw_df)
    assert transformed.shape[0] == 1
    assert transformed.shape[1] > 10

def test_ml_prediction_inference():
    predictor = get_predictor()
    
    # Low risk test scenario
    low_risk_input = {
        "origin": "Frankfurt",
        "destination": "London",
        "distance_km": 650.0,
        "transport_mode": "Air",
        "cargo_type": "Automotive Parts",
        "shipment_value_usd": 15000.0,
        "weight_kg": 120.0,
        "priority": "Express",
        "is_fragile": 0,
        "is_perishable": 0,
        "transit_stops": 0,
        "carrier_historical_delay_rate": 0.05,
        "origin_temp_c": 16.0,
        "origin_precip_mm": 0.0,
        "origin_wind_kmh": 10.0,
        "weather_severity_index": 0.05,
        "route_risk_index": 0.10
    }
    res = predictor.predict_risk(low_risk_input)
    assert "ml_probability" in res
    assert 0.0 <= res["ml_probability"] <= 1.0
    assert res["risk_category"] in ["Low", "Medium", "High"]
    assert len(res["contributing_factors"]) > 0

    # High risk scenario
    high_risk_input = {
        "origin": "Shanghai",
        "destination": "Rotterdam",
        "distance_km": 11500.0,
        "transport_mode": "Sea",
        "cargo_type": "Perishables & Food",
        "shipment_value_usd": 85000.0,
        "weight_kg": 8500.0,
        "priority": "Standard",
        "is_fragile": 1,
        "is_perishable": 1,
        "transit_stops": 4,
        "carrier_historical_delay_rate": 0.40,
        "origin_temp_c": -12.0, # sub-zero freezing
        "origin_precip_mm": 25.0, # heavy precipitation
        "origin_wind_kmh": 70.0, # gale winds
        "weather_severity_index": 0.85,
        "route_risk_index": 0.65
    }
    res_high = predictor.predict_risk(high_risk_input)
    assert res_high["ml_probability"] > res["ml_probability"]
    assert res_high["risk_category"] in ["Medium", "High"]
