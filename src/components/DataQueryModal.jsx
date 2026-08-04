import React, { useState } from 'react';
import { X, AlertCircle, HelpCircle, Send } from 'lucide-react';

export default function DataQueryModal({ caseData, onSubmitQuery, onClose }) {
  const [queryCategory, setQueryCategory] = useState('MISSING_TIMESTAMP');
  const [queryText, setQueryText] = useState('Blood pressure measurement date/time missing on screening Visit 1. Unable to confirm 4-hour recheck interval.');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmitQuery({
      caseId: caseData.id,
      queryCategory,
      queryText,
      timestamp: new Date().toISOString()
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '580px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={22} color="var(--acrn-orange-primary)" />
            <div>
              <h3 style={{ margin: 0, fontSize: '16px' }}>FORM-ADJ-09: Data Query & Incident Escalation</h3>
              <p style={{ margin: 0, fontSize: '11px', color: 'var(--acrn-teal-accent)' }}>SOP-ADJ-001 & SOP-ADJ-002 Data Quality Issue</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>
            <X size={22} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '14px', marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Query Target Case</div>
              <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--acrn-navy-base)' }}>
                Participant {caseData.id} ({caseData.caseNo})
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label>Query Category (FORM-ADJ-09)</label>
              <select
                className="form-select"
                value={queryCategory}
                onChange={(e) => setQueryCategory(e.target.value)}
              >
                <option value="MISSING_TIMESTAMP">Missing Measurement Date/Time (e.g. BP timestamp)</option>
                <option value="UNIT_ANOMALY">Lab Unit Anomaly (e.g. Creatinine mmol/L magnitude error)</option>
                <option value="UNBLINDING_INCIDENT">Suspected Unblinding Content (sFlt-1/PlGF visible)</option>
                <option value="MISSING_ULTRASOUND">Missing Ultrasound Doppler structured report</option>
                <option value="CONTRADICTORY_DATA">Contradictory values between EDC and LIMS</option>
              </select>
            </div>

            <div className="form-group">
              <label>Query Rationale & Details for Data Manager</label>
              <textarea
                className="narrative-box"
                style={{ height: '90px' }}
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              <Send size={16} /> Submit Data Query to Coordinator
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
