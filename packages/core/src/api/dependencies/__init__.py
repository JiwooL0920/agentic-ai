"""FastAPI dependency injection for API routes."""

from .auth import CurrentUser, User, get_current_user
from .registry import AgentRegistry, get_registry

__all__ = [
    # Auth
    "CurrentUser",
    "User",
    "get_current_user",
    # Registry
    "AgentRegistry",
    "get_registry",
]
