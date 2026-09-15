"""Step 3: assemble the report context and generate the report.

Mirrors "Get Report Competitors" -> "Get Report Evidence" ->
"Build Report Context" -> "Generate Competitive Report" ->
"Prepare Word Report" (content only — the docx file itself is written by
docx_writer.py, replacing the original's RTF-as-Word trick).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from . import llm
from .config import RESEARCH_TOPICS
from .models import Competitor, EvidenceRow, RunRecord

_EXPECTED_CATEGORIES = [t["category"] for t in RESEARCH_TOPICS]


def build_report_context(
    run: RunRecord,
    competitors: list[Competitor],
    evidence: list[EvidenceRow],
) -> dict[str, Any]:
    exactly_three = len(competitors) == 3
    all_categories_present = exactly_three and all(
        any(
            row.competitor_name == c.competitor_name and row.category == category
            for row in evidence
        )
        for c in competitors
        for category in _EXPECTED_CATEGORIES
    )

    unique_evidence: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for row in evidence:
        url = row.source_url.strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique_evidence.append(
            {
                "source_id": f"S{len(unique_evidence) + 1}",
                "competitor_name": row.competitor_name,
                "category": row.category,
                "source_type": row.source_type,
                "source_url": url,
                "source_title": row.source_title,
                "source_date": row.source_date or "not publicly available",
                "excerpt": row.excerpt[:1200],
                "associated_claims": row.associated_claims,
                "validation_status": row.validation_status,
                "validation_issues": row.validation_issues,
                "validation_checks_json": row.validation_checks_json,
                "conflicting_sources": row.conflicting_sources,
                "retry_count": row.retry_count,
            }
        )

    successful_records = [r for r in unique_evidence if r["validation_status"] == "complete"]
    failed_records = [r for r in unique_evidence if r["validation_status"] != "complete"]

    context = {
        "research_run_id": run.research_run_id,
        "target_company": run.target_company,
        "target_website": run.target_website,
        "industry": run.industry,
        "target_market": run.target_market,
        "country_or_region": run.country_or_region,
        "news_lookback_days": run.news_lookback_days,
        "report_date": date.today().isoformat(),
        "competitors": [
            {
                "name": c.competitor_name,
                "website": c.competitor_website,
                "pricing": c.pricing,
                "features": c.features,
                "positioning": c.positioning,
                "validation_status": c.validation_status,
            }
            for c in competitors
        ],
        "successful_records": successful_records,
        "failed_or_incomplete_records": failed_records,
        "evidence": unique_evidence,
    }

    return {
        "report_ready": all_categories_present and not failed_records,
        "competitor_count": len(competitors),
        "evidence_count": len(evidence),
        "successful_record_count": len(successful_records),
        "failed_record_count": len(failed_records),
        "context": context,
    }


def generate_report_markdown(report_meta: dict[str, Any]) -> tuple[str, str]:
    """Returns (markdown_report, completion_status)."""
    markdown = llm.generate_competitive_report(report_meta["context"])
    status = "completed" if report_meta["report_ready"] else "completed_with_gaps"
    return markdown, status
