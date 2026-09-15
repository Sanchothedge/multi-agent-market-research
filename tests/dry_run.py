"""Offline smoke test: mocks you_search.search and the three llm.* calls so
the full pipeline (competitor selection -> 8-topic research loop with a
retry -> report context -> markdown -> docx) can be exercised without real
API keys or network access.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.models import RunRequest
from src.orchestrator import run_pipeline

config.YOU_SEARCH_DELAY_SECONDS = 0  # skip real pacing delay in the test

SAMPLE_SEARCH_RESULT = {
    "web": [
        {
            "url": "https://example-competitor.com/pricing",
            "title": "Pricing - Example Competitor",
            "description": "Plans start at $499/month for the professional tier.",
            "snippets": ["Enterprise pricing available on request."],
            "page_age": "2026-08-01",
        }
    ],
    "news": [
        {
            "url": "https://news.example.com/competitor-launch",
            "title": "Example Competitor launches new AI module",
            "description": "The company announced a new product line this week.",
            "published_at": "2026-09-01",
        }
    ],
}

_call_counts = {"validate": 0}


def fake_search(query, count=10, apply_freshness=False, lookback_days=30):
    return SAMPLE_SEARCH_RESULT


def fake_select_direct_competitors(**kwargs):
    return [
        {"name": "Example Competitor", "website": "https://example-competitor.com"},
        {"name": "Second Rival Inc", "website": "not publicly available"},
    ]


def fake_validate_research_evidence(**kwargs):
    _call_counts["validate"] += 1
    # Force exactly one retry cycle for the 'pricing' category on the first
    # competitor to prove the retry path works, complete everything else.
    if kwargs["category"] == "pricing" and kwargs["competitor_name"] == "Example Competitor" and _call_counts["validate"] < 3:
        return {
            "complete": False,
            "checks": {"claims_have_urls": False},
            "issues": ["Pricing source is not official domain"],
            "conflicting_sources": [],
            "associated_claims": [],
            "category_summary": "not publicly available",
            "retry_query": "Example Competitor official pricing page site:example-competitor.com",
        }
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
            {"claim": "Plans start at $499/month.", "url": "https://example-competitor.com/pricing", "kind": "fact"}
        ],
        "category_summary": f"{kwargs['category']}: evidence-grounded summary for {kwargs['competitor_name']}.",
        "retry_query": "",
    }


def fake_generate_competitive_report(context):
    lines = [
        "## Executive summary",
        f"{context['target_company']} faces {len(context['competitors'])} direct competitors.",
        "",
        "## Successful validation records",
        "- Example Competitor | pricing | complete | S1 | https://example-competitor.com/pricing",
        "",
        "## Failed or incomplete validation records",
        "- (none)",
        "",
        "## Competitor comparison table",
        "| Competitor | Website | Validation Status |",
        "| --- | --- | --- |",
    ]
    for c in context["competitors"]:
        lines.append(f"| {c['name']} | {c['website']} | {c['validation_status']} |")
    lines += [
        "",
        "## Pricing comparison",
        "| Competitor | Pricing |",
        "| --- | --- |",
    ]
    for c in context["competitors"]:
        lines.append(f"| {c['name']} | {c['pricing']} |")
    lines += [
        "",
        "## Feature comparison",
        "| Competitor | Features |",
        "| --- | --- |",
    ]
    for c in context["competitors"]:
        lines.append(f"| {c['name']} | {c['features']} |")
    lines += [
        "",
        "## Positioning analysis",
        "**Interpretation:** the market is fragmenting [S1].",
        "",
        "## Recent market developments",
        "- Example Competitor launched a new AI module [S2].",
        "",
        "## Competitive risks",
        "- Price competition on entry-level tiers.",
        "",
        "## Opportunities for differentiation",
        "- Vertical-specific integrations.",
        "",
        "## Recommended actions",
        "1. Benchmark pricing quarterly.",
        "2. Track competitor product launches.",
        "",
        "## Source list",
        "- [S1] Pricing - Example Competitor | 2026-08-01 | Example Competitor | https://example-competitor.com/pricing",
        "- [S2] Example Competitor launches new AI module | 2026-09-01 | Example Competitor | https://news.example.com/competitor-launch",
    ]
    return "\n".join(lines)


def main():
    request = RunRequest(
        company_name="TheEdge LLC",
        company_website="www.thedgellc.ai",
        industry="ReInvention, AI and Software Services",
        target_market="Financial Services, Healthcare, Life Sciences, Hitech",
        country_or_region="Global",
        news_lookback_days=30,
    )

    with patch("src.you_search.search", side_effect=fake_search), \
         patch("src.llm.select_direct_competitors", side_effect=fake_select_direct_competitors), \
         patch("src.llm.validate_research_evidence", side_effect=fake_validate_research_evidence), \
         patch("src.llm.generate_competitive_report", side_effect=fake_generate_competitive_report):
        output_path = run_pipeline(request, verbose=True)

    assert os.path.exists(output_path), "docx was not written"
    size = os.path.getsize(output_path)
    assert size > 5000, f"docx suspiciously small: {size} bytes"
    print(f"\nOK - docx written at {output_path} ({size} bytes)")
    print(f"Validator was called {_call_counts['validate']} times (expect a retry to have happened).")


if __name__ == "__main__":
    main()
