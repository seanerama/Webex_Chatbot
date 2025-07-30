# Webex AI Chatbot Setup Summary

## 🏗️ Architecture Overview

```
Internet → DMZ Relay Server → Internal Bot Server → Ollama AI Service
         (Port <dmz_port>/HTTPS)    (Port <internal_bot_port>/HTTP)     (Port <ollama_service_port(typcially_11434)>/HTTP)
```

**Enhanced Security & AI Flow:**
1. Webex sends webhooks to DMZ server via HTTPS
2. DMZ server validates webhook signatures and forwards to internal server
3. Internal bot server checks user authorization against approved users list
4. Authorized messages are processed with AI prompts via local Ollama instance
5. AI-generated responses are formatted and sent back to Webex

## 📁 Project Structure

### DMZ Relay Server (`dmz_relay/`)
```
dmz_relay/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── webhook_validator.py   # Webex signature validation
├── relay_client.py        # HTTP client for forwarding
├── logging_config.py      # Logging setup
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
├── netwhs.cer            # SSL certificate
├── whs.key               # SSL private key
└── logs/                 # Log files
```

### Internal Bot Server (`bot_server/`)
```
bot_server/
├── app.py                # Main Flask application
├── config.py             # Configuration management
├── ollama_service.py     # AI processing service
├── handlers/
│   └── webhook_handler.py # Webhook processing logic + User Access Control
├── services/
│   └── webex_api.py      # Webex API wrapper with AI integration
├── utils/
│   └── decorators.py     # Authentication decorators
├── logging_config.py     # Logging setup
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
├── prompts.json          # AI prompt templates
├── approved_users.json   # Approved users list
└── logs/                 # Log files
```

## 🔧 Configuration

### DMZ Relay Server (.env)
```bash
# Server Configuration
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=<dmz_port>

# SSL Configuration
SSL_ENABLED=true
SSL_CERT_FILE=netwhs.cer
SSL_KEY_FILE=whs.key

# Internal Bot Server
INTERNAL_BOT_URL=https://internal-server:<internal_bot_port>
INTERNAL_BOT_TIMEOUT=30
INTERNAL_BOT_RETRY_ATTEMPTS=3
INTERNAL_BOT_API_KEY=your_secure_api_key

# Security
WEBEX_WEBHOOK_SECRET=your_webhook_secret

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/dmz_relay.log
```

### Internal Bot Server (.env)
```bash
# Server Configuration
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=<internal_bot_port>

# Webex Configuration
WEBEX_BOT_TOKEN=your_bot_token
WEBEX_BOT_ID=your_bot_id
WEBEX_BOT_NAME=AI Assistant

# Ollama AI Configuration
OLLAMA_URL=http://localhost:<ollama_service_port(typcially_11434)>
PROMPTS_FILE=prompts.json

# User Access Control
APPROVED_USERS_FILE=approved_users.json
SEND_UNAUTHORIZED_MESSAGE=false
ADMIN_EMAILS=admin@company.com,manager@company.com

# Security (must match DMZ server)
DMZ_API_KEY=your_secure_api_key

# Bot Features
ENABLE_AI=true
DEFAULT_RESPONSE=Hello! I'm your AI assistant. How can I help you today?

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/bot_server.log
```

## 🚀 Deployment Steps

### 1. DMZ Relay Server Setup
```bash
# Create virtual environment
python3 -m venv dmz_relay_env
source dmz_relay_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual values

# Add SSL certificates
cp /path/to/netwhs.cer .
cp /path/to/whs.key .
chmod 600 whs.key

# Start server
python3 app.py
```

### 2. Internal Bot Server Setup
```bash
# Create virtual environment
python3 -m venv bot_server_env
source bot_server_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your bot token, API key, and admin emails

# Create directory structure
mkdir -p handlers services utils logs

# Create approved users file
# Edit approved_users.json with your authorized users

# Start server
python3 app.py
```

### 4. Ollama AI Setup
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull your preferred model
ollama pull llama3.1:8b

# Verify Ollama is running
curl http://localhost:<ollama_service_port(typcially_11434)>/api/tags
```
### 5. Webhook Configuration

```bash
# Install webhook setup dependencies
pip install webexteamssdk python-dotenv

# Configure webhook setup
cp .env.webhook .env
# Edit with bot token, webhook URL, and secret

