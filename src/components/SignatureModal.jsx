import React, { useState } from 'react';
import { Lock, ShieldCheck, Key, AlertCircle, CheckCircle } from 'lucide-react';

export default function SignatureModal({ caseData, onSignConfirm, onClose }) {
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('849201');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Pre-calculated SHA-256 hash representation of the case facts + narrative
  const caseHash = "SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

  const handleSignature = (e) => {
    e.preventDefault();
    if (!password) {
      setErrorMsg('Please enter your ACRN account credentials to authenticate.');
      return;
    }
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      onSignConfirm({
        signer: "Dr. Tinotenda Chibongore",
        email: "tinotenda.chibongore@acrnhealth.com",
        timestamp: new Date().toISOString(),
        hash: caseHash
      });
    }, 1200);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Lock size={20} color="var(--acrn-orange-primary)" />
            <h3 style={{ margin: 0, fontSize: '16px' }}>21 CFR Part 11 Electronic Signature</h3>
          </div>
        </div>

        <form onSubmit={handleSignature}>
          <div className="modal-body">
            <div style={{
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '14px',
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Signing Target</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--acrn-navy-base)' }}>
                Case {caseData.caseNo} ({caseData.id})
              </div>
              <div style={{ fontSize: '12px', color: 'var(--acrn-sky-blue)', marginTop: '4px', wordBreak: 'break-all' }}>
                {caseHash}
              </div>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              By signing below, I certify that I have reviewed the source data, derived criteria, and clinical narrative for participant <strong>{caseData.id}</strong>. This record will be cryptographically locked and filed directly to the TMF.
            </p>

            {errorMsg && (
              <div style={{
                background: '#ffebe9',
                color: '#cf222e',
                padding: '10px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                marginBottom: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                {errorMsg}
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label>Re-enter Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Entra ID MFA Security Passcode</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="form-input"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                />
                <button type="button" className="btn-secondary" style={{ whiteSpace: 'nowrap' }} onClick={() => alert('Demo OTP resent. In production, this action will invoke Entra ID step-up authentication and will not expose or store the OTP in the browser.')}>
                  Resend OTP
                </button>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? (
                <>Signing Case...</>
              ) : (
                <>
                  <ShieldCheck size={16} /> Authenticate & Lock Record
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
