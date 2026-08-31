"""
eTMF Storage Adapter
====================
Abstract write interface for signed ETMF PDF routing.

Adapters:
  LocalFilesystemAdapter  — writes to backend/.etmf_local/  (test / dev)
  SharePointAdapter       — STUB: raises NotImplementedError (requires real MS Graph wiring)

Factory:
  get_etmf_adapter()  reads ETMF_ADAPTER env var ('local' | 'sharepoint', default 'local')

Naming convention: {study}/{blinded_subject_id}/FORM_ADJ_15A_{subject_id}_{timestamp_utc}.pdf
Access scope note: the destination path should be restricted to Monitor + Admin roles only;
  adjudicators must never receive a direct path or URL to the eTMF repository.

Outstanding external dependency:
  SharePointAdapter requires:
    - ETMF_SHAREPOINT_SITE_URL  (e.g. https://acrnfoundation.sharepoint.com/sites/PROTECT-eTMF)
    - ETMF_SHAREPOINT_LIBRARY   (document library name, e.g. 'Adjudication Records')
    - AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID  (app registration with Files.ReadWrite)
  Until these are wired, all production eTMF writes MUST use the local adapter and the
  SharePoint upload must be treated as a manual post-process step.
"""

import abc
import os
import hashlib
import json
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime
from pathlib import Path


class ETMFAdapter(abc.ABC):
    """Abstract eTMF write interface."""

    @abc.abstractmethod
    def write(
        self,
        subject_id: str,
        blinded_id: str,
        study: str,
        pdf_bytes: bytes,
        timestamp: datetime | None = None,
        visit_code: str | None = None,
    ) -> str:
        """Write a signed adjudication PDF to the eTMF repository."""

    @abc.abstractmethod
    def write_meeting_report(
        self,
        meeting_id: str,
        meeting_title: str,
        study: str,
        report_bytes: bytes,
        timestamp: datetime | None = None,
    ) -> str:
        """Write a signed committee meeting summary report to the eTMF repository."""

    @staticmethod
    def _naming(study: str, blinded_id: str, subject_id: str, ts: datetime) -> str:
        """Deterministic filename per naming convention SOP-ADJ-002 §7."""
        study_safe = study.replace(" ", "_").replace("/", "-")
        return f"FORM_ADJ_15A_{blinded_id}.pdf"

    @staticmethod
    def _path_parts(study: str, blinded_id: str) -> tuple[str, str]:
        """Returns (folder_path, study_safe) for use by concrete adapters."""
        study_safe = study.replace(" ", "_").replace("/", "-")
        return study_safe, blinded_id


class LocalFilesystemAdapter(ETMFAdapter):
    """
    Writes signed PDFs to a local filesystem path.

    Root defaults to  <backend_dir>/.etmf_local/
    Override with ETMF_LOCAL_ROOT env var.

    Structure:
      .etmf_local/
        PROTECT-Africa/
          ADJ-E2E-001/
            FORM_ADJ_15A_ADJ-E2E-001_20260818T143000Z.pdf
          MEETINGS/
            MEETING_REPORT_<id>_<ts>.pdf
    """

    def __init__(self, root: str | None = None):
        if root:
            self._root = Path(root)
        else:
            # Resolve relative to this file's parent's parent (backend/)
            here = Path(__file__).parent.parent
            self._root = Path(os.getenv("ETMF_LOCAL_ROOT", str(here / ".etmf_local")))

    def write(
        self,
        subject_id: str,
        blinded_id: str,
        study: str,
        pdf_bytes: bytes,
        timestamp: datetime | None = None,
        visit_code: str | None = None,
    ) -> str:
        ts = timestamp or datetime.utcnow()
        study_dir, bid_dir = self._path_parts(study, blinded_id)
        dest_dir = self._root / study_dir / bid_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = self._naming(study, f"{blinded_id}-{visit_code}" if visit_code else blinded_id, subject_id, ts)
        dest_path = dest_dir / filename

        dest_path.write_bytes(pdf_bytes)

        # Write SHA-256 manifest alongside
        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        (dest_dir / (filename + ".sha256")).write_text(
            f"{checksum}  {filename}\n", encoding="utf-8"
        )
        return str(dest_path)

    def write_meeting_report(
        self,
        meeting_id: str,
        meeting_title: str,
        study: str,
        report_bytes: bytes,
        timestamp: datetime | None = None,
    ) -> str:
        ts = timestamp or datetime.utcnow()
        study_safe = study.replace(" ", "_").replace("/", "-")
        dest_dir = self._root / study_safe / "MEETINGS"
        dest_dir.mkdir(parents=True, exist_ok=True)

        ts_str = ts.strftime("%Y%m%dT%H%M%SZ")
        filename = f"MEETING_REPORT_{meeting_id}_{ts_str}.pdf"
        dest_path = dest_dir / filename

        dest_path.write_bytes(report_bytes)
        checksum = hashlib.sha256(report_bytes).hexdigest()
        (dest_dir / (filename + ".sha256")).write_text(
            f"{checksum}  {filename}\n", encoding="utf-8"
        )
        return str(dest_path)


