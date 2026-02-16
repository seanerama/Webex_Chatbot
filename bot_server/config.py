"""Configuration loader, validation, and logging setup for Webex AI Chatbot."""

import logging
import os
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    webex_bot_token: str
    webex_bot_id: str
    llm_provider: str
    llm_model: str
    ollama_url: str
    llm_api_key: str
    admin_emails: list[str]
    log_level: str
    ngrok_authtoken: str
    config_dir: str


def get_settings() -> Settings:
    """Load settings from .env file and environment variables.

    Raises ValueError if required fields are missing.
    """
    load_dotenv()

    missing = []
    webex_bot_token = os.environ.get("WEBEX_BOT_TOKEN", "")
    if not webex_bot_token:
        missing.append("WEBEX_BOT_TOKEN")

    llm_provider = os.environ.get("LLM_PROVIDER", "")
    if not llm_provider:
        missing.append("LLM_PROVIDER")

    llm_model = os.environ.get("LLM_MODEL", "")
    if not llm_model:
        missing.append("LLM_MODEL")

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    admin_emails_raw = os.environ.get("ADMIN_EMAILS", "")
    admin_emails = [e.strip() for e in admin_emails_raw.split(",") if e.strip()]

    config_dir = str(Path(__file__).parent / "config")

    return Settings(
        webex_bot_token=webex_bot_token,
        webex_bot_id=os.environ.get("WEBEX_BOT_ID", ""),
        llm_provider=llm_provider,
        llm_model=llm_model,
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        llm_api_key=os.environ.get("LLM_API_KEY", ""),
        admin_emails=admin_emails,
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        ngrok_authtoken=os.environ.get("NGROK_AUTHTOKEN", ""),
        config_dir=config_dir,
    )


def setup_logging(settings: Settings) -> None:
    """Configure logging with console and rotating file handlers."""
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates on repeated calls
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_dir / "bot_server.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
