"""
REST API Endpoints Integration Tests
"""

import uuid

def test_api_predict_risk(client):
    resp = client.post("/api/predict-risk", json={
        "origin": "Frankfurt",
        "destination": "London",
        "transport_mode": "Air",
        "cargo_type": "Electronics",
        "shipment_value_usd": 45000.0,
        "weight_kg": 320.0,
        "priority": "Express",
        "transit_stops": 0,
        "carrier_historical_delay_rate": 0.08
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_risk_score" in data
    assert "ml_probability" in data
    assert "weather" in data
    assert "anomaly" in data
    assert len(data["factor_breakdown"]) > 0

def test_api_create_and_list_shipments(client):
    unique_trk = f"NXG-TEST-{uuid.uuid4().hex[:6].upper()}"
    create_resp = client.post("/api/shipments", json={
        "tracking_number": unique_trk,
        "origin": "Tokyo",
        "destination": "Singapore",
        "transport_mode": "Air",
        "cargo_type": "Pharmaceuticals",
        "shipment_value_usd": 120000.0,
        "weight_kg": 400.0,
        "priority": "Standard",
        "transit_stops": 1
    })
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["tracking_number"] == unique_trk

    # List shipments and confirm presence
    list_resp = client.get(f"/api/shipments?search={unique_trk}")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert items[0]["tracking_number"] == unique_trk

def test_api_dashboard_summary(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "charts" in data
    assert "total_shipments" in data["kpis"]
    assert data["kpis"]["total_shipments"] > 0
