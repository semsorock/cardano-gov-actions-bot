#!/usr/bin/env python3
"""Create/validate X webhook config and account subscription."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, NoReturn

import requests

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
    # Webhooks endpoints require app bearer auth, while account activity
    # subscription endpoints can use OAuth1 user context.
    return Client(
        bearer_token=_required_env("BEARER_TOKEN"),
        auth=oauth1,
    )


def _extract_attr(item: object, key: str) -> str:
    if isinstance(item, dict):
        direct = item.get(key)
        if direct:
            return str(direct)
        nested = item.get("data")
        if isinstance(nested, dict) and nested.get(key):
            return str(nested[key])
        return ""

    direct = getattr(item, key, "")
    if direct:
        return str(direct)

    nested = getattr(item, "data", None)
    if nested is not None:
        return _extract_attr(nested, key)

    return ""


def _to_dict(item: object) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    model_dump = getattr(item, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    return {}


def _extract_webhook_id(item: object) -> str:
    for key in ("id", "webhook_id", "webhookId"):
        value = _extract_attr(item, key)
        if value:
            return value
    return ""


def _coerce_webhook_items(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _normalise_url(value: str) -> str:
    return value.strip().rstrip("/")


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


def _extract_subscriptions(response: object) -> list[object]:
    if isinstance(response, dict):
        data = response.get("data", {})
        if isinstance(data, dict):
            subs = data.get("subscriptions")
            if isinstance(subs, list):
                return subs
        return []

    data = getattr(response, "data", None)
    subs = getattr(data, "subscriptions", None)
    if isinstance(subs, list):
        return subs
    return []


def _raise_http_error(exc: requests.HTTPError, *, operation: str) -> NoReturn:
    response = exc.response
    if response is None:
        raise SystemExit(f"{operation} failed: {exc}") from exc

    request_id = response.headers.get("x-request-id", "")
    body = (response.text or "").strip()
    details = [f"{operation} failed with HTTP {response.status_code}."]
    if request_id:
        details.append(f"x-request-id: {request_id}")
    if body:
        details.append(f"response body: {body}")

    if response.status_code == 403 and "/2/webhooks" in operation:
        details.append(
            "hint: your app likely lacks Account Activity/Webhooks access, or the BEARER_TOKEN "
            "belongs to a different app than your API/OAuth1 keys."
        )
        details.append(
            "hint: in X Developer Console, confirm Account Activity package access and "
            "app permissions set to Read/Write/Direct Messages, then regenerate tokens."
        )

    raise SystemExit("\n".join(details)) from exc


def main() -> None:
    callback_url = _required_env("X_WEBHOOK_CALLBACK_URL")
    callback_url_normalised = _normalise_url(callback_url)
    client = _get_client()

    webhook_id = os.environ.get("X_WEBHOOK_ID", "").strip()
    if webhook_id:
        logger.info("Using webhook ID from env override: id=%s", webhook_id)
    else:
        try:
            webhooks = client.webhooks.get()
        except requests.HTTPError as exc:
            _raise_http_error(exc, operation="GET /2/webhooks")
        webhooks_payload = _to_dict(webhooks)
        webhook_items = _coerce_webhook_items(
            webhooks_payload.get("data", getattr(webhooks, "data", None)),
        )

        for item in webhook_items or []:
            if _normalise_url(_extract_attr(item, "url")) == callback_url_normalised:
                webhook_id = _extract_webhook_id(item)
                break

    if webhook_id:
        logger.info("Found existing webhook config: id=%s", webhook_id)
    else:
        try:
            created = client.webhooks.create(CreateRequest(url=callback_url))
        except requests.HTTPError as exc:
            _raise_http_error(exc, operation="POST /2/webhooks")
        webhook_id = _extract_webhook_id(created)
        if not webhook_id:
            # Some responses may omit id; retry lookup by URL before failing.
            try:
                webhooks = client.webhooks.get()
            except requests.HTTPError as exc:
                _raise_http_error(exc, operation="GET /2/webhooks")
            webhooks_payload = _to_dict(webhooks)
            webhook_items = _coerce_webhook_items(
                webhooks_payload.get("data", getattr(webhooks, "data", None)),
            )
            for item in webhook_items or []:
                if _normalise_url(_extract_attr(item, "url")) == callback_url_normalised:
                    webhook_id = _extract_webhook_id(item)
                    if webhook_id:
                        break

            if not webhook_id:
                created_payload = _to_dict(created)
                raise SystemExit(
                    "Failed to create webhook: missing webhook ID in response. "
                    f"response payload: {created_payload}"
                )
        logger.info("Created webhook config: id=%s", webhook_id)

    try:
        validate_response = client.webhooks.validate(webhook_id)
    except requests.HTTPError as exc:
        _raise_http_error(exc, operation=f"PUT /2/webhooks/{webhook_id}")
    logger.info("Webhook validation attempted=%s", _extract_attempted(validate_response))

    try:
        subscription = client.account_activity.validate_subscription(webhook_id)
    except requests.HTTPError as exc:
        _raise_http_error(
            exc,
            operation=f"GET /2/account_activity/webhooks/{webhook_id}/subscriptions/all",
        )
    subscribed = _extract_subscribed(subscription)
    logger.info("Current subscription status: subscribed=%s", subscribed)

    if not subscribed:
        try:
            created_subscription = client.account_activity.create_subscription(webhook_id)
        except requests.HTTPError as exc:
            _raise_http_error(
                exc,
                operation=f"POST /2/account_activity/webhooks/{webhook_id}/subscriptions/all",
            )
        subscribed = _extract_subscribed(created_subscription)
        logger.info("Subscription created: subscribed=%s", subscribed)
    else:
        logger.info("Subscription already active")

    try:
        subscriptions_response = client.account_activity.get_subscriptions(webhook_id)
    except requests.HTTPError as exc:
        _raise_http_error(
            exc,
            operation=f"GET /2/account_activity/webhooks/{webhook_id}/subscriptions/all/list",
        )
    subscriptions = _extract_subscriptions(subscriptions_response)
    logger.info("Active subscription entries for webhook %s: %s", webhook_id, subscriptions)


if __name__ == "__main__":
    main()
