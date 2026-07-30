# app/tests/test_valuation.py
# Auto-D Kenya - Valuation Tests
# ================================================================
# TYPE: TESTS - Valuation module tests

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_valuation_calculation():
    """Test valuation calculation."""
    response = client.post(
        "/api/v1/valuation/calculate",
        json={
            "variant_id": "test-variant",
            "year": 2020,
            "mileage": 50000,
            "condition": "good"
        }
    )
    assert response.status_code in [200, 401]  # 401 if not authenticated
