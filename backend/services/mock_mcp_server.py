"""
Mock MCP (Model Context Protocol) Integration Server
=====================================================
Simulates an MCP server exposing live EDC, eSource, and LIMS database queries
using local CSV data files (`Subject Source (10)_converted.csv`).

Supports:
  - mcp_query_participant_events(subject_id)
  - mcp_query_vitals_trajectory(subject_id)
  - mcp_query_lims_labs(subject_id)
"""

import os, csv
from typing import List, Dict, Any, Optional
from services.derivation_engine import validate_and_convert_creatinine, NOT_DOCUMENTED


class MockMcpServer:
    def __init__(self, csv_filepath: str):
        self.csv_filepath = csv_filepath
        self._records_by_subject: Dict[str, List[Dict[str, str]]] = {}
        self._load_csv()

    def _load_csv(self):
        if not os.path.exists(self.csv_filepath):
            return
        with open(self.csv_filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                subjid = row.get("SUBJID", "").strip()
                if subjid:
                    if subjid not in self._records_by_subject:
                        self._records_by_subject[subjid] = []
                    self._records_by_subject[subjid].append(row)

    def get_subject_ids(self) -> List[str]:
        return list(self._records_by_subject.keys())

    def query_vitals_trajectory(self, subject_id: str) -> List[Dict[str, Any]]:
        rows = self._records_by_subject.get(subject_id, [])
        bp_log = []
        for r in rows:
            sbp = r.get("SBP") or r.get("VITAL_SBP")
            dbp = r.get("DBP") or r.get("VITAL_DBP")
            if sbp and dbp:
                try:
                    s_num, d_num = int(float(sbp)), int(float(dbp))
                    bp_log.append({
                        "date": r.get("EVENT_DT") or r.get("VITAL_DT") or "2026-07-04",
                        "ga": r.get("GA_EVENT") or r.get("GA") or "31+2",
                        "sbp": s_num,
                        "dbp": d_num,
                        "severe": (s_num >= 160 or d_num >= 110),
                        "source": r.get("SOURCE_SYSTEM", "eSource Vitals")
                    })
                except ValueError:
                    pass
        return bp_log

    def query_lims_labs(self, subject_id: str) -> Dict[str, Any]:
        rows = self._records_by_subject.get(subject_id, [])
        labs = {}
        for r in rows:
            for k, v in r.items():
                if k in ("UPCR", "PLATELET_COUNT", "CREATININE", "AST", "ALT", "LDH") and v:
                    labs[k] = v
        return labs
