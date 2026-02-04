"""
Supervisor pattern - equivalent to company's SUPERVISOR_ROUTER mode.

Company Pattern:
- aws_bedrockagent_agent.agent_collaboration = "SUPERVISOR"
- aws_bedrockagent_agent_collaborator resources

Local Adaptation:
- agent-squad (awslabs) with OllamaAgents
- Routing based on agent YAML definitions
"""

from typing import Any, AsyncIterable, Dict, List, Optional

import structlog
from agent_squad.classifiers import Classifier, ClassifierResult
from agent_squad.orchestrator import AgentSquad
from agent_squad.types import ConversationMessage
from ollama import AsyncClient

from ..agents.base import OllamaAgent

logger = structlog.get_logger()


class OllamaSupervisorClassifier(Classifier):
    """
    LLM-based supervisor classifier using Ollama.
    Mirrors AWS Bedrock's supervisor routing pattern but runs locally.
    
    The supervisor ONLY routes queries to collaborator agents - it never responds directly.
    All agents are equals; there is no "default" agent.
    """

    def __init__(self, agents: Dict[str, OllamaAgent], model_id: str = "qwen2.5:7b"):
        super().__init__()  # Initialize base class attributes
        self.agents = agents
        self.agent_list = list(agents.keys())
        self.model_id = model_id
        self._client = AsyncClient()
        # Register agents with the classifier base class
        self.set_agents(agents)

    def _build_routing_prompt(self, input_text: str, agent_descriptions: str) -> str:
        """Build the prompt for the supervisor LLM to route the query."""
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
6. If the query is a greeting or general conversation, route to "SystemArchitect" as it can handle general interactions
7. Do NOT respond with multiple agents - choose the single BEST match

