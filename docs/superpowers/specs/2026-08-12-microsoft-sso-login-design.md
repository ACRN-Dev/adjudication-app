# ACRN Adjudication Platform — Microsoft SSO Login Design

**Date:** 2026-08-12
**Status:** Approved (pending written-spec review)
**Scope:** Add Microsoft Entra ID (Azure AD) single sign-on as the login mechanism for the real dev/prod servers, close the header-based authorization gap it would otherwise leave open in the Admin and Monitor portals, and document the Azure setup. No unrelated feature/UI work.

## 1. Goal

Every user on the real ACRN dev/prod deployments must authenticate via the organization's Microsoft Entra ID tenant before reaching any portal. Demo/local testing keeps working exactly as it does today (`ENABLE_DEMO_ACCOUNTS=true`), so nothing changes for offline development.

Today, SSO would only secure the front door: the Admin and Monitor portals authorize their API calls from client-supplied `X-Demo-Role`/`X-Study-Scope` headers rather than the actual session, so anyone able to craft requests could bypass a login screen entirely. This design closes that gap as part of the same change — otherwise Microsoft SSO would be cosmetic for those two portals.

## 2. Decisions (locked with user)

| Topic | Decision |
|---|---|
| Demo accounts | Keep working when `ENABLE_DEMO_ACCOUNTS=true` (local/offline dev). When `false` (real dev/prod servers), only Microsoft SSO can establish a session. |
| Role mapping | No Entra App Roles or Security Groups. An Admin pre-provisions each user's work email + role in the existing `PortalUser` table via the Admin portal. On first Microsoft login we match the verified email from the token to that record. Unregistered emails are rejected — no auto-provisioning (no JIT). |
| OAuth flow | Backend-driven Authorization Code flow via the `msal` Python library (confidential client). The whole browser redirects to Microsoft and back; the client secret and tokens never reach the browser. No new frontend auth library. |
| Admin/Monitor authorization gap | Closed as part of this work. Both portals stop trusting `X-Demo-Role`/`X-Study-Scope`/`X-Demo-User` as authoritative and instead derive identity from the validated session, same as `/auth/me` does today. Headers remain a fallback only when `ENABLE_DEMO_ACCOUNTS=true` and no valid session cookie is present (keeps local/offline testing and existing header-based tests working); ignored entirely otherwise. |
| Azure app registration | Not yet created — this design's deliverables include a step-by-step setup guide. Recommend **separate App Registrations for dev and prod** (matches the project's existing pattern of full dev/prod isolation — separate servers, databases, secrets); a single shared registration with two redirect URIs is a valid alternative if preferred later. |
| Study scope storage | Does not exist server-side today (frontend either hardcodes or omits it). Added as a new `study_scope` column on `PortalUser` (comma-separated study codes, or `"*"` for all), since Admin/Monitor can no longer take it from a header. |

## 3. Login flow

```
Browser                          Backend (FastAPI)                    Microsoft Entra ID
   |                                     |                                     |
   |-- GET / (login page) -------------->|                                     |
   |<-- "Sign in with Microsoft" --------|                                     |
   |                                     |                                     |
   |-- click button -------------------->|                                     |
   |<-- 302 to Microsoft, sets state ----|                                     |
   |------------------------------------------------------------------------->|
   |                                     |               user authenticates    |
   |<-------------------------------------------------------------------------|
   |-- GET /auth/sso/callback?code&state>|                                     |
   |                                     |-- exchange code for tokens -------->|
   |                                     |<-- ID token (email, name, verified)-|
   |                                     |                                     |
   |                              lookup PortalUser by email                  |
   |                              found+active? -> issue AuthSession + cookie |
   |                              not found?    -> redirect with clear error  |
   |                                     |                                     |
   |<-- 302 to portal landing, Set-Cookie|                                     |
```

`state` is a random value set in a short-lived cookie before the redirect and checked on callback — mismatch is rejected (400) and logged to `AuthAuditEvent` as a possible CSRF attempt. MSAL validates the ID token's signature, issuer, audience, and expiry against Microsoft's published keys automatically; the backend never needs to implement JWT verification by hand.

