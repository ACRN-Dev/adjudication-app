import React, { useEffect, useState } from 'react';
import { SSO_LOGIN_URL, getAuthConfig, login } from '../services/authApi';

export default function LoginPage({ onLoginSuccess }) {
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

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

    let active = true;
    getAuthConfig()
      .then(config => {
        if (active) {
          const isDemo = Boolean(config?.demo_enabled);
          setDemoEnabled(isDemo);
          if (isDemo && !email) {
            setEmail('admin@acrnhealth.com');
            setPassword('ACRN@2026');
          }
        }
      })
      .catch(() => {
        if (active) setDemoEnabled(true);
      });

    return () => { active = false; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg('Please enter your email address and password.');
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
    border: '1px solid #cbd5e1',
    backgroundColor: '#f8fafc',
    color: '#0f172a',
    outline: 'none',
    boxSizing: 'border-box',
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#f1f5f9', fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif', padding: '20px' }}>
      <div style={{ width: '100%', maxWidth: '460px', backgroundColor: '#ffffff', borderRadius: '8px', boxShadow: '0 10px 25px -5px rgba(0,0,0,.08), 0 8px 10px -6px rgba(0,0,0,.04)', overflow: 'hidden', borderTop: '4px solid #0f172a' }}>
        <div style={{ padding: '36px 40px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '28px' }}>
            <img src="/acrn-logo.png" alt="ACRN Logo" style={{ height: '52px', width: 'auto', objectFit: 'contain' }} />
          </div>

          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>ACRN Adjudication Platform</h1>
            <p style={{ fontSize: '13px', color: '#64748b', margin: 0 }}>Sign in to access your clinical adjudication portal</p>
          </div>

          <button
            type="button"
            onClick={() => { window.location.href = SSO_LOGIN_URL; }}
            style={{
              width: '100%',
              padding: '13px',
              fontSize: '14px',
              fontWeight: 600,
              color: '#ffffff',
              backgroundColor: '#0f172a',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              transition: 'background-color 0.2s',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 0H0V10H10V0Z" fill="#F25022"/>
              <path d="M21 0H11V10H21V0Z" fill="#7FBA00"/>
              <path d="M10 11H0V21H10V11Z" fill="#00A4EF"/>
              <path d="M21 11H11V21H21V11Z" fill="#FFB900"/>
            </svg>
            Sign in with Microsoft
          </button>

          <div style={{ display: 'flex', alignItems: 'center', margin: '24px 0 20px', gap: '12px' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#e2e8f0' }}></div>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.05em' }}>OR SIGN IN WITH CREDENTIALS</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#e2e8f0' }}></div>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '14px' }}>
            <div>
              <label htmlFor="user-email" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Email Address</label>
              <input
                id="user-email"
                type="email"
                placeholder="name@acrnhealth.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="user-password" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Password</label>
              <input
                id="user-password"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              disabled={busy}
              style={{
                width: '100%',
                padding: '12px',
                fontSize: '14px',
                fontWeight: 700,
                color: '#ffffff',
                backgroundColor: busy ? '#64748b' : '#2563eb',
                border: 'none',
                borderRadius: '6px',
                cursor: busy ? 'not-allowed' : 'pointer',
                marginTop: '4px',
              }}
            >
              {busy ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {errorMsg && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginTop: '16px', lineHeight: '1.4' }}>
              {errorMsg}
            </div>
          )}

          {demoEnabled && (
            <div style={{ marginTop: '20px', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px dashed #cbd5e1', fontSize: '11px', color: '#64748b', textAlign: 'center' }}>
              <strong>Demo Environment Active:</strong> Default demo accounts seeded for testing.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