Your response (agent name only):"""

    async def process_request(
        self,
        input_text: str,
        chat_history: List[ConversationMessage],
    ) -> ClassifierResult:
        """
        Process request and select an agent using LLM-based routing.
        The supervisor only routes - never responds to queries directly.
        """
        # Build agent descriptions
        agent_descriptions = []
        for agent_key, agent in self.agents.items():
            agent_descriptions.append(f"- {agent.name}: {agent.description}")
        
        agent_desc_text = "\n".join(agent_descriptions)
        
        logger.info("supervisor_routing", 
                   input=input_text[:100], 
                   available_agents=list(self.agents.keys()))
        
        try:
            # Use Ollama to route the query
            prompt = self._build_routing_prompt(input_text, agent_desc_text)
            
            response = await self._client.chat(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                options={
                    "temperature": 0.1,  # Low temperature for consistent routing
                    "num_predict": 50,   # Short response - just agent name
                },
            )
            
            selected_agent_name = response.get("message", {}).get("content", "").strip()
            
            # Clean up the response - sometimes LLMs add extra text
            # Extract just the agent name
            for agent_key, agent in self.agents.items():
                if agent.name.lower() in selected_agent_name.lower():
                    selected_agent = agent
                    confidence = 0.9
                    logger.info("supervisor_selected", 
                               agent=selected_agent.name, 
                               confidence=confidence,
                               llm_response=selected_agent_name)
                    return ClassifierResult(
                        selected_agent=selected_agent,
                        confidence=confidence
                    )
            
            # If we couldn't find a match, log it and route to SystemArchitect
            # as it can handle general queries and provide guidance
            logger.warning("supervisor_no_match_found", 
                         llm_response=selected_agent_name,
                         falling_back="systemarchitect")
            
            systemarchitect = self.agents.get("systemarchitect")
            if systemarchitect:
                return ClassifierResult(
                    selected_agent=systemarchitect,
                    confidence=0.6
                )
            
            # Last resort - use first available agent
            fallback_agent = self.agents[self.agent_list[0]]
            logger.warning("supervisor_using_first_agent", agent=fallback_agent.name)
            return ClassifierResult(
                selected_agent=fallback_agent,
                confidence=0.4
            )
            
        except Exception as e:
            logger.error("supervisor_routing_error", error=str(e), exc_info=True)
            # On error, route to SystemArchitect as it can handle general queries
            systemarchitect = self.agents.get("systemarchitect")
            if systemarchitect:
                return ClassifierResult(
                    selected_agent=systemarchitect,
                    confidence=0.3
                )
            # Absolute fallback
            return ClassifierResult(
                selected_agent=self.agents[self.agent_list[0]],
                confidence=0.2
            )


class SupervisorOrchestrator:
    """
    True Bedrock supervisor pattern implementation.
    
    Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │              Supervisor Agent (qwen2.5:7b)                   │
    │  - Analyzes queries and determines routing strategy          │
    │  - Can ask clarifying questions                              │
    │  - Can coordinate multiple agents                            │
    │  - Synthesizes multi-agent responses                         │
    └─────────────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    │SystemArchitect│KubernetesExpert│PythonExpert│FrontendExpert│
    │  (collaborator)│  (collaborator)│  (collaborator)│  (collaborator)│
    └──────────────┴──────────────┴──────────────┴──────────────┘
    
    The supervisor is always the entry point and decides:
    1. Route to single specialist
    2. Ask clarifying question  
    3. Coordinate multiple specialists
    """

    def __init__(self, agents: Dict[str, OllamaAgent]):
        """
        Initialize supervisor orchestrator with collaborator agents.

        Args:
            agents: Dictionary mapping agent names to OllamaAgent instances
        """
        self.agents = agents
        
        # Extract supervisor agent
        agents_lower = {name.lower(): agent for name, agent in agents.items()}
        self.supervisor_agent = agents_lower.get("supervisor")
        
        if not self.supervisor_agent:
            logger.warning("supervisor_agent_not_found", 
                         available=list(agents_lower.keys()))
            # Fallback: create a simple routing classifier
            classifier = OllamaSupervisorClassifier(agents_lower, model_id="qwen2.5:7b")
            self.orchestrator = AgentSquad(classifier=classifier)
            for agent in agents.values():
                self.orchestrator.add_agent(agent)
        else:
            # Remove supervisor from collaborators list
            self.collaborators = {k: v for k, v in agents_lower.items() if k != "supervisor"}
            logger.info("supervisor_initialized", 
                       agent_count=len(self.collaborators),
                       has_supervisor=True)

    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        chat_history: Optional[List] = None,
    ) -> Dict[str, Any]:
        """
        Process query through supervisor agent (non-streaming).
        """
        logger.info(
            "processing_query",
            user_id=user_id,
            session_id=session_id,
            query_length=len(query),
        )

        try:
            if not self.supervisor_agent:
                # Fallback behavior
                return {
                    "response": "Supervisor agent not available",
                    "agent": "system",
                    "session_id": session_id,
                }
            
            # Build context
            collaborator_context = "Available specialists:\n"
            for name, agent in self.collaborators.items():
                collaborator_context += f"- {agent.name}: {agent.description}\n"
            
            enhanced_query = f"""{collaborator_context}

User Query: {query}

