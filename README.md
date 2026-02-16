# Webex AI Chatbot Framework

A local-AI-powered Webex chatbot framework that anyone can run in 5 minutes and optionally deploy to production behind enterprise infrastructure.

## Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Ollama](https://ollama.ai) installed and running with at least one model pulled
- A [Webex Bot account](https://developer.webex.com/my-apps/new/bot) (free developer account)
- [ngrok](https://ngrok.com) account (free tier works)

### Setup
```bash
git clone https://github.com/seanerama/Webex_Chatbot.git
cd Webex_Chatbot
uv sync --dev
uv run python setup.py
```

The setup wizard will:
1. Ask for your Webex Bot token and verify it
2. Let you choose an LLM provider (Ollama default, or Anthropic/OpenAI/Gemini/xAI)
3. Test LLM connectivity
4. Configure admin email and first approved user
5. Start an ngrok tunnel and register the Webex webhook
6. Generate your `.env` file and launch the bot

**That's it.** Message your bot in Webex and start chatting.

### Subsequent Launches
```bash
uv run python start.py
```

This reuses your existing `.env`, starts a fresh ngrok tunnel, re-registers the webhook (ngrok free tier rotates URLs), and launches the bot.

## Features

### Multi-Provider LLM Support
- **Ollama** (default) — local AI, your messages never leave your machine
- **Anthropic** (Claude) — cloud provider
- **OpenAI** (GPT) — cloud provider
- **Gemini** (Google) — cloud provider
- **xAI** (Grok) — cloud provider

One provider is selected at setup. All providers use the same interface.

### Personality System
JSON-defined AI personalities assigned to users by email pattern:
- **Default Assistant** — general conversation and help
- **Cisco Expert** — networking-focused technical answers
- **Code Reviewer** — code analysis and review

Personalities are resolved per-user: exact email match first, then glob pattern match (`*@cisco.com`), then default fallback. Users can override with `use prompt [name] [question]` for a single message.

Edit `bot_server/config/personalities.json` and `bot_server/config/user-mappings.json` to customize.

### User Access Control
- **Approved users list** — control who can interact with the bot
- **Admin commands via chat** — add/remove users without touching config files
- **Silent blocking** — unauthorized users are ignored and logged

### Conversation Memory
- Sliding window of 20 messages per room
- Independent per-room history
- Clears on restart (in-memory for v1)

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

## Architecture

### Quick Start (single machine)
```
You ── Webex Cloud ── ngrok tunnel ── Bot Server ── Ollama
                                      (FastAPI)     (local)
```

### Production (enterprise)
```
Webex Cloud ── DMZ Relay Server ── Internal Bot Server ── Ollama
               (HTTPS/SSL)         (FastAPI)               (local)
```

The quick-start path and production path run the **same bot framework**. The only difference is how traffic reaches it: ngrok for development, a reverse proxy or DMZ relay for production. See [Deployment Guide](docs/deploy-instruct.md) for production setup.

## Project Structure

```
Webex_Chatbot/
├── setup.py                          # Interactive setup wizard
├── start.py                          # Bot launcher (subsequent runs)
├── pyproject.toml                    # Dependencies and project config
├── .env.example                      # Environment variable template
├── bot_server/
│   ├── app.py                        # FastAPI app, webhook + health endpoints
│   ├── config.py                     # Settings dataclass, config loader, logging
│   ├── providers/
│   │   ├── base.py                   # Abstract LLM provider interface
│   │   ├── ollama.py                 # Ollama provider
│   │   ├── anthropic.py              # Anthropic provider
│   │   ├── openai_provider.py        # OpenAI provider
│   │   ├── gemini.py                 # Gemini provider
│   │   └── xai.py                    # xAI provider (OpenAI-compatible)
│   ├── handlers/
│   │   ├── webhook_handler.py        # Webhook receipt + routing
│   │   ├── command_handler.py        # Built-in command parsing
│   │   └── message_queue.py          # Async message queue + LLM processing
│   ├── services/
│   │   ├── personality.py            # Personality resolution by email
│   │   ├── memory.py                 # Conversation history (sliding window)
│   │   └── user_manager.py           # Approved users CRUD
│   └── config/
│       ├── personalities.json        # AI personality definitions
│       ├── user-mappings.json        # Email → personality mapping rules
│       └── approved_users.json       # Approved user list
├── tests/                            # 139 tests (pytest)
└── docs/
    ├── project-plan.md               # Technical project plan
    └── deploy-instruct.md            # Production deployment guide
```

## Configuration

### Environment Variables (.env)

Generated by `setup.py`. See `.env.example` for all options:

```bash
WEBEX_BOT_TOKEN=your_bot_token       # Webex bot access token
WEBEX_BOT_ID=                        # Auto-retrieved during setup
LLM_PROVIDER=ollama                  # ollama | anthropic | openai | gemini | xai
LLM_MODEL=llama3.1:8b               # Model name
OLLAMA_URL=http://localhost:11434    # Ollama endpoint
LLM_API_KEY=                         # API key (cloud providers only)
ADMIN_EMAILS=admin@example.com       # Comma-separated admin emails
LOG_LEVEL=INFO                       # DEBUG | INFO | WARNING | ERROR
NGROK_AUTHTOKEN=                     # ngrok auth token (recommended)
```

### Personality Configuration

Edit `bot_server/config/personalities.json`:
```json
{
  "default": {
    "name": "Helpful Assistant",
    "system_prompt": "You are a helpful AI assistant...",
    "temperature": 0.2,
    "max_tokens": 1000
  }
}
```

Map users to personalities in `bot_server/config/user-mappings.json`:
```json
{
  "default_personality": "default",
  "mappings": [
    {"match": "*@cisco.com", "type": "pattern", "personality": "cisco-expert"}
  ]
}
```

## Development

### Running Tests
```bash
uv sync --dev
uv run pytest -v           # 139 tests
uv run ruff check .        # Lint
uv run ruff format --check .  # Format check
```

### Health Check
```bash
curl http://localhost:8080/health
# {"status": "healthy", "provider": true}
```

## Troubleshooting

| Symptom | Likely Cause |
|---------|-------------|
| `ModuleNotFoundError` running setup.py | Run `uv sync --dev` first to install dependencies |
| Bot not responding | Check Ollama is running (`ollama serve`) |
| ngrok tunnel expired | Restart with `uv run python start.py` (re-registers webhook) |
| "Unauthorized user" in logs | Add user via `add user email@domain.com` chat command |
| Slow AI responses | Try a smaller model (`ollama pull llama3.2:3b`) |

## License

MIT
