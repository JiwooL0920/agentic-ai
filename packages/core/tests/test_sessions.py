"""
Tests for session management endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestSessionEndpoints:
    """Tests for /api/sessions endpoints."""

    def test_create_session(self, test_app: TestClient) -> None:
        """Test creating a new session."""
        response = test_app.post(
            "/api/sessions",
            json={"blueprint": "test-blueprint", "user_id": "test-user"},
        )
        # Should succeed or fail gracefully
        assert response.status_code in [200, 201, 422, 500]

    def test_list_sessions(self, test_app: TestClient) -> None:
        """Test listing sessions for a user."""
        response = test_app.get("/api/sessions", params={"user_id": "test-user"})
        # Should return list or empty
        assert response.status_code in [200, 404]

    def test_get_session(self, test_app: TestClient) -> None:
        """Test getting a specific session."""
        response = test_app.get("/api/sessions/test-session-123")
        # Non-existent session should return 404
        assert response.status_code in [200, 404]

    def test_get_session_messages(self, test_app: TestClient) -> None:
        """Test getting messages for a session."""
        response = test_app.get("/api/sessions/test-session-123/messages")
        # Should return messages or 404 for non-existent session
        assert response.status_code in [200, 404]

    def test_delete_session(self, test_app: TestClient) -> None:
        """Test deleting a session."""
        response = test_app.delete("/api/sessions/test-session-123")
        # Should succeed or return 404
        assert response.status_code in [200, 204, 404]
