"""Interactive setup wizard for Webex AI Chatbot.

Walks the user through configuration step by step:
1. Webex bot token verification
2. LLM provider selection and connectivity test
3. Admin email configuration
4. First approved user setup
5. ngrok tunnel and webhook registration
6. .env generation and bot launch
"""

import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

import httpx
from pyngrok import conf, ngrok
from webexteamssdk import WebexTeamsAPI

from bot_server.config import Settings
from bot_server.providers import get_provider

logger = logging.getLogger(__name__)

PROVIDERS = {
    "1": ("ollama", "Ollama (local)"),
    "2": ("anthropic", "Anthropic (Claude)"),
    "3": ("openai", "OpenAI (GPT)"),
    "4": ("gemini", "Google Gemini"),
    "5": ("xai", "xAI (Grok)"),
}

CLOUD_MODEL_EXAMPLES = {
    "anthropic": "claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001",
    "openai": "gpt-4o, gpt-4o-mini",
    "gemini": "gemini-2.0-flash, gemini-2.5-pro",
    "xai": "grok-2, grok-2-mini",
}

CONFIG_DIR = Path(__file__).parent / "bot_server" / "config"
APPROVED_USERS_FILE = CONFIG_DIR / "approved_users.json"


def print_banner() -> None:
    """Display the welcome banner."""
    print()
    print("=" * 60)
    print("  Webex AI Chatbot — Setup Wizard")
    print("=" * 60)
    print()
    print("This wizard will walk you through configuring your bot.")
    print("You can press Ctrl+C at any time to exit.")
    print()


def prompt_bot_token() -> tuple[str, str]:
    """Prompt for and validate the Webex bot token.

    Returns:
        Tuple of (token, bot_id)
    """
    while True:
        token = input("Enter your Webex Bot Token: ").strip()
        if not token:
            print("  Token cannot be empty. Please try again.\n")
            continue

        print("  Verifying bot token... ", end="", flush=True)
        try:
            api = WebexTeamsAPI(access_token=token)
            me = api.people.me()
            bot_id = me.id
            print("OK")
            print(f"  Bot name: {me.displayName}")
            print(f"  Bot ID:   {bot_id}")
            print()
            return token, bot_id
        except Exception as exc:
            print("FAILED")
            print(f"  Error: {exc}")
            print("  Please check your token and try again.\n")


def prompt_provider() -> str:
    """Prompt user to select an LLM provider.

    Returns:
        Provider key (e.g. 'ollama', 'anthropic')
    """
    print("Select your LLM provider:")
    for key, (_, label) in PROVIDERS.items():
        default_tag = " [default]" if key == "1" else ""
        print(f"  {key}. {label}{default_tag}")
    print()

    while True:
        choice = input("Enter choice (1-5) [1]: ").strip() or "1"
        if choice in PROVIDERS:
            provider_key, label = PROVIDERS[choice]
            print(f"  Selected: {label}\n")
            return provider_key
        print("  Invalid choice. Please enter 1-5.\n")


def prompt_ollama_url() -> str:
    """Prompt for Ollama URL."""
    url = input("Enter Ollama URL [http://localhost:11434]: ").strip()
    return url or "http://localhost:11434"


def prompt_api_key(provider: str) -> str:
    """Prompt for cloud provider API key."""
    while True:
        key = input(f"Enter your {provider.title()} API key: ").strip()
        if key:
            return key
        print("  API key cannot be empty.\n")


def prompt_ollama_model(ollama_url: str) -> str:
    """List Ollama models and let user pick one."""
    print("  Fetching available models... ", end="", flush=True)
    try:
        url = ollama_url.rstrip("/") + "/api/tags"
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        models = [m["name"] for m in data.get("models", [])]
    except Exception:
        print("FAILED")
        print("  Could not fetch models from Ollama.")
        model = input("  Enter model name manually (e.g. llama3.1:8b): ").strip()
        return model or "llama3.1:8b"

    if not models:
        print("NONE FOUND")
        print("  No models found. Make sure you've pulled a model with 'ollama pull <model>'.")
        model = input("  Enter model name manually (e.g. llama3.1:8b): ").strip()
        return model or "llama3.1:8b"

    print("OK")
    print()
    print("  Available models:")
    for i, model_name in enumerate(models, 1):
        print(f"    {i}. {model_name}")
    print()

    while True:
        choice = input(f"  Select model (1-{len(models)}) [1]: ").strip() or "1"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                print(f"  Selected: {selected}\n")
                return selected
        except ValueError:
            pass
        print(f"  Invalid choice. Enter 1-{len(models)}.\n")


