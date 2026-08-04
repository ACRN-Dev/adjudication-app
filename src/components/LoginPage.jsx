import React, { useState } from 'react';
import { login } from '../services/authApi';

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('admin@acrnhealth.com');
  const [password, setPassword] = useState('ACRN@2026');
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg('Please enter your ACRN email address and password.');
      return;
    }
    setBusy(true);
    setErrorMsg('');
    try {
      onLoginSuccess(await login(email, password));
    } catch (err) {
      setErrorMsg(err.message || 'Invalid email or password.');
    } finally {
      setBusy(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '12px 14px',
    fontSize: '14px',
    borderRadius: '6px',
    border: '1px solid #dbeafe',
    backgroundColor: '#edf4ff',
    color: '#0f172a',
    outline: 'none',
    boxSizing: 'border-box',
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#f1f5f9', fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif', padding: '20px' }}>
      <div style={{ width: '100%', maxWidth: '460px', backgroundColor: '#ffffff', borderRadius: '8px', boxShadow: '0 10px 25px -5px rgba(0,0,0,.08), 0 8px 10px -6px rgba(0,0,0,.04)', overflow: 'hidden', borderTop: '4px solid #0f172a' }}>
        <div style={{ padding: '40px 44px 36px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
            <img src="/acrn-logo.png" alt="ACRN Logo" style={{ height: '52px', width: 'auto', objectFit: 'contain' }} />
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ background: '#fff7ed', border: '1px solid #fdba74', borderLeft: '3px solid #F07E26', padding: '12px 14px', borderRadius: '6px', fontSize: '12px', marginBottom: '18px', color: '#7c2d12' }}>
              <div style={{ fontWeight: 700, marginBottom: '6px' }}>Select Demo Account / Role:</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => { setEmail('adjudicatora@acrnhealth.com'); setPassword('ACRN@2026'); }}
                  style={{
                    flex: '1', padding: '6px 10px', fontSize: '11px', fontWeight: 600,
                    borderRadius: '4px', border: email === 'adjudicatora@acrnhealth.com' ? '2px solid #ea580c' : '1px solid #fdba74',
                    background: email === 'adjudicatora@acrnhealth.com' ? '#ffedd5' : '#ffffff',
                    color: '#9a3412', cursor: 'pointer', textAlign: 'center'
                  }}
                >
                  ⚕️ Adjudicator
                </button>
                <button
                  type="button"
                  onClick={() => { setEmail('monitor1@acrnhealth.com'); setPassword('ACRN@2026'); }}
                  style={{
                    flex: '1', padding: '6px 10px', fontSize: '11px', fontWeight: 600,
                    borderRadius: '4px', border: email === 'monitor1@acrnhealth.com' ? '2px solid #ea580c' : '1px solid #fdba74',
                    background: email === 'monitor1@acrnhealth.com' ? '#ffedd5' : '#ffffff',
                    color: '#9a3412', cursor: 'pointer', textAlign: 'center'
                  }}
                >
                  📋 Monitor / QC
                </button>
                <button
                  type="button"
                  onClick={() => { setEmail('admin@acrnhealth.com'); setPassword('ACRN@2026'); }}
                  style={{
                    flex: '1', padding: '6px 10px', fontSize: '11px', fontWeight: 600,
                    borderRadius: '4px', border: email === 'admin@acrnhealth.com' ? '2px solid #ea580c' : '1px solid #fdba74',
                    background: email === 'admin@acrnhealth.com' ? '#ffedd5' : '#ffffff',
                    color: '#9a3412', cursor: 'pointer', textAlign: 'center'
                  }}
                >
                  🔑 Admin
                </button>
              </div>
              <div style={{ fontSize: '11px', marginTop: '8px', color: '#9a3412' }}>
                Shared Demo Password: <code>ACRN@2026</code>
              </div>
            </div>

            {errorMsg && (
              <div style={{ background: '#fef2f2', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginBottom: '18px' }}>
                {errorMsg}
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                ACRN Email Address
              </label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} autoComplete="username" required />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                Password
              </label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={inputStyle} autoComplete="current-password" required />
            </div>

            <button type="submit" disabled={busy} style={{ width: '100%', padding: '14px', fontSize: '15px', fontWeight: 700, color: '#ffffff', backgroundColor: busy ? '#94a3b8' : '#ea580c', border: 'none', borderRadius: '6px', cursor: busy ? 'wait' : 'pointer' }}>
              {busy ? 'Checking account...' : 'Access Portal'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <button type="button" onClick={() => alert('Access request form: Please contact the ACRN Adjudication Portal Administrator at admin@acrnhealth.com.')} style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}>
              Request access
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
