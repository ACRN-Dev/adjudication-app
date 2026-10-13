import React, { useEffect, useState } from 'react';
import { SSO_LOGIN_URL, getAuthConfig, login } from '../services/authApi';

const DEMO_ACCOUNTS = [
  { label: 'Admin', email: 'admin@acrnhealth.com', badge: '🔑', desc: 'System Administration' },
  { label: 'Owner', email: 'tariro@acrnhealth.com', badge: '👑', desc: 'Study Owner' },
  { label: 'Monitor', email: 'monitor1@acrnhealth.com', badge: '📋', desc: 'Clinical QC & Monitor' },
  { label: 'Medical Officer', email: 'medical.officer@acrnhealth.com', badge: '🩺', desc: 'Safety & Protocol' },
  { label: 'Medical Monitor', email: 'medical.monitor@acrnhealth.com', badge: '🩺', desc: 'Medical Oversight' },
  { label: 'Chair', email: 'chairperson@acrnhealth.com', badge: '🏛️', desc: 'Committee Chairperson' },
  { label: 'Adjudicator A', email: 'adjudicatora@acrnhealth.com', badge: '⚕️', desc: 'Primary Reviewer A' },
  { label: 'Adjudicator B', email: 'adjudicatorb@acrnhealth.com', badge: '⚕️', desc: 'Primary Reviewer B' },
  { label: 'Reviewer C', email: 'adjudicatorc@acrnhealth.com', badge: '⚖️', desc: 'Tiebreaker Reviewer C' },
];

export default function LoginPage({ onLoginSuccess }) {
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(true);
  const [email, setEmail] = useState('admin@acrnhealth.com');
  const [password, setPassword] = useState('ACRN@2026');

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
    const isLocalhost = typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname.endsWith('.local')
    );

    getAuthConfig()
      .then(config => {
        if (active) {
          // Always keep demo panel active on local development, or if backend reports demo_enabled !== false
          const isDemo = isLocalhost || Boolean(config?.demo_enabled);
          setDemoEnabled(isDemo);
          if (isDemo && !email) {
            setEmail('admin@acrnhealth.com');
            setPassword('ACRN@2026');
          }
        }
      })
      .catch(() => {
        if (active) {
          setDemoEnabled(true);
          if (!email) {
            setEmail('admin@acrnhealth.com');
            setPassword('ACRN@2026');
          }
        }
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

  const loadDemoCredentials = (account = DEMO_ACCOUNTS[0]) => {
    setEmail(account.email);
    setPassword('ACRN@2026');
    setErrorMsg('');
  };

  const signInDemo = async (account) => {
    setBusy(true);
    setErrorMsg('');
    try {
      setEmail(account.email);
      setPassword('ACRN@2026');
      onLoginSuccess(await login(account.email, 'ACRN@2026'));
    } catch (err) {
      setErrorMsg(err.message || 'Demo sign-in failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#f1f5f9', fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif', padding: '20px' }}>
      <div style={{ width: '100%', maxWidth: '480px', backgroundColor: '#ffffff', borderRadius: '10px', boxShadow: '0 10px 25px -5px rgba(0,0,0,.08), 0 8px 10px -6px rgba(0,0,0,.04)', overflow: 'hidden', borderTop: '4px solid #F07E26' }}>
        <div style={{ padding: '32px 36px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
            <img src="/acrn-logo.png" alt="ACRN Logo" style={{ height: '50px', width: 'auto', objectFit: 'contain' }} />
          </div>

          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', margin: '0 0 4px' }}>ACRN Adjudication Platform</h1>
            <p style={{ fontSize: '13px', color: '#64748b', margin: 0 }}>Sign in to access your clinical adjudication portal</p>
          </div>

          {/* Quick Access Demo Accounts Panel */}
          {demoEnabled && (
            <div style={{
              backgroundColor: '#fff7ed',
              border: '1px solid #fed7aa',
              borderLeft: '4px solid #F07E26',
              borderRadius: '8px',
              padding: '12px 14px',
              marginBottom: '20px',
              boxShadow: '0 1px 3px rgba(240, 126, 38, 0.08)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '13px' }}>⚡</span>
                  <strong style={{ fontSize: '11px', color: '#9a3412', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Quick Access Demo Accounts
                  </strong>
                </div>
                <span style={{ fontSize: '10px', color: '#c2410c', background: '#ffedd5', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                  1-CLICK LOGIN
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginBottom: '10px' }}>
                {DEMO_ACCOUNTS.map((account) => {
                  const isSelected = email === account.email;
                  return (
                    <button
                      key={account.email}
                      type="button"
                      onClick={() => signInDemo(account)}
                      title={`Instant login as ${account.label} (${account.email})`}
                      disabled={busy}
                      style={{
                        padding: '7px 6px',
                        fontSize: '11px',
                        fontWeight: isSelected ? 700 : 600,
                        borderRadius: '5px',
                        border: isSelected ? '1.5px solid #ea580c' : '1px solid #fdba74',
                        backgroundColor: isSelected ? '#ffedd5' : '#ffffff',
                        color: isSelected ? '#9a3412' : '#7c2d12',
                        cursor: busy ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px',
                        transition: 'all 0.15s ease-in-out',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}
                    >
                      <span style={{ fontSize: '12px' }}>{account.badge}</span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{account.label}</span>
                    </button>
                  );
                })}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10.5px', color: '#9a3412', borderTop: '1px dashed #fdba74', paddingTop: '6px' }}>
                <span>Shared Demo Password: <code style={{ backgroundColor: '#ffedd5', padding: '1px 5px', borderRadius: '3px', fontWeight: 700, color: '#c2410c' }}>ACRN@2026</code></span>
                <button
                  type="button"
                  onClick={() => loadDemoCredentials()}
                  style={{ background: 'none', border: 'none', color: '#ea580c', fontWeight: 600, cursor: 'pointer', padding: 0, textDecoration: 'underline', fontSize: '10.5px' }}
                >
                  Fill Form Only
                </button>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => { window.location.href = SSO_LOGIN_URL; }}
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '13.5px',
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
            <svg width="17" height="17" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 0H0V10H10V0Z" fill="#F25022"/>
              <path d="M21 0H11V10H21V0Z" fill="#7FBA00"/>
              <path d="M10 11H0V21H10V11Z" fill="#00A4EF"/>
              <path d="M21 11H11V21H21V11Z" fill="#FFB900"/>
            </svg>
            Sign in with Microsoft
          </button>

          <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0 16px', gap: '12px' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#e2e8f0' }}></div>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.05em' }}>OR SIGN IN WITH CREDENTIALS</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#e2e8f0' }}></div>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '12px' }}>
            <div>
              <label htmlFor="user-email" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '5px' }}>Email Address</label>
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
              <label htmlFor="user-password" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '5px' }}>Password</label>
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
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginTop: '14px', lineHeight: '1.4' }}>
              {errorMsg}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

