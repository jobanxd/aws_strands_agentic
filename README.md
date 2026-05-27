# Strands Agent System — Skeletal Starter

Multi-agent pipeline using [AWS Strands Agents SDK](https://github.com/strands-agents/sdk-python).
Works with AWS Bedrock, local Ollama, or any OpenAI-compatible endpoint.

---

## Project structure

```
strands_agent_project/
├── main.py                        # Entry point
├── requirements.txt
├── .env.example                   # Copy to .env and configure
└── src/
    ├── config/
    │   ├── settings.py            # Loads .env into typed settings
    │   └── model_factory.py       # Returns the right model provider
    ├── tools/
    │   └── data_tools.py          # @tool functions (stub — replace with real logic)
    ├── agents/
    │   ├── base_agent.py          # Base class all agents inherit from
    │   ├── drm_agents.py          # DataAnalyst, ActivityMonitor, Compliance
    │   └── odd_agents.py          # DataSummarizer, Verifier
    ├── pipelines/
    │   ├── data_request_manager.py  # DRM super agent (sequences DRM sub-agents)
    │   ├── odd_validator.py         # ODD super agent (sequences ODD sub-agents)
    │   └── orchestrator.py          # Top-level: routes query, handles all exceptions
    └── utils/
        ├── logger.py              # Shared logger (loguru)
        └── exceptions.py         # Typed exceptions for pipeline control flow
```

---

## Setup

```bash
# 1. Clone / copy this project
cd strands_agent_project

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your model provider
cp .env.example .env
# Edit .env — uncomment the block for your provider (Ollama, Bedrock, or LiteLLM)

# 5. Run
python main.py
python main.py "your custom query here"
```

---

## Model provider quick-start

### Ollama (local, no cloud needed)
```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2
# Set in .env: MODEL_PROVIDER=ollama, MODEL_ID=llama3.2
```

### AWS Bedrock
```bash
# Set in .env: MODEL_PROVIDER=bedrock
# Add AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

### LM Studio / vLLM (OpenAI-compatible)
```bash
pip install litellm
# Set in .env: MODEL_PROVIDER=litellm, LITELLM_API_BASE=http://localhost:1234/v1
```

---

## Pipeline flow

```
Query
  └─► Orchestrator
        ├─► DataRequestManager (super agent)
        │     ├─► DataAnalystAgent        ← may raise InsufficientDataError (early exit)
        │     ├─► ActivityMonitorAgent
        │     └─► ComplianceAgent
        └─► ODDValidator (super agent)
              ├─► DataSummarizerAgent
              └─► VerifierAgent           ← may raise ValidationError
```

### Result statuses
| Status | Meaning |
|---|---|
| `success` | Full pipeline completed |
| `insufficient_data` | Stopped at DataAnalystAgent |
| `validation_failed` | Stopped at VerifierAgent |
| `error` | Unexpected pipeline failure |

---

## Adding a new sub-agent (checklist)

1. Add any new `@tool` functions to `src/tools/`
2. Create the agent class in the relevant `src/agents/` file, inheriting `BaseAgent`
3. Set `SYSTEM_PROMPT` and `TOOLS` on the class
4. Add it to the pipeline sequence in `src/pipelines/`
5. Handle any new exception types in `src/pipelines/orchestrator.py`

---

## Replacing stub tools with real logic

Every function in `src/tools/data_tools.py` has a `# TODO` comment.
Replace the stub return values with your actual DB queries, API calls, or file reads.
Agent code does not need to change — only the tool implementations.
