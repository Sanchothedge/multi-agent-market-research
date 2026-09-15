"""JSON-file persistence, standing in for the three n8n Data Tables
(Research Runs, Competitors, Evidence). One directory per run under runs/.

Not a database — just enough durability to inspect a run afterward and to
let `Get Report Competitors` / `Get Report Evidence` equivalents read back
what was collected.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

from . import config
from .models import Competitor, EvidenceRow, RunRecord


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


class RunStore:
    def __init__(self, research_run_id: str):
        self.research_run_id = research_run_id
        self.dir = os.path.join(config.RUNS_DIR, research_run_id)
        os.makedirs(self.dir, exist_ok=True)
        self._competitors: list[Competitor] = []
        self._evidence: list[EvidenceRow] = []

    # ---- Research Runs table equivalent ----
    def save_run(self, run: RunRecord) -> None:
        self._write_json("run.json", run.to_dict())

    def update_run(self, **fields: Any) -> None:
        run = self._read_json("run.json") or {}
        run.update(fields)
        self._write_json("run.json", run)

    # ---- Competitors table equivalent ----
    def save_competitors(self, competitors: list[Competitor]) -> None:
        self._competitors = competitors
        self._write_json("competitors.json", [c.to_dict() for c in competitors])

    def get_competitors(self) -> list[Competitor]:
        if self._competitors:
            return self._competitors
        rows = self._read_json("competitors.json") or []
        self._competitors = [Competitor(**row) for row in rows]
        return self._competitors

    def update_competitor(self, competitor_name: str, **fields: Any) -> None:
        competitors = self.get_competitors()
        for c in competitors:
            if c.competitor_name == competitor_name:
                for key, value in fields.items():
                    setattr(c, key, value)
        self.save_competitors(competitors)

    # ---- Evidence table equivalent ----
    def append_evidence(self, rows: list[EvidenceRow]) -> None:
        self._evidence.extend(rows)
        existing = self._read_json("evidence.json") or []
        existing.extend([r.to_dict() for r in rows])
        self._write_json("evidence.json", existing)

    def get_evidence(self) -> list[EvidenceRow]:
        rows = self._read_json("evidence.json") or []
        return [EvidenceRow(**row) for row in rows]

    # ---- helpers ----
    def _write_json(self, name: str, data: Any) -> None:
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _read_json(self, name: str) -> Any:
        path = os.path.join(self.dir, name)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def report_path(self) -> str:
        return os.path.join(self.dir, "report.docx")
