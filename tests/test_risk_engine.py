"""
Multi-Factor Risk Engine and AI Recommendations Tests
"""

from app.services.risk_scoring_service import MultiFactorRiskEngine
from app.services.recommendation_service import RecommendationEngine

def test_risk_scoring_calculation_bounds():
    # Low risk inputs
    low_res = MultiFactorRiskEngine.calculate_composite_risk(
        ml_probability=0.08,
        weather_severity=0.05,
        distance_km=450.0,
        transit_stops=0,
        carrier_historical_delay_rate=0.06,
        anomaly_score=10.0,
        is_suspicious=False
    )
    assert 0.0 <= low_res["overall_risk_score"] <= 100.0
    assert low_res["risk_category"] == "Low Risk"

    # High risk inputs
    high_res = MultiFactorRiskEngine.calculate_composite_risk(
        ml_probability=0.92,
        weather_severity=0.85,
        distance_km=11000.0,
        transit_stops=4,
        carrier_historical_delay_rate=0.45,
        anomaly_score=85.0,
        is_suspicious=True
    )
    assert high_res["overall_risk_score"] >= 70.0
    assert high_res["risk_category"] == "High Risk"
    assert len(high_res["factor_breakdown"]) == 5

def test_ai_recommendation_generation():
    recs = RecommendationEngine.generate_recommendations(
        risk_category="High Risk",
        overall_risk_score=78.5,
        weather_info={"severity_index": 0.45, "weather_description": "Thunderstorm", "temperature_c": -6.0},
        anomaly_info={"is_suspicious": True, "recommended_actions": ["Audit customs invoice declaration."]},
        shipment_data={"transport_mode": "Air", "is_perishable": True, "transit_stops": 3, "carrier_historical_delay_rate": 0.30}
    )
    assert len(recs) >= 3
    actions = [r["action"] for r in recs]
    assert any("Weather" in a or "Cold-Chain" in a for a in actions)
