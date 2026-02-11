"""
Pytest configuration and fixtures for agentic-core tests.
"""

from pathlib import Path
from typing import AsyncIterator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Add src to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def mock_ollama_client() -> Generator[MagicMock, None, None]:
    """Mock Ollama AsyncClient for tests."""
    with patch("ollama.AsyncClient") as mock:
        client = AsyncMock()
        client.list = AsyncMock(return_value={"models": [{"name": "qwen2.5:32b"}]})
        client.chat = AsyncMock(
            return_value={
                "message": {"role": "assistant", "content": "Test response"},
                "done": True,
            }
        )
        mock.return_value = client
        yield mock


@pytest.fixture
def mock_redis() -> Generator[dict, None, None]:
    """Mock Redis client for tests."""
    with patch("src.cache.redis_client.init_redis", new_callable=AsyncMock) as init_mock:
        with patch(
            "src.cache.redis_client.close_redis", new_callable=AsyncMock
        ) as close_mock:
            with patch(
                "src.cache.redis_client.get_redis_client"
            ) as get_mock:
                redis_mock = MagicMock()
                # Session caching methods
                redis_mock.get_cached_session = AsyncMock(return_value=None)
                redis_mock.cache_session = AsyncMock()
                redis_mock.invalidate_session = AsyncMock()
                # User sessions caching methods
                redis_mock.get_cached_user_sessions = AsyncMock(return_value=None)
                redis_mock.cache_user_sessions = AsyncMock()
                redis_mock.invalidate_user_sessions = AsyncMock()
                get_mock.return_value = redis_mock
                yield {"init": init_mock, "close": close_mock, "get": get_mock}


@pytest.fixture
def mock_dynamodb() -> Generator[MagicMock, None, None]:
    """Mock DynamoDB client for tests."""
    with patch("src.repositories.dynamodb_client.get_dynamodb_client") as mock:
        client = MagicMock()
        client.put_item = AsyncMock(return_value=None)
        client.get_item = AsyncMock(return_value=None)
        client.query = AsyncMock(return_value=[])
        client.update_item = AsyncMock(return_value=None)
        client.delete_item = AsyncMock(return_value=None)
        mock.return_value = client
        yield mock


@pytest.fixture
def blueprints_path(tmp_path: Path) -> Path:
    """Create a temporary blueprints directory with test data."""
    blueprints_dir = tmp_path / "blueprints"
    blueprints_dir.mkdir()

    # Create test blueprint
    test_blueprint = blueprints_dir / "test-blueprint"
    test_blueprint.mkdir()

    # Create config.yaml
    config_content = """
name: Test Blueprint
description: A test blueprint for unit tests
version: 1.0.0
"""
    (test_blueprint / "config.yaml").write_text(config_content)

    # Create agents directory with test agent
    agents_dir = test_blueprint / "agents"
    agents_dir.mkdir()

    agent_content = """
name: TestAgent
agent_id: test-agent
description: A test agent for unit tests
model_id: qwen2.5:32b
system_prompt: You are a helpful test assistant.
icon: "🧪"
color: "#00FF00"
temperature: 0.7
"""
    (agents_dir / "test-agent.yaml").write_text(agent_content)

    return blueprints_dir


@pytest.fixture
def mock_settings(blueprints_path: Path) -> Generator[MagicMock, None, None]:
    """Mock settings with test blueprints path."""
    with patch("src.config.get_settings") as mock:
        settings = MagicMock()
        settings.blueprints_path = str(blueprints_path)
        settings.ollama_host = "http://localhost:11434"
        settings.ollama_model = "qwen2.5:32b"
        settings.ollama_embedding_model = "nomic-embed-text"
        settings.debug = True
        mock.return_value = settings
        yield mock


@pytest.fixture
def test_app(
    mock_ollama_client: MagicMock,
    mock_redis: MagicMock,
    mock_settings: MagicMock,
    mock_dynamodb: MagicMock,
    blueprints_path: Path,
) -> Generator[TestClient, None, None]:
    """Create a test FastAPI application."""
    from src.api.app import create_app

    app = create_app()
    # Use raise_server_exceptions=False to get HTTP 500 instead of raw exceptions
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
async def async_test_client(
    mock_ollama_client: MagicMock,
    mock_redis: MagicMock,
    mock_settings: MagicMock,
    mock_dynamodb: MagicMock,
    blueprints_path: Path,
) -> AsyncIterator[AsyncClient]:
    """Create an async test client for streaming tests."""
    from src.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_agent_config() -> dict:
    """Sample agent configuration for tests."""
    return {
        "name": "TestAgent",
        "agent_id": "test-agent",
        "description": "A test agent",
        "model_id": "qwen2.5:32b",
        "system_prompt": "You are a helpful assistant.",
        "icon": "🤖",
        "color": "#007AFF",
        "temperature": 0.7,
    }


@pytest.fixture
def sample_chat_request() -> dict:
    """Sample chat request payload."""
    return {
        "message": "Hello, how are you?",
        "session_id": "test-session-123",
        "stream": False,
    }
