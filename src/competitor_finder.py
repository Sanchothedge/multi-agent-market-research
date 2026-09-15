"""Step 1: find and store direct competitors.

Mirrors "Find Direct Competitors with You.com" -> "Select Direct Competitors"
-> "Build Competitor Rows" -> "Save Competitors" in the original workflow.
"""
from __future__ import annotations

from . import llm, you_search
from .models import Competitor, RunRecord


def find_competitors(run: RunRecord) -> tuple[list[Competitor], dict]:
    query = (
        f"Find direct competitors of {run.target_company} ({run.target_website}) "
        f"serving {run.target_market} in {run.industry} for "
        f"{run.country_or_region or 'Global'}. Require evidence of product, customer, "
        f"business-model and geographic overlap. Prefer recent official sources; "
        f"otherwise credible third-party sources. Return URLs."
    )
    discovery_evidence = you_search.search(
        query,
        count=10,
        apply_freshness=True,
        lookback_days=run.news_lookback_days,
    )

    selected = llm.select_direct_competitors(
        company_name=run.target_company,
        company_website=run.target_website,
        industry=run.industry,
        target_market=run.target_market,
        country_or_region=run.country_or_region,
        you_evidence=discovery_evidence,
    )

    competitors = [
        Competitor(
            research_run_id=run.research_run_id,
            target_company=run.target_company,
            competitor_name=c["name"],
            competitor_website=c.get("website") or "not publicly available",
        )
        for c in selected
    ]
    return competitors, discovery_evidence
