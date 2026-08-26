import React, { useState } from 'react';
import { changePassword } from '../services/authApi';

// Blocks all portal access until a user replaces a shared/temporary password
// with one only they know (21 CFR Part 11 non-repudiation requirement).
export default function ForceChangePassword({ user, onChanged, onLogout }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    if (!currentPassword || !newPassword || !confirmPassword) {
      setErrorMsg('Please fill in all fields.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMsg('New password and confirmation do not match.');
      return;
    }
    setBusy(true);
    try {
      const updated = await changePassword(currentPassword, newPassword);
      onChanged(updated);
    } catch (err) {
      setErrorMsg(err.message || 'Unable to change password.');
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
      <div style={{ width: '100%', maxWidth: '460px', backgroundColor: '#ffffff', borderRadius: '8px', boxShadow: '0 10px 25px -5px rgba(0,0,0,.08), 0 8px 10px -6px rgba(0,0,0,.04)', overflow: 'hidden', borderTop: '4px solid #b45309' }}>
        <div style={{ padding: '36px 40px' }}>
          <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>Set a New Password</h1>
          <p style={{ fontSize: '13px', color: '#64748b', margin: '0 0 20px' }}>
            {user?.display_name ? `Welcome, ${user.display_name}. ` : ''}
            For security, you must set a password known only to you before you can access the portal.
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '14px' }}>
            <div>
              <label htmlFor="current-password" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Current / Temporary Password</label>
              <input
                id="current-password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                style={inputStyle}
                autoComplete="current-password"
              />
            </div>
            <div>
              <label htmlFor="new-password" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>New Password</label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                style={inputStyle}
                autoComplete="new-password"
              />
            </div>
            <div>
              <label htmlFor="confirm-password" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Confirm New Password</label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                style={inputStyle}
                autoComplete="new-password"
              />
            </div>
            <p style={{ fontSize: '11px', color: '#64748b', margin: 0 }}>
              At least 12 characters, including at least 3 of: lowercase, uppercase, digit, symbol. Must not contain your email or match the shared default password.
            </p>

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
              {busy ? 'Updating...' : 'Set Password & Continue'}
            </button>
          </form>

          {errorMsg && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginTop: '16px', lineHeight: '1.4' }}>
              {errorMsg}
            </div>
          )}

          <button
            type="button"
            onClick={onLogout}
            style={{ marginTop: '18px', background: 'none', border: 'none', color: '#64748b', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline' }}
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
