"""Routing modules for supervisor orchestrator."""

from .patterns import (
    EXPLICIT_AGENT_PATTERNS,
    SUPERVISOR_DIRECT_RESPONSE_PATTERNS,
    get_explicit_agent_request,
    should_supervisor_answer_directly,
)
from .prompts import (
    build_collaborator_context,
    build_routing_prompt,
    build_supervisor_analysis_prompt,
    build_supervisor_direct_response_prompt,
)

__all__ = [
    "EXPLICIT_AGENT_PATTERNS",
    "SUPERVISOR_DIRECT_RESPONSE_PATTERNS",
    "get_explicit_agent_request",
    "should_supervisor_answer_directly",
    "build_collaborator_context",
    "build_routing_prompt",
    "build_supervisor_analysis_prompt",
    "build_supervisor_direct_response_prompt",
]
