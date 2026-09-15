"""Configuration and constants for the market research agent.

Mirrors the tunable knobs that were hardcoded inside the n8n workflow's
nodes, so they're all in one place instead of buried in node parameters.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


YOU_API_KEY = os.getenv("YOU_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DRY_RUN = _env_flag("DRY_RUN")

YOU_SEARCH_URL = "https://ydc-index.io/v1/search"
YOU_SEARCH_DELAY_SECONDS = float(os.getenv("YOU_SEARCH_DELAY_SECONDS", "0.25"))
YOU_SEARCH_TIMEOUT_SECONDS = 60

# Matches the original workflow's "Research Complete?" cutoff: after this
# many retries an incomplete topic is stored as incomplete rather than
# retried again.
MAX_RETRIES = 2

MAX_COMPETITORS = 3

# The 8 research topics run for every competitor, matching
# "Build Per-Competitor Research Queries" in the original workflow.
# `fresh=True` applies a date-bounded freshness window to the You.com query.
RESEARCH_TOPICS = [
    {
        "category": "official_products",
        "terms": "current official website product pages products services",
        "fresh": False,
    },
    {
        "category": "pricing",
        "terms": "current official pricing plans costs fees",
        "fresh": False,
    },
    {
        "category": "core_features",
        "terms": "current official core features capabilities solutions",
        "fresh": False,
    },
    {
        "category": "target_customers",
        "terms": "current official target customers industries clients case studies",
        "fresh": False,
    },
    {
        "category": "market_positioning",
        "terms": "current official market positioning value proposition competitors",
        "fresh": False,
    },
    {
        "category": "customer_reviews",
        "terms": "recent customer reviews testimonials G2 Capterra",
        "fresh": False,
    },
    {
        "category": "funding_partnerships_launches_leadership",
        "terms": "recent official funding partnerships launches leadership press release news",
        "fresh": False,
    },
    {
        "category": "recent_news",
        "terms": "recent official news announcements launches partnerships leadership",
        "fresh": True,
    },
]

RUNS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs")
