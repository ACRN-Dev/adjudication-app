import React from 'react';
import { X, ExternalLink, BookOpen } from 'lucide-react';

export default function HelpModal({ onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={22} color="var(--acrn-navy-base)" />
            <h3 style={{ margin: 0, fontSize: '18px' }}>Clinical Guidelines & Reading Material</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>
            <X size={22} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <p style={{ fontSize: '14px', color: '#64748b', margin: 0 }}>
            Below are external guideline resources and reference materials to support your clinical adjudication.
          </p>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', width: '100%' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>
                ACOG Practice Bulletin #222
              </h4>
              <p style={{ fontSize: '13px', color: '#475569', margin: '0 0 10px' }}>
                Gestational Hypertension & Preeclampsia (2020 with June 2024 update).
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <a href="https://www.acog.org/clinical/clinical-guidance/practice-bulletin/articles/2020/06/gestational-hypertension-and-preeclampsia" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--acrn-orange-primary)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 600 }}>
                  <ExternalLink size={12} /> acog.org
                </a>
                <a href="https://www.preeclampsia.org/frontend/assets/img/advocacy_resource/Gestational_Hypertension_and_Preeclampsia_ACOG_Practice_Bulletin,_Number_222_1605448006.pdf" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--acrn-orange-primary)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 600 }}>
                  <ExternalLink size={12} /> Full PDF
                </a>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', width: '100%' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>
                WHO Recommendations
              </h4>
              <p style={{ fontSize: '13px', color: '#475569', margin: '0 0 10px' }}>
                Prevention and Treatment of Pre-eclampsia and Eclampsia.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <a href="https://www.who.int/publications/i/item/9789241548335" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--acrn-orange-primary)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 600 }}>
                  <ExternalLink size={12} /> who.int
                </a>
                <a href="https://iris.who.int/server/api/core/bitstreams/02f76d6d-4f9f-4662-84fe-e23c186e1594/content" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--acrn-orange-primary)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 600 }}>
                  <ExternalLink size={12} /> Full PDF
                </a>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', width: '100%' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>
                ISSHP 2021 Guidelines
              </h4>
              <p style={{ fontSize: '13px', color: '#475569', margin: '0 0 10px' }}>
                International Society for the Study of Hypertension in Pregnancy.
              </p>
              <a href="https://isshp.org/wp-content/uploads/2023/09/ISSHP-2021-guidelines.pdf" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--acrn-orange-primary)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 600 }}>
                <ExternalLink size={12} /> Full PDF
              </a>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', width: '100%' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>
                Preeclampsia Foundation Hub
              </h4>
              <p style={{ fontSize: '13px', color: '#475569', margin: '0 0 10px' }}>
                Aggregates ACOG, WHO, NICE, FIGO, and ISSHP guidelines in one place.
              </p>
              <a href="https://www.preeclampsia.org/current-guidelines" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--acrn-orange-primary)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 600 }}>
                <ExternalLink size={12} /> preeclampsia.org
              </a>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-large btn-next" onClick={onClose} style={{ padding: '10px 20px', fontSize: '14px' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
