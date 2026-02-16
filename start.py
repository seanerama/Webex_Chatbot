"""Quick bot launcher for Webex AI Chatbot.

Uses existing .env configuration to start the bot:
1. Load settings from .env
2. Start ngrok tunnel (new URL each time on free tier)
3. Clean up old webhooks and register new one
4. Launch uvicorn with bot_server.app:app
"""

import logging
import sys
from pathlib import Path

from pyngrok import conf, ngrok
from webexteamssdk import WebexTeamsAPI

logger = logging.getLogger(__name__)


def check_env_file() -> None:
    """Verify .env file exists."""
    if not Path(".env").exists():
        print("Error: .env file not found.")
        print("Run 'python setup.py' first to configure your bot.")
        sys.exit(1)


def load_settings():
    """Load and return application settings from .env."""
    from bot_server.config import get_settings

    return get_settings()


def start_ngrok(authtoken: str, port: int = 8080) -> str:
    """Start an ngrok tunnel and return the public URL."""
    print("Starting ngrok tunnel... ", end="", flush=True)
    try:
        if authtoken:
            conf.get_default().auth_token = authtoken

        tunnel = ngrok.connect(port, "http")
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://", 1)

        print("OK")
        print(f"  Public URL: {public_url}")
        return public_url
    except Exception as exc:
        print("FAILED")
        print(f"  Error: {exc}")
        print("  Check your ngrok authtoken and that ngrok is installed.")
        sys.exit(1)


def register_webhook(token: str, ngrok_url: str) -> None:
    """Clean up old webhooks and register a new one."""
    print("Registering webhook... ", end="", flush=True)
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
    except Exception as exc:
        print("FAILED")
        print(f"  Error: {exc}")
        sys.exit(1)


def launch_bot(settings) -> None:
    """Launch the bot server."""
    print()
    print("=" * 60)
    print("  Bot is running!")
    print(f"  Provider: {settings.llm_provider}")
    print(f"  Model:    {settings.llm_model}")
    print("=" * 60)
    print()
    print("  Press Ctrl+C to stop the bot.")
    print()

    import uvicorn

    uvicorn.run("bot_server.app:app", host="0.0.0.0", port=8080)


def main() -> None:
    """Run the bot launcher."""
    try:
        print()
        print("Webex AI Chatbot — Starting...\n")

        # Step 1: Check .env exists
        check_env_file()

        # Step 2: Load settings
        print("Loading configuration... ", end="", flush=True)
        settings = load_settings()
        print("OK")
        print(f"  Provider: {settings.llm_provider}")
        print(f"  Model:    {settings.llm_model}")
        print()

        # Step 3: Start ngrok
        ngrok_url = start_ngrok(settings.ngrok_authtoken)
        print()

        # Step 4: Register webhook
        register_webhook(settings.webex_bot_token, ngrok_url)
        print()

        # Step 5: Launch
        launch_bot(settings)

    except KeyboardInterrupt:
        print("\n\nBot stopped. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