Session issuance on success reuses the existing mechanism exactly: a new `AuthSession` row, a random opaque token, the same httpOnly cookie. (The cookie is currently named `acrn_demo_session` — renamed to `acrn_session` as part of this work, since it's no longer demo-only.)

## 4. Files to create / change

### 4.1 Backend — new SSO endpoints
- `backend/api/auth.py` (or a new `backend/api/sso.py` router mounted alongside it):
  - `GET /auth/sso/login` — builds the Microsoft authorization URL via MSAL's confidential client (`msal.ConfidentialClientApplication`), sets the `state` cookie, redirects.
  - `GET /auth/sso/callback` — validates `state`, calls `acquire_token_by_authorization_code`, extracts `preferred_username`/`email` and `name` from the verified claims, normalizes the email, looks up an active `PortalUser`. Match found → issue session exactly like `services/auth_service.login()` does today (reuse that session-issuance code, just skip the password check). No match → redirect to `/` with an error message.
  - `POST /auth/logout` (existing) unchanged — clears our session only, no Microsoft single-sign-out in this design.

### 4.2 Backend — new dependency
`msal` added to `backend/requirements.txt`.

### 4.3 Backend — data model (`backend/models/auth.py`)
- `PortalUser.password_hash` becomes nullable (SSO-only accounts have none).
- `PortalUser.study_scope` — new `String`, nullable, default `"*"`.

A migration file is added under `backend/migrations/versions/` following the existing convention (the app itself still uses `Base.metadata.create_all`; these files remain additive markers per current practice, unchanged from the Docker deployment design).

### 4.4 Backend — closing the header-trust gap
- `backend/services/admin_security.py` (`get_identity`) and `backend/services/monitor_security.py` (`identity`): resolve `role` and `studies` (from `study_scope`) from the session-backed `PortalUser` first. Only fall back to `X-Demo-*` headers when `ENABLE_DEMO_ACCOUNTS=true` and no valid session cookie is present. When `ENABLE_DEMO_ACCOUNTS=false`, a missing/invalid session is rejected (401) regardless of headers.

### 4.5 Backend — Admin user management
- Existing user-management endpoints in `backend/api/auth.py` gain a `study_scope` field on create/edit, and allow creating a user without a password (SSO-managed).

### 4.6 Frontend
- `src/components/LoginPage.jsx`: always show a "Sign in with Microsoft" button (navigates the browser to `/auth/sso/login`, a plain link/redirect, not a fetch call); keep the existing demo form visible only when `ENABLE_DEMO_ACCOUNTS=true`, surfaced to the frontend via a new unauthenticated `GET /auth/config` endpoint returning `{"demo_enabled": bool}`.
- `src/admin/AdminPortal.jsx` / `src/monitor/MonitorPortal.jsx`: stop sending hardcoded `X-Demo-Role`/`X-Study-Scope` headers — the session cookie (already sent via `credentials: 'include'`) is now sufficient and authoritative.

### 4.7 Configuration
New vars in `.env.dev.example` / `.env.prod.example` (real values only in the git-ignored `.env.dev`/`.env.prod`):
- `ENTRA_TENANT_ID`
- `ENTRA_CLIENT_ID`
- `ENTRA_CLIENT_SECRET`
- `APP_BASE_URL` — the environment's own public HTTPS URL (e.g. `https://adjudication-dev.acrncloud.com`), used to construct the OAuth redirect URI. Does not exist today; small, necessary addition.

### 4.8 Documentation
- New `docs/entra-sso-setup.md`: step-by-step Azure Portal walkthrough (App Registration, redirect URIs, client secret, minimal API permissions) — see Section 5 below for the content.
- `README.md` env-var table gains the four new vars; login section updated to describe SSO as the real dev/prod login path and demo accounts as the local-only fallback.

## 5. Azure App Registration setup (reference — same content ships in `docs/entra-sso-setup.md`)

Repeat per environment (recommended: one App Registration each for Dev and Prod).

1. [portal.azure.com](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **+ New registration**.
2. Name: e.g. "ACRN Adjudication Platform (Dev)" / "(Prod)".
3. Supported account types: **Accounts in this organizational directory only (Single tenant)**.
4. Redirect URI — platform **Web**:
   - Prod: `https://adjudication.acrncloud.com/auth/sso/callback`
   - Dev: `https://adjudication-dev.acrncloud.com/auth/sso/callback`
5. **Register.**
6. From **Overview**, record **Application (client) ID** → `ENTRA_CLIENT_ID`, and **Directory (tenant) ID** → `ENTRA_TENANT_ID`.
7. **Certificates & secrets** → **+ New client secret** → set an expiry → **Add** → copy the secret **Value** immediately (shown once) → `ENTRA_CLIENT_SECRET`, typed straight into the server's `.env.dev`/`.env.prod`, never committed or pasted elsewhere.
8. **API permissions**: default **Microsoft Graph → User.Read** is sufficient (only `openid`/`profile`/`email` claims are needed); no admin consent required.
9. Leave **Front-channel logout URL** blank (no Microsoft single-sign-out in this design).
10. No changes needed under "Implicit grant and hybrid flows" — not used by this flow.

## 6. Testing

- SSO callback: mock `ConfidentialClientApplication.acquire_token_by_authorization_code` to return fixed claims; test the match/session-issuance path and the unregistered-email rejection path without any network call.
- `state` mismatch: test returns 400 and writes an `AuthAuditEvent` row.
- Admin/Monitor authorization: rewrite tests that currently authenticate via raw `X-Demo-Role`/`X-Study-Scope` headers to log in through a real session first; add a test proving that headers alone, with `ENABLE_DEMO_ACCOUNTS=false` and no session, are rejected (401).
- Manual end-to-end verification against a real Entra tenant happens once the App Registration exists (Section 5) and `.env.dev` is populated — covered in the implementation plan's verification steps, not automatable in CI.

## 7. Error handling

| Case | Behavior |
|---|---|
| Email not found / inactive `PortalUser` | Redirect to `/` with "Your account isn't registered. Contact your administrator to be added." No account is created. |
| User cancels on Microsoft's side, or wrong tenant | Redirect to `/` with a generic friendly message. |
| `state` mismatch | 400, logged to `AuthAuditEvent` as a possible CSRF attempt. |
| Token/signature validation failure | Rejected by MSAL before our code runs; surfaced as a generic login error, logged. |

## 8. Out of scope (YAGNI)

- Entra App Roles / Security Groups for role mapping (explicitly rejected in favor of Admin pre-provisioning).
- JIT (just-in-time) auto-provisioning of unknown users.
- Microsoft single sign-out / front-channel logout.
- MFA / step-up authentication for e-signature (a separately documented production-hardening item; this design only covers login).
- Frontend MSAL.js / token-in-browser flow.
- Any change to the Adjudicator portal's authorization model (it already uses the session correctly; only Admin/Monitor had the header-trust gap).