def prompt_cloud_model(provider: str) -> str:
    """Prompt for cloud provider model name."""
    examples = CLOUD_MODEL_EXAMPLES.get(provider, "")
    hint = f" (e.g. {examples})" if examples else ""
    model = input(f"Enter model name{hint}: ").strip()
    if not model:
        print("  Model name cannot be empty.")
        return prompt_cloud_model(provider)
    return model


def verify_llm_connectivity(
    provider: str,
    ollama_url: str,
    api_key: str,
    model: str,
) -> bool:
    """Verify LLM provider connectivity by running a health check.

    Returns:
        True if successful, False otherwise
    """
    print("  Testing LLM connectivity... ", end="", flush=True)

    try:
        settings = Settings(
            webex_bot_token="test",
            webex_bot_id="test",
            llm_provider=provider,
            llm_model=model,
            ollama_url=ollama_url,
            llm_api_key=api_key,
            admin_emails=[],
            log_level="WARNING",
            ngrok_authtoken="",
            config_dir=str(CONFIG_DIR),
        )
        llm = get_provider(settings)
        result = asyncio.run(llm.health_check())

        if result:
            print("OK")
            return True
        else:
            print("FAILED")
            print("  Provider responded but health check returned unhealthy.")
            return False
    except Exception as exc:
        print("FAILED")
        print(f"  Error: {exc}")
        return False


def prompt_admin_email() -> str:
    """Prompt for admin email address(es)."""
    while True:
        emails = input("Enter admin email address(es), comma-separated: ").strip()
        if emails:
            return emails
        print("  At least one admin email is required.\n")


def prompt_first_user(admin_emails: str) -> None:
    """Ask if the admin wants to add themselves as an approved user."""
    answer = input("Add yourself to approved users? (y/n) [y]: ").strip().lower() or "y"
    if answer != "y":
        return

    first_email = admin_emails.split(",")[0].strip()
    name = input(f"  Your display name [{first_email}]: ").strip() or first_email

    add_approved_user(first_email, name)
    print(f"  Added {first_email} to approved users.\n")


