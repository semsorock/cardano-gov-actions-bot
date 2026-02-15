#!/usr/bin/env python3
"""Create/validate X webhook config and account subscription."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from xdk import Client
from xdk.oauth1_auth import OAuth1
from xdk.webhooks.models import CreateRequest

from bot.logging import get_logger, setup_logging

load_dotenv(override=True)
setup_logging()
logger = get_logger("setup_x_webhook")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def _get_client() -> Client:
    oauth1 = OAuth1(
        api_key=_required_env("API_KEY"),
        api_secret=_required_env("API_SECRET_KEY"),
        callback="oob",
        access_token=_required_env("ACCESS_TOKEN"),
        access_token_secret=_required_env("ACCESS_TOKEN_SECRET"),
    )
    return Client(auth=oauth1)


def _extract_attr(item: object, key: str) -> str:
    if isinstance(item, dict):
        return str(item.get(key) or "")
    return str(getattr(item, key, "") or "")


def _extract_subscribed(response: object) -> bool:
    if isinstance(response, dict):
        data = response.get("data", {})
        if isinstance(data, dict):
            return bool(data.get("subscribed"))
        return False

    data = getattr(response, "data", None)
    return bool(getattr(data, "subscribed", False))


def _extract_attempted(response: object) -> bool:
    if isinstance(response, dict):
        data = response.get("data", {})
        if isinstance(data, dict):
            return bool(data.get("attempted"))
        return False

    data = getattr(response, "data", None)
    return bool(getattr(data, "attempted", False))


def main() -> None:
    callback_url = _required_env("X_WEBHOOK_CALLBACK_URL")
    client = _get_client()

    webhooks = client.webhooks.get()
    webhook_items = webhooks.get("data", []) if isinstance(webhooks, dict) else getattr(webhooks, "data", [])

    webhook_id = ""
    for item in webhook_items or []:
        if _extract_attr(item, "url") == callback_url:
            webhook_id = _extract_attr(item, "id")
            break

    if webhook_id:
        logger.info("Found existing webhook config: id=%s", webhook_id)
    else:
        created = client.webhooks.create(CreateRequest(url=callback_url))
        webhook_id = _extract_attr(created, "id")
        if not webhook_id:
            raise SystemExit("Failed to create webhook: missing webhook ID in response")
        logger.info("Created webhook config: id=%s", webhook_id)

    validate_response = client.webhooks.validate(webhook_id)
    logger.info("Webhook validation attempted=%s", _extract_attempted(validate_response))

    subscription = client.account_activity.validate_subscription(webhook_id)
    subscribed = _extract_subscribed(subscription)
    logger.info("Current subscription status: subscribed=%s", subscribed)

    if not subscribed:
        created_subscription = client.account_activity.create_subscription(webhook_id)
        subscribed = _extract_subscribed(created_subscription)
        logger.info("Subscription created: subscribed=%s", subscribed)
    else:
        logger.info("Subscription already active")


if __name__ == "__main__":
    main()
