# app/tests/test_mpesa.py
# Auto-D Kenya - M-Pesa Tests
# ================================================================
# TYPE: TESTS - M-Pesa module tests

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mpesa_health():
    """Test M-Pesa health endpoint."""
    response = client.get("/api/v1/mpesa/health")
    assert response.status_code == 200
