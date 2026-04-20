# mcp-business-workflows

**An opinionated MCP server that gives AI agents a business-grade workflow layer — not just tool access.**

Most MCP servers expose raw capabilities. This one adds the routing layer on top: every tool returns a structured decision envelope with a `recommended_action`, `confidence` score, `requires_human_review` flag, and `next_step` instruction. Agents can act on these directly, without extra prompt engineering.

---

## Why

Agents need more than tools. They need:
- **Triage** — is this an incident or a routine task?
- **Routing** — escalate to human, dispatch webhook, or continue autonomously?
- **Confidence** — how certain is the system about this recommendation?

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
# Edit .env: set MCP_API_TOKEN, optionally GITHUB_TOKEN and WEBHOOK_DEFAULT_URL

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

## Tools

| Tool | Description |
|---|---|
| `search_notes` | Search operational notes by keyword/tag — returns results + routing signal |
| `create_task` | Create a note/task in the local store — auto-flags incidents for human review |
| `list_open_issues` | Fetch GitHub issues — detects bug/critical labels and recommends triage |
| `dispatch_webhook` | HTTP POST to a webhook — reports delivery status and recommends retry on failure |
| `get_system_status` | Check connector health (GitHub, Webhook) — recommends investigation when degraded |
| `recommend_next_action` | Analyze context, detect signals, recommend the best next workflow step |

Every tool response follows this envelope:

```json
{
  "result": {},
  "recommended_action": "escalate_to_oncall",
  "confidence": 0.92,
  "requires_human_review": true,
  "next_step": "Page the on-call engineer and open an incident note.",
  "context_summary": "Detected incident-level signals in context.",
  "event_id": "a3f1b2c4d5e6"
}
```

---

## Architecture

```
MCP transport (stdio)
  └── Tool definitions     tools/*.py
        └── Service layer  services/*.py
              └── Adapters adapters/*.py
                    ├── NoteStore  (local JSON)
                    ├── GitHubClient (REST API)
                    └── WebhookClient (HTTP POST)

Observability: structlog JSON + event_id on every call
Decision layer: embedded in services, explicit via recommend_next_action
```

See [docs/architecture.md](docs/architecture.md) for the full breakdown and [docs/tools.md](docs/tools.md) for the complete tool reference.

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCP_API_TOKEN` | **Yes** | — | Bearer token for auth |
| `GITHUB_TOKEN` | No | `""` | GitHub PAT for `list_open_issues` |
| `GITHUB_DEFAULT_REPO` | No | `""` | Default `owner/repo` |
| `WEBHOOK_DEFAULT_URL` | No | `""` | Default webhook endpoint |
| `NOTES_STORE_PATH` | No | `./data/notes.json` | Path to notes file |

Copy `.env.example` and fill in your values.

---

## Development

```bash
# Install deps
uv sync --extra dev

# Run tests
make test

# Lint + type check
make lint

# Full check (lint + tests)
make check
```

---

## Roadmap

- [x] `search_notes` — local JSON note store
- [x] `create_task` — note creation with incident detection
- [x] `list_open_issues` — GitHub REST API integration
- [x] `dispatch_webhook` — HTTP POST with delivery status
- [x] `get_system_status` — connector health checks
- [x] `recommend_next_action` — explicit decision-layer tool
- [x] Structured output envelope on all tools
- [x] Structured JSON logging with event IDs
- [x] Bearer token auth
- [ ] Dockerfile + CI (in progress)
- [ ] `recommend_next_action` v2 — LLM-backed with Claude API

---

## License

MIT
