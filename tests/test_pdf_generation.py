"""
PDF Report Generation and Download Tests
"""

import os
from app.database import SessionLocal
from app.models.shipment import Shipment

def test_generate_and_download_pdf(client):
    db = SessionLocal()
    try:
        shipment = db.query(Shipment).first()
        assert shipment is not None, "At least one shipment required for report test."

        # 1. Trigger report generation
        gen_resp = client.post(f"/api/reports/generate/{shipment.id}")
        assert gen_resp.status_code == 200
        data = gen_resp.json()
        assert data["success"] is True
        assert os.path.exists(data["file_path"])
        assert os.path.getsize(data["file_path"]) > 1000

        # 2. Download PDF via API
        pdf_resp = client.get(data["download_url"])
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert len(pdf_resp.content) > 1000
    finally:
        db.close()
