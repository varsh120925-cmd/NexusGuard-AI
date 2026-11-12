"""
NexusGuard Machine Learning Preprocessing and Feature Engineering Module
Standardizes and encodes logistics shipment features for model training and live inference.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.pipeline import Pipeline

NUMERICAL_FEATURES = [
    "distance_km",
    "shipment_value_usd",
    "weight_kg",
    "transit_stops",
    "carrier_historical_delay_rate",
    "origin_temp_c",
    "origin_precip_mm",
    "origin_wind_kmh",
    "weather_severity_index",
    "route_risk_index",
    "val_weight_ratio",
    "stop_density"
]

CATEGORICAL_FEATURES = [
    "transport_mode",
    "cargo_type",
    "priority",
    "is_fragile",
    "is_perishable"
]

class LogisticsFeatureEngineer(BaseEstimator, TransformerMixin):
    """Adds domain-specific supply chain and logistics features."""
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_df = X.copy()
        if not isinstance(X_df, pd.DataFrame):
            X_df = pd.DataFrame(X_df)

        # 1. Value to weight ratio (vital for fraud & density risk)
        val = pd.to_numeric(X_df["shipment_value_usd"], errors="coerce").fillna(500.0)
        weight = pd.to_numeric(X_df["weight_kg"], errors="coerce").fillna(10.0).clip(lower=0.1)
        X_df["val_weight_ratio"] = val / weight

        # 2. Stop density (stops per 1000km)
        dist = pd.to_numeric(X_df["distance_km"], errors="coerce").fillna(500.0).clip(lower=50.0)
        stops = pd.to_numeric(X_df["transit_stops"], errors="coerce").fillna(0.0)
        X_df["stop_density"] = (stops / (dist / 1000.0)).clip(upper=10.0)

        return X_df

def build_preprocessor_pipeline():
    """Builds a complete Scikit-Learn preprocessing pipeline with feature engineering."""
    numeric_transformer = Pipeline(steps=[
        ("scaler", RobustScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    column_preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERICAL_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES)
        ],
        remainder="drop"
    )

    full_pipeline = Pipeline(steps=[
        ("feature_engineering", LogisticsFeatureEngineer()),
        ("preprocessor", column_preprocessor)
    ])

    return full_pipeline

def prepare_features_df(raw_data):
    """
    Normalizes a single record or list/dataframe into the expected format.
    Accepts dict or pandas DataFrame.
    """
    if isinstance(raw_data, dict):
        df = pd.DataFrame([raw_data])
    elif isinstance(raw_data, list):
        df = pd.DataFrame(raw_data)
    elif isinstance(raw_data, pd.DataFrame):
        df = raw_data.copy()
    else:
        raise ValueError("Unsupported data format for feature preparation.")

    # Defaults for optional / missing columns
    defaults = {
        "distance_km": 500.0,
        "transport_mode": "Road",
        "cargo_type": "Electronics",
        "shipment_value_usd": 1500.0,
        "weight_kg": 25.0,
        "priority": "Standard",
        "is_fragile": 0,
        "is_perishable": 0,
        "transit_stops": 1,
        "carrier_historical_delay_rate": 0.15,
        "origin_temp_c": 20.0,
        "origin_precip_mm": 0.0,
        "origin_wind_kmh": 12.0,
        "weather_severity_index": 0.10,
        "route_risk_index": 0.15
    }

    for col, default_val in defaults.items():
        if col not in df.columns:
            df[col] = default_val
        else:
            df[col] = df[col].fillna(default_val)

    # Convert types
    for num_col in ["distance_km", "shipment_value_usd", "weight_kg", "transit_stops",
                    "carrier_historical_delay_rate", "origin_temp_c", "origin_precip_mm",
                    "origin_wind_kmh", "weather_severity_index", "route_risk_index"]:
        df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(defaults[num_col])

    for cat_col in ["is_fragile", "is_perishable"]:
        df[cat_col] = pd.to_numeric(df[cat_col], errors="coerce").fillna(0).astype(int)

    for str_col in ["transport_mode", "cargo_type", "priority"]:
        df[str_col] = df[str_col].astype(str)

    return df
