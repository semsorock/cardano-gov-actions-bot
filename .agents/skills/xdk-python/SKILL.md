---
name: xdk-python
description: Use this skill when implementing or debugging Python integrations with the official X XDK, including auth setup, endpoint usage, pagination, and streaming.
---

# XDK Python

## Use This Skill When

- The user wants to build or fix Python code that talks to X API v2 via `xdk`.
- The task includes authentication setup (Bearer token, OAuth 2.0 PKCE, or OAuth 1.0a).
- The task needs pagination or filtered stream handling.
- The user wants to migrate raw HTTP requests to the official SDK.

## Canonical Sources

- [Overview](https://docs.x.com/xdks/python/overview)
- [Install](https://docs.x.com/xdks/python/install)
- [Quickstart](https://docs.x.com/xdks/python/quickstart)
- [Authentication](https://docs.x.com/xdks/python/authentication)
- [Pagination](https://docs.x.com/xdks/python/pagination)
- [Streaming](https://docs.x.com/xdks/python/streaming)

## Baseline Setup

- Runtime: Python 3.8+.
- Install: `pip install xdk`.
- Import client: `from xdk import Client`.

Bearer-token quick start:

```python
from xdk import Client

client = Client(bearer_token="YOUR_BEARER_TOKEN")

for page in client.posts.search_recent(query="api", max_results=10):
    if page.data:
        first_post = page.data[0]
        text = first_post.text if hasattr(first_post, "text") else first_post.get("text", "")
        print(text)
        break
```

## Authentication Decision Guide

1. Bearer token (app-only): read-only and app-context endpoints.
2. OAuth 2.0 PKCE: user-authorized access with scopes (recommended for modern user-context flows).
3. OAuth 1.0a: legacy user-context operations when required by endpoint or existing integration.

Use environment variables for all secrets/tokens. Do not hardcode credentials in source files.

## Working Pattern

1. Identify endpoint and required permission scope/context.
2. Instantiate one `Client` with the correct auth mode.
3. Execute API call with explicit parameters (`max_results`, fields, expansions as needed).
4. Handle paginated iterators until data target is reached.
5. Add retry/backoff strategy for transient failures and rate limits.
6. For streaming, run a long-lived process and define clear shutdown behavior.

## Pagination Patterns

Automatic pagination (recommended):

```python
all_posts = []
for page in client.posts.search_recent(query="python", max_results=100):
    if page.data:
        all_posts.extend(page.data)
```

Manual page token flow (when custom control is needed):

```python
first_page = next(client.posts.search_recent(query="python", max_results=100, pagination_token=None))
next_token = getattr(getattr(first_page, "meta", None), "next_token", None)
if next_token:
    second_page = next(client.posts.search_recent(query="python", max_results=100, pagination_token=next_token))
```

## Streaming Pattern

Before consuming stream results, ensure stream rules are configured for your filter criteria.

```python
from xdk import Client

client = Client(bearer_token="YOUR_BEARER_TOKEN")

for post_response in client.stream.posts():
    payload = post_response.model_dump() if hasattr(post_response, "model_dump") else dict(post_response)
    data = payload.get("data")
    if data:
        print(data.get("text", ""))
```

## Troubleshooting Checklist

- `401`: invalid/expired token or wrong auth type for endpoint.
- `403`: app permissions/scopes do not cover requested operation.
- `429`: rate-limited; back off and retry.
- Empty results: verify query/rules and inspect response `meta`.

## Implementation Notes

- Prefer SDK methods over hand-built HTTP calls for correctness and maintainability.
- Keep endpoint naming exact (`client.posts.search_recent`, `client.stream.posts`, etc.).
- Validate code against current docs and changelog when behavior is unexpected.
