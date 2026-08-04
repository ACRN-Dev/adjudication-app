/**
 * ACRN Adjudication API Client Service
 * Connects React frontend to FastAPI backend service (http://localhost:8000/api).
 * Includes automatic fallback to mock data when backend is unreachable.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

/**
 * Health check helper to verify if backend is running
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch('http://localhost:8000/', { method: 'GET' });
    if (res.ok) {
      const data = await res.json();
      return { online: true, data };
    }
  } catch (e) {
    // Backend offline
  }
  return { online: false };
}

/**
 * Import EDC CSV file
 */
export async function importEdcFile(file, study = 'PROTECT-Africa') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('study', study);
  formData.append('mapping_version', '1.0');
  formData.append('imported_by', 'dr.makadzange@acrn.org');

  const res = await fetch(`${API_BASE_URL}/import/edc`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'EDC import failed');
  }

  return await res.json();
}

/**
 * Import eSource CSV file
 */
export async function importEsourceFile(file, study = 'PROTECT-Africa') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('study', study);
  formData.append('mapping_version', '1.0');
  formData.append('imported_by', 'dr.makadzange@acrn.org');

  const res = await fetch(`${API_BASE_URL}/import/esource`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'eSource import failed');
  }

  return await res.json();
}

/**
 * Run EDC vs eSource reconciliation
 */
export async function reconcileParticipant(subjectId) {
  const res = await fetch(`${API_BASE_URL}/reconcile/${subjectId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Reconciliation failed');
  return await res.json();
}

/**
 * Run ISSHP 2021 deterministic derivation engine
 */
export async function deriveCriteria(subjectId) {
  const res = await fetch(`${API_BASE_URL}/derive/${subjectId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Derivation engine call failed');
  return await res.json();
}

/**
 * Generate AI clinical narrative (FORM-ADJ-15A/15B)
 */
export async function generateNarrative(subjectId) {
  const res = await fetch(`${API_BASE_URL}/narrative/${subjectId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Narrative generation failed');
  return await res.json();
}

/**
 * Edit narrative text with version history retention
 */
export async function updateNarrative(subjectId, editData) {
  const res = await fetch(`${API_BASE_URL}/narrative/${subjectId}/edit`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(editData),
  });
  if (!res.ok) throw new Error('Narrative update failed');
  return await res.json();
}

/**
 * Submit reviewer adjudication (Reviewer A or Reviewer B)
 */
export async function submitAdjudication(subjectId, submissionData) {
  const res = await fetch(`${API_BASE_URL}/adjudication/${subjectId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(submissionData),
  });
  if (!res.ok) throw new Error('Adjudication submission failed');
  return await res.json();
}

/**
 * Lock OAC Chair Committee consensus decision
 */
export async function lockCommitteeDecision(subjectId, lockData) {
  const res = await fetch(`${API_BASE_URL}/committee/${subjectId}/lock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(lockData),
  });
  if (!res.ok) throw new Error('Committee lock failed');
  return await res.json();
}

/**
 * Get 21 CFR Part 11 audit trail
 */
export async function getAuditTrail(subjectId) {
  const res = await fetch(`${API_BASE_URL}/audit/${subjectId}`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return await res.json();
}

/**
 * Get PDF download URL
 */
export function getPdfDownloadUrl(subjectId) {
  return `${API_BASE_URL}/export/pdf/${encodeURIComponent(subjectId)}`;
}

/**
 * Download a signed PDF and surface API failures to the calling screen.
 */
export async function downloadPdfReport(subjectId) {
  const res = await fetch(getPdfDownloadUrl(subjectId));
  if (!res.ok) {
    let detail = '';
    try {
      const error = await res.json();
      detail = error.detail ? `: ${error.detail}` : '';
    } catch {
      // The API may return a plain-text proxy error.
    }
    throw new Error(`TMF report download failed (${res.status})${detail}`);
  }

  const blob = await res.blob();
  if (!blob.size) throw new Error('The TMF report returned an empty file.');

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `FORM_ADJ_15A_Report_${subjectId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Get CSV export URL
 */
export function getCsvExportUrl() {
  return `${API_BASE_URL}/export/csv`;
}
