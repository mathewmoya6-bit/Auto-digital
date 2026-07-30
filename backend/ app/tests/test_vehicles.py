# app/tests/test_vehicles.py
# Auto-D Kenya - Vehicles Tests
# ================================================================
# TYPE: TESTS - Vehicles module tests

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_makes():
    """Test get makes endpoint."""
    response = client.get("/api/v1/makes")
    assert response.status_code == 200


def test_get_models():
    """Test get models endpoint."""
    response = client.get("/api/v1/models/test-id")
    assert response.status_code in [200, 404]  # 404 if test-id doesn't exist
