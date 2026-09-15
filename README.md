# Multi-Agent Market Research

An n8n workflow that orchestrates web research and AI validation to produce a Word-compatible competitive market research report.

## What it does

1. Accepts a company profile and news lookback period through an n8n Form Trigger.
2. Uses You.com search evidence to identify up to three direct competitors.
3. Researches eight categories per competitor: official products, pricing, core features, target customers, market positioning, customer reviews, funding/partnerships/launches/leadership, and recent news.
4. Uses OpenAI to validate evidence, identify missing or conflicting support, and generate retry queries.
5. Stores research runs, competitors, and evidence in n8n Data Tables.
6. Generates a Microsoft Word-compatible RTF report with source IDs and validation warnings.

## Repository contents

- `workflow/multi-agent-market-research.workflow.json` — importable n8n workflow export.
- `README.md` — setup, architecture, and verification notes.

## Requirements

- n8n with Data Tables and the required nodes installed.
- A You.com API credential using Simplified Custom Auth.
- An OpenAI API credential with access to `gpt-4o-mini`.
- Three n8n Data Tables named `Research Runs`, `Competitors`, and `Evidence` with columns matching the schemas embedded in the workflow nodes.

Credential bindings are intentionally removed from the committed workflow export. After import, select your own You.com and OpenAI credentials. Data Table IDs are instance-specific; select the corresponding tables in each Data Table node.

## Import and configure

1. Download `workflow/multi-agent-market-research.workflow.json`.
2. In n8n, import the workflow from file.
3. Configure credentials on the You.com HTTP Request nodes and OpenAI nodes.
4. Create or select the three Data Tables and update all Data Table node references.
5. Review the Form Trigger defaults and publish the workflow when ready.

## Verified run

The source workflow was executed live on **September 15, 2026** with its configured TheEdge LLC defaults and a **30-day** news lookback.

- n8n execution ID: `76`
- Execution status: `success`
- Started: `2026-09-15T21:28:24.232Z`
- Finished: `2026-09-15T21:31:52.017Z`
- Competitors selected: Accenture, Deloitte, and IBM Consulting
- Final research-run status: `completed_with_gaps`
- Gap: IBM Consulting recent-news evidence did not satisfy the requested date window after two retries.

The workflow itself completed without node errors and generated the report file. The `completed_with_gaps` status is a deliberate data-quality outcome, not an execution failure.

## Security

No API keys, tokens, or credential secrets are included in this repository.
