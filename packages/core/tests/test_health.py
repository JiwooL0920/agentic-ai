"""
Tests for health check endpoints.

These are smoke tests to verify basic API functionality.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for /health, /ready, /live endpoints."""

    def test_health_check(self, test_app: TestClient) -> None:
        """Test basic health check returns healthy status."""
        response = test_app.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_liveness_check(self, test_app: TestClient) -> None:
        """Test Kubernetes liveness probe."""
        response = test_app.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_check(self, test_app: TestClient) -> None:
        """Test Kubernetes readiness probe."""
        response = test_app.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]

    def test_detailed_health_check(self, test_app: TestClient) -> None:
        """Test detailed health check includes dependency status."""
        response = test_app.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        
        # Should have api and ollama status
        assert "api" in data
        assert data["api"]["status"] == "healthy"
        assert "ollama" in data
        assert data["ollama"]["status"] in ["healthy", "unhealthy", "unknown"]


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint."""

    def test_metrics_endpoint_exists(self, test_app: TestClient) -> None:
        """Test that /metrics endpoint is mounted."""
        response = test_app.get("/metrics")
        # Prometheus metrics returns 200 with text content
        assert response.status_code == 200
        # Should contain Prometheus metric format
        assert "python_info" in response.text or "process_" in response.text


class TestAPIDocsEndpoints:
    """Tests for OpenAPI documentation endpoints."""

    def test_openapi_docs(self, test_app: TestClient) -> None:
        """Test Swagger UI is available."""
        response = test_app.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc_docs(self, test_app: TestClient) -> None:
        """Test ReDoc is available."""
        response = test_app.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json(self, test_app: TestClient) -> None:
        """Test OpenAPI JSON schema is available."""
        response = test_app.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Agentic AI Platform"
