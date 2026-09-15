"""End-to-end pipeline orchestration, replacing the node-to-node wiring of
the n8n workflow's canvas."""
from __future__ import annotations

from . import competitor_finder, config, report_builder, researcher
from .docx_writer import markdown_to_docx
from .models import RunRecord, RunRequest, now_iso
from .storage import RunStore, new_run_id


def run_pipeline(request: RunRequest, verbose: bool = True, dry_run: bool | None = None) -> str:
    if dry_run is not None:
        config.DRY_RUN = bool(dry_run)
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    research_run_id = new_run_id()
    store = RunStore(research_run_id)

    run = RunRecord(
        research_run_id=research_run_id,
        target_company=request.company_name,
        target_website=request.company_website,
        industry=request.industry,
        target_market=request.target_market,
        country_or_region=request.country_or_region,
        news_lookback_days=request.news_lookback_days,
    )
    store.save_run(run)
    log(f"[{research_run_id}] Started research run for {run.target_company}")

    log("[1/4] Finding direct competitors...")
    competitors, discovery_evidence = competitor_finder.find_competitors(run)
    if not competitors:
        log("  No sufficiently-evidenced competitors found. Report will note the gap.")
    else:
        log(f"  Found {len(competitors)}: {', '.join(c.competitor_name for c in competitors)}")
    store.save_competitors(competitors)

    log("[2/4] Researching each competitor across 8 topics (this calls the API a lot)...")
    all_evidence = []
    for idx, competitor in enumerate(competitors, start=1):
        log(f"  ({idx}/{len(competitors)}) {competitor.competitor_name}")
        evidence_rows = researcher.research_competitor(run, competitor, discovery_evidence)
        all_evidence.extend(evidence_rows)
        store.update_competitor(
            competitor.competitor_name,
            pricing=competitor.pricing,
            features=competitor.features,
            positioning=competitor.positioning,
            validation_status=competitor.validation_status,
            updated_at=now_iso(),
        )
    store.append_evidence(all_evidence)

    log("[3/4] Building report context and generating the report...")
    report_meta = report_builder.build_report_context(run, competitors, all_evidence)
    log(
        f"  {report_meta['successful_record_count']} validated source(s), "
        f"{report_meta['failed_record_count']} failed/incomplete"
    )
    markdown, completion_status = report_builder.generate_report_markdown(report_meta)

    log("[4/4] Writing .docx report...")
    title = f"Competitive Market Research - {run.target_company} - {report_meta['context']['report_date']}"
    output_path = store.report_path()
    markdown_to_docx(
        title=title,
        subtitle=f"Prepared for {run.target_company} | Run ID {research_run_id}",
        markdown=markdown,
        output_path=output_path,
    )

    store.update_run(status=completion_status, completed_at=now_iso())
    log(f"Done ({completion_status}). Report: {output_path}")
    return output_path