# Create webhooks
python3 setup_webhooks.py --recreate
```

## 🔐 Security Features

### DMZ Relay Server
- ✅ **Webhook Signature Validation** - Validates Webex HMAC-SHA1 signatures
- ✅ **SSL/TLS Encryption** - HTTPS with custom certificates
- ✅ **API Key Authentication** - Secure communication with internal server
- ✅ **Security Headers** - HSTS, XSS protection, content type sniffing prevention
- ✅ **Request Retry Logic** - Exponential backoff for failed forwards
- ✅ **Comprehensive Logging** - All requests and errors logged

### Internal Bot Server
- ✅ **API Key Authentication** - Only accepts requests from DMZ server
- ✅ **User Access Control** - Only approved users can interact with bot
- ✅ **Admin User Management** - Controlled access to user management features
- ✅ **Webex SDK Integration** - Official SDK for API interactions
- ✅ **Message Validation** - Prevents bot from responding to itself
- ✅ **AI Service Security** - Local Ollama instance, no external AI API calls
- ✅ **Error Handling** - Graceful failure handling
- ✅ **Request Logging** - Detailed logging for debugging and security monitoring

## 🤖 Bot Features

### AI-Powered Responses
- **Smart Context Detection** - Automatically selects appropriate AI prompts based on message content
- **Multiple AI Personalities** - Default, Technical, Creative, Summarizer, and Business Analyst prompts
- **Markdown Formatting** - AI responses formatted for optimal Webex display
- **Local AI Processing** - Uses your own Ollama instance for privacy and control

### User Access Control
- **Approved Users List** - Only authorized users can interact with the bot
- **JSON-Based Management** - Easy user management via `approved_users.json` file
- **Admin Commands** - Manage users directly through chat commands
- **Silent Blocking** - Unauthorized users are ignored (no error messages)

### Built-in Commands
- **AI Interaction:**
  - Natural conversation with automatic prompt selection
  - `use prompt [name] [question]` - Force specific AI personality
  - `health check` - Check AI service status
  - `list models` - Show available Ollama models
  - `reload prompts` - Reload AI prompt configurations

- **User Management (Admin only):**
  - `add user email@company.com` - Add user to approved list
  - `remove user email@company.com` - Remove user from approved list
  - `list users` - Show all approved users
  - `reload users` - Reload approved users from file

- **General:**
  - `help` - Show available commands
  - `ping` - Test bot responsiveness

### Webhook Handlers
- **Messages Created** - Process new messages with AI and user authorization
- **Messages Deleted** - Log message deletions
- **Attachment Actions** - Handle card/form submissions
- **Memberships Created** - Send welcome message when bot added to space

## 🧠 AI Prompt System

### Available AI Personalities

#### Default Assistant
- **Use Case**: General conversation and help
- **Auto-Detection**: Default for most messages
- **Features**: Friendly, professional, markdown formatting

#### Technical Expert  
- **Use Case**: Programming, debugging, technical questions
- **Auto-Detection**: Messages containing "code", "programming", "technical", "debug", "error"
- **Features**: Code blocks, detailed explanations, best practices

#### Creative Assistant
- **Use Case**: Brainstorming, creative writing, marketing
- **Auto-Detection**: Messages containing "creative", "story", "idea", "brainstorm"
- **Features**: Imaginative responses, engaging formatting, inspiration

#### Content Summarizer
- **Use Case**: Summarizing long content or information
- **Auto-Detection**: Messages containing "summarize", "summary", "tldr", "brief"
- **Features**: Bullet points, key takeaways, action items

#### Business Analyst
- **Use Case**: Business analysis, data interpretation, strategy
- **Manual Selection**: `use prompt analyst [question]`
- **Features**: Structured analysis, insights, recommendations, risk assessment

### Prompt Configuration (prompts.json)
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

## 🔐 User Access Control

### Approved Users Management

#### approved_users.json Structure
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

#### Access Control Behavior
- **Authorized Users**: Full access to AI features and commands
- **Unauthorized Users**: Messages silently ignored and logged
- **Admin Users**: Additional user management capabilities
- **Optional Notifications**: Can send polite "not authorized" messages

#### Admin User Management
- Set admin emails in `ADMIN_EMAILS` environment variable
- Admins can add/remove users via chat commands
- Real-time user list management without server restart

## 🌐 Network Configuration

### Network Configuration

### Firewall Rules
```bash
# DMZ Server (External facing)
- Allow HTTPS (443/<dmz_port>) from Webex IP ranges
- Allow outbound HTTPS to internal bot server

# Internal Bot Server  
- Allow HTTP (<internal_bot_port>) from DMZ server only
- Allow outbound HTTPS to webexapis.com
- Allow outbound HTTP to Ollama (localhost:<ollama_service_port(typcially_11434)>)

# Ollama Service
- Allow HTTP (<ollama_service_port(typcially_11434)>) from internal bot server only
```

### URLs and Endpoints
- **External Webhook URL**: `https://netwhs.hdrinc.com:<dmz_port>/webhook`
- **Internal Bot URL**: `https://internal-server:<internal_bot_port>/webhook`
- **Ollama API**: `http://localhost:<ollama_service_port(typcially_11434)>/api/generate`
- **Health Check URLs**: 
  - DMZ: `https://netwhs.hdrinc.com:<dmz_port>/health`
  - Bot: `https://internal-server:<internal_bot_port>/health`
  - Ollama: `http://localhost:<ollama_service_port(typcially_11434)>/api/tags`

