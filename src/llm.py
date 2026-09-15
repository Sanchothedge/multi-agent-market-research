"""OpenAI calls, replacing the three @n8n/n8n-nodes-langchain.openAi nodes:
"Select Direct Competitors", "Validate Research Evidence", and
"Generate Competitive Report". Prompts are carried over verbatim from the
original workflow's system messages — that's the part worth keeping as-is.
"""
from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from . import config

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def _chat(system: str, user: str, max_tokens: int, temperature: float = 0.1) -> str:
    if config.DRY_RUN:
        return '{"competitors":[{"name":"Example Competitor","website":"https://example-competitor.com"},{"name":"Second Rival Inc","website":"https://second-rival.example"},{"name":"Northstar Platform","website":"https://northstar.example"}]}'

    client = _get_client()
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or "{}"


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = "```"
    if text.startswith(fence):
        text = text[3:].lstrip()
        if text.startswith("json"):
            text = text[4:].lstrip()
        if text.endswith(fence):
            text = text[:-3].rstrip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ---- 1. Select Direct Competitors ----

_COMPETITOR_SYSTEM_PROMPT = """Use only the supplied You.com evidence. Do not use prior knowledge, browse independently, or invent missing details. Select exactly three direct competitors when the supplied evidence materially supports overlap in products or services, target customers, business model, and geography. If fewer than three candidates are sufficiently supported, return only those supported candidates and let the final Word report identify the gap. Treat competitor identification as an inference and require supporting facts from the evidence. Prefer official company sources and the most recent dated sources; use third-party sources only when official evidence is unavailable. Exclude directories, publications, the target company, and weak analogs. When a website is not established by the evidence, write exactly "not publicly available". Return only valid compact JSON with this exact shape: {"competitors":[{"name":"Company","website":"https://company.example or not publicly available"}]}. Do not use markdown or code fences."""


def select_direct_competitors(
    company_name: str,
    company_website: str,
    industry: str,
    target_market: str,
    country_or_region: str,
    you_evidence: dict[str, Any],
) -> list[dict[str, str]]:
    if config.DRY_RUN:
        return [
            {"name": "Example Competitor", "website": "https://example-competitor.com"},
            {"name": "Second Rival Inc", "website": "https://second-rival.example"},
            {"name": "Northstar Platform", "website": "https://northstar.example"},
        ]

    user = (
        f"Target company: {company_name}. Website: {company_website}. "
        f"Industry: {industry}. Customers: {target_market}. Region: {country_or_region}. "
        f"Supplied You.com evidence: {json.dumps(you_evidence)}"
    )
    raw = _chat(_COMPETITOR_SYSTEM_PROMPT, user, max_tokens=1200)
    payload = _extract_json(raw)
    competitors = payload.get("competitors", [])
    if not isinstance(competitors, list):
        return []
    cleaned = []
    for c in competitors[: config.MAX_COMPETITORS]:
        if isinstance(c, dict) and c.get("name"):
            cleaned.append(
                {
                    "name": str(c.get("name", "")),
                    "website": str(c.get("website", "not publicly available")),
                }
            )
    return cleaned


# ---- 2. Validate Research Evidence ----

_VALIDATOR_SYSTEM_PROMPT = """Validate one competitor research bundle using only the supplied You.com evidence. Check: (1) every material factual claim has a non-empty supporting URL; (2) pricing evidence is current and from the competitor official domain; (3) news dates fall within the supplied requested window; (4) the company is a direct competitor based on material product, customer, business-model and geographic overlap; (5) facts are clearly separated from interpretations and interpretations are labeled; (6) conflicting sources are explicitly identified with their URLs. Apply pricing and news checks only to relevant categories, marking them true when not applicable. Prefer official and recent evidence. Return only compact valid JSON: {"complete":true,"checks":{"claims_have_urls":true,"pricing_current_official":true,"news_within_period":true,"direct_competitor":true,"facts_separated_from_interpretations":true,"conflicts_identified":true},"issues":[],"conflicting_sources":[],"associated_claims":[],"category_summary":"","retry_query":""}. For associated_claims, return an array of objects with claim, url, and kind (fact or interpretation); every fact must use a URL present in the topic evidence. category_summary must be a concise, evidence-grounded summary for the current category and say "not publicly available" when unsupported. Set complete false if any applicable check fails. The retry_query must target missing evidence, be under 45 words and under 380 characters."""


