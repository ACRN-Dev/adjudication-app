"""Execute an eTMF write/read-back contract check and retain JSON evidence."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.etmf_adapter import get_etmf_adapter


def build_pdf(run_id: str) -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    page.drawString(72, 760, "ACRN eTMF integration qualification artifact")
    page.drawString(72, 740, f"Run: {run_id}")
    page.drawString(72, 720, "Synthetic data only. Retain as validation evidence.")
    page.save()
    return buffer.getvalue()


def main(args) -> int:
    if args.confirm_live_write != "VALIDATION-ONLY":
        raise SystemExit("Refusing destination write: pass --confirm-live-write VALIDATION-ONLY")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    content = build_pdf(run_id)
    expected = hashlib.sha256(content).hexdigest()
    adapter = get_etmf_adapter()
    destination = adapter.write("SYNTHETIC", f"QUAL-{run_id}", args.study, content,
                                timestamp=datetime.now(timezone.utc), visit_code="V00")
    receipt = adapter.verify(destination, expected)
    evidence = {
        "schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "adapter": adapter.__class__.__name__, "study": args.study, "synthetic": True,
        "destination": receipt.destination, "content_sha256": receipt.content_sha256,
        "manifest_sha256": receipt.manifest_sha256, "receipt_id": receipt.receipt_id,
        "verified_at": receipt.verified_at.isoformat(),
        "result": "PASS" if receipt.content_sha256 == expected and receipt.manifest_sha256 == expected else "FAIL",
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["result"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qualify configured eTMF adapter with a synthetic write/read-back")
    parser.add_argument("--confirm-live-write", required=True)
    parser.add_argument("--study", default="VALIDATION")
    parser.add_argument("--output", default="output/qualification/etmf.json")
    raise SystemExit(main(parser.parse_args()))
