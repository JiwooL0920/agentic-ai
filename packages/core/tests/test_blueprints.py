"""
Tests for blueprint management endpoints.
"""

from fastapi.testclient import TestClient


class TestBlueprintEndpoints:
    """Tests for /api/blueprints endpoints."""

    def test_list_blueprints(self, test_app: TestClient) -> None:
        """Test listing all available blueprints."""
        response = test_app.get("/api/blueprints")
        assert response.status_code == 200
        data = response.json()

        # Endpoint returns list of blueprint name strings
        assert isinstance(data, list)
        assert "test-blueprint" in data

    def test_get_blueprint_details(self, test_app: TestClient) -> None:
        """Test getting details for a specific blueprint."""
        response = test_app.get("/api/blueprints/test-blueprint")
        assert response.status_code == 200
        data = response.json()

        # name is title-cased, slug is the original identifier
        assert data["slug"] == "test-blueprint"
        assert "agents" in data
        assert "description" in data

    def test_get_nonexistent_blueprint(self, test_app: TestClient) -> None:
        """Test getting a blueprint that doesn't exist returns 404."""
        response = test_app.get("/api/blueprints/nonexistent-blueprint")
        assert response.status_code == 404

    def test_blueprint_agents_list(self, test_app: TestClient) -> None:
        """Test listing agents for a blueprint."""
        response = test_app.get("/api/blueprints/test-blueprint/agents/status")
        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert "total_count" in data
        assert isinstance(data["agents"], list)