def validate_research_evidence(
    company_name: str,
    industry: str,
    target_market: str,
    country_or_region: str,
    competitor_name: str,
    competitor_website: str,
    category: str,
    lookback_days: int,
    query: str,
    discovery_evidence: dict[str, Any],
    topic_evidence: dict[str, Any],
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    if config.DRY_RUN:
        return {
            "complete": True,
            "checks": {
                "claims_have_urls": True,
                "pricing_current_official": True,
                "news_within_period": True,
                "direct_competitor": True,
                "facts_separated_from_interpretations": True,
                "conflicts_identified": True,
            },
            "issues": [],
            "conflicting_sources": [],
            "associated_claims": [
                {
                    "claim": f"{competitor_name} evidence for {category} is available in the dry-run dataset.",
                    "url": "https://example-competitor.com/pricing",
                    "kind": "fact",
                }
            ],
            "category_summary": f"Offline dry-run summary for {competitor_name} in {category}.",
            "retry_query": "",
        }

    user = (
        f"Target: {company_name}; industry: {industry}; customers: {target_market}; "
        f"region: {country_or_region}. Candidate: {competitor_name} ({competitor_website}). "
        f"Category: {category}. Requested window: {window_start} through {window_end}. "
        f"Current query: {query}. Direct-competitor discovery evidence: "
        f"{json.dumps(discovery_evidence)}. Topic evidence: {json.dumps(topic_evidence)}"
    )
    raw = _chat(_VALIDATOR_SYSTEM_PROMPT, user, max_tokens=1500, temperature=0.1)
    payload = _extract_json(raw)
    if not payload:
        return {
            "complete": False,
            "checks": {},
            "issues": ["Validator returned invalid JSON"],
            "conflicting_sources": [],
            "associated_claims": [],
            "category_summary": "not publicly available",
            "retry_query": "",
        }
    return payload


# ---- 3. Generate Competitive Report ----

_REPORT_SYSTEM_PROMPT = """Produce one decision-ready competitive market research report using only the supplied evidence. Include both successful validation records and failed or incomplete validation records. Do not browse, use prior knowledge, or invent details. Separate facts from interpretations and label interpretations explicitly. Never present failed or incomplete evidence as verified: mark every affected statement or table cell with "[Failed/Incomplete validation]", state the validation issues and retry count, and retain conflicting-source warnings. Ground every material factual claim with one or more supplied source IDs in square brackets, such as [S4]. Use "not publicly available" whenever the evidence does not support a requested detail. Prefer recent official sources; identify material conflicts rather than resolving them without evidence. Recent market developments must fall inside the supplied lookback period. Include these sections in this exact order: Executive summary; Successful validation records; Failed or incomplete validation records; Competitor comparison table; Pricing comparison; Feature comparison; Positioning analysis; Recent market developments; Competitive risks; Opportunities for differentiation; Recommended actions; Source list. The two validation-record sections must list each record with competitor, category, validation status, source ID, and source URL; the failed section must also include validation issues and retry count. Include the overall validation status for each competitor in the comparison table. Use concise Markdown that converts cleanly into a Microsoft Word-compatible document. The comparison, pricing, and feature sections must each contain a readable Markdown table. In the Source list, include every cited source ID, title, date, competitor, and full URL. Never cite a source ID that is absent from the supplied evidence."""


def generate_competitive_report(report_context: dict[str, Any]) -> str:
    if config.DRY_RUN:
        title = report_context.get("target_company", "Target company")
        competitors = report_context.get("competitors", [])
        lines = [
            "## Executive summary",
            f"{title} was evaluated in dry-run mode because external APIs were unavailable.",
            "The report below uses the offline placeholder evidence so the pipeline can still run end-to-end.",
            "",
            "## Successful validation records",
        ]
        for competitor in competitors:
            lines.append(f"- {competitor.get('name', 'Unknown')} | pricing | complete | S1 | https://example-competitor.com/pricing")
        lines.extend([
            "",
            "## Failed or incomplete validation records",
            "- (none in dry-run mode)",
            "",
            "## Competitor comparison table",
            "| Competitor | Website | Validation Status |",
            "| --- | --- | --- |",
        ])
        for competitor in competitors:
            lines.append(f"| {competitor.get('name', 'Unknown')} | {competitor.get('website', 'n/a')} | {competitor.get('validation_status', 'complete')} |")
        lines.extend([
            "",
            "## Pricing comparison",
            "| Competitor | Pricing |",
            "| --- | --- |",
        ])
        for competitor in competitors:
            lines.append(f"| {competitor.get('name', 'Unknown')} | Dry-run placeholder pricing |")
        lines.extend([
            "",
            "## Feature comparison",
            "| Competitor | Features |",
            "| --- | --- |",
        ])
        for competitor in competitors:
            lines.append(f"| {competitor.get('name', 'Unknown')} | Dry-run placeholder features |")
        lines.extend([
            "",
            "## Positioning analysis",
            "**Interpretation:** This is a dry-run placeholder assessment built without live web/API evidence.",
            "",
            "## Recent market developments",
            "- Placeholder update: dry-run mode does not fetch live news.",
            "",
            "## Competitive risks",
            "- External data sources were unavailable during this run.",
            "",
            "## Opportunities for differentiation",
            "- Replace dry-run placeholders with live verified evidence for the final report.",
            "",
            "## Recommended actions",
            "1. Enable a valid You.com and OpenAI configuration.",
            "2. Re-run the workflow to populate live findings.",
            "",
            "## Source list",
            "- [S1] Example Competitor pricing and plans | 2026-09-01 | Example Competitor | https://example-competitor.com/pricing",
        ])
        return "\n".join(lines)

    user = f"Research context with successful and failed records: {json.dumps(report_context)}"
    raw = _chat(_REPORT_SYSTEM_PROMPT, user, max_tokens=7000, temperature=0.1)
    return raw.strip()