def add_approved_user(email: str, name: str) -> None:
    """Add a user to approved_users.json."""
    data = {"description": "Approved users for Webex AI Bot", "users": []}
    if APPROVED_USERS_FILE.exists():
        with open(APPROVED_USERS_FILE) as f:
            data = json.load(f)

    users = data.get("users", [])
    if any(u["email"].lower() == email.lower() for u in users):
        return

    users.append(
        {
            "email": email,
            "name": name,
            "added_date": date.today().isoformat(),
            "added_by": "setup",
        }
    )
    data["users"] = users

    with open(APPROVED_USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def prompt_ngrok_token() -> str:
    """Prompt for ngrok authtoken."""
    print("ngrok provides a public URL for Webex to reach your bot.")
    print("  A free ngrok account is required: https://ngrok.com")
    print("  Get your authtoken: https://dashboard.ngrok.com/get-started/your-authtoken")
    print()
    while True:
        token = input("Enter ngrok authtoken: ").strip()
        if token:
            return token
        print("  ngrok authtoken is required. Sign up free at https://ngrok.com")
        print()


def start_ngrok(authtoken: str, port: int = 8080) -> str:
    """Start an ngrok tunnel and return the public URL.

    Returns:
        The public HTTPS URL
    """
    print("  Starting ngrok tunnel... ", end="", flush=True)
    try:
        if authtoken:
            conf.get_default().auth_token = authtoken

        tunnel = ngrok.connect(port, "http")
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://", 1)

        print("OK")
        print(f"  Public URL: {public_url}")
        print()
        return public_url
    except Exception as exc:
        print("FAILED")
        print(f"  Error: {exc}")
        print("  Check your ngrok authtoken and that ngrok is installed.")
        print()
        sys.exit(1)


def register_webhook(token: str, ngrok_url: str) -> None:
    """Clean up old webhooks and register a new one for this bot."""
    print("  Registering Webex webhook... ", end="", flush=True)
    try:
        api = WebexTeamsAPI(access_token=token)

        # Clean up existing webhooks
        for wh in api.webhooks.list():
            api.webhooks.delete(wh.id)

        # Register new webhook
        webhook_url = f"{ngrok_url}/webhook"
        api.webhooks.create(
            name="Webex AI Chatbot",
            targetUrl=webhook_url,
            resource="messages",
            event="created",
        )
        print("OK")
        print(f"  Webhook URL: {webhook_url}")
        print()
    except Exception as exc:
        print("FAILED")
        print(f"  Error: {exc}")
        raise


def generate_env_file(
    token: str,
    bot_id: str,
    provider: str,
    model: str,
    ollama_url: str,
    api_key: str,
    admin_emails: str,
    ngrok_authtoken: str,
) -> None:
    """Write collected configuration to .env file."""
    env_path = Path(".env")
    if env_path.exists():
        print("  WARNING: .env file already exists and will be overwritten.")
        confirm = input("  Continue? (y/n) [y]: ").strip().lower() or "y"
        if confirm != "y":
            print("  Aborted. Existing .env preserved.")
            sys.exit(0)

    content = f"""# Webex Bot Configuration
WEBEX_BOT_TOKEN={token}
WEBEX_BOT_ID={bot_id}

# LLM Provider: ollama, anthropic, openai, gemini, xai
LLM_PROVIDER={provider}
LLM_MODEL={model}
OLLAMA_URL={ollama_url}
LLM_API_KEY={api_key}

# Admin emails (comma-separated)
ADMIN_EMAILS={admin_emails}

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# ngrok auth token (optional but recommended)
NGROK_AUTHTOKEN={ngrok_authtoken}
"""
    env_path.write_text(content)
    print("  .env file generated.\n")


def launch_bot() -> None:
    """Launch the bot server with uvicorn."""
    print("=" * 60)
    print("  Bot is starting!")
    print("=" * 60)
    print()
    print("  Press Ctrl+C to stop the bot.")
    print()

    import uvicorn

    uvicorn.run("bot_server.app:app", host="0.0.0.0", port=8080)


def main() -> None:
    """Run the complete setup wizard."""
    try:
        print_banner()

        # Step 1: Webex bot token
        print("--- Step 1: Webex Bot Token ---\n")
        token, bot_id = prompt_bot_token()

        # Step 2: LLM provider
        print("--- Step 2: LLM Provider ---\n")
        provider = prompt_provider()

        ollama_url = "http://localhost:11434"
        api_key = ""

        if provider == "ollama":
            ollama_url = prompt_ollama_url()
            print()
        else:
            api_key = prompt_api_key(provider)
            print()

        # Step 3: Model selection
        print("--- Step 3: Model Selection ---\n")
        if provider == "ollama":
            model = prompt_ollama_model(ollama_url)
        else:
            model = prompt_cloud_model(provider)
        print()

        # Step 4: LLM connectivity test
        print("--- Step 4: LLM Connectivity Test ---\n")
        if not verify_llm_connectivity(provider, ollama_url, api_key, model):
            answer = input("  Continue anyway? (y/n) [n]: ").strip().lower() or "n"
            if answer != "y":
                print("  Setup aborted. Fix the LLM connection and try again.")
                sys.exit(1)
        print()

        # Step 5: Admin email
        print("--- Step 5: Admin Email ---\n")
        admin_emails = prompt_admin_email()
        print()

        # Step 6: First approved user
        print("--- Step 6: Approved User ---\n")
        prompt_first_user(admin_emails)

        # Step 7: ngrok setup
        print("--- Step 7: ngrok Setup ---\n")
        ngrok_authtoken = prompt_ngrok_token()
        print()
        ngrok_url = start_ngrok(ngrok_authtoken)

        # Step 8: Webhook registration
        print("--- Step 8: Webhook Registration ---\n")
        register_webhook(token, ngrok_url)

        # Step 9: Generate .env
        print("--- Step 9: Generate Configuration ---\n")
        generate_env_file(
            token=token,
            bot_id=bot_id,
            provider=provider,
            model=model,
            ollama_url=ollama_url,
            api_key=api_key,
            admin_emails=admin_emails,
            ngrok_authtoken=ngrok_authtoken,
        )

        # Step 10: Launch bot
        print("--- Step 10: Launch Bot ---\n")
        launch_bot()

    except KeyboardInterrupt:
        print("\n\n  Setup cancelled. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
