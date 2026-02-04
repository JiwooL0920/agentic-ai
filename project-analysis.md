# Multi-Agent Supervisor Pattern

**Reference Implementation:** OneMesh Data Discoverability Chatbot  
**Author:** Analysis based on production chatbot system  
**Date:** January 30, 2026  
**Purpose:** Guide for implementing multi-agent orchestration in Bedrock Agents

---

## Table of Contents

1. [Quick Start Checklist](#quick-start-checklist)
2. [Overview](#overview)
3. [Agent Patterns Comparison](#agent-patterns-comparison) ← **Start here for pattern selection**
   - [Pattern 1: Simple Agent](#pattern-1-simple-agent-single-agent)
   - [Pattern 2: Supervisor + Collaborators](#pattern-2-supervisor--collaborators-this-documents-focus)
   - [Pattern 3: Multi-Level Supervisors](#pattern-3-multi-level-supervisors-hierarchical)
4. [Architecture Diagrams](#architecture-diagrams)
5. [Architecture Pattern](#architecture-pattern)
6. [Core Components](#core-components)
7. [Implementation Details](#implementation-details)
8. [Best Practices](#best-practices)
9. [Adapting to Bedrock Agents](#adapting-to-bedrock-agents)
10. [Testing Strategy](#testing-strategy)

---

## Quick Start Checklist

> **For newcomers:** Use this checklist to implement multi-agent collaboration in your project.

### Prerequisites

- [ ] AWS account with Bedrock access enabled
- [ ] Terraform installed (v1.5+)
- [ ] At least one working Bedrock agent (e.g., `bedrock-agent-clinical-analyst`)
- [ ] Understanding of basic Bedrock agent concepts (prompts, action groups, knowledge bases)

### Implementation TODO List

#### Phase 1: Prepare Collaborator Agents
- [ ] **Deploy first collaborator agent** (e.g., clinical-analyst)
  - Location: `blueprints/bedrock-agent-clinical-analyst/`
  - Run: `terraform init && terraform apply`
  - Note the `agent_alias_arn` output
- [ ] **Deploy second collaborator agent** (e.g., confluence-retriever)
  - Location: `blueprints/bedrock-agent-confluence-retriever/`
  - Run: `terraform init && terraform apply`
  - Note the `agent_alias_arn` output
- [ ] **Test each agent independently** before integration
  - Use AWS Console → Bedrock → Agents → Test

#### Phase 2: Create Supervisor Agent
- [ ] **Create new blueprint directory**: `blueprints/bedrock-agent-supervisor/`
- [ ] **Create supervisor agent Terraform** with `agent_collaboration = "SUPERVISOR_ROUTER"`
- [ ] **Write supervisor instructions** defining routing logic
- [ ] **Associate collaborator agents** using `aws_bedrockagent_agent_collaborator`
- [ ] **Deploy supervisor**: `terraform init && terraform apply`

#### Phase 3: Test & Validate
- [ ] **Test routing** - verify queries go to correct collaborator
- [ ] **Test edge cases** - ambiguous queries, errors, timeouts
- [ ] **Test conversation history** - multi-turn conversations work
- [ ] **Monitor CloudWatch** - check for errors and latency

#### Phase 4: Production Readiness
- [ ] **Add guardrails** to supervisor and collaborators
- [ ] **Set up alarms** for error rates and latency
- [ ] **Document usage patterns** for your team
- [ ] **Create runbook** for troubleshooting

### File Checklist for New Supervisor Blueprint

```
blueprints/bedrock-agent-supervisor/
├── main.tf                              # [ ] Supervisor agent + collaborator associations
├── variables.tf                         # [ ] Input variables (agent IDs, env, etc.)
├── outputs.tf                           # [ ] Output supervisor agent ARN/ID
├── provider.tf                          # [ ] AWS provider config
├── backend.tf                           # [ ] Terraform state backend
├── prompts/
│   └── supervisor-instructions.txt      # [ ] Routing logic and behavior
├── config/
│   └── example/
│       ├── backend.conf.example         # [ ] Example backend config
│       └── tfvars.conf.example          # [ ] Example variables
├── Makefile                             # [ ] Build/deploy commands
└── README.md                            # [ ] Blueprint documentation
```

---

## Overview

### Multi-Agent Patterns: Two Approaches

AWS identifies **two distinct patterns** for multi-agent systems. This document focuses on the **Workflow Agent (Supervisor) pattern**, but it's important to understand both:

| Feature | **Workflow Agents (This Doc)** | **Multi-Agent Collaboration** |
|---------|-------------------------------|-------------------------------|
| **Control** | Centralized coordinator (supervisor) | Decentralized, peer-based |
| **Interaction** | One agent delegates and tracks | Multiple agents negotiate and share |
| **Design** | Predefined task sequence | Emergent, flexible distribution |
| **Coordination** | Procedural orchestration | Cooperative/competitive interactions |
| **Best For** | Enterprise process automation | Complex reasoning, exploration |
| **AWS Implementation** | Bedrock Multi-Agent Collaboration | Step Functions + EventBridge + shared memory |

> **Reference:** [AWS Prescriptive Guidance - Multi-Agent Collaboration](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/multi-agent-collaboration.html)

### Which Pattern Should You Use?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CHOOSING A MULTI-AGENT PATTERN                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  START: What type of problem are you solving?                               │
│                           │                                                  │
│           ┌───────────────┴───────────────┐                                 │
│           ▼                               ▼                                 │
│  ┌─────────────────┐             ┌─────────────────┐                        │
│  │ Well-defined    │             │ Open-ended      │                        │
│  │ tasks with      │             │ problems with   │                        │
│  │ clear routing   │             │ emergent needs  │                        │
│  └────────┬────────┘             └────────┬────────┘                        │
│           │                               │                                  │
│           ▼                               ▼                                  │
│  ┌─────────────────┐             ┌─────────────────┐                        │
│  │ WORKFLOW AGENT  │             │ MULTI-AGENT     │                        │
│  │ (Supervisor)    │             │ COLLABORATION   │                        │
│  │                 │             │                 │                        │
│  │ • Customer      │             │ • Research      │                        │
│  │   service bots  │             │   teams         │                        │
│  │ • Data lookup   │             │ • Code review   │                        │
│  │ • Process       │             │   (coder +      │                        │
│  │   automation    │             │   tester +      │                        │
│  │ • FAQ routing   │             │   reviewer)     │                        │
│  │                 │             │ • Scenario      │                        │
│  │ Use: Bedrock    │             │   modeling      │                        │
│  │ Multi-Agent     │             │                 │                        │
│  │ Collaboration   │             │ Use: Step       │                        │
│  │                 │             │ Functions +     │                        │
│  │                 │             │ EventBridge +   │                        │
│  │                 │             │ Shared Memory   │                        │
│  └─────────────────┘             └─────────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**This document covers the Workflow Agent (Supervisor) pattern** because:
- It's natively supported by AWS Bedrock Multi-Agent Collaboration
- It's simpler to implement and reason about
- It fits most enterprise use cases (FAQ bots, data retrieval, process automation)
- It has lower operational complexity

For peer-to-peer multi-agent collaboration (research teams, code review systems), see the [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/multi-agent-collaboration.html).

---

## Agent Patterns Comparison

This section explains the three main patterns you can implement with Bedrock Agents, from simplest to most complex.

### Pattern 1: Simple Agent (Single Agent)

The most basic pattern - one agent handles all requests directly.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SIMPLE AGENT PATTERN                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌─────────┐         ┌─────────────────────────────────┐                  │
│    │  User   │────────►│         SINGLE AGENT            │                  │
│    └─────────┘         │                                 │                  │
│         ▲              │  • Instructions (prompt)        │                  │
│         │              │  • Action Groups (tools)        │                  │
│         │              │  • Knowledge Bases (RAG)        │                  │
│         │              │  • Guardrails                   │                  │
│         │              └────────────────┬────────────────┘                  │
│         │                               │                                    │
│         └───────────────────────────────┘                                    │
│                      Response                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**When to Use:**
- ✅ Single domain/purpose (e.g., "Clinical trials FAQ bot")
- ✅ Simple workflows with clear scope
- ✅ Quick MVP or proof of concept
- ✅ Limited number of tools/knowledge bases

**When NOT to Use:**
- ❌ Multiple distinct domains (clinical + finance + HR)
- ❌ Complex routing logic needed
- ❌ Prompt becomes too long/complex

**Example Blueprints in This Repo:**
- `blueprints/bedrock-agent-clinical-analyst/` - Single agent for clinical trials
- `blueprints/bedrock-agent-confluence-retriever/` - Single agent for documentation
- `blueprints/bedrock-agent-for-developers/` - Single agent for developer tools

**Terraform:**
```hcl
module "simple_agent" {
  source = "../../modules/bedrock/agent"
  
  agent_name       = "my-simple-agent"
  foundation_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  instruction      = file("prompts/instructions.txt")
  # No agent_collaboration - defaults to single agent
}
```

---

### Pattern 2: Supervisor + Collaborators (This Document's Focus)

One supervisor agent coordinates multiple specialist collaborator agents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPERVISOR + COLLABORATORS PATTERN                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌─────────┐         ┌─────────────────────────────────┐                  │
│    │  User   │────────►│       SUPERVISOR AGENT          │                  │
│    └─────────┘         │  agent_collaboration = SUPERVISOR│                  │
│         ▲              └────────────────┬────────────────┘                  │
│         │                               │                                    │
│         │              ┌────────────────┼────────────────┐                  │
│         │              │                │                │                  │
│         │              ▼                ▼                ▼                  │
│         │     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│         │     │ Collaborator │ │ Collaborator │ │ Collaborator │           │
│         │     │      #1      │ │      #2      │ │      #3      │           │
│         │     │  (Clinical)  │ │ (Confluence) │ │   (Data)     │           │
│         │     └──────────────┘ └──────────────┘ └──────────────┘           │
│         │              │                │                │                  │
│         │              └────────────────┼────────────────┘                  │
│         │                               │                                    │
│         │                               ▼                                    │
│         │              ┌─────────────────────────────────┐                  │
│         │              │   SUPERVISOR synthesizes        │                  │
│         └──────────────│   responses from collaborators  │                  │
│                        └─────────────────────────────────┘                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**When to Use:**
- ✅ Multiple distinct domains that need coordination
- ✅ Queries often span multiple specialists
- ✅ Want to reuse existing agents as collaborators
- ✅ Need centralized routing and response synthesis

**When NOT to Use:**
- ❌ Simple single-domain use case
- ❌ Extremely latency-sensitive applications
- ❌ Need peer-to-peer agent communication

**Example Blueprint (to be created):**
- `blueprints/bedrock-agent-supervisor/` - Supervisor with clinical + confluence collaborators

**Terraform:**
```hcl
# Supervisor agent (ONLY supervisor gets agent_collaboration)
resource "aws_bedrockagent_agent" "supervisor" {
  agent_name              = "supervisor-agent"
  agent_collaboration     = "SUPERVISOR_ROUTER"  # or "SUPERVISOR"
  agent_resource_role_arn = aws_iam_role.agent_role.arn
  foundation_model        = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  instruction             = file("prompts/supervisor-instructions.txt")
  prepare_agent           = false  # Prepare after collaborators are associated
}

# Create alias for collaborator (required before association)
resource "aws_bedrockagent_agent_alias" "clinical_alias" {
  agent_id         = module.clinical_agent.bedrock_agent_id
  agent_alias_name = "live"
}

# Associate collaborators (use depends_on for correct ordering)
resource "aws_bedrockagent_agent_collaborator" "clinical" {
  agent_id                   = aws_bedrockagent_agent.supervisor.agent_id
  collaborator_name          = "clinical-analyst"
  collaboration_instruction  = "Use for clinical trial queries..."
  relay_conversation_history = "TO_COLLABORATOR"
  
  agent_descriptor {
    alias_arn = aws_bedrockagent_agent_alias.clinical_alias.agent_alias_arn
  }
  
  depends_on = [aws_bedrockagent_agent_alias.clinical_alias]
}
```

---

### Pattern 3: Multi-Level Supervisors (Hierarchical)

Supervisors can themselves be collaborators of a higher-level supervisor, creating a hierarchy.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-LEVEL SUPERVISORS PATTERN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌─────────┐         ┌─────────────────────────────────┐                  │
│    │  User   │────────►│     TOP-LEVEL SUPERVISOR        │                  │
│    └─────────┘         │    (Enterprise Assistant)       │                  │
│         ▲              └────────────────┬────────────────┘                  │
│         │                               │                                    │
│         │              ┌────────────────┼────────────────┐                  │
│         │              │                │                │                  │
│         │              ▼                ▼                ▼                  │
│         │     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│         │     │  RESEARCH    │ │   IT/DEV     │ │    HR        │           │
│         │     │  SUPERVISOR  │ │  SUPERVISOR  │ │  SUPERVISOR  │           │
│         │     └──────┬───────┘ └──────┬───────┘ └──────┬───────┘           │
│         │            │                │                │                    │
│         │     ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐            │
│         │     │             │  │             │  │             │            │
│         │     ▼             ▼  ▼             ▼  ▼             ▼            │
│         │  ┌──────┐    ┌──────┐ ┌──────┐  ┌──────┐ ┌──────┐ ┌──────┐      │
│         │  │Clin- │    │Conflu│ │Code  │  │Infra │ │Poli- │ │Bene- │      │
│         │  │ical  │    │ence  │ │Review│  │Help  │ │cies  │ │fits  │      │
│         │  └──────┘    └──────┘ └──────┘  └──────┘ └──────┘ └──────┘      │
│         │                                                                   │
│         └─────────────── Synthesized Response ──────────────────────────────│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**When to Use:**
- ✅ Very large organizations with many domains
- ✅ Natural domain hierarchies (Research → Clinical, Confluence)
- ✅ Need to scale beyond 10 collaborators per supervisor (AWS limit)
- ✅ Different teams own different domain supervisors

**When NOT to Use:**
- ❌ Simple use cases (adds unnecessary complexity)
- ❌ Latency-critical applications (more hops = more latency)
- ❌ Small number of total agents

**Architecture Notes:**
- Each level adds ~1-2 seconds latency
- Max 10 collaborators per supervisor (AWS limit)
- Workaround: Use mid-level supervisors to group related agents

**Terraform Example:**
```hcl
# Level 1: Leaf agents (simple agents)
module "clinical_agent" {
  source     = "../../modules/bedrock/agent"
  agent_name = "clinical-analyst"
  # ... no agent_collaboration (simple agent)
}

module "confluence_agent" {
  source     = "../../modules/bedrock/agent"
  agent_name = "confluence-retriever"
}

# Level 2: Domain supervisor (groups related agents)
resource "aws_bedrockagent_agent" "research_supervisor" {
  agent_name          = "research-supervisor"
  agent_collaboration = "SUPERVISOR"
  instruction         = "You coordinate research-related queries..."
}

resource "aws_bedrockagent_agent_collaborator" "clinical_collab" {
  agent_id          = aws_bedrockagent_agent.research_supervisor.id
  collaborator_name = "clinical"
  agent_descriptor {
    alias_arn = module.clinical_agent.bedrock_agent_alias_arn
  }
  collaboration_instruction = "Handles clinical queries"
}

resource "aws_bedrockagent_agent_collaborator" "confluence_collab" {
  agent_id          = aws_bedrockagent_agent.research_supervisor.id
  collaborator_name = "confluence"
  agent_descriptor {
    alias_arn = module.confluence_agent.bedrock_agent_alias_arn
  }
  collaboration_instruction = "Handles documentation queries"
}

# Level 3: Top-level supervisor (enterprise-wide)
resource "aws_bedrockagent_agent" "enterprise_supervisor" {
  agent_name          = "enterprise-assistant"
  agent_collaboration = "SUPERVISOR_ROUTER"
  instruction         = "You are the enterprise assistant..."
}

resource "aws_bedrockagent_agent_collaborator" "research_collab" {
  agent_id          = aws_bedrockagent_agent.enterprise_supervisor.id
  collaborator_name = "research-team"
  agent_descriptor {
    # Note: Reference the research SUPERVISOR's alias, not a simple agent
    alias_arn = aws_bedrockagent_agent_alias.research_supervisor_alias.agent_alias_arn
  }
  collaboration_instruction = "Handles all research, clinical, and documentation queries"
}
```

---

### Pattern Comparison Summary

| Aspect | Simple Agent | Supervisor + Collaborators | Multi-Level Supervisors |
|--------|-------------|---------------------------|------------------------|
| **Complexity** | Low | Medium | High |
| **Latency** | ~1-2s | ~2-4s | ~4-8s |
| **Max Agents** | 1 | 11 (1 + 10 collaborators) | Unlimited (via hierarchy) |
| **Best For** | Single domain | Multiple domains | Enterprise-wide |
| **Maintenance** | Simple | Moderate | Complex |
| **Blueprints** | `clinical-analyst`, `confluence-retriever` | `bedrock-agent-supervisor` (TBD) | Custom |

### Choosing the Right Pattern

```
START: How many distinct domains?
           │
           ▼
    ┌──────────────┐
    │   1 domain   │──────────► Simple Agent
    └──────────────┘            (blueprints/bedrock-agent-clinical-analyst)
           │
           │ 2-10 domains
           ▼
    ┌──────────────┐
    │ Need queries │
    │ across       │──────────► Supervisor + Collaborators
    │ domains?     │            (this document)
    └──────────────┘
           │
           │ >10 domains OR natural hierarchy
           ▼
    ┌──────────────┐
    │ Multi-Level  │──────────► Multi-Level Supervisors
    │ Supervisors  │            (enterprise scale)
    └──────────────┘
```

---

### What is the Supervisor Pattern?

The **Supervisor Pattern** (also called Orchestrator Pattern or Workflow Agent) is a multi-agent coordination strategy where:

- **One "supervisor" agent** coordinates multiple specialized "worker" agents
- Each worker agent has a specific domain expertise
- The supervisor routes requests, aggregates results, and synthesizes final responses
- Workers don't communicate directly with each other

### Why Use This Pattern?

**Benefits:**
- ✅ **Specialization**: Each agent becomes expert in one domain
- ✅ **Scalability**: Add new specialist agents without changing existing ones
- ✅ **Maintainability**: Update one agent without affecting the system
- ✅ **Parallel execution**: Multiple agents can work simultaneously
- ✅ **Reusability**: Specialist agents can be used standalone
- ✅ **Native AWS Support**: Built into Bedrock Multi-Agent Collaboration

**Trade-offs:**
- ❌ More complex than single agent
- ❌ Higher latency (multiple agent calls)
- ❌ More expensive (each agent invocation costs tokens)
- ❌ Requires robust error handling
- ❌ Less flexible than peer-to-peer collaboration

---

## Architecture Diagrams

### What is an AI Agent? (For Newcomers)

An **AI Agent** is an LLM (Large Language Model) enhanced with:
- **Instructions** - Tell the agent its role and how to behave
- **Tools** - Actions the agent can take (call APIs, query databases)
- **Knowledge** - Data sources the agent can search

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI AGENT                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    LLM (Brain)                           │    │
│  │              e.g., Claude 3.5 Sonnet                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │ Instructions│     │   Tools     │     │  Knowledge  │        │
│  │  (Prompt)   │     │(Action Grps)│     │   (KB/RAG)  │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│         │                    │                    │              │
│         │           ┌───────┴───────┐            │              │
│         │           ▼               ▼            ▼              │
│         │      Lambda APIs     External    Vector DBs           │
│         │      (your code)      Services   (OpenSearch)         │
└─────────────────────────────────────────────────────────────────┘
```

### AWS Bedrock Multi-Agent Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           AWS BEDROCK MULTI-AGENT SYSTEM                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│    ┌─────────┐                                                               │
│    │  User   │                                                               │
│    └────┬────┘                                                               │
│         │ "What clinical trials exist for diabetes datasets?"                │
│         ▼                                                                    │
│    ┌─────────────────────────────────────────────────────────────────┐      │
│    │                    SUPERVISOR AGENT                              │      │
│    │  ┌─────────────────────────────────────────────────────────┐    │      │
│    │  │  agent_collaboration = "SUPERVISOR_ROUTER"               │    │      │
│    │  │                                                          │    │      │
│    │  │  Responsibilities:                                       │    │      │
│    │  │  • Analyze user intent                                   │    │      │
│    │  │  • Route to appropriate collaborator                     │    │      │
│    │  │  • Synthesize responses (SUPERVISOR mode)                │    │      │
│    │  └─────────────────────────────────────────────────────────┘    │      │
│    └────────────────────────────┬────────────────────────────────────┘      │
│                                 │                                            │
│              ┌──────────────────┼──────────────────┐                        │
│              │                  │                  │                        │
│              ▼                  ▼                  ▼                        │
│    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│    │  COLLABORATOR 1 │ │  COLLABORATOR 2 │ │  COLLABORATOR 3 │             │
│    │ Clinical Analyst│ │ Confluence Bot  │ │  Data Analyst   │             │
│    ├─────────────────┤ ├─────────────────┤ ├─────────────────┤             │
│    │ Specializes in: │ │ Specializes in: │ │ Specializes in: │             │
│    │ • Clinical trials│ │ • Documentation │ │ • Data catalogs │             │
│    │ • Drug research │ │ • How-to guides │ │ • Dataset search│             │
│    │ • Medical data  │ │ • Policies      │ │ • Schema info   │             │
│    ├─────────────────┤ ├─────────────────┤ ├─────────────────┤             │
│    │   [Tools]       │ │   [Tools]       │ │   [Tools]       │             │
│    │ • ClinicalTrials│ │ • Confluence API│ │ • Snowflake     │             │
│    │   API           │ │                 │ │ • Data Catalog  │             │
│    │   [Knowledge]   │ │   [Knowledge]   │ │   [Knowledge]   │             │
│    │ • Medical KB    │ │ • Docs KB       │ │ • Datasets KB   │             │
│    └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Routing Flow: SUPERVISOR vs SUPERVISOR_ROUTER

```
                    SUPERVISOR_ROUTER Mode                    SUPERVISOR Mode
                    (Lower Latency)                          (Richer Responses)

User: "Find diabetes trials"              User: "Find diabetes trial datasets"
         │                                          │
         ▼                                          ▼
   ┌───────────┐                              ┌───────────┐
   │ Supervisor│                              │ Supervisor│
   └─────┬─────┘                              └─────┬─────┘
         │                                          │
         │ Routes to ONE agent                      │ Routes to MULTIPLE agents
         ▼                                          ├─────────────┐
   ┌───────────┐                              ┌─────▼─────┐ ┌─────▼─────┐
   │ Clinical  │                              │ Clinical  │ │   Data    │
   │ Analyst   │                              │ Analyst   │ │  Analyst  │
   └─────┬─────┘                              └─────┬─────┘ └─────┬─────┘
         │                                          │             │
         │ Responds directly                        │             │
         ▼                                          └──────┬──────┘
   ┌───────────┐                                          │
   │   User    │◄─────────────────────────────────────────┤
   └───────────┘                                          ▼
                                                   ┌───────────┐
                                                   │ Supervisor│
                                                   │ Synthesizes│
                                                   └─────┬─────┘
                                                         │
                                                         ▼
                                                   ┌───────────┐
                                                   │   User    │
                                                   └───────────┘
```

### Terraform Resource Relationships

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TERRAFORM RESOURCES                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ aws_bedrockagent_agent.supervisor                                 │   │
│  │   agent_name        = "my-supervisor"                             │   │
│  │   agent_collaboration = "SUPERVISOR_ROUTER"  ◄── CRITICAL         │   │
│  │   foundation_model  = "anthropic.claude-3-5-sonnet-..."           │   │
│  │   instruction       = "You are a supervisor..."                   │   │
│  └──────────────────────────────────────┬───────────────────────────┘   │
│                                         │                                │
│                    ┌────────────────────┼────────────────────┐          │
│                    │                    │                    │          │
│                    ▼                    ▼                    ▼          │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐│
│  │aws_bedrockagent_    │ │aws_bedrockagent_    │ │aws_bedrockagent_    ││
│  │agent_collaborator   │ │agent_collaborator   │ │agent_collaborator   ││
│  │.clinical_analyst    │ │.confluence_retriever│ │.data_analyst        ││
│  ├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤│
│  │agent_id = supervisor│ │agent_id = supervisor│ │agent_id = supervisor││
│  │collaborator_name    │ │collaborator_name    │ │collaborator_name    ││
│  │agent_descriptor {   │ │agent_descriptor {   │ │agent_descriptor {   ││
│  │  alias_arn = ...    │ │  alias_arn = ...    │ │  alias_arn = ...    ││
│  │}                    │ │}                    │ │}                    ││
│  │collaboration_       │ │collaboration_       │ │collaboration_       ││
│  │  instruction = ...  │ │  instruction = ...  │ │  instruction = ...  ││
│  └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘│
│             │                       │                       │           │
│             ▼                       ▼                       ▼           │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐│
│  │aws_bedrockagent_    │ │aws_bedrockagent_    │ │aws_bedrockagent_    ││
│  │agent                │ │agent                │ │agent                ││
│  │(existing blueprint) │ │(existing blueprint) │ │(new or existing)    ││
│  │                     │ │                     │ │                     ││
│  │bedrock-agent-       │ │bedrock-agent-       │ │bedrock-agent-       ││
│  │clinical-analyst/    │ │confluence-retriever/│ │data-analyst/        ││
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘│
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

LEGEND:
  ───────►  "references" or "depends on"
  ═══════►  "creates"
```

### Conversation Flow Example

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER: "What datasets are available for diabetes clinical trials?"            │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SUPERVISOR AGENT (thinks):                                                   │
│   "This query involves both clinical trials AND datasets.                   │
│    I should consult multiple specialists."                                  │
│                                                                              │
│   Mode: SUPERVISOR → Will synthesize responses                              │
│   Routing: clinical-analyst + data-analyst                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                          │                         │
                          ▼                         ▼
┌────────────────────────────────────┐ ┌────────────────────────────────────┐
│ CLINICAL ANALYST:                  │ │ DATA ANALYST:                      │
│                                    │ │                                    │
│ "Based on ClinicalTrials.gov,      │ │ "I found these datasets in our     │
│  there are 3 active diabetes       │ │  catalog related to diabetes:      │
│  trials:                           │ │                                    │
│  1. DiabetesA - Phase 3            │ │  1. diabetes_outcomes_2024         │
│  2. GlucoseStudy - Phase 2         │ │  2. glucose_monitoring_raw         │
│  3. InsulinTrial - Phase 1"        │ │  3. patient_demographics"          │
└────────────────────────────────────┘ └────────────────────────────────────┘
                          │                         │
                          └───────────┬─────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SUPERVISOR AGENT (synthesizes):                                              │
│                                                                              │
│ "I found information from both clinical trials and data sources:            │
│                                                                              │
│  **Active Clinical Trials:**                                                │
│  - DiabetesA (Phase 3), GlucoseStudy (Phase 2), InsulinTrial (Phase 1)      │
│                                                                              │
│  **Related Datasets:**                                                      │
│  - diabetes_outcomes_2024, glucose_monitoring_raw, patient_demographics     │
│                                                                              │
│  Would you like more details on any specific trial or dataset?"             │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER receives synthesized response                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Pattern

### High-Level Flow

```
User Query
    ↓
┌─────────────────────┐
│ Supervisor Agent    │  ← Analyzes intent, routes requests
│ (Orchestrator)      │
└─────────────────────┘
    ↓
    ├──────────┬──────────┬──────────┐
    ↓          ↓          ↓          ↓
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│Intent   │ │Data     │ │Search   │ │Response │
│Planner  │ │Retriever│ │Agent    │ │Curator  │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
    ↓          ↓          ↓          ↓
    └──────────┴──────────┴──────────┘
                    ↓
        Synthesized Response
                    ↓
                  User
```

### Component Responsibilities

| Component | Role | Example Tasks |
|-----------|------|---------------|
| **Supervisor** | Orchestration, routing, synthesis | Analyze request → route → combine results |
| **Intent Planner** | Understand user intent | Classify question type, extract entities |
| **Data Retriever** | Search data sources | Query databases, APIs, knowledge bases |
| **Search Agent** | Execute specific searches | Run Cortex Search, filter results |
| **Response Curator** | Format final answer | Structure response, add suggestions |

---

## Core Components

### 1. AgentOrchestrator (The Supervisor)

**File:** `orchestration/agent_orchestrator.py`

**Purpose:** Central coordinator that routes requests to specialist agents

**Key Methods:**

```python
class AgentOrchestrator:
    def __init__(self, session: Session):
        # Initialize all specialist agents
        self.intent_planner_agent = IntentPlannerAgent(session)
        self.response_curator_agent = ResponseCuratorAgent(session)
        
    async def process_query(
        self,
        question: str,
        chat_history: List[Dict],
        data_sources: List[str]
    ) -> Dict:
        """Main orchestration logic"""
        
        # Step 1: Format context
        chat_history = await self._format_chat_history(chat_history)
        
        # Step 2: Identify intent (ROUTING LOGIC)
        question_type = await self.intent_planner_agent.identify_question_type(
            user_query=question,
            chat_history=chat_history
        )
        
        # Step 3: Route based on intent (DECISION TREE)
        if question_type == QuestionType.UNRELATED_QUESTION:
            response = await self.response_curator_agent.curate_unrelated_response()
            
        elif question_type == QuestionType.SPECIFIC_DATASET:
            # Multi-step workflow
            dataset_info = await self.intent_planner_agent.identify_specific_dataset()
            search_results = await self._run_search(dataset_info)
            response = await self.response_curator_agent.curate_dataset_response(
                search_results
            )
            
        elif question_type == QuestionType.DATA_SEARCH:
            # Parallel execution
            data_sources = await self.intent_planner_agent.identify_data_sources()
            search_tasks = [
                self._run_search(source) for source in data_sources
            ]
            search_results = await asyncio.gather(*search_tasks)
            response = await self.response_curator_agent.curate_search_response(
                search_results
            )
        
        # Step 4: Return synthesized response
        return response
```

**Key Patterns:**

1. **Intent-Based Routing**: Supervisor decides which agents to call based on question type
2. **Sequential Orchestration**: Intent → Data → Response (when dependent)
3. **Parallel Execution**: Multiple searches run simultaneously (when independent)
4. **Error Handling**: Try/catch wraps all orchestration logic

---

### 2. IntentPlannerAgent (Intent Classification)

**File:** `agents/intent_planner_agent.py`

**Purpose:** Analyze user queries and classify intent

**Key Methods:**

```python
class IntentPlannerAgent:
    async def identify_question_type(
        self,
        user_query: str,
        chat_history: str
    ) -> Dict[str, str]:
        """
        Classifies question into predefined types
        
        Returns: {"question_type": "DATA_SEARCH"}
        """
        prompt = IDENTIFY_QUESTION_TYPE_PROMPT.format(
            user_query=user_query,
            chat_history=chat_history
        )
        
        response = await complete(
            model=self.model_name,
            prompt=prompt,
            session=self.session
        )
        
        return json.loads(response)
    
    async def identify_data_sources(
        self,
        user_query: str,
        chat_history: str
    ) -> Dict[str, Any]:
        """
        Identifies which data sources to search
        
        Returns: {
            "summarized_query": "Find sales data",
            "data_sources": [
                {"data_source_name": "CDMP", "num_chunks": 5},
                {"data_source_name": "CDGC", "num_chunks": 3}
            ]
        }
        """
        prompt = IDENTIFY_DATA_SOURCES_PROMPT.format(
            user_query=user_query,
            chat_history=chat_history
        )
        
        intent = await complete(
            model=self.model_name,
            prompt=prompt,
            session=self.session
        )
        
        return json.loads(intent)
```

**Question Types (Enum):**

```python
class QuestionType(str, Enum):
    UNRELATED_QUESTION = "unrelated_question"
    UNIMPLEMENTED_QUESTION = "unimplemented_question"
    GENERAL_QUESTION = "general_question"
    SPECIFIC_DATASET = "specific_dataset"
    DATA_SEARCH = "data_search"
    UNCLEAR_QUESTION = "unclear_question"
```

**Best Practice:** Use enums for question types to ensure type safety and consistent routing

---

### 3. DataRetrieverAgent (Data Access)

**File:** `agents/data_retriever_agent.py`

**Purpose:** Execute searches across multiple data sources

**Key Methods:**

```python
class DataRetrieverAgent:
    async def retrieve_datasets(
        self,
        query: str,
        data_sources_and_configs: List[Dict],
        limit: int = 10
    ) -> List[Dict]:
        """
        Multi-step retrieval with LLM filtering:
        1. Search all data sources
        2. Use LLM to rank/filter results
        3. Return top N most relevant
        """
        
        # Step 1: Search all sources in parallel
        combined_datasets = await self.combine_datasets_from_data_sources(
            query=query,
            data_sources_and_configs=data_sources_and_configs
        )
        
        # Step 2: Use LLM to analyze and rank results
        prompt = DATA_RETRIEVER_PROMPT.format(
            user_query=query,
            search_results=combined_datasets,
            limit=limit
        )
        
        reduced_datasets = await complete(
            model=self.model_name,
            prompt=prompt,
            session=self.session
        )
        
        # Step 3: Enrich top results with full metadata
        results = self._enrich_results(reduced_datasets, combined_datasets)
        
        return results
    
    async def combine_datasets_from_data_sources(
        self,
        query: str,
        data_sources_and_configs: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Execute searches in parallel"""
        
        search_tasks = [
            self.run_cortex_search(
                query=query,
                data_source=config["data_source_name"],
                num_chunks=config.get("num_chunks", 5),
                filter=config.get("filter")
            )
            for config in data_sources_and_configs
        ]
        
        # Parallel execution
        search_results = await asyncio.gather(*search_tasks)
        
        # Convert list of tuples to dict
        return {
            data_source: results
            for data_source, results in search_results
        }
```

**Key Pattern:** **Two-Stage Retrieval**
1. **Retrieve**: Get many results from all sources (cast wide net)
2. **Filter**: Use LLM to select most relevant results (intelligent filtering)

This avoids overwhelming the final response with too many results.

---

### 4. CortexSearchAgent (Specific Search Execution)

**File:** `agents/cortex_search_agent.py`

**Purpose:** Execute specific search operations (lowest level agent)

```python
class CortexSearchAgent:
    def __init__(
        self,
        session: Session,
        cortex_search_service_name: str
    ):
        self.session = session
        self.cortex_search_service_name = cortex_search_service_name
    
    def search(
        self,
        query: str,
        columns: List[str],
        filter: Dict[str, Any] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Execute actual search"""
        
        resp = CortexSearchService(
            service_name=self.cortex_search_service_name,
            session=self.session
        ).search(
            query=query,
            columns=columns,
            filter=filter,
            limit=limit
        )
        
        return resp.results
```

**Note:** This is the "leaf node" agent - it doesn't call other agents, just executes searches.

---

### 5. ResponseCuratorAgent (Response Formatting)

**File:** `agents/response_curator_agent.py`

**Purpose:** Format final responses with appropriate structure

**Key Methods:**

```python
class ResponseCuratorAgent:
    async def curate_data_search_response(
        self,
        summarized_query: str,
        search_results: Dict[str, List],
        chat_history: str
    ) -> str:
        """
        Format search results into user-friendly response
        """
        
        prompt = RESPONSE_CURATOR_PROMPT.format(
            summarized_query=summarized_query,
            search_results=json.dumps(search_results),
            chat_history=chat_history
        )
        
        response = await complete(
            model=self.model_name,
            prompt=prompt,
            session=self.session
        )
        
        # Returns JSON with:
        # {
        #   "response": "Here are the datasets I found...",
        #   "suggestions": ["Try searching for X", "You might also want Y"]
        # }
        return response
    
    async def curate_unrelated_question_response(
        self,
        user_query: str,
        chat_history: str
    ) -> str:
        """
        Handle out-of-scope questions politely
        """
        prompt = UNRELATED_QUESTION_PROMPT.format(
            user_query=user_query,
            chat_history=chat_history
        )
        
        return await complete(
            model=self.model_name,
            prompt=prompt,
            session=self.session
        )
```

**Response Curator handles:**
- Formatting results into natural language
- Adding helpful suggestions
- Handling edge cases (no results, errors)
- Maintaining consistent response structure

---

## Implementation Details

### Parallel Execution Pattern

**Problem:** Searching multiple data sources sequentially is slow

**Solution:** Use `asyncio.gather()` to run searches in parallel

```python
# ❌ Sequential (slow)
results = []
for source in data_sources:
    result = await search(source)
    results.append(result)

# ✅ Parallel (fast)
search_tasks = [
    search(source)
    for source in data_sources
]
results = await asyncio.gather(*search_tasks)
```

**Performance Impact:**
- Sequential: 3 sources × 2 seconds = 6 seconds
- Parallel: max(2, 2, 2) = 2 seconds

**When to use:**
- ✅ Multiple independent searches
- ✅ Multiple agent invocations with different inputs
- ❌ Sequential workflow (output of A needed for input of B)

---

### Chat History Management

**Problem:** Full chat history is too long for LLM context window

**Solution:** Summarize older messages, keep recent messages verbatim

```python
async def format_chat_history(
    self,
    chat_history: List[Dict],
    limit: int = 5
) -> str:
    """
    Keep last N messages as-is
    Summarize messages before that
    """
    
    # Older messages (summarize)
    older_messages = chat_history[-2*limit : -limit]
    formatted_older = "\n".join([
        f"User: {m['user']['message']}\nBot: {m['bot']['response']}"
        for m in older_messages
    ])
    
    # Use LLM to summarize older context
    summary_prompt = f"""
    Summarize this chat history in 2-3 sentences:
    {formatted_older}
    """
    
    summary = await complete(
        model=self.model_name,
        prompt=summary_prompt
    )
    
    # Recent messages (keep verbatim)
    recent_messages = chat_history[-limit:]
    formatted_recent = "\n".join([
        f"User: {m['user']['message']}\n"
        f"Bot Response: {m['bot']['response']}\n"
        f"Search Results: {m['bot'].get('search_results', [])}\n"
        f"Suggestions: {m['bot'].get('suggestions', [])}"
        for m in recent_messages
    ])
    
    return f"""
    Earlier conversation summary:
    {summary}
    
    Last {limit} messages:
    {formatted_recent}
    """
```

**Best Practice:** Keep full details of recent messages (search results, suggestions) so agents can reference them.

---

### Error Handling Strategy

**Pattern:** Supervisor catches all errors and returns user-friendly messages

```python
class AgentOrchestrator:
    async def process_query(self, question, chat_history):
        try:
            # All orchestration logic here
            
            # Format history
            chat_history = await self._format_chat_history(chat_history)
            
            # Identify intent
            question_type = await self.intent_planner_agent.identify_question_type()
            
            # Route and process
            response = await self._route_and_process(question_type)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in agent orchestrator: {str(e)}")
            
            # Return graceful error to user
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "error": str(e)
            }, None, Error(f"Orchestration error: {str(e)}")
```

**Error Hierarchy:**
1. **Agent-level errors**: Each agent handles its own errors
2. **Orchestrator-level errors**: Supervisor catches and logs all errors
3. **User-facing errors**: Return friendly message, never expose internals

---

### Configuration Management

**Pattern:** Centralized configuration for all agents and data sources

```python
# configuration/settings.py

class Settings:
    # LLM Configuration
    DEFAULT_LLM_MODEL_NAME = "claude-3-sonnet"
    
    # Snowflake Configuration
    SNOWFLAKE_DATABASE = "DATA_CATALOG"
    SNOWFLAKE_SCHEMA = "PUBLIC"
    
    # Cortex Search Services Configuration
    SNOWFLAKE_CORTEX_SEARCH_SERVICES = {
        "CDMP": {
            "cortex_search_service_name": "CDMP_SEARCH_SERVICE",
            "columns": [
                "DATA_PRODUCT_ID",
                "DATA_PRODUCT_NAME",
                "DATA_PRODUCT_DESCRIPTION",
                "DATA_PRODUCT_URL"
            ],
            "column_name_for_dataset_id": "DATA_PRODUCT_ID",
            "column_name_for_dataset_name": "DATA_PRODUCT_NAME",
            "num_chunks_default": 5
        },
        "CDGC": {
            "cortex_search_service_name": "CDGC_SEARCH_SERVICE",
            "columns": [
                "IDENTITY",
                "NAME",
                "DESCRIPTION",
                "DATA_PRODUCT_URL"
            ],
            "column_name_for_dataset_id": "IDENTITY",
            "column_name_for_dataset_name": "NAME",
            "num_chunks_default": 3
        }
    }
    
    # Response Configuration
    EXTRA_RESULTS_SIZE = 10
    
    # Key Mapping (for frontend)
    KEY_NAME_MAPPING = {
        "DATA_PRODUCT_ID": "ref_id",
        "DATA_PRODUCT_NAME": "name",
        "DATA_PRODUCT_DESCRIPTION": "description",
        "DATA_PRODUCT_URL": "url"
    }
```

**Best Practice:** 
- ✅ All configuration in one place
- ✅ Environment-specific overrides
- ✅ Type hints for IDE support
- ✅ Descriptive names for data source configs

---

## Best Practices

### 1. Prompt Engineering

**Structure prompts consistently across all agents:**

```python
# Base prompt (context)
BASE_PROMPT = """
You are a data discovery assistant helping users find datasets.

Available data sources:
- CDMP: Clinical Data Management Platform
- CDGC: Clinical Data Governance Catalog
- RWD: Real World Data

User Query: {user_query}
Chat History: {chat_history}
"""

# Task-specific prompt (instruction)
IDENTIFY_QUESTION_TYPE_PROMPT = """
Analyze the user query and classify it into one of these types:
1. unrelated_question: Not about data discovery
2. general_question: About the system capabilities
3. specific_dataset: Looking for a specific named dataset
4. data_search: General search for datasets

Return JSON: {"question_type": "...", "reasoning": "..."}
"""

# Complete prompt
full_prompt = BASE_PROMPT + IDENTIFY_QUESTION_TYPE_PROMPT
```

**Best Practices:**
- ✅ Use structured output (JSON) for agent responses
- ✅ Include reasoning field for debugging
- ✅ Provide examples in prompts (few-shot learning)
- ✅ Be explicit about output format
- ✅ Version your prompts (store in config files)

---

### 2. Logging and Observability

**Log at every orchestration step:**

```python
logger.info("Starting query processing...")

logger.info("Formatting chat history...")
chat_history = await self._format_chat_history(chat_history)

logger.info("Identifying question type...")
question_type = await self.intent_planner_agent.identify_question_type()
logger.debug(f"Question type identified: {question_type}")

if question_type == QuestionType.DATA_SEARCH:
    logger.info("Identifying data sources...")
    data_sources = await self.intent_planner_agent.identify_data_sources()
    logger.debug(f"Data sources identified: {data_sources}")
    
    logger.info("Searching for datasets...")
    search_results = await self._run_search(data_sources)
    logger.debug(f"Found {len(search_results)} results")
    
    logger.info("Curating response...")
    response = await self.response_curator_agent.curate_response()

logger.info("Query processing complete")
```

**What to log:**
- ✅ Start/end of each orchestration step
- ✅ Agent decisions (question type, data sources)
- ✅ Performance metrics (search time, result counts)
- ✅ Errors with full stack traces
- ❌ Don't log sensitive user data
- ❌ Don't log giant JSON blobs (summarize instead)

---

### 3. Testing Strategy

**Unit Tests: Test each agent independently**

```python
# test_intent_planner_agent.py

@pytest.mark.asyncio
async def test_identify_question_type_data_search(mock_session):
    agent = IntentPlannerAgent(session=mock_session)
    
    # Mock the LLM response
    with patch('snowflake.cortex.complete') as mock_complete:
        mock_complete.return_value = '{"question_type": "data_search"}'
        
        result = await agent.identify_question_type(
            user_query="Find datasets about sales",
            chat_history=""
        )
        
        assert result["question_type"] == "data_search"
```

**Integration Tests: Test orchestration**

```python
# test_agent_orchestrator.py

@pytest.mark.asyncio
async def test_orchestrator_data_search_workflow(mock_session):
    orchestrator = AgentOrchestrator(session=mock_session)
    
    # Mock each agent's responses
    with patch.object(
        orchestrator.intent_planner_agent,
        'identify_question_type'
    ) as mock_intent:
        mock_intent.return_value = {"question_type": "data_search"}
        
        with patch.object(
            orchestrator.intent_planner_agent,
            'identify_data_sources'
        ) as mock_sources:
            mock_sources.return_value = {
                "data_sources": [{"data_source_name": "CDMP", "num_chunks": 5}]
            }
            
            with patch.object(
                orchestrator,
                '_run_search'
            ) as mock_search:
                mock_search.return_value = ("CDMP", [{"result": "data"}])
                
                response, _ = await orchestrator.process_query(
                    question="Find sales data",
                    chat_history=[]
                )
                
                assert response is not None
```

**End-to-End Tests: Test full system**

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_query_workflow(real_session):
    """
    Test with real Snowflake session
    Warning: This test costs money (LLM calls)
    """
    orchestrator = AgentOrchestrator(session=real_session)
    
    response, _ = await orchestrator.process_query(
        question="What datasets do you have about clinical trials?",
        chat_history=[]
    )
    
    assert "response" in response
    assert len(response["response"]) > 0
```

---

### 4. Performance Optimization

**Cache expensive operations:**

```python
from functools import lru_cache

class IntentPlannerAgent:
    @lru_cache(maxsize=100)
    async def identify_question_type(
        self,
        user_query: str,
        chat_history_hash: str  # Hash of chat history
    ) -> Dict:
        """
        Cache question type identification
        
        Use hash of chat_history instead of full history
        to make it cacheable
        """
        # ... implementation
```

**Timeout long-running operations:**

```python
import asyncio

# Set timeout for agent calls
try:
    response = await asyncio.wait_for(
        self.data_retriever_agent.retrieve_datasets(),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    logger.error("Data retrieval timed out")
    return self._get_timeout_response()
```

**Stream responses for better UX:**

```python
# Instead of waiting for full response
response = await generate_full_response()  # User waits...
return response

# Stream partial responses
async for chunk in generate_streaming_response():
    yield chunk  # User sees progress!
```

---

### 5. Versioning and Deployment

**Version your agents:**

```python
class IntentPlannerAgent:
    VERSION = "2.1.0"  # Track agent versions
    
    def __init__(self):
        logger.info(f"Initializing IntentPlannerAgent v{self.VERSION}")
```

**A/B test different strategies:**

```python
class AgentOrchestrator:
    def __init__(self, strategy="v2"):
        self.strategy = strategy
        
        if strategy == "v1":
            # Old sequential approach
            self.data_retriever = DataRetrieverV1()
        elif strategy == "v2":
            # New parallel approach
            self.data_retriever = DataRetrieverV2()
```

---

## Adapting to Bedrock Agents

### AWS Native Multi-Agent Support (GA March 2025)

**IMPORTANT:** AWS Bedrock now has **native multi-agent collaboration** built into the service!

**Official Documentation:**
- [Multi-agent collaboration user guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [AWS Solutions: Multi-Agent Orchestration](https://aws.amazon.com/solutions/guidance/multi-agent-orchestration-on-aws/)

**Key Features:**
- ✅ Native supervisor/collaborator pattern
- ✅ Automatic task delegation and response aggregation
- ✅ Built-in monitoring and observability
- ✅ Supports up to **10 collaborator agents** per supervisor
- ✅ All agents have full capabilities (action groups, knowledge bases, guardrails)

**AWS Terraform Samples:**
- [amazon-bedrock-multiagent-orchestrator-terraform](https://github.com/aws-samples/amazon-bedrock-multiagent-orchestrator-terraform)
- [bedrock-multi-agents-collaboration-workshop](https://github.com/aws-samples/bedrock-multi-agents-collaboration-workshop)
- [aws-ia/terraform-aws-bedrock](https://registry.terraform.io/modules/aws-ia/bedrock/aws/latest) (includes agent-collaborator example)

### Key Differences

| OneMesh Pattern | Bedrock Pattern |
|-----------------|-----------------|
| Python functions | **Native Bedrock Agents with built-in collaboration** |
| Snowflake Cortex LLM | Claude models via Bedrock |
| Direct function calls | Agent invocation via API **or native collaboration** |
| Synchronous control flow | Async agent invocations (managed by Bedrock) |
| Cortex Search | Knowledge Base queries |
| Single-tenant | Multi-tenant AWS service |
| Custom orchestration code | **Native collaboration features (preferred)** |

### Supervisor Collaboration Modes

AWS Bedrock offers **two distinct collaboration modes** for supervisor agents. Choose based on your use case:

| Mode | `agent_collaboration` Value | Behavior | Best For |
|------|----------------------------|----------|----------|
| **Coordinator** | `SUPERVISOR` | Supervisor coordinates responses from multiple collaborators and **synthesizes** a combined answer | Complex queries requiring insights from multiple agents |
| **Router** | `SUPERVISOR_ROUTER` | Supervisor routes to a **single** collaborator who sends the final response directly | Single-domain queries, lower latency requirements |

**When to use `SUPERVISOR` mode:**
- Queries often require combining information from multiple specialists
- You need the supervisor to synthesize and format responses
- Response quality is more important than latency

**When to use `SUPERVISOR_ROUTER` mode:**
- Queries typically map to a single domain expert
- Lower latency is critical
- Collaborators can provide complete answers independently

**Recommendation:** Start with `SUPERVISOR_ROUTER` for simpler implementation and lower latency. Switch to `SUPERVISOR` if you frequently need multi-agent synthesis.

---

### Translation Guide

## IMPLEMENTATION APPROACH: Two Options

### Option A: Native Bedrock Multi-Agent (RECOMMENDED)

AWS Bedrock now has **built-in multi-agent collaboration**. This is the recommended approach.

**Advantages:**
- ✅ No Lambda orchestration needed
- ✅ AWS handles coordination automatically
- ✅ Built-in monitoring and logging
- ✅ Simpler to implement and maintain
- ✅ Lower latency (no Lambda hops)
- ✅ Better error handling out of the box

**Limitations:**
- ❌ Less control over orchestration logic
- ❌ Cannot customize coordination beyond prompts
- ❌ Max 10 collaborator agents
- ❌ No custom workflow engines

### Option B: Custom Lambda Orchestration

Build your own orchestrator with Lambda (like OneMesh pattern).

**Advantages:**
- ✅ Full control over orchestration
- ✅ Custom workflow logic
- ✅ Parallel execution strategies
- ✅ Integration with non-Bedrock systems

**Limitations:**
- ❌ More code to maintain
- ❌ Higher latency (Lambda hops)
- ❌ More complex error handling
- ❌ Need to handle retries, timeouts, etc.

**Recommendation:** Start with **Option A (Native)** unless you have specific requirements for custom orchestration.

---

## Option A: Native Multi-Agent Implementation

#### 1. Create Collaborator Agents First

**OneMesh:**
```python
class AgentOrchestrator:
    def __init__(self):
        self.intent_planner_agent = IntentPlannerAgent()
        self.data_retriever_agent = DataRetrieverAgent()
```

**Bedrock (Native):**
```hcl
# Step 1: Create specialist agents (collaborators)

# Clinical Analyst Agent (already exists in your repo)
module "clinical_analyst_agent" {
  source = "../../modules/bedrock/agent"
  
  agent_name = "${var.app_name_short}-${var.env}-clinical-analyst"
  foundation_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  agent_instruction_path = file("${path.module}/prompts/clinical-analyst-instructions.txt")
  
  # This agent becomes a collaborator
}

# Confluence Retriever Agent (already exists)
module "confluence_retriever_agent" {
  source = "../../modules/bedrock/agent"
  
  agent_name = "${var.app_name_short}-${var.env}-confluence-retriever"
  foundation_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  agent_instruction_path = file("${path.module}/prompts/confluence-instructions.txt")
}

# Data Analyst Agent
module "data_analyst_agent" {
  source = "../../modules/bedrock/agent"
  
  agent_name = "${var.app_name_short}-${var.env}-data-analyst"
  foundation_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  agent_instruction_path = file("${path.module}/prompts/data-analyst-instructions.txt")
}
```

#### 2. Create Supervisor Agent with Collaborators

> **Reference Implementation:** Based on [ajaydhungel7/bedrock-agents-collab](https://github.com/ajaydhungel7/bedrock-agents-collab) (AWS Summit Toronto 2025)

```hcl
# Step 2: Create supervisor agent
# IMPORTANT: Only the SUPERVISOR agent gets agent_collaboration set
resource "aws_bedrockagent_agent" "supervisor" {
  agent_name                  = "${var.app_name_short}-${var.env}-supervisor-agent"
  agent_resource_role_arn     = aws_iam_role.supervisor_agent_role.arn
  foundation_model            = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  idle_session_ttl_in_seconds = 600
  
  instruction = file("${path.module}/prompts/supervisor-instructions.txt")
  
  # CRITICAL: Enable multi-agent collaboration
  # Options: "SUPERVISOR" (synthesizes responses) or "SUPERVISOR_ROUTER" (routes to single agent)
  agent_collaboration = "SUPERVISOR_ROUTER"
  
  # Set to false - we'll prepare after associating collaborators
  prepare_agent = false
}

# Step 3: Create aliases for collaborator agents (required for association)
resource "aws_bedrockagent_agent_alias" "clinical_analyst_alias" {
  agent_id         = module.clinical_analyst_agent.bedrock_agent_id
  agent_alias_name = "live"
}

resource "aws_bedrockagent_agent_alias" "confluence_retriever_alias" {
  agent_id         = module.confluence_retriever_agent.bedrock_agent_id
  agent_alias_name = "live"
}

# Step 4: Associate collaborator agents with supervisor
# IMPORTANT: Use depends_on to ensure aliases exist before association
resource "aws_bedrockagent_agent_collaborator" "clinical_analyst" {
  agent_id          = aws_bedrockagent_agent.supervisor.agent_id
  collaborator_name = "clinical-analyst"
  
  collaboration_instruction = "Use this agent for clinical trial questions, drug development, and medical research queries."
  relay_conversation_history = "TO_COLLABORATOR"
  
  agent_descriptor {
    alias_arn = aws_bedrockagent_agent_alias.clinical_analyst_alias.agent_alias_arn
  }
  
  depends_on = [aws_bedrockagent_agent_alias.clinical_analyst_alias]
}

resource "aws_bedrockagent_agent_collaborator" "confluence_retriever" {
  agent_id          = aws_bedrockagent_agent.supervisor.agent_id
  collaborator_name = "confluence-retriever"
  
  collaboration_instruction = "Use this agent for documentation, how-to guides, and internal knowledge queries."
  relay_conversation_history = "TO_COLLABORATOR"
  
  agent_descriptor {
    alias_arn = aws_bedrockagent_agent_alias.confluence_retriever_alias.agent_alias_arn
  }
  
  depends_on = [aws_bedrockagent_agent_alias.confluence_retriever_alias]
}

# Step 5: Create supervisor alias (after collaborators are associated)
resource "aws_bedrockagent_agent_alias" "supervisor_alias" {
  agent_id         = aws_bedrockagent_agent.supervisor.agent_id
  agent_alias_name = "live"
  
  depends_on = [
    aws_bedrockagent_agent_collaborator.clinical_analyst,
    aws_bedrockagent_agent_collaborator.confluence_retriever
  ]
}
```

**Key Implementation Notes (from AWS Summit demo):**

1. **Only supervisor gets `agent_collaboration`** - Collaborator agents are simple agents (no `agent_collaboration` attribute)
2. **Create aliases first** - Collaborators must have aliases before they can be associated
3. **Use `depends_on`** - Ensures correct resource ordering
4. **`prepare_agent = false`** on supervisor - Prepare after all collaborators are associated
5. **`relay_conversation_history = "TO_COLLABORATOR"`** - Enables context passing
```

#### 3. Supervisor Agent Instructions (Prompt)

**Supervisor instructions (`prompts/supervisor-instructions.txt`):**
```
You are a supervisor agent coordinating a team of specialist agents to help users with their queries.

Your team of collaborators:
- clinical-analyst: Specializes in clinical trials, drug development, and medical research
- confluence-retriever: Specializes in finding documentation, how-to guides, and internal knowledge
- data-analyst: Specializes in datasets, data catalogs, and data discovery

Your responsibilities:
1. Analyze the user's query to understand their intent
2. Determine which specialist agent(s) can best answer the query
3. Collaborate with the appropriate agent(s)
4. Synthesize their responses into a comprehensive answer

Routing Guidelines:
- Clinical/medical questions → Collaborate with clinical-analyst
- Documentation/how-to questions → Collaborate with confluence-retriever
- Dataset/data questions → Collaborate with data-analyst
- Complex questions → Collaborate with multiple agents and combine insights
- Simple/general questions → Answer directly if you have the information

Best Practices:
- Always explain which specialists you're consulting
- If multiple agents provide information, synthesize it cohesively
- If an agent cannot answer, try alternative approaches
- Be transparent about which information came from which specialist

Example:
User: "What datasets are available for diabetes clinical trials?"
You should: Collaborate with both clinical-analyst (for trial context) and data-analyst (for datasets), then combine their insights.
```

**NOTE:** With native Bedrock multi-agent, you don't need to explicitly call functions. Bedrock automatically handles agent invocation based on your instructions and the collaboration_instruction for each collaborator.

---

## Option B: Custom Lambda Orchestration (Legacy/Advanced)

> **⚠️ Note:** This approach is more complex and typically **not recommended** for new implementations. Use Option A (Native Multi-Agent) unless you have specific requirements for custom orchestration logic, integration with non-Bedrock systems, or workflows that exceed native capabilities.

The following sections show how to build custom orchestration with Lambda. This is provided for reference and advanced use cases only.

#### 2. Agent Functions → Action Groups

**OneMesh:**
```python
class DataRetrieverAgent:
    async def retrieve_datasets(self, query, sources):
        # Search logic
        return results
```

**Bedrock:**
```hcl
# Lambda action group for agent invocation
resource "aws_bedrockagent_agent_action_group" "invoke_agents" {
  agent_id = aws_bedrockagent_agent.supervisor.id
  action_group_name = "invoke_agents"
  
  action_group_executor {
    lambda = aws_lambda_function.invoke_agents.arn
  }
  
  function_schema {
    member_functions {
      functions {
        name = "invoke_agent"
        description = "Invoke a specialist agent to answer a query"
        
        parameters {
          map_block_key = "agent_name"
          type = "string"
          description = "Name of agent to invoke: clinical-analyst, confluence-retriever, or data-analyst"
          required = true
        }
        
        parameters {
          map_block_key = "query"
          type = "string"
          description = "The query to send to the specialist agent"
          required = true
        }
      }
    }
  }
}
```

**Lambda function (`lambdas/functions/invoke_agents/index.py`):**
```python
import boto3
import json

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Map agent names to IDs
AGENT_MAP = {
    'clinical-analyst': 'ABC123',
    'confluence-retriever': 'DEF456',
    'data-analyst': 'GHI789'
}

def lambda_handler(event, context):
    """
    Invoke a specialist Bedrock agent
    
    This is analogous to calling agent methods in OneMesh
    """
    try:
        # Extract parameters
        agent_name = event['requestBody']['content']['application/json']['properties'][0]['value']
        query = event['requestBody']['content']['application/json']['properties'][1]['value']
        
        # Get agent ID
        agent_id = AGENT_MAP.get(agent_name)
        if not agent_id:
            return format_error_response(400, f"Unknown agent: {agent_name}")
        
        # Invoke the specialist agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId='TSTALIASID',
            sessionId=f"supervisor-{context.aws_request_id}",
            inputText=query
        )
        
        # Extract response
        agent_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                agent_response += event['chunk']['bytes'].decode('utf-8')
        
        # Return to supervisor
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({
                            "agent_name": agent_name,
                            "query": query,
                            "response": agent_response
                        })
                    }
                }
            }
        }
        
    except Exception as e:
        return format_error_response(500, str(e))

def format_error_response(status_code, message):
    return {
        "messageVersion": "1.0",
        "response": {
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": message})
                }
            }
        }
    }
```

#### 3. Question Types → Agent Routing Logic

**OneMesh:** Enum-based routing
```python
if question_type == QuestionType.DATA_SEARCH:
    # Route to data agents
elif question_type == QuestionType.SPECIFIC_DATASET:
    # Route to dataset lookup
```

**Bedrock:** Prompt-based routing (supervisor decides)

The supervisor agent's prompt teaches it to route:

```
When user asks about:
- Clinical trials, drug development, medical research → invoke clinical-analyst
- How to use system, documentation, guides → invoke confluence-retriever
- Available datasets, data catalog → invoke data-analyst

If multiple agents needed:
1. Invoke clinical-analyst for medical context
2. Invoke data-analyst for datasets
3. Combine both responses

Example:
User: "What datasets are available for diabetes clinical trials?"
You should:
1. Invoke clinical-analyst with "What are diabetes clinical trials?"
2. Invoke data-analyst with "Find datasets related to diabetes"
3. Synthesize: "Based on clinical trials data and available datasets, here's what I found..."
```

#### 4. Parallel Execution

**OneMesh:**
```python
# Parallel searches
search_tasks = [
    self._run_search(source1),
    self._run_search(source2),
    self._run_search(source3)
]
results = await asyncio.gather(*search_tasks)
```

**Bedrock:**

Option A: Lambda handles parallel invocation
```python
# In invoke_agents Lambda
async def invoke_multiple_agents(agent_queries):
    """Invoke multiple agents in parallel"""
    tasks = [
        invoke_bedrock_agent(agent_id, query)
        for agent_id, query in agent_queries
    ]
    return await asyncio.gather(*tasks)
```

Option B: Supervisor invokes sequentially (simpler)
```
The supervisor agent invokes agents one at a time:
1. Clinical analyst result: "..."
2. Data analyst result: "..."
3. Combines them
```

For MVP, **Option B is recommended** (simpler, easier to debug).

#### 5. Error Handling

**OneMesh:**
```python
try:
    response = await agent.process()
except Exception as e:
    logger.error(f"Error: {e}")
    return error_response
```

**Bedrock:**

In Lambda:
```python
try:
    response = bedrock_agent_runtime.invoke_agent(...)
except ClientError as e:
    if e.response['Error']['Code'] == 'ThrottlingException':
        # Handle rate limiting
        return retry_response()
    else:
        return error_response(str(e))
except Exception as e:
    return error_response(str(e))
```

In Supervisor instructions:
```
If an agent invocation fails:
- Acknowledge the failure to the user
- Try an alternative approach if possible
- Don't show technical errors to users
```

---

### Complete Bedrock Implementation Example

**File structure:**
```
blueprints/bedrock-agent-supervisor/
├── main.tf                           # Terraform orchestration
├── prompts/
│   └── supervisor-instructions.txt   # Supervisor agent prompt
├── lambdas/
│   └── invoke_agents/
│       ├── index.py                  # Agent invocation Lambda
│       └── requirements.txt          # boto3
└── config/
    └── dev/
        └── tfvars.conf              # Configuration
```

**`main.tf`:**
```hcl
# KMS, Lambda Layer (reuse existing modules)

# Supervisor Agent
module "supervisor_agent" {
  source = "../../modules/bedrock/agent"
  
  agent_name = "${var.app_name_short}-${var.env}-supervisor-agent"
  foundation_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  agent_instruction_path = file("${path.module}/prompts/supervisor-instructions.txt")
  
  kms_key_arn = module.kms_key.kms_key_arn
}

# Lambda for invoking other agents
module "lambda_invoke_agents" {
  source = "../../modules/lambda"
  
  lambda_name = "${var.app_name_short}-${var.env}-invoke-agents"
  lambda_handler = "index.lambda_handler"
  lambda_runtime = "python3.12"
  lambda_source_code_path = "lambdas/invoke_agents"
  
  lambda_variables = {
    CLINICAL_AGENT_ID = var.clinical_agent_id
    CONFLUENCE_AGENT_ID = var.confluence_agent_id
    DATA_AGENT_ID = var.data_agent_id
  }
  
  kms_key_arn = module.kms_key.kms_key_arn
}

# IAM policy for Lambda to invoke agents
resource "aws_iam_role_policy" "lambda_invoke_agents_policy" {
  name = "${var.app_name_short}-${var.env}-invoke-agents-policy"
  role = module.lambda_invoke_agents.lambda_role.name
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent"
        ]
        Resource = [
          "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:agent/*"
        ]
      }
    ]
  })
}

# Action Group for agent invocation
resource "aws_bedrockagent_agent_action_group" "invoke_agents" {
  agent_id = module.supervisor_agent.bedrock_agent_id
  agent_version = "DRAFT"
  action_group_name = "invoke_agents"
  
  action_group_executor {
    lambda = module.lambda_invoke_agents.lambda_arn
  }
  
  function_schema {
    member_functions {
      functions {
        name = "invoke_agent"
        description = "Invoke a specialist agent to answer specific queries"
        
        parameters {
          map_block_key = "agent_name"
          type = "string"
          description = "Agent to invoke: clinical-analyst, confluence-retriever, or data-analyst"
          required = true
        }
        
        parameters {
          map_block_key = "query"
          type = "string"
          description = "Query to send to the agent"
          required = true
        }
      }
    }
  }
  
  depends_on = [
    module.supervisor_agent,
    module.lambda_invoke_agents
  ]
}
```

---

## Testing Strategy

### Unit Tests

Test each component independently:

```python
# test_intent_classification.py
def test_supervisor_identifies_clinical_query():
    """Test that clinical queries route correctly"""
    query = "What clinical trials are available for diabetes?"
    
    # Mock Bedrock response
    assert classify_intent(query) == "clinical_query"

# test_agent_invocation.py  
def test_lambda_invokes_clinical_agent():
    """Test Lambda can invoke specialist agent"""
    event = {
        "agent_name": "clinical-analyst",
        "query": "Find trials for diabetes"
    }
    
    response = lambda_handler(event, context)
    assert response['httpStatusCode'] == 200
```

### Integration Tests

Test agent interactions:

```python
# test_supervisor_to_specialist.py
@pytest.mark.integration
def test_supervisor_calls_specialist():
    """
    Test full flow: User → Supervisor → Specialist → Response
    """
    # Invoke supervisor agent
    response = bedrock.invoke_agent(
        agentId=supervisor_agent_id,
        sessionId=test_session_id,
        inputText="What clinical trials are available?"
    )
    
    # Verify response mentions clinical trials
    assert "clinical trial" in response.lower()
```

### End-to-End Tests

Test with real users:

```python
@pytest.mark.e2e
def test_multi_agent_workflow():
    """
    Test complex query requiring multiple agents
    """
    response = bedrock.invoke_agent(
        agentId=supervisor_agent_id,
        inputText="Find documentation about diabetes datasets"
    )
    
    # Should invoke both confluence and data agents
    assert "documentation" in response
    assert "dataset" in response
```

---

## Summary

### Key Takeaways

1. **Supervisor Pattern = Orchestration**
   - One coordinator, multiple specialists
   - Supervisor handles routing and synthesis
   - Specialists focus on domain expertise

2. **Intent Classification is Critical**
   - Determines which agents to invoke
   - Can be LLM-based (flexible) or rule-based (predictable)
   - Bedrock uses prompt-based routing

3. **Parallel Execution Improves Performance**
   - Independent operations run simultaneously
   - Use `asyncio.gather()` in Python
   - Lambda can coordinate parallel Bedrock invocations

4. **Error Handling Must Be Robust**
   - Each layer handles its own errors
   - Supervisor provides fallbacks
   - Never expose technical errors to users

5. **Prompts Are the New Code**
   - Version and test prompts
   - Use structured output (JSON)
   - Include examples and reasoning

### Next Steps for Implementation

**Phase 1: Setup Collaborator Agents**
- Ensure existing agents (clinical-analyst, confluence-retriever) are deployed with aliases
- Verify each agent works standalone before integrating

**Phase 2: Create Supervisor Agent**
- Create supervisor agent with `agent_collaboration = "SUPERVISOR_ROUTER"`
- Write clear supervisor instructions defining routing logic
- Associate collaborator agents using `aws_bedrockagent_agent_collaborator`

**Phase 3: Test & Iterate**
- Test routing with various query types
- Verify conversation history flows correctly
- Adjust `collaboration_instruction` for each collaborator as needed

**Phase 4: Production Readiness**
- Add guardrails to supervisor and collaborators
- Set up CloudWatch monitoring and alarms
- Document usage patterns and examples

---

## AWS Services for Multi-Agent Systems

Based on [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/multi-agent-collaboration.html):

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| **Agent Hosting** | Amazon Bedrock, SageMaker, Lambda | Host individual LLM-driven agents |
| **Communication** | Amazon SQS, EventBridge | Messaging and coordination between agents |
| **Shared Memory** | DynamoDB, S3, OpenSearch | Multi-agent memory or blackboard system |
| **Orchestration** | Step Functions, Lambda pipelines | Kickoff, timeout, fallback, and retry logic |
| **Agent Identity** | Bedrock Agents (role-defined) | Role-based tool invocation and boundary enforcement |
| **Dynamic Routing** | EventBridge pipelines | Enable dynamic task routing or escalation |

### Key Takeaways from AWS

> **"Agent patterns are composable"** – Most real-world agents blend two or more patterns (e.g., a voice agent with tool-based reasoning and memory).

> **"Agent design is contextual"** – Choose patterns based on the interaction surface, task complexity, latency tolerance, and domain-specific constraints.

---

## References

### Official AWS Documentation
- [AWS Multi-Agent Collaboration Overview](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html) - Introduction to native Bedrock multi-agent
- [Create Multi-Agent Collaboration (Step-by-Step)](https://docs.aws.amazon.com/bedrock/latest/userguide/create-multi-agent-collaboration.html) - Detailed implementation guide with Console & API instructions
- [AWS Prescriptive Guidance: Agentic AI Patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/multi-agent-collaboration.html) - Architectural patterns overview
- [AWS Solutions: Multi-Agent Orchestration](https://aws.amazon.com/solutions/guidance/multi-agent-orchestration-on-aws/)

### Official AWS Code Samples & Workshops
- [aws-samples/bedrock-multi-agents-collaboration-workshop](https://github.com/aws-samples/bedrock-multi-agents-collaboration-workshop) - Energy Efficiency Management System workshop with supervisor + sub-agents (Python/Jupyter)
- [Terraform AWS Bedrock Module](https://registry.terraform.io/modules/aws-ia/bedrock/aws/latest) - Community Terraform module

### Terraform Examples (Native Multi-Agent)

> **⚠️ Important:** Not all "multi-agent" repos use native Bedrock collaboration. Some use Step Functions/Lambda orchestration (legacy approach).

| Repository | Approach | Recommended? |
|------------|----------|--------------|
| [ajaydhungel7/bedrock-agents-collab](https://github.com/ajaydhungel7/bedrock-agents-collab) | **Native** `agent_collaboration` + `aws_bedrockagent_agent_collaborator` | ✅ **Yes - Best Reference** |
| [aws-samples/amazon-bedrock-multiagent-orchestrator-terraform](https://github.com/aws-samples/amazon-bedrock-multiagent-orchestrator-terraform) | Step Functions + Lambda (custom orchestration) | ⚠️ Legacy approach |

**The ajaydhungel7 repo is the best Terraform reference** because it uses native Bedrock multi-agent collaboration exactly as recommended by AWS.

### Community Open Source Examples
| Repository | Description | Tech Stack |
|------------|-------------|------------|
| [sathish15g/aws-bedrock-multi-ai-agent-system](https://github.com/sathish15g/aws-bedrock-multi-ai-agent-system) | Supervisor Agent with HR leave + hotel booking collaborators | Python |
| [JGalego/swarm_bedrock](https://github.com/JGalego/swarm_bedrock) | Lightweight multi-agent orchestration framework on Bedrock | Python |
| [zdolin/health-agent-lab](https://github.com/zdolin/health-agent-lab) | Clinical reasoning multi-agent prototype using Strands Agents | Python, FastAPI |
| [divyajshah/bedrock-multi-agent](https://github.com/divyajshah/bedrock-multi-agent) | Multi-agent orchestration code examples | Python |

### Conceptual References
- OneMesh Data Discoverability Chatbot (production implementation pattern)

---

**Document Version:** 1.5  
**Last Updated:** January 30, 2026  
**Maintained By:** Agents Team  
**Changelog:**
- v1.5: **Critical update** - Verified Terraform examples against official AWS docs and [ajaydhungel7/bedrock-agents-collab](https://github.com/ajaydhungel7/bedrock-agents-collab) (AWS Summit Toronto 2025). Added `depends_on`, alias creation, correct resource ordering. Clarified that aws-samples/amazon-bedrock-multiagent-orchestrator-terraform uses Step Functions (legacy), not native collaboration. Updated references to highlight correct native implementation.
- v1.4: Added comprehensive "Agent Patterns Comparison" section covering all three patterns per ticket requirements: Simple Agent, Supervisor + Collaborators, Multi-Level Supervisors. Added pattern selection flowchart, Terraform examples for each pattern, and when-to-use guidance.
- v1.3: Added comparison of Workflow Agents vs Multi-Agent Collaboration patterns (per AWS Prescriptive Guidance), added pattern selection decision tree, added AWS services reference table, expanded references section
- v1.2: Added Quick Start Checklist with actionable TODOs, added comprehensive architecture diagrams for newcomers (AI Agent anatomy, Bedrock multi-agent system, routing flows, Terraform resources, conversation flow example)
- v1.1: Added SUPERVISOR vs SUPERVISOR_ROUTER mode documentation, added `agent_collaboration` attribute to Terraform, marked Lambda orchestration as legacy, updated implementation phases, added official AWS references