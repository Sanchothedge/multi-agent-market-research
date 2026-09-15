"""Step 2: research each competitor across 8 topics, validate the evidence,
and retry incomplete topics up to MAX_RETRIES times.

Mirrors, in order: "Build Per-Competitor Research Queries" -> "Research Loop"
-> "Prepare Search Request" -> "Research Each Competitor Topic with You.com"
-> "Attach Research Context" -> "Validate Research Evidence" ->
"Parse Validation Result" -> "Research Complete?" -> (loop back via
"Build Validation Retry Query", or proceed to) "Get Competitor Record" ->
"Build Competitor Update" -> "Update Competitor Record" ->
"Normalize Research Results" -> "Save Evidence".
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from . import config, llm, you_search
from .models import Competitor, EvidenceRow, RunRecord


def _window(lookback_days: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(1, lookback_days))
    return start.date().isoformat(), now.date().isoformat()


def _build_query(competitor_name: str, competitor_website: str, terms: str) -> str:
    site_part = "" if competitor_website == "not publicly available" else competitor_website
    guidance = (
        " Prefer official and recent sources. Use third-party sources only "
        "when official information is not publicly available."
    )
    return " ".join(part for part in [competitor_name, site_part, terms, guidance] if part).strip()


def research_and_validate_topic(
    run: RunRecord,
    competitor: Competitor,
    category: str,
    initial_query: str,
    apply_freshness: bool,
    discovery_evidence: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Runs the search -> validate -> (retry) loop for one topic.

    Returns (validation_result, search_results, retry_count_used).
    """
    query = initial_query
    retry_count = 0
    window_start, window_end = _window(run.news_lookback_days)

    while True:
        search_results = you_search.search(
            query,
            count=5,
            apply_freshness=apply_freshness,
            lookback_days=run.news_lookback_days,
        )

        validation = llm.validate_research_evidence(
            company_name=run.target_company,
            industry=run.industry,
            target_market=run.target_market,
            country_or_region=run.country_or_region,
            competitor_name=competitor.competitor_name,
            competitor_website=competitor.competitor_website,
            category=category,
            lookback_days=run.news_lookback_days,
            query=query,
            discovery_evidence=discovery_evidence,
            topic_evidence=search_results,
            window_start=window_start,
            window_end=window_end,
        )

        complete = validation.get("complete") is True
        ready_to_store = complete or retry_count >= config.MAX_RETRIES

        if ready_to_store:
            validation["_validation_status"] = (
                "complete"
                if complete
                else ("incomplete_after_retries" if retry_count >= config.MAX_RETRIES else "incomplete")
            )
            return validation, search_results, retry_count

        # Not complete and retries remain: build a sharper retry query and loop.
        fallback = f"{competitor.competitor_name} {category} current official source URL evidence"
        requested = str(validation.get("retry_query") or fallback).strip()
        query = " ".join(requested.split()[:45])[:380]
        retry_count += 1
        apply_freshness = category == "recent_news"


def _apply_summary_to_competitor(competitor: Competitor, category: str, summary: str) -> None:
    if category == "pricing":
        competitor.pricing = summary
    elif category in ("core_features", "official_products"):
        competitor.features = summary
    elif category == "market_positioning":
        competitor.positioning = summary


def _normalize_evidence(
    run: RunRecord,
    competitor: Competitor,
    category: str,
    validation: dict[str, Any],
    search_results: dict[str, Any],
    retry_count: int,
) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    associated_claims = validation.get("associated_claims") or []
    sections = [
        ("web", search_results.get("web") if isinstance(search_results, dict) else None),
        ("news", search_results.get("news") if isinstance(search_results, dict) else None),
    ]
    for source_type, results in sections:
        for result in results or []:
            if not isinstance(result, dict):
                continue
            highlights = (result.get("contents") or {}).get("highlights") or []
            snippets = result.get("snippets") or []
            excerpt_parts = []
            if result.get("description"):
                excerpt_parts.append(str(result["description"]))
            if snippets:
                excerpt_parts.append(" ".join(snippets))
            if highlights:
                excerpt_parts.append(" ".join(highlights))
            url = str(result.get("url", ""))
            claims_for_source = [
                c for c in associated_claims if not c.get("url") or str(c.get("url")) == url
            ]
            rows.append(
                EvidenceRow(
                    research_run_id=run.research_run_id,
                    competitor_name=competitor.competitor_name,
                    category=category,
                    source_type=source_type,
                    source_url=url,
                    source_title=str(result.get("title", "")),
                    source_date=str(
                        result.get("page_age")
                        or result.get("published_at")
                        or result.get("date")
                        or "not publicly available"
                    ),
                    excerpt=" ".join(excerpt_parts)[:5000],
                    associated_claims=json.dumps(claims_for_source),
                    validation_status=validation["_validation_status"],
                    validation_issues=" | ".join(str(i) for i in (validation.get("issues") or [])),
                    validation_checks_json=json.dumps(validation.get("checks") or {}),
                    conflicting_sources=json.dumps(validation.get("conflicting_sources") or []),
                    retry_count=retry_count,
                )
            )
    return rows


def research_competitor(
    run: RunRecord,
    competitor: Competitor,
    discovery_evidence: dict[str, Any],
) -> list[EvidenceRow]:
    """Runs all 8 topics for one competitor, updating the competitor's
    pricing/features/positioning summaries in place and returning the
    evidence rows collected."""
    all_evidence: list[EvidenceRow] = []

    for topic in config.RESEARCH_TOPICS:
        category = topic["category"]
        query = _build_query(competitor.competitor_name, competitor.competitor_website, topic["terms"])

        validation, search_results, retry_count = research_and_validate_topic(
            run=run,
            competitor=competitor,
            category=category,
            initial_query=query,
            apply_freshness=topic["fresh"],
            discovery_evidence=discovery_evidence,
        )

        summary = str(validation.get("category_summary") or "not publicly available")
        _apply_summary_to_competitor(competitor, category, summary)
        competitor.validation_status = validation["_validation_status"]

        all_evidence.extend(
            _normalize_evidence(run, competitor, category, validation, search_results, retry_count)
        )

    return all_evidence
