# Project Plan: Webex AI Chatbot Framework

**Version**: 0.1.0

## Vision

A local-AI-powered Webex chatbot framework that anyone can run in 5 minutes and optionally deploy to production behind enterprise infrastructure. Users pick their LLM provider (Ollama by default, or a cloud provider), paste their Webex bot token, and they're chatting. A personality system lets admins assign custom AI behaviors to users by email pattern.

## Features

### Core (v1)

- **One-script setup** (`setup.py`) — interactive wizard that generates `.env` config, verifies LLM connectivity, starts ngrok, registers the Webex webhook, and launches the bot
- **Separate start script** (`start.py`) — launches the bot using existing `.env` config; re-running `setup.py` overwrites the `.env`
- **Multi-provider LLM support** — Ollama (primary), Anthropic, OpenAI, Gemini, xAI; one provider selected at setup
- **Personality system** — JSON-defined AI personalities (system prompt, temperature, max tokens) assigned to users via email or email-pattern matching
- **User access control** — approved users list (JSON), admin commands to add/remove users via chat
- **Conversation memory** — sliding window of 20 messages per room/conversation, oldest dropped when exceeded
- **Message queue** — async queue so messages are processed in order; concurrent messages wait rather than pile up
- **Webex integration** — works in direct messages and @mentions in group spaces, using the official `webexteamssdk`
- **Built-in commands** — help, ping, health check, list models, user management (admin), prompt management

### Built-in Commands

| Command | Access | Description |
|---------|--------|-------------|
| `help` | All | Show available commands |
| `ping` | All | Test bot responsiveness |
| `health check` | All | Check LLM provider status |
| `list models` | All | Show available models (Ollama only) |
| `use prompt [name] [question]` | All | Use a specific personality for one message |
| `add user email@domain.com` | Admin | Add user to approved list |
| `remove user email@domain.com` | Admin | Remove user from approved list |
| `list users` | Admin | Show all approved users |
| `reload users` | Admin | Reload approved users from file |
| `reload prompts` | Admin | Reload personality configurations |

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.10+ | Primary language |
| Framework | FastAPI | Async web framework for webhooks |
| Package manager | uv | Dependency management |
| Webex SDK | webexteamssdk | Official Webex API integration |
| LLM (primary) | Ollama | Local AI inference |
| LLM (cloud) | Anthropic, OpenAI, Gemini, xAI | Optional cloud LLM providers |
| Tunnel | ngrok | Dev webhook tunneling |
| Linter | Ruff | Linting + formatting |
| Testing | pytest | Unit and integration tests |

### Key Python Dependencies

- `fastapi` + `uvicorn` — web server
- `webexteamssdk` — Webex API
- `httpx` — async HTTP client (for Ollama and cloud LLM APIs)
- `python-dotenv` — `.env` loading
- `pyngrok` — ngrok tunnel management from Python
- `anthropic` — Anthropic SDK (optional, installed if selected)
- `openai` — OpenAI SDK (optional, installed if selected)
- `google-generativeai` — Gemini SDK (optional, installed if selected)

**Note:** xAI uses the OpenAI-compatible API format, so the `openai` package covers both.

## Architecture

### High-Level Flow

```
User (Webex) → Webex Cloud → ngrok tunnel → FastAPI webhook endpoint
                                                    ↓
                                            Webhook Handler
                                            (validate, authorize)
                                                    ↓
                                            Message Queue
                                            (async, ordered)
                                                    ↓
                                            Personality Resolver
                                            (email → personality mapping)
                                                    ↓
                                            Conversation Memory
                                            (load room history)
                                                    ↓
                                            LLM Provider
                                            (Ollama / Cloud)
                                                    ↓
                                            Send response via
                                            Webex SDK
```

### Component Interactions

1. **Webhook endpoint** receives POST from Webex Cloud, validates the request
2. **Webhook handler** checks if the sender is in the approved users list; if not, silently ignores and logs
3. **Command handler** checks if the message is a built-in command; if so, handles it directly
4. **Message queue** accepts non-command messages and processes them one at a time per room
5. **Personality resolver** looks up the sender's email against `user-mappings.json` (exact match first, then pattern match, then default)
6. **Conversation memory** retrieves the last N messages for that room/conversation
7. **LLM provider** sends the system prompt + conversation history to the configured provider and returns the response
8. **Webex SDK** sends the response back to the room/conversation

### Direct Messages vs Group Spaces

- **Direct messages**: bot receives all messages, responds to all
- **Group spaces**: bot only responds when @mentioned; the @mention prefix is stripped before processing

## Project Structure

