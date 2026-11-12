"""
Multi-Factor Risk Scoring Engine
Calculates transparent composite shipment risk scores (0 - 100) combining
Machine Learning delay probability, live atmospheric impact, route vulnerability,
carrier track record, and anomaly detection intensity.
"""

from typing import Dict, Any, List

class MultiFactorRiskEngine:
    """
    Transparent Risk Scoring Engine.
    Formula:
      Risk Score = (ML_Prob * 45) + (Weather_Index * 20) + (Route_Index * 15) + (Carrier_Factor * 10) + (Anomaly_Factor * 10)
    Result bounded to [0, 100].
    """

    @classmethod
    def calculate_composite_risk(
        cls,
        ml_probability: float,
        weather_severity: float,
        distance_km: float,
        transit_stops: int,
        carrier_historical_delay_rate: float,
        anomaly_score: float,
        is_suspicious: bool
    ) -> Dict[str, Any]:

        # 1. ML Probability Component (45% weight)
        ml_component = round(ml_probability * 45.0, 2)

        # 2. Weather Impact Component (20% weight)
        weather_component = round(min(1.0, max(0.0, weather_severity)) * 20.0, 2)

        # 3. Route Corridor & Distance Factor (15% weight)
        # Combines transit distance (up to 12,000km) and transfer stops
        dist_factor = min(1.0, distance_km / 10000.0) * 0.6
        stops_factor = min(1.0, transit_stops / 4.0) * 0.4
        route_component = round((dist_factor + stops_factor) * 15.0, 2)

        # 4. Carrier Reliability Factor (10% weight)
        # Normalizes carrier historical rate (0.0 to 0.5) to a 10-point scale
        carrier_component = round(min(1.0, max(0.0, carrier_historical_delay_rate / 0.40)) * 10.0, 2)

        # 5. Anomaly / Suspicious Score Factor (10% weight)
        anomaly_ratio = (anomaly_score / 100.0) if is_suspicious else (anomaly_score / 200.0)
        anomaly_component = round(min(1.0, max(0.0, anomaly_ratio)) * 10.0, 2)

        # Total Composite Score
        total_score = round(ml_component + weather_component + route_component + carrier_component + anomaly_component, 1)
        total_score = max(0.0, min(100.0, total_score))

        # Risk Classification
        if total_score < 40.0:
            category = "Low Risk"
            badge_class = "success"
        elif total_score < 70.0:
            category = "Medium Risk"
            badge_class = "warning"
        else:
            category = "High Risk"
            badge_class = "danger"

        factor_breakdown = [
            {
                "dimension": "Machine Learning Prediction",
                "weight_percent": 45,
                "score_contribution": ml_component,
                "raw_value": f"{ml_probability * 100:.1f}% delay probability",
                "status": "High" if ml_component > 25 else ("Medium" if ml_component > 12 else "Low")
            },
            {
                "dimension": "Real-Time Atmospheric Impact",
                "weight_percent": 20,
                "score_contribution": weather_component,
                "raw_value": f"{weather_severity * 100:.1f}/100 severity index",
                "status": "High" if weather_component > 10 else ("Medium" if weather_component > 5 else "Low")
            },
            {
                "dimension": "Route Distance & Multi-Stop Exposure",
                "weight_percent": 15,
                "score_contribution": route_component,
                "raw_value": f"{distance_km:,.0f} km, {transit_stops} stops",
                "status": "High" if route_component > 9 else ("Medium" if route_component > 5 else "Low")
            },
            {
                "dimension": "Carrier Operational Reliability",
                "weight_percent": 10,
                "score_contribution": carrier_component,
                "raw_value": f"{carrier_historical_delay_rate * 100:.1f}% delay rate",
                "status": "High" if carrier_component > 6 else ("Medium" if carrier_component > 3 else "Low")
            },
            {
                "dimension": "Anomaly & Fraud Risk Vector",
                "weight_percent": 10,
                "score_contribution": anomaly_component,
                "raw_value": f"{anomaly_score:.1f}/100 intensity" + (" (Suspicious)" if is_suspicious else " (Baseline)"),
                "status": "Critical" if is_suspicious else "Low"
            }
        ]

        return {
            "overall_risk_score": total_score,
            "risk_category": category,
            "badge_class": badge_class,
            "components": {
                "ml_component": ml_component,
                "weather_component": weather_component,
                "route_component": route_component,
                "carrier_component": carrier_component,
                "anomaly_component": anomaly_component
            },
            "factor_breakdown": factor_breakdown
        }
