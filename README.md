# Webex AI Chatbot Framework

A local-AI-powered Webex chatbot framework that anyone can run in 5 minutes and optionally deploy to production behind enterprise infrastructure.

## Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) installed and running with at least one model pulled
- A [Webex Bot account](https://developer.webex.com/my-apps/new/bot) (free developer account)
- [ngrok](https://ngrok.com) installed (free account)

### Setup
```bash
# Clone the repo
git clone <repo-url>
cd Webex_Chatbot

# Run the setup script
python3 setup.py
```

The setup script will:
1. Ask for your Webex Bot token
2. Check that Ollama is running and has a model available
3. Start an ngrok tunnel
4. Register the Webex webhook
5. Launch the bot

**That's it.** Message your bot in Webex and start chatting.

## What You Get

### AI-Powered Responses
- **Local AI via Ollama** — your messages never leave your machine
- **Multiple AI personalities** — auto-selected based on what you ask:
  - **Default Assistant** — general conversation and help
  - **Technical Expert** — code, debugging, technical questions
  - **Creative Assistant** — brainstorming, writing, ideas
  - **Content Summarizer** — TLDRs, bullet points, key takeaways
  - **Business Analyst** — analysis, strategy, recommendations
- **Customizable prompts** — edit `prompts.json` to create your own personalities

### User Access Control
- **Approved users list** — control who can interact with the bot
- **Admin commands via chat** — add/remove users without touching config files
- **Silent blocking** — unauthorized users are ignored and logged

### Built-in Commands
| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `ping` | Test bot responsiveness |
| `use prompt [name] [question]` | Use a specific AI personality |
| `health check` | Check AI service status |
| `list models` | Show available Ollama models |
| `reload prompts` | Reload AI prompt configurations |
| `add user email@company.com` | Add user to approved list (admin) |
| `remove user email@company.com` | Remove user from approved list (admin) |
| `list users` | Show all approved users (admin) |
| `reload users` | Reload approved users from file (admin) |

## Architecture

### Quick Start (single machine)
```
You ── Webex Cloud ── ngrok tunnel ── Bot Server ── Ollama
                                      (FastAPI)     (local)
```

### Production Deployment (enterprise)
```
Webex Cloud ── DMZ Relay Server ── Internal Bot Server ── Ollama
               (HTTPS/SSL)         (FastAPI)               (local)
```

The quick-start path and production path run the **same bot framework**. The only difference is how traffic reaches it: ngrok for development, DMZ relay for production.

## Project Structure

### Bot Framework (`bot_server/`)
```
bot_server/
├── app.py                # Main FastAPI application
├── config.py             # Configuration management
├── ollama_service.py     # AI processing service
├── handlers/
│   └── webhook_handler.py # Webhook processing + user access control
├── services/
│   └── webex_api.py      # Webex API wrapper with AI integration
├── utils/
│   └── decorators.py     # Authentication decorators
├── prompts.json          # AI prompt templates
├── approved_users.json   # Approved users list
└── logs/                 # Log files
```

### DMZ Relay (optional, for production — `dmz_relay/`)
```
dmz_relay/
├── app.py                 # FastAPI relay application
├── config.py              # Configuration management
├── webhook_validator.py   # Webex signature validation
├── relay_client.py        # HTTP client for forwarding
└── logs/                  # Log files
```

## Configuration

### Bot Server (.env)
```bash
# Webex Configuration
WEBEX_BOT_TOKEN=your_bot_token
WEBEX_BOT_ID=your_bot_id
WEBEX_BOT_NAME=AI Assistant

# Ollama AI Configuration
OLLAMA_URL=http://localhost:11434
PROMPTS_FILE=prompts.json

# User Access Control
APPROVED_USERS_FILE=approved_users.json
SEND_UNAUTHORIZED_MESSAGE=false
ADMIN_EMAILS=admin@company.com

# Bot Features
ENABLE_AI=true
DEFAULT_RESPONSE=Hello! I'm your AI assistant. How can I help you today?

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/bot_server.log
```

### AI Prompt Configuration (prompts.json)
```json
{
  "default": {
    "name": "Default Assistant",
    "model": "llama3.1:8b",
    "system_prompt": "You are a helpful AI assistant...",
    "temperature": 0.7,
    "max_tokens": 1000,
    "enabled": true
  }
}
```

### Approved Users (approved_users.json)
```json
{
  "description": "Approved users for Webex AI Bot",
  "users": [
    {
      "email": "john.doe@company.com",
      "name": "John Doe",
      "department": "Engineering",
      "added_date": "2025-07-30",
      "notes": "Initial setup"
    }
  ]
}
```

## Production Deployment

When you're ready to move beyond the quick-start path, the production deployment adds:

- **DMZ relay server** — public-facing HTTPS endpoint that validates webhooks and forwards to your internal network
- **SSL/TLS certificates** — proper certificate management instead of ngrok
- **API key authentication** — secure communication between DMZ relay and bot server
- **Firewall rules** — network segmentation between DMZ and internal servers

See [Production Deployment Guide](docs/production-deployment.md) for full setup instructions.

### Production Architecture
```
Internet ── DMZ Relay Server ── Internal Bot Server ── Ollama AI Service
            (HTTPS/SSL)         (FastAPI)               (local)
```

**Security features in production:**
- Webhook signature validation (HMAC-SHA1)
- SSL/TLS encryption with custom certificates
- API key authentication between servers
- Security headers (HSTS, XSS protection, content type sniffing prevention)
- Request retry logic with exponential backoff
- Comprehensive logging and monitoring

## Monitoring & Troubleshooting

### Log Location
- Bot Server: `./logs/bot_server.log`
- DMZ Relay (production): `./logs/dmz_relay.log`

### Health Checks
```bash
# Bot server
curl http://localhost:8080/health

# Ollama
curl http://localhost:11434/api/tags
```

### Common Issues
| Symptom | Likely Cause |
|---------|-------------|
| Bot not responding | Check Ollama is running (`ollama serve`) |
| ngrok tunnel expired | Restart with `python3 setup.py` |
| "Unauthorized user" in logs | Add user to `approved_users.json` or via admin command |
| Slow AI responses | Try a smaller model (`ollama pull llama3.2:3b`) |

## License

[TBD]