class SharePointAdapter(ETMFAdapter):
    """
    STUB — SharePoint / MS Graph eTMF adapter.

    NOT IMPLEMENTED. Requires:
      ETMF_SHAREPOINT_SITE_URL, ETMF_SHAREPOINT_LIBRARY,
      AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID

    This class exists so the interface is stable and swappable.
    Raises NotImplementedError at runtime until the dependency is wired.
    """

    def __init__(self):
        required = ["ETMF_SHAREPOINT_SITE_URL", "ETMF_SHAREPOINT_LIBRARY", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID"]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"SharePoint configuration missing: {', '.join(missing)}")
        self.site_url = os.environ["ETMF_SHAREPOINT_SITE_URL"].rstrip("/")
        self.library = os.environ["ETMF_SHAREPOINT_LIBRARY"]
        self._token = None

    def _access_token(self):
        if self._token:
            return self._token
        token_url = f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/token"
        body = urlencode({"client_id": os.environ["AZURE_CLIENT_ID"], "client_secret": os.environ["AZURE_CLIENT_SECRET"], "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"}).encode()
        with urlopen(Request(token_url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30) as response:
            self._token = json.loads(response.read())["access_token"]
        return self._token

    def _request(self, url, method="GET", body=None, content_type="application/json"):
        headers = {"Authorization": f"Bearer {self._access_token()}", "Content-Type": content_type}
        payload = json.dumps(body).encode() if isinstance(body, dict) else body
        with urlopen(Request(url, data=payload, headers=headers, method=method), timeout=60) as response:
            return json.loads(response.read())

    def _drive_id(self):
        parsed = urlparse(self.site_url)
        site = self._request(f"https://graph.microsoft.com/v1.0/sites/{parsed.hostname}:{parsed.path}")
        drives = self._request(f"https://graph.microsoft.com/v1.0/sites/{site['id']}/drives")["value"]
        drive = next((item for item in drives if item["name"].lower() == self.library.lower()), None)
        if not drive:
            raise RuntimeError(f"SharePoint document library not found: {self.library}")
        return drive["id"]

    def _upload(self, folder, filename, content):
        drive_id = self._drive_id()
        parent = ""
        for part in folder.split("/"):
            endpoint = (
                f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
                if not parent else
                f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{quote(parent, safe='/')}:/children"
            )
            try:
                self._request(endpoint, method="POST", body={"name": part, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"})
            except HTTPError as exc:
                if exc.code != 409:
                    raise
            parent = f"{parent}/{part}" if parent else part
        path = quote(f"{folder}/{filename}", safe="/")
        result = self._request(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path}:/content",
            method="PUT", body=content, content_type="application/pdf",
        )
        return result.get("webUrl") or result["id"]

    def write(self, subject_id, blinded_id, study, pdf_bytes, timestamp=None, visit_code=None):
        filename = self._naming(study, f"{blinded_id}-{visit_code}" if visit_code else blinded_id, subject_id, timestamp or datetime.utcnow())
        return self._upload(f"{study}/{blinded_id}", filename, pdf_bytes)

    def write_meeting_report(self, meeting_id, meeting_title, study, report_bytes, timestamp=None):
        return self._upload(f"{study}/MEETINGS", f"MEETING_REPORT_{meeting_id}.pdf", report_bytes)



def get_etmf_adapter() -> ETMFAdapter:
    """
    Factory: returns the correct adapter based on ETMF_ADAPTER env var.
      'local'      -> LocalFilesystemAdapter  (default)
      'sharepoint' -> SharePointAdapter       (stub — not wired)
    """
    adapter_name = os.getenv("ETMF_ADAPTER", "local").strip().lower()
    if adapter_name == "sharepoint":
        return SharePointAdapter()
    return LocalFilesystemAdapter()
