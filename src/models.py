"""Plain dataclasses standing in for the original n8n Data Table rows
(Research Runs / Competitors / Evidence tables)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunRequest:
    company_name: str
    company_website: str
    industry: str
    target_market: str
    country_or_region: str
    news_lookback_days: int


@dataclass
class RunRecord:
    research_run_id: str
    target_company: str
    target_website: str
    industry: str
    target_market: str
    country_or_region: str
    news_lookback_days: int
    status: str = "running"
    started_at: str = field(default_factory=now_iso)
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Competitor:
    research_run_id: str
    target_company: str
    competitor_name: str
    competitor_website: str = "not publicly available"
    pricing: str = "not publicly available"
    features: str = "not publicly available"
    positioning: str = "not publicly available"
    validation_status: str = "pending"
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceRow:
    research_run_id: str
    competitor_name: str
    category: str
    source_type: str
    source_url: str
    source_title: str
    source_date: str
    excerpt: str
    associated_claims: str  # JSON string, kept as text like the original table column
    validation_status: str
    validation_issues: str
    validation_checks_json: str
    conflicting_sources: str
    retry_count: int
    retrieved_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