Analyze this query and decide your response strategy."""
            
            response = await self.supervisor_agent.process_request(
                input_text=enhanced_query,
                user_id=user_id,
                session_id=session_id,
                chat_history=[],
                additional_params={},
            )

            content = ""
            if hasattr(response, 'content') and response.content:
                content = response.content[0].get("text", "")

            return {
                "response": content,
                "agent": self.supervisor_agent.name,
                "session_id": session_id,
            }

        except Exception as e:
            logger.error("query_processing_error", error=str(e))
            raise

    async def process_query_streaming(
        self,
        query: str,
        user_id: str,
        session_id: str,
        chat_history: Optional[List] = None,
    ) -> AsyncIterable[Dict[str, Any]]:
        """
        Process query through supervisor agent.
        
        The supervisor analyzes the query, selects the appropriate specialist,
        and returns the specialist's response (not the supervisor's routing decision).
        """
        logger.info(
            "processing_query_streaming",
            user_id=user_id,
            session_id=session_id,
        )

        try:
            if not self.supervisor_agent:
                # Fallback to classifier-based routing
                agents_lower = {name.lower(): agent for name, agent in self.agents.items()}
                classifier = OllamaSupervisorClassifier(agents_lower, model_id="qwen2.5:7b")
                classifier_result = await classifier.process_request(
                    input_text=query,
                    chat_history=chat_history or [],
                )
                
                if not classifier_result.selected_agent:
                    yield {"type": "error", "error": "No agent selected"}
                    return
                
                selected_agent = classifier_result.selected_agent
                agent_name = selected_agent.name
                
                logger.info("agent_selected_fallback", agent=agent_name, confidence=classifier_result.confidence)

                yield {
                    "type": "metadata",
                    "agent": agent_name,
                    "session_id": session_id,
                }

                response = await selected_agent.process_request(
                    input_text=query,
                    user_id=user_id,
                    session_id=session_id,
                    chat_history=[],
                    additional_params={},
                )

                if hasattr(response, "__aiter__"):
                    async for chunk in response:
                        yield {
                            "type": "content",
                            "content": chunk,
                        }
                else:
                    content = ""
                    if hasattr(response, 'content') and response.content:
                        content = response.content[0].get("text", "")
                    yield {
                        "type": "content",
                        "content": content,
                    }

                yield {"type": "done"}
                return
            
            # Step 1: Check if user explicitly requested a specific agent
            query_lower = query.lower()
            explicit_agent = None
            
            # Check for explicit agent requests
            if any(word in query_lower for word in ["kubernetes expert", "kubernetesexpert", "k8s expert"]):
                explicit_agent = self.collaborators.get("kubernetesexpert")
            elif any(word in query_lower for word in ["terraform expert", "terraformexpert", "iac expert"]):
                explicit_agent = self.collaborators.get("terraformexpert")
            elif any(word in query_lower for word in ["python expert", "pythonexpert"]):
                explicit_agent = self.collaborators.get("pythonexpert")
            elif any(word in query_lower for word in ["frontend expert", "frontendexpert", "react expert"]):
                explicit_agent = self.collaborators.get("frontendexpert")
            elif any(word in query_lower for word in ["architect", "systemarchitect", "system architect"]):
                explicit_agent = self.collaborators.get("systemarchitect")
            
            if explicit_agent:
                logger.info("explicit_agent_request", agent=explicit_agent.name)
                
                yield {
                    "type": "metadata",
                    "agent": explicit_agent.name,
                    "session_id": session_id,
                }
                
                response = await explicit_agent.process_request(
                    input_text=query,
                    user_id=user_id,
                    session_id=session_id,
                    chat_history=[],
                    additional_params={},
                )

                if hasattr(response, "__aiter__"):
                    async for chunk in response:
                        yield {"type": "content", "content": chunk}
                else:
                    content = ""
                    if hasattr(response, 'content') and response.content:
                        content = response.content[0].get("text", "")
                    yield {"type": "content", "content": content}

                yield {"type": "done"}
                return
            
            # Step 2: Use classifier for intelligent routing (more reliable than supervisor LLM call)
            logger.info("using_classifier_for_routing")
            
            classifier = OllamaSupervisorClassifier(self.collaborators, model_id="qwen2.5:7b")
            classifier_result = await classifier.process_request(
                input_text=query,
                chat_history=chat_history or [],
            )
            
            selected_agent = classifier_result.selected_agent
            
            if not selected_agent:
                logger.warning("classifier_no_agent")
                selected_agent = self.collaborators.get("systemarchitect")
            
            if not selected_agent:
                yield {"type": "error", "error": "No suitable agent found"}
                return
            
            agent_name = selected_agent.name
            logger.info("classifier_selected", 
                       agent=agent_name, 
                       confidence=classifier_result.confidence)
            
            # Step 3: Yield metadata showing which specialist is responding
            yield {
                "type": "metadata",
                "agent": agent_name,
                "session_id": session_id,
            }
            
            # Step 4: Get actual response from the specialist agent
            response = await selected_agent.process_request(
                input_text=query,
                user_id=user_id,
                session_id=session_id,
                chat_history=[],
                additional_params={},
            )

            # Step 5: Stream the specialist's response
            if hasattr(response, "__aiter__"):
                async for chunk in response:
                    yield {
                        "type": "content",
                        "content": chunk,
                    }
            else:
                content = ""
                if hasattr(response, 'content') and response.content:
                    content = response.content[0].get("text", "")
                yield {
                    "type": "content",
                    "content": content,
                }

            yield {"type": "done"}

        except Exception as e:
            logger.error("streaming_error", error=str(e), exc_info=True)
            yield {"type": "error", "error": str(e)}

    def list_agents(self) -> List[str]:
        """List available agent names."""
        return list(self.agents.keys())

    def get_agent(self, name: str) -> Optional[OllamaAgent]:
        """Get a specific agent by name."""
        return self.agents.get(name)
