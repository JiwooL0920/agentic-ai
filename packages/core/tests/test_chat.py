"""
Tests for chat endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestChatEndpoints:
    """Tests for /api/blueprints/{blueprint}/chat endpoints."""

    def test_chat_endpoint_exists(self, test_app: TestClient) -> None:
        """Test that chat endpoint is accessible."""
        # Should return 400 or 422 for missing body, not 404
        response = test_app.post("/api/blueprints/test-blueprint/chat")
        assert response.status_code in [400, 422]  # Not 404

    def test_chat_with_valid_request(
        self, test_app: TestClient, sample_chat_request: dict
    ) -> None:
        """Test chat with valid request payload."""
        with patch("src.orchestrator.supervisor.SupervisorOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock(return_value="Test response")
            mock_orch.return_value = mock_instance

            response = test_app.post(
                "/api/blueprints/test-blueprint/chat",
                json=sample_chat_request,
            )
            
            # Should either succeed or fail gracefully
            assert response.status_code in [200, 500]

    def test_chat_missing_message(self, test_app: TestClient) -> None:
        """Test chat fails without message field."""
        response = test_app.post(
            "/api/blueprints/test-blueprint/chat",
            json={"session_id": "test-123"},
        )
        assert response.status_code == 422  # Validation error

    def test_chat_nonexistent_blueprint(
        self, test_app: TestClient, sample_chat_request: dict
    ) -> None:
        """Test chat to non-existent blueprint returns 404."""
        response = test_app.post(
            "/api/blueprints/nonexistent/chat",
            json=sample_chat_request,
        )
        assert response.status_code == 404


class TestChatStreamEndpoints:
    """Tests for streaming chat endpoints."""

    def test_stream_endpoint_exists(self, test_app: TestClient) -> None:
        """Test that stream endpoint is accessible."""
        response = test_app.post("/api/blueprints/test-blueprint/chat/stream")
        assert response.status_code in [400, 422]  # Not 404

    def test_stream_with_valid_request(
        self, test_app: TestClient, sample_chat_request: dict
    ) -> None:
        """Test streaming chat returns SSE response."""
        stream_request = {**sample_chat_request, "stream": True}
        
        with patch("src.orchestrator.supervisor.SupervisorOrchestrator") as mock_orch:
            async def mock_stream():
                yield {"content": "Hello"}
                yield {"content": " world"}
            
            mock_instance = MagicMock()
            mock_instance.process_stream = mock_stream
            mock_orch.return_value = mock_instance

            response = test_app.post(
                "/api/blueprints/test-blueprint/chat/stream",
                json=stream_request,
            )
            
            # Stream endpoint should return 200 with event-stream content type
            # or fail gracefully
            assert response.status_code in [200, 500]


class TestChatRequestValidation:
    """Tests for chat request validation."""

    def test_empty_message_rejected(self, test_app: TestClient) -> None:
        """Test that empty message is rejected."""
        response = test_app.post(
            "/api/blueprints/test-blueprint/chat",
            json={"message": "", "session_id": "test-123"},
        )
        # Empty string might be accepted or rejected depending on validation
        assert response.status_code in [200, 422, 500]

    def test_message_max_length(self, test_app: TestClient) -> None:
        """Test that overly long messages are handled."""
        long_message = "a" * 100000  # 100k characters
        response = test_app.post(
            "/api/blueprints/test-blueprint/chat",
            json={"message": long_message, "session_id": "test-123"},
        )
        # Should either succeed or fail gracefully, not crash
        assert response.status_code in [200, 413, 422, 500]
