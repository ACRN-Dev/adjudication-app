const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
  } catch {
    throw new Error('The backend API is unavailable. Start it on port 8000 and try again.');
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}) at ${BASE}${path}`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((item) => item.msg || item.message || item.detail).filter(Boolean).join(' ') || detail;
      } else {
        detail = body.detail?.message || body.message || detail;
      }
    } catch {
      try {
        const text = await res.text();
        if (text) detail = `${detail}: ${text.slice(0, 180)}`;
      } catch {}
    }
    throw new Error(detail);
  }
  return res.json();
}

export const login = (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
export const logout = () => request('/auth/logout', { method: 'POST', body: '{}' });
export const me = () => request('/auth/me');
export const changePassword = (currentPassword, newPassword) => request('/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
export const listUsers = (params = {}) => request(`/auth/users?${new URLSearchParams(params)}`);
export const setUserStatus = (id, status, reason) => request(`/auth/users/${id}/status`, { method: 'POST', body: JSON.stringify({ status, reason }) });
export const unlockUser = (id, reason) => request(`/auth/users/${id}/unlock`, { method: 'POST', body: JSON.stringify({ reason }) });
export const resetDemoPassword = (id, reason) => request(`/auth/users/${id}/reset-password`, { method: 'POST', body: JSON.stringify({ reason }) });
export const setUserRole = (id, role, reason) => request(`/auth/users/${id}/role`, { method: 'POST', body: JSON.stringify({ role, reason }) });
export const setPortalRole = (id, portal_role, reason) => request(`/auth/users/${id}/portal-role`, { method: 'POST', body: JSON.stringify({ portal_role, reason }) });
export const createUser = (data) => request('/auth/users', { method: 'POST', body: JSON.stringify(data) });
export const getAuthConfig = () => request('/auth/config');
export const SSO_LOGIN_URL = `${BASE}/auth/sso/login`;

