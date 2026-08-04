import React, { useState } from 'react';
import { X, FileText, Database, Activity, Stethoscope } from 'lucide-react';

export default function SourceDocViewer({ caseData, onClose }) {
  const [activeDocTab, setActiveDocTab] = useState('ultrasound');

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '800px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={20} color="var(--acrn-teal-accent)" />
            <h3 style={{ margin: 0, fontSize: '16px' }}>Source Evidence Inspector — Participant {caseData.id}</h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        <div className="modal-body" style={{ padding: 0 }}>
          {/* Tab Navigation */}
          <div style={{ display: 'flex', background: '#f1f5f9', borderBottom: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => setActiveDocTab('ultrasound')}
              style={{
                padding: '12px 18px',
                border: 'none',
                background: activeDocTab === 'ultrasound' ? '#fff' : 'transparent',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                color: activeDocTab === 'ultrasound' ? 'var(--acrn-navy-base)' : 'var(--text-muted)',
                borderBottom: activeDocTab === 'ultrasound' ? '3px solid var(--acrn-orange-primary)' : 'none'
              }}
            >
              Ultrasound SR (PDF)
            </button>
            <button
              onClick={() => setActiveDocTab('lims')}
              style={{
                padding: '12px 18px',
                border: 'none',
                background: activeDocTab === 'lims' ? '#fff' : 'transparent',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                color: activeDocTab === 'lims' ? 'var(--acrn-navy-base)' : 'var(--text-muted)',
                borderBottom: activeDocTab === 'lims' ? '3px solid var(--acrn-orange-primary)' : 'none'
              }}
            >
              Crelio LIMS (HL7 Exports)
            </button>
            <button
              onClick={() => setActiveDocTab('vitals')}
              style={{
                padding: '12px 18px',
                border: 'none',
                background: activeDocTab === 'vitals' ? '#fff' : 'transparent',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                color: activeDocTab === 'vitals' ? 'var(--acrn-navy-base)' : 'var(--text-muted)',
                borderBottom: activeDocTab === 'vitals' ? '3px solid var(--acrn-orange-primary)' : 'none'
              }}
            >
              eSource Vitals Log
            </button>
            <button
              onClick={() => setActiveDocTab('delivery')}
              style={{
                padding: '12px 18px',
                border: 'none',
                background: activeDocTab === 'delivery' ? '#fff' : 'transparent',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                color: activeDocTab === 'delivery' ? 'var(--acrn-navy-base)' : 'var(--text-muted)',
                borderBottom: activeDocTab === 'delivery' ? '3px solid var(--acrn-orange-primary)' : 'none'
              }}
            >
              Delivery Summary (EHR)
            </button>
          </div>

          <div style={{ padding: '24px', minHeight: '280px', background: '#ffffff', fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.6' }}>
            {activeDocTab === 'ultrasound' && (
              <div>
                <div style={{ fontWeight: 'bold', color: 'var(--acrn-navy-base)', marginBottom: '8px' }}>[OBSTETRIC ULTRASOUND STRUCTURED REPORT]</div>
                <div style={{ color: '#334155', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  {caseData.sourceDocs.ultrasound}
                </div>
              </div>
            )}

            {activeDocTab === 'lims' && (
              <div>
                <div style={{ fontWeight: 'bold', color: 'var(--acrn-navy-base)', marginBottom: '8px' }}>[CRELIO LIMS HL7 ORU^R01 AUDIT EXPORT]</div>
                <div style={{ color: '#334155', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  {caseData.sourceDocs.lims}
                </div>
              </div>
            )}

            {activeDocTab === 'vitals' && (
              <div>
                <div style={{ fontWeight: 'bold', color: 'var(--acrn-navy-base)', marginBottom: '8px' }}>[REALTIME ESOURCE BLOOD PRESSURE TIMELINE]</div>
                <div style={{ color: '#334155', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  {caseData.sourceDocs.vitals}
                </div>
              </div>
            )}

            {activeDocTab === 'delivery' && (
              <div>
                <div style={{ fontWeight: 'bold', color: 'var(--acrn-navy-base)', marginBottom: '8px' }}>[DELIVERY & NEONATAL MEDICAL RECORD]</div>
                <div style={{ color: '#334155', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  {caseData.sourceDocs.delivery}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
