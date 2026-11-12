"""
NexusGuard Machine Learning Inference and Prediction Engine
Provides unified risk prediction and unsupervised anomaly detection with feature attribution.
"""

import json
import os
import joblib
import numpy as np
import pandas as pd

from app.ml.preprocessor import (
    prepare_features_df,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES
)

class NexusPredictor:
    """Singleton inference class for NexusGuard ML and Anomaly models."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NexusPredictor, cls).__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        models_dir = os.path.join(base_dir, "trained_models")

        model_path = os.path.join(models_dir, "logistics_risk_rf_model.joblib")
        preproc_path = os.path.join(models_dir, "preprocessor.joblib")
        anomaly_path = os.path.join(models_dir, "isolation_forest_anomaly.joblib")
        metrics_path = os.path.join(models_dir, "model_metrics.json")

        if not os.path.exists(model_path) or not os.path.exists(preproc_path):
            raise FileNotFoundError("Trained ML model or preprocessor artifact not found. Please run training script first.")

        self.model = joblib.load(model_path)
        self.preprocessor = joblib.load(preproc_path)
        self.anomaly_model = joblib.load(anomaly_path) if os.path.exists(anomaly_path) else None

        if os.path.exists(metrics_path):
            with open(metrics_path, "r") as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {}

    def predict_risk(self, shipment_dict: dict) -> dict:
        """
        Executes ML risk prediction on input shipment details.
        Returns risk probability, risk category, and key contributing risk factors.
        """
        df = prepare_features_df(shipment_dict)
        X_trans = self.preprocessor.transform(df)

        # Risk Probability from ML model
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X_trans)[0]
            # Probability of delay/disruption class (class 1)
            risk_prob = round(float(probs[1]), 4)
        else:
            pred = int(self.model.predict(X_trans)[0])
            risk_prob = 0.85 if pred == 1 else 0.15

        # Classify into Low, Medium, High
        if risk_prob < 0.30:
            category = "Low"
        elif risk_prob < 0.65:
            category = "Medium"
        else:
            category = "High"

        # Explain contributing factors based on operational values
        contributing_factors = []

        carrier_delay = float(df["carrier_historical_delay_rate"].iloc[0])
        if carrier_delay > 0.28:
            contributing_factors.append({
                "factor": "Carrier Historical Delay Rate",
                "severity": "High",
                "value": f"{carrier_delay * 100:.1f}%",
                "impact": f"Carrier historical delay rate ({carrier_delay*100:.1f}%) significantly exceeds operational target (15%)."
            })
        elif carrier_delay > 0.18:
            contributing_factors.append({
                "factor": "Carrier Historical Delay Rate",
                "severity": "Medium",
                "value": f"{carrier_delay * 100:.1f}%",
                "impact": "Carrier historical reliability is moderately degraded on this corridor."
            })

        weather_idx = float(df["weather_severity_index"].iloc[0])
        if weather_idx > 0.40:
            contributing_factors.append({
                "factor": "Severe Weather Disruption",
                "severity": "High",
                "value": f"{weather_idx * 100:.1f}/100",
                "impact": "Atmospheric conditions (precipitation/wind/freezing) pose severe transit hazards."
            })
        elif weather_idx > 0.20:
            contributing_factors.append({
                "factor": "Adverse Weather Advisory",
                "severity": "Medium",
                "value": f"{weather_idx * 100:.1f}/100",
                "impact": "Moderate atmospheric turbulence or rain may cause checkpoint congestion."
            })

        stops = int(df["transit_stops"].iloc[0])
        if stops >= 3:
            contributing_factors.append({
                "factor": "Multi-Stop Transfer Density",
                "severity": "High" if stops >= 4 else "Medium",
                "value": f"{stops} transfer stops",
                "impact": f"High number of hub transfers ({stops} stops) elevates handling delay probability."
            })

        dist = float(df["distance_km"].iloc[0])
        if dist > 6000:
            contributing_factors.append({
                "factor": "Long-Haul Corridor Exposure",
                "severity": "Medium",
                "value": f"{dist:,.0f} km",
                "impact": "Extended route distance compounds cumulative corridor vulnerability."
            })

        is_perish = int(df["is_perishable"].iloc[0])
        temp_c = float(df["origin_temp_c"].iloc[0])
        if is_perish and (temp_c > 30 or temp_c < 0):
            contributing_factors.append({
                "factor": "Perishable Temperature Sensitivity",
                "severity": "High",
                "value": f"{temp_c:.1f}°C",
                "impact": "Extreme ambient temperature threatens cold chain integrity."
            })

        if not contributing_factors:
            contributing_factors.append({
                "factor": "Corridor Baseline",
                "severity": "Low",
                "value": "Normal parameters",
                "impact": "Operational indicators align with baseline supply chain parameters."
            })

        return {
            "ml_probability": risk_prob,
            "risk_category": category,
            "predicted_class": 1 if risk_prob >= 0.50 else 0,
            "contributing_factors": contributing_factors
        }

    def detect_anomaly(self, shipment_dict: dict) -> dict:
        """
        Evaluates suspicious shipment patterns using trained Isolation Forest
        combined with domain-specific fraud vector heuristics.
        """
        df = prepare_features_df(shipment_dict)

        val = float(df["shipment_value_usd"].iloc[0])
        weight = float(df["weight_kg"].iloc[0])
        dist = float(df["distance_km"].iloc[0])
        stops = int(df["transit_stops"].iloc[0])
        mode = str(df["transport_mode"].iloc[0])
        priority = str(df["priority"].iloc[0])
        cargo = str(df["cargo_type"].iloc[0])
        val_to_weight = val / max(0.1, weight)

        # 1. Isolation Forest Evaluation
        anomaly_cols = [
            "shipment_value_usd", "weight_kg", "distance_km",
            "transit_stops", "carrier_historical_delay_rate", "weather_severity_index"
        ]
        iso_score = 0.0
        iso_pred = 1 # 1 = normal, -1 = anomaly
        if self.anomaly_model is not None:
            features_subset = df[anomaly_cols]
            iso_pred = int(self.anomaly_model.predict(features_subset)[0])
            # Raw decision function: negative values indicate outliers
            raw_score = float(self.anomaly_model.decision_function(features_subset)[0])
            # Normalize to 0-100 anomaly intensity (lower raw score -> higher anomaly intensity)
            iso_score = round(max(0.0, min(100.0, (0.25 - raw_score) * 200)), 1)

        # 2. Heuristic Pattern Detection
        reasons = []
        recommended_actions = []

        # Pattern A: Extreme value-to-weight discrepancy
        if val > 80000 and val_to_weight > 1500 and cargo in ["Apparel & Textiles", "Automotive Parts"]:
            reasons.append(f"Suspicious declared value (${val:,.2f}) for low-density cargo ({cargo}, {weight} kg). Value-to-weight ratio is ${val_to_weight:.1f}/kg.")
            recommended_actions.append("Mandate physical cargo verification and bill-of-lading invoice audit before loading.")

        # Pattern B: Conflicting transport mode and priority
        if mode == "Sea" and priority == "Overnight":
            reasons.append("Logistically incompatible transport mode: 'Overnight' priority assigned to maritime freight.")
            recommended_actions.append("Re-verify shipping manifest instructions with shipper and carrier dispatcher.")

        # Pattern C: Excessive route waypoints
        if stops >= 4 and dist < 1500:
            reasons.append(f"Irregular route topology: {stops} transfer stops scheduled for short regional haul ({dist} km).")
            recommended_actions.append("Inspect route deviation to preclude unauthorized off-manifest diversion.")

        # Pattern D: High value cargo with unverified low-security parameters
        if val > 200000 and mode == "Road" and priority == "Standard":
            reasons.append(f"High-value target shipment (${val:,.2f}) scheduled via unescorted standard road freight.")
            recommended_actions.append("Upgrade transit security to GPS geo-fenced escort and dual-driver mandate.")

        # Pattern E: ML Isolation Forest Outlier
        if iso_pred == -1 and not reasons:
            reasons.append(f"Unsupervised Isolation Forest detected statistical outlier in multi-dimensional space (Anomaly Score: {iso_score}/100).")
            recommended_actions.append("Flag shipment for manual compliance review by senior logistics security specialist.")

        is_suspicious = len(reasons) > 0 or (iso_pred == -1 and iso_score > 60.0)

        if not reasons:
            reasons.append("Shipment parameters adhere to standard operational baselines.")
            recommended_actions.append("Proceed with standard dispatch workflow.")

        return {
            "anomaly_score": iso_score if is_suspicious else round(min(25.0, iso_score), 1),
            "is_suspicious": is_suspicious,
            "status_label": "Suspicious Pattern Requiring Verification" if is_suspicious else "Normal Operating Pattern",
            "detected_reasons": reasons,
            "recommended_actions": recommended_actions
        }

# Global predictor singleton accessor
_predictor_instance = None

def get_predictor():
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = NexusPredictor()
    return _predictor_instance