```
Webex_Chatbot/
├── setup.py                          # Interactive setup wizard
├── start.py                          # Bot launcher
├── pyproject.toml                    # uv project config + dependencies
├── .env.example                      # Template with all config vars
├── .gitignore
├── bot_server/
│   ├── __init__.py
│   ├── app.py                        # FastAPI app, webhook endpoint, lifespan
│   ├── config.py                     # Config loader, validation, settings dataclass
│   ├── providers/
│   │   ├── __init__.py               # Provider factory (get_provider())
│   │   ├── base.py                   # Abstract BaseLLMProvider
│   │   ├── ollama.py                 # OllamaProvider
│   │   ├── anthropic.py              # AnthropicProvider
│   │   ├── openai_provider.py        # OpenAIProvider
│   │   ├── gemini.py                 # GeminiProvider
│   │   └── xai.py                    # XAIProvider (OpenAI-compatible)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── webhook_handler.py        # Webhook receipt + routing
│   │   ├── command_handler.py        # Built-in command parsing + execution
│   │   └── message_queue.py          # Async message queue + worker
│   ├── services/
│   │   ├── __init__.py
│   │   ├── personality.py            # Load personalities, resolve per-user
│   │   ├── memory.py                 # Conversation history manager
│   │   └── user_manager.py           # Approved users CRUD + admin checks
│   └── config/
│       ├── personalities.json        # Personality definitions
│       ├── user-mappings.json        # Email/pattern → personality rules
│       └── approved_users.json       # Approved user list
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── test_providers/
│   │   ├── test_ollama.py
│   │   ├── test_anthropic.py
│   │   ├── test_openai.py
│   │   ├── test_gemini.py
│   │   └── test_xai.py
│   ├── test_handlers/
│   │   ├── test_webhook_handler.py
│   │   ├── test_command_handler.py
│   │   └── test_message_queue.py
│   └── test_services/
│       ├── test_personality.py
│       ├── test_memory.py
│       └── test_user_manager.py
├── docs/
│   ├── project-plan.md               # This document
│   ├── deploy-instruct.md            # Deployment prompt
│   ├── production-deployment.md      # DMZ relay / enterprise guide
│   ├── personality-guide.md          # How to create + assign personalities
│   └── webex-bot-setup.md            # How to create a Webex bot token
└── logs/                             # Runtime logs (gitignored)
```

## Data Models

### personalities.json

Defines available AI personalities. Each personality has a unique key.

```json
{
  "default": {
    "name": "Helpful Assistant",
    "system_prompt": "You are a helpful AI assistant. Be concise, clear, and friendly. If you don't know something, say so.",
    "temperature": 0.2,
    "max_tokens": 1000
  },
  "cisco-expert": {
    "name": "Cisco Expert",
    "system_prompt": "You are a Cisco networking expert. You specialize in Cisco routing, switching, security, and collaboration technologies. Provide precise, technically accurate answers with relevant IOS/NX-OS commands when applicable.",
    "temperature": 0.3,
    "max_tokens": 1500
  },
  "code-reviewer": {
    "name": "Code Reviewer",
    "system_prompt": "You are a senior code reviewer. Analyze code for bugs, security issues, performance problems, and style. Be constructive but thorough.",
    "temperature": 0.1,
    "max_tokens": 2000
  }
}
```

**Fields:**
- `name` — display name shown in help/list commands
- `system_prompt` — the system message sent to the LLM
- `temperature` — creativity dial (0.0 = deterministic, 1.0 = creative)
- `max_tokens` — maximum response length

### user-mappings.json

Maps users to personalities. Evaluated in order: exact email match first, then pattern match, then default.

```json
{
  "default_personality": "default",
  "mappings": [
    {
      "match": "admin@company.com",
      "type": "exact",
      "personality": "code-reviewer"
    },
    {
      "match": "*@cisco.com",
      "type": "pattern",
      "personality": "cisco-expert"
    },
    {
      "match": "*@engineering.company.com",
      "type": "pattern",
      "personality": "code-reviewer"
    }
  ]
}
```

**Matching logic:**
1. Check all `"type": "exact"` entries for the sender's email
2. Check all `"type": "pattern"` entries using glob/wildcard matching, first match wins
3. Fall back to `default_personality`

Users can override with `use prompt [name] [question]` for a single message.

### approved_users.json

Controls who can interact with the bot.

```json
{
  "description": "Approved users for Webex AI Bot",
  "users": [
    {
      "email": "john.doe@company.com",
      "name": "John Doe",
      "added_date": "2025-07-30",
      "added_by": "setup"
    }
  ]
}
```

### Conversation Memory (in-memory)

```python
# Keyed by room_id
{
  "room_abc123": [
    {"role": "user", "content": "What is BGP?", "timestamp": "..."},
    {"role": "assistant", "content": "BGP is...", "timestamp": "..."}
  ]
}
```

- Maximum 20 messages per room (sliding window)
- When message 21 arrives, message 1 is dropped
- Memory clears on bot restart (acceptable for v1)

## External Integrations

