# mcp-business-workflows

**An MCP server that gives AI agents a structured decision layer for tech ops workflows.**

Most MCP servers expose raw capabilities. This one adds a routing layer on top: every tool returns a structured decision envelope with a `recommended_action`, `confidence` score, `requires_human_review` flag, and `next_step` instruction — so agents can act without extra prompt engineering.

**v1 scope:** tech ops — deployments, incidents, GitHub triage, webhook dispatch.
**Designed to extend** to other domains (support, finance, legal) as verticals.

---

## The problem

An AI agent with raw tool access can *do* things. But it doesn't know:
- Is this situation an incident or a routine task?
- Should it escalate to a human or continue autonomously?
- How confident should it be in this action?

`mcp-business-workflows` bakes these decisions into every tool response.

---

## Quickstart

```bash
# 1. Clone and install
git clone https://github.com/binodev/mcp-business-workflows
cd mcp-business-workflows
uv sync --extra dev

# 2. Configure
cp .env.example .env
# Set MCP_API_TOKEN (required), GITHUB_TOKEN and WEBHOOK_DEFAULT_URL (optional)

# 3. Run
uv run mcp-business-workflows
```

Or with Docker:

```bash
docker run --rm \
  -e MCP_API_TOKEN=your-token \
  -e GITHUB_TOKEN=ghp_xxx \
  -v $(pwd)/data:/app/data \
  ghcr.io/binodev/mcp-business-workflows:latest
```

---

## Tools — v1 (tech ops)

| Tool | What it does |
|---|---|
| `get_system_status` | Check connector health — recommends investigation when degraded |
| `search_notes` | Search operational notes by keyword/tag — surfaces past incidents and decisions |
| `create_task` | Create a traceable note — auto-flags incidents for human review |
| `list_open_issues` | Fetch GitHub issues — detects critical labels and recommends triage |
| `dispatch_webhook` | HTTP POST to a webhook — reports delivery status, recommends retry on failure |
| `recommend_next_action` | Analyze context, detect signals, recommend the best next step |

Every tool response follows the same envelope:

```json
{
  "recommended_action": "escalate_to_oncall",
  "confidence": 0.92,
  "requires_human_review": true,
  "next_step": "Page the on-call engineer and open an incident note.",
  "context_summary": "Incident-level signals detected in context.",
  "event_id": "a3f1b2c4d5e6"
}
```

When `requires_human_review` is `true`, a well-designed agent stops and routes to a human. Automation does not proceed blindly.

---

## Real agent test

Connect any supported LLM to this server. The agent autonomously decides which tools to call and stops when human review is required — no scripted flow.

```bash
# Google AI Studio (free tier available)
LLM_PROVIDER=google GOOGLE_API_KEY=... uv run python examples/agent_test.py

# Anthropic
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... uv run python examples/agent_test.py
```

```
[tool call] get_system_status      → system_operational  (confidence: 0.95)
[tool call] create_task            → continue_workflow   (confidence: 0.90)
[tool call] search_notes           → review_results      (confidence: 0.67)
[tool call] list_open_issues       → review_backlog      (confidence: 0.50)
[tool call] recommend_next_action  → requires_human_review: true
```

---

## Architecture

```
MCP transport (stdio)
  └── Tool definitions     tools/*.py
        └── Service layer  services/*.py
              └── Adapters adapters/*.py
                    ├── NoteStore      (local JSON)
                    ├── GitHubClient   (REST API)
                    └── WebhookClient  (HTTP POST)

Observability : structlog JSON + event_id on every call
Decision layer: embedded in services, explicit via recommend_next_action
```

The envelope pattern and decision layer are domain-agnostic. The v1 tools are one vertical — the architecture is designed to add others.

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCP_API_TOKEN` | **Yes** | — | Bearer token for auth |
| `GITHUB_TOKEN` | No | `""` | GitHub PAT for `list_open_issues` |
| `GITHUB_DEFAULT_REPO` | No | `""` | Default `owner/repo` |
| `WEBHOOK_DEFAULT_URL` | No | `""` | Default webhook endpoint |
| `NOTES_STORE_PATH` | No | `./data/notes.json` | Path to notes file |

---

## Development

```bash
uv sync --extra dev   # install
make test             # run tests (44 passing)
make lint             # ruff + mypy
make check            # lint + tests
```

---

## License

MIT
