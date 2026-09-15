"""Thin client for the You.com Search API, replacing the two
n8n-nodes-base.httpRequest nodes ("Find Direct Competitors with You.com" and
"Research Each Competitor Topic with You.com")."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from . import config


class YouSearchError(RuntimeError):
    pass


def _freshness_window(lookback_days: int) -> str:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(1, lookback_days))
    return f"{start:%Y-%m-%d}to{now:%Y-%m-%d}"


def _dry_run_results(query: str, count: int, apply_freshness: bool) -> dict[str, Any]:
    return {
        "web": [
            {
                "url": "https://example-competitor.com/pricing",
                "title": "Example Competitor pricing and plans",
                "description": "Sample dry-run result for the provided query.",
                "snippets": [
                    "Pricing is available from the official site and is consistent with a mid-market SaaS competitor.",
                    "The source is included only to demonstrate the offline fallback mode.",
                ],
                "contents": {"highlights": ["Example Competitor pricing overview"]},
            }
            for _ in range(min(2, max(1, count // 2)))
        ],
        "news": [
            {
                "url": "https://news.example.com/launch",
                "title": "Example Competitor launches new AI feature",
                "description": "Dry-run news stub for offline validation.",
                "page_age": "2026-09-01T12:00:00Z",
            }
        ] if apply_freshness else [],
        "query": query,
    }


def search(
    query: str,
    count: int = 10,
    apply_freshness: bool = False,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Call You.com's search endpoint. Returns the raw JSON response
    (expected shape: {"web": [...], "news": [...], ...})."""
    if config.DRY_RUN:
        return _dry_run_results(query, count, apply_freshness)

    if not config.YOU_API_KEY:
        raise YouSearchError(
            "YOU_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    body: dict[str, Any] = {
        "query": query,
        "count": count,
        "language": "EN",
        "safesearch": "moderate",
        "extraction": {"extraction_mode": "highlights"},
    }
    if apply_freshness:
        body["freshness"] = _freshness_window(lookback_days)

    headers = {
        "Authorization": f"Bearer {config.YOU_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            config.YOU_SEARCH_URL,
            json=body,
            headers=headers,
            timeout=config.YOU_SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise YouSearchError(f"You.com search failed for query {query!r}: {exc}") from exc
    finally:
        # Basic pacing between calls — the original workflow batched requests
        # one at a time with a 250ms interval.
        time.sleep(config.YOU_SEARCH_DELAY_SECONDS)

    return response.json()
