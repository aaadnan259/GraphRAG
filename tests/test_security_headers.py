
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_security_headers():
    """Test that security headers are present in the response."""
    response = client.get("/")
    assert response.status_code == 200

    headers = response.headers

    # Check for X-Content-Type-Options
    assert headers.get("X-Content-Type-Options") == "nosniff", "X-Content-Type-Options header missing or incorrect"

    # Check for X-Frame-Options
    assert headers.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"], "X-Frame-Options header missing or incorrect"

    # Check for X-XSS-Protection
    assert "1; mode=block" in headers.get("X-XSS-Protection", ""), "X-XSS-Protection header missing or incorrect"

    # Check for Referrer-Policy
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin", "Referrer-Policy header missing or incorrect"

    # Check for Content-Security-Policy (Optional but recommended)
    # assert headers.get("Content-Security-Policy") is not None
