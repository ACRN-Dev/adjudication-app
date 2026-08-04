import React from 'react';
import { X, CheckCircle, FileText, UploadCloud, ShieldCheck } from 'lucide-react';

export default function HelpModal({ onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <HelpCircleIcon />
            <h3 style={{ margin: 0, fontSize: '18px' }}>User Guide: How to Complete an Adjudication</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>
            <X size={22} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#f97316', color: '#fff', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, flexShrink: 0 }}>1</div>
            <div>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>Step 1: Pick a Patient or Upload CSV</h4>
              <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
                Select an existing study patient card or drag-and-drop a patient CSV data file (from EDC or LIMS).
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#0284c7', color: '#fff', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, flexShrink: 0 }}>2</div>
            <div>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>Step 2: Review Findings</h4>
              <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
                Look over the 3 summary boxes: Blood Pressure timeline, Lab alerts (proteinuria, platelets, liver/kidney values), and the automated rule diagnosis.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#10b981', color: '#fff', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, flexShrink: 0 }}>3</div>
            <div>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>Step 3: Approve & Sign</h4>
              <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
                Read the clear clinical summary text, choose your final diagnosis, and enter your password to sign and lock the record.
              </p>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-large btn-next" onClick={onClose} style={{ padding: '10px 20px', fontSize: '14px' }}>
            Got It! Close Guide
          </button>
        </div>
      </div>
    </div>
  );
}

function HelpCircleIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"></circle>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
      <line x1="12" y1="17" x2="12.01" y2="17"></line>
    </svg>
  );
}
