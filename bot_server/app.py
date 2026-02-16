"""FastAPI application for Webex AI Chatbot.

Ties all components together: config loading, service initialization,
provider creation, handler wiring, webhook endpoint, and lifespan management.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from webexteamssdk import WebexTeamsAPI

from bot_server.config import get_settings, setup_logging
from bot_server.handlers.command_handler import CommandHandler
from bot_server.handlers.message_queue import MessageQueue
from bot_server.handlers.webhook_handler import WebhookHandler
from bot_server.providers import get_provider
from bot_server.services.memory import MemoryService
from bot_server.services.personality import PersonalityService
from bot_server.services.user_manager import UserManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: initialize on startup, cleanup on shutdown."""
    # STARTUP
    settings = get_settings()
    setup_logging(settings)

    webex_client = WebexTeamsAPI(access_token=settings.webex_bot_token)
    provider = get_provider(settings)
    personality_svc = PersonalityService(config_dir=settings.config_dir)
    memory_svc = MemoryService(max_messages=20)
    user_mgr = UserManager(config_dir=settings.config_dir, admin_emails=settings.admin_emails)

    command_handler = CommandHandler(webex_client, user_mgr, personality_svc, provider)
    message_queue = MessageQueue(webex_client, provider, personality_svc, memory_svc)
    webhook_handler = WebhookHandler(
        webex_client, settings.webex_bot_id, user_mgr, command_handler, message_queue
    )

    await message_queue.start()

    app.state.webhook_handler = webhook_handler
    app.state.provider = provider

    logger.info("Bot server started successfully")

    yield

    # SHUTDOWN
    await message_queue.stop()
    logger.info("Bot server shut down")


app = FastAPI(title="Webex AI Chatbot", lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """Receive webhook events from Webex."""
    body = await request.json()
    logger.info("Webhook received for room %s", body.get("data", {}).get("roomId", "unknown"))
    logger.debug("Webhook payload: %s", body)
    try:
        await request.app.state.webhook_handler.handle(body)
    except Exception:
        logger.exception("Error processing webhook")
    return Response(status_code=200)


@app.get("/health")
async def health(request: Request) -> dict:
    """Health check endpoint for monitoring."""
    try:
        provider_healthy = await request.app.state.provider.health_check()
    except Exception:
        logger.exception("Health check failed")
        provider_healthy = False
    return {
        "status": "healthy" if provider_healthy else "degraded",
        "provider": provider_healthy,
    }
