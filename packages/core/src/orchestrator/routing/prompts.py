"""LLM prompts for supervisor routing and coordination."""


def build_routing_prompt(input_text: str, agent_descriptions: str) -> str:
    return f"""You are a supervisor agent in a multi-agent system. Your ONLY job is to analyze user queries and route them to the most appropriate specialist agent. You never answer questions directly.

Available Specialist Agents:
{agent_descriptions}

User Query: "{input_text}"

Instructions:
1. Carefully analyze what the user is asking about
2. Determine which specialist agent is BEST suited to handle this specific query
3. Consider the agent's expertise and the query's domain
4. Respond with ONLY the exact agent name from the list above (e.g., "KubernetesExpert", "PythonExpert", etc.)
5. If the query is about system architecture, design patterns, or general engineering decisions, route to "SystemArchitect"
6. Do NOT respond with multiple agents - choose the single BEST match

Your response (agent name only):"""


def build_supervisor_direct_response_prompt(
    query: str, collaborator_context: str
) -> str:
    return f"""{collaborator_context}

User Query: {query}

You are the Supervisor agent. Answer this query directly in a friendly, helpful manner. If it's a greeting, respond warmly and let them know you can help with various tasks. If they ask what you can do, briefly explain the available specialists and that you can route their questions appropriately."""


def build_supervisor_analysis_prompt(query: str, collaborator_context: str) -> str:
    return f"""{collaborator_context}

User Query: {query}

Analyze this query and decide your response strategy."""


def build_collaborator_context(agents: dict) -> str:
    lines = ["Available specialists:"]
    for _name, agent in agents.items():
        lines.append(f"- {agent.name}: {agent.description}")
    return "\n".join(lines)
