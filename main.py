#!/usr/bin/env python3
"""CLI entry point for the Multi-Agent Market Research pipeline.

Mirrors the fields of the original n8n Form Trigger:
  Company name, Company website, Industry, Target market,
  Country or region, News lookback period (days).
"""
from __future__ import annotations

import argparse
import sys

from src import config
from src.models import RunRequest
from src.orchestrator import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Agent Market Research")
    parser.add_argument("--company-name", help="Company name")
    parser.add_argument("--company-website", help="Company website")
    parser.add_argument("--industry", help="Industry")
    parser.add_argument("--target-market", help="Target market (customer segments)")
    parser.add_argument("--country", dest="country_or_region", help="Country or region (default: Global)")
    parser.add_argument("--lookback-days", type=int, help="News lookback period in days")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress logging")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use built-in offline data instead of live You.com/OpenAI calls.",
    )
    return parser.parse_args()


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def build_request(args: argparse.Namespace) -> RunRequest:
    company_name = args.company_name or prompt("Company name", "TheEdge LLC")
    company_website = args.company_website or prompt("Company website", "www.thedgellc.ai")
    industry = args.industry or prompt("Industry", "ReInvention, AI and Software Services")
    target_market = args.target_market or prompt(
        "Target market", "Financial Services, Healthcare, Life Sciences, Hitech"
    )
    country_or_region = args.country_or_region or prompt("Country or region", "Global")

    lookback_days = args.lookback_days
    if lookback_days is None:
        raw = prompt("News lookback period (days)", "30")
        lookback_days = int(raw) if raw.strip().isdigit() else 30

    return RunRequest(
        company_name=company_name,
        company_website=company_website,
        industry=industry,
        target_market=target_market,
        country_or_region=country_or_region,
        news_lookback_days=max(1, lookback_days),
    )


def main() -> int:
    args = parse_args()
    config.DRY_RUN = args.dry_run or config.DRY_RUN
    request = build_request(args)
    try:
        output_path = run_pipeline(request, verbose=not args.quiet, dry_run=config.DRY_RUN)
    except Exception as exc:  # noqa: BLE001 - top-level CLI error surface
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
