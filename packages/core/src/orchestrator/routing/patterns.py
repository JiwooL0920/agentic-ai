"""Routing pattern detection for supervisor orchestrator."""

SUPERVISOR_DIRECT_RESPONSE_PATTERNS = [
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "how are you", "what can you do", "help", "what agents", "list agents",
    "available agents", "who are you", "what is this", "thanks", "thank you"
]

EXPLICIT_AGENT_PATTERNS = {
    "kubernetesexpert": ["kubernetes expert", "kubernetesexpert", "k8s expert"],
    "terraformexpert": ["terraform expert", "terraformexpert", "iac expert"],
    "pythonexpert": ["python expert", "pythonexpert"],
    "frontendexpert": ["frontend expert", "frontendexpert", "react expert"],
    "systemarchitect": ["architect", "systemarchitect", "system architect"],
}


def should_supervisor_answer_directly(query: str) -> bool:
    query_lower = query.lower().strip()
    return any(pattern in query_lower for pattern in SUPERVISOR_DIRECT_RESPONSE_PATTERNS)


def get_explicit_agent_request(query: str) -> str | None:
    query_lower = query.lower().strip()
    for agent_key, patterns in EXPLICIT_AGENT_PATTERNS.items():
        if any(pattern in query_lower for pattern in patterns):
            return agent_key
    return None
