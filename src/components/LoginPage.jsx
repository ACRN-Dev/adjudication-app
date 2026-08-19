import React, { useEffect, useState } from 'react';
import { SSO_LOGIN_URL } from '../services/authApi';

export default function LoginPage({ onLoginSuccess }) {
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ssoError = params.get('sso_error');
    if (ssoError) {
      const messages = {
        not_registered: "Your account isn't registered. Contact your administrator to be added.",
        account_inactive: 'Your account has been deactivated. Contact your administrator.',
        cancelled: 'Microsoft sign-in was cancelled.',
        auth_failed: 'Microsoft sign-in failed. Please try again.',
        not_configured: 'Microsoft sign-in is not yet configured for this environment. Please contact your administrator.',
      };
      setErrorMsg(messages[ssoError] || 'Microsoft sign-in failed. Please try again.');
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

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

          <button
            type="button"
            onClick={() => { window.location.href = SSO_LOGIN_URL; }}
            style={{ width: '100%', padding: '14px', fontSize: '15px', fontWeight: 700, color: '#ffffff', backgroundColor: '#0f172a', border: 'none', borderRadius: '6px', cursor: 'pointer', marginBottom: '20px' }}
          >
            Sign in with Microsoft
          </button>

          {errorMsg && (
            <div style={{ background: '#fef2f2', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginTop: '18px' }}>
              {errorMsg}
            </div>
          )}

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
