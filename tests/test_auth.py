"""
Authentication and Security Tests
"""

import uuid
from app.services.auth_service import get_password_hash, verify_password, create_access_token

def test_password_hashing():
    raw_pass = "SecurePass2026!"
    hashed = get_password_hash(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_creation():
    payload = {"sub": "test@nexusguard.io", "name": "Test User"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    assert len(token) > 20

def test_api_register_and_login(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@nexusguard.io"
    
    # 1. Register
    reg_resp = client.post("/api/register", json={
        "name": "Integration Tester",
        "email": unique_email,
        "password": "Password123!",
        "role": "Logistics Analyst"
    })
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert "access_token" in data
    assert data["user_email"] == unique_email

    # 2. Duplicate registration should fail
    dup_resp = client.post("/api/register", json={
        "name": "Integration Tester",
        "email": unique_email,
        "password": "Password123!"
    })
    assert dup_resp.status_code == 400

    # 3. Successful Login
    login_resp = client.post("/api/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 4. Failed Login
    bad_login = client.post("/api/login", json={
        "email": unique_email,
        "password": "IncorrectPassword"
    })
    assert bad_login.status_code == 401

    # 5. Profile check with token
    me_resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == unique_email