## 📊 Monitoring & Troubleshooting

### Log Locations
- DMZ Relay: `./logs/dmz_relay.log`
- Bot Server: `./logs/bot_server.log`
- Ollama: System logs (varies by OS)

### Key Log Messages
```bash
# Successful AI-powered webhook flow
DMZ: "Successfully forwarded webhook to internal server"
Bot: "ALLOWING: Authorized user: user@company.com"
Bot: "AI response generated using llama3.1:8b in 2.34s"
Bot: "Message processed and responded"

# User access control
Bot: "BLOCKING: Unauthorized user: stranger@external.com"
Bot: "WebhookHandler initialized with 5 approved users"

# AI processing
Bot: "Ollama connected - Available models: ['llama3.1:8b', 'codellama:7b']"
Bot: "Using 'technical' prompt for message content"

# Common issues
DMZ: "Request timeout" - Check firewall rules
DMZ: "Invalid signature" - Check webhook secret
Bot: "Invalid API key" - Check API key match
Bot: "AI service is currently unavailable" - Check Ollama status
```

### Testing Commands
```bash
# Test DMZ health
curl -k https://netwhs.hdrinc.com:<dmz_port>/health

# Test internal bot health  
curl -k https://internal-server:<internal_bot_port>/health

# Test Ollama connectivity
curl http://localhost:<ollama_service_port(typcially_11434)>/api/tags

# Test webhook forwarding
curl -X POST https://internal-server:<internal_bot_port>/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"test": "webhook"}'

# Test AI processing (direct Ollama)
curl -X POST http://localhost:<ollama_service_port(typcially_11434)>/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.1:8b", "prompt": "Hello", "stream": false}'
```

## 🔄 Maintenance

### Certificate Renewal
```bash
# Update certificates
cp new_netwhs.cer ./netwhs.cer
cp new_whs.key ./whs.key
chmod 600 whs.key

# Restart DMZ server
```

### Bot Token Rotation
```bash
# Update bot token in internal server .env
WEBEX_BOT_TOKEN=new_token

# Restart internal bot server
```

### AI Model Management
```bash
# Pull new Ollama model
ollama pull llama3.1:8b-instruct

# Update prompts.json to use new model
# Restart bot server to reload prompts
```

### User Access Management
```bash
# Add user via chat (admin only)
add user new.user@company.com

# Or edit approved_users.json directly
# Then reload: reload users

# Remove user access
remove user old.user@company.com
```

### Webhook Management
```bash
# List current webhooks
python3 setup_webhooks.py --list

# Recreate all webhooks
python3 setup_webhooks.py --recreate
```

## ✅ Success Indicators

When everything is working correctly, you should see:

1. **DMZ Server Logs**:
   ```
   INFO - Processing webhook: messages.created
   INFO - Successfully forwarded webhook to internal server
   ```

2. **Bot Server Logs**:
   ```
   INFO - WebhookHandler initialized with 5 approved users
   INFO - ALLOWING: Authorized user: user@company.com
   INFO - Ollama connected - Available models: ['llama3.1:8b']
   INFO - AI response generated using llama3.1:8b in 2.34s
   INFO - Message processed and responded
   ```

3. **Webex Client**: 
   - Bot responds to authorized users with AI-generated content
   - Unauthorized users receive no response (silently blocked)
   - Admin commands work for managing users
   - AI responses are well-formatted with markdown

4. **User Access Control**:
   - Only approved users can interact with the bot
   - Admin users can manage the approved list via chat
   - All access attempts are logged for security

## 🎉 Congratulations!

Your Webex AI chatbot is now successfully deployed with:

**🔒 Enterprise Security:**
- DMZ relay architecture protecting internal networks
- User access control with approved users list
- Comprehensive logging and monitoring

**🧠 AI Intelligence:**
- Local Ollama integration for privacy and control
- Multiple AI personalities for different use cases
- Smart prompt selection based on message content
- Customizable AI behavior via JSON configuration

**⚡ Advanced Features:**
- Real-time user management via chat commands
- Admin controls for system management
- Scalable, modular architecture
- Professional markdown-formatted responses

**🚀 Production Ready:**
- SSL/TLS encryption and security headers
- Retry logic and error handling
- Health checks and monitoring endpoints
- Easy maintenance and updates

The bot can now intelligently respond to authorized users using your local AI while maintaining enterprise-grade security and comprehensive access controls!
