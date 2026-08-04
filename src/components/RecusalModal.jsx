import React, { useState } from 'react';
import { X, ShieldAlert, UserX, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function RecusalModal({ caseData, onConfirmRecusal, onClose }) {
  const [recusalReason, setRecusalReason] = useState('SITE_INVESTIGATOR');
  const [comments, setComments] = useState('I am an investigator at this site and provided direct clinical care for the participant.');

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirmRecusal({
      caseId: caseData.id,
      recusalReason,
      comments,
      date: new Date().toISOString()
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '580px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header" style={{ background: '#7c2d12' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <UserX size={22} color="#fdba74" />
            <div>
              <h3 style={{ margin: 0, fontSize: '16px' }}>FORM-ADJ-08: Conflict of Interest & Recusal</h3>
              <p style={{ margin: 0, fontSize: '11px', color: '#fed7aa' }}>SOP-ADJ-003 Committee Independence Compliance</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>
            <X size={22} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '8px', padding: '14px', marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: '#9a3412', fontWeight: 600 }}>Target Case for Recusal</div>
              <div style={{ fontSize: '16px', fontWeight: 800, color: '#7c2d12', marginTop: '2px' }}>
                Participant {caseData.id} ({caseData.site})
              </div>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Under <strong>SOP-ADJ-003 §5.2</strong>, adjudicators must recuse themselves from cases where they are a site investigator, provided direct care, or have an institutional conflict. This case will be re-routed to an independent reviewer.
            </p>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label>Reason for Recusal (FORM-ADJ-08)</label>
              <select
                className="form-select"
                value={recusalReason}
                onChange={(e) => setRecusalReason(e.target.value)}
              >
                <option value="SITE_INVESTIGATOR">Site Principal Investigator or Co-Investigator</option>
                <option value="CLINICAL_CARE">Provided direct clinical care to participant</option>
                <option value="INSTITUTIONAL">Institutional / Financial Conflict of Interest</option>
                <option value="PERSONAL">Personal relationship with participant / site staff</option>
              </select>
            </div>

            <div className="form-group">
              <label>Adjudicator Declaration Notes</label>
              <textarea
                className="narrative-box"
                style={{ height: '80px' }}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" style={{ background: '#c2410c' }}>
              Submit Recusal & Re-route Case
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