### Webex API (via webexteamssdk)
- **Webhook registration** — bot registers its ngrok URL to receive message events
- **Message retrieval** — when a webhook fires, the bot fetches the message content
- **Message sending** — bot sends responses back to the room
- **Documentation**: [developer.webex.com](https://developer.webex.com)

### Ollama API
- **Endpoint**: configurable, default `http://localhost:11434`
- **Used for**: chat completions (`/api/chat`), model listing (`/api/tags`), health checks
- **Can be local or remote** — any machine running Ollama on a reachable IP

### Cloud LLM APIs (optional)
- **Anthropic** — `https://api.anthropic.com` via `anthropic` SDK
- **OpenAI** — `https://api.openai.com` via `openai` SDK
- **Gemini** — `https://generativelanguage.googleapis.com` via `google-generativeai` SDK
- **xAI** — `https://api.x.ai` via `openai` SDK (OpenAI-compatible)

## Deployment Target

**Primary**: Self-hosted Linux server or WSL environment. The bot runs as a Python process with ngrok providing the public webhook endpoint.

**Production upgrade path**: documented in [production-deployment.md](production-deployment.md) — covers DMZ relay server, SSL, systemd services, and enterprise network topology.

## Standards

### Logging

- **Format**: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- **Levels**: DEBUG (development), INFO (default), WARNING, ERROR
- **Output**: stdout + rotating file handler
- **File**: `logs/bot_server.log`, 5MB max, 3 backup files
- **Config**: `LOG_LEVEL` in `.env`
- **Sensitive data**: never log message content at INFO level; DEBUG only. Never log API keys.

### Error Handling

- **LLM provider failures** → return friendly message to user: "I'm having trouble connecting to the AI service. Please try again in a moment."
- **LLM timeout** → 30-second timeout per request, same friendly message on timeout
- **Webex API failures** → log error, retry once with 2-second delay, then drop silently
- **Invalid webhook** → return 401, log sender info at WARNING level
- **Unauthorized user** → silently ignore, log at INFO level
- **Config file parse errors** → log ERROR, refuse to start with clear message about which file is malformed
- **Never** expose stack traces, internal errors, or file paths in chat responses

### Authentication & Authorization

- **Webex webhooks**: validate using webhook secret (HMAC) when available
- **User authorization**: sender email checked against `approved_users.json`
- **Admin actions**: sender email checked against `ADMIN_EMAILS` in `.env`
- **LLM API keys**: stored in `.env`, loaded at startup, never logged

### Code Style

- **Linter/formatter**: Ruff (replaces black + isort + flake8)
- **Type hints**: required on all public function signatures
- **Docstrings**: required on modules and classes; optional on self-explanatory functions
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Imports**: sorted by Ruff (stdlib → third-party → local)
- **Line length**: 100 characters

### Testing

- **Framework**: pytest
- **Structure**: mirrors `bot_server/` under `tests/`
- **Mocking**: all external calls (Webex API, LLM providers, file I/O) are mocked
- **Naming**: `test_<function_name>_<scenario>` (e.g., `test_resolve_personality_exact_match`)
- **Coverage**: aim for 80%+ on services and handlers
- **Fixtures**: shared fixtures in `tests/conftest.py`

## Secrets Management

- **Approach**: `.env` file generated by `setup.py`
- **Template**: `.env.example` committed to repo with placeholder values
- **`.env` is gitignored** — never committed
- **What's in `.env`**:
  - `WEBEX_BOT_TOKEN` — Webex bot access token
  - `WEBEX_BOT_ID` — bot's Webex ID (retrieved automatically during setup)
  - `LLM_PROVIDER` — selected provider name (`ollama`, `anthropic`, `openai`, `gemini`, `xai`)
  - `OLLAMA_URL` — Ollama endpoint (if provider is Ollama)
  - `LLM_API_KEY` — API key for cloud providers (if not Ollama)
  - `LLM_MODEL` — model name to use (e.g., `llama3.1:8b`, `claude-sonnet-4-5-20250929`)
  - `ADMIN_EMAILS` — comma-separated admin email addresses
  - `LOG_LEVEL` — logging level
  - `NGROK_AUTHTOKEN` — ngrok auth token (optional but recommended)

## Constraints & Considerations

- **ngrok free tier**: URLs rotate per session; webhook must be re-registered on every restart. `start.py` handles this automatically. Document this limitation clearly.
- **Ollama performance**: response time depends on hardware and model size. The message queue prevents pile-ups, but users may wait. Document recommended models for different hardware.
- **Memory loss on restart**: conversation history is in-memory only. Acceptable for v1; note that persistent storage (SQLite) is a natural upgrade.
- **Single-process**: the bot runs as one FastAPI process. Adequate for the target use case (small team, single bot). Not designed for high concurrency.
- **Cloud provider costs**: users selecting cloud LLM providers should be aware of per-token API costs. Setup script should note this.

## Out of Scope (for now)

- DMZ relay server implementation (documented as a production upgrade path)
- SSL certificate management (ngrok handles in dev; documented for production)
- Persistent conversation storage (database)
- Web UI or dashboard
- Multi-bot support (running multiple bots from one instance)
- Ollama installation or model pulling (prerequisite, not managed by this tool)
- Webex bot creation (user creates their own; we provide documentation link)
- Token-based conversation memory management (using message count instead)
- Streaming responses (full response returned at once)
