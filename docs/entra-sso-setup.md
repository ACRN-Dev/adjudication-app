# Microsoft Entra ID SSO Setup

Do this once per environment (Dev and Prod each get their own App Registration, matching how this project already keeps dev/prod fully isolated).

**Callback URLs to register:**
- Prod: `https://adjudication.acrncloud.com/api/auth/sso/callback`
- Dev: `https://adjudication-dev.acrncloud.com/api/auth/sso/callback`

## Steps in the Azure Portal (repeat per environment)

1. Go to [portal.azure.com](https://portal.azure.com) -> **Microsoft Entra ID** -> **App registrations** -> **+ New registration**.
2. Name it something identifiable, e.g. "ACRN Adjudication Platform (Dev)" / "(Prod)".
3. Supported account types: **Accounts in this organizational directory only (Single tenant)**.
4. Redirect URI - platform **Web**, value = the callback URL above for that environment.
5. Click **Register**.
6. From the **Overview** page, record:
   - **Application (client) ID** -> `ENTRA_CLIENT_ID`
   - **Directory (tenant) ID** -> `ENTRA_TENANT_ID`
7. **Certificates & secrets** -> **+ New client secret** -> set an expiry -> **Add** -> copy the secret's **Value** immediately (shown once) -> `ENTRA_CLIENT_SECRET`. Type this directly into the server's `.env.dev`/`.env.prod` file — never commit it.
8. **API permissions**: the default **Microsoft Graph -> User.Read** (delegated) permission is already sufficient — no admin consent required.
9. Leave **Authentication -> Front-channel logout URL** blank.
10. No changes are needed under "Implicit grant and hybrid flows" for this flow.

## After registration

On the server, fill in `.env.dev` (or `.env.prod`):

```
ENTRA_TENANT_ID=<Directory (tenant) ID from step 6>
ENTRA_CLIENT_ID=<Application (client) ID from step 6>
ENTRA_CLIENT_SECRET=<secret value from step 7>
APP_BASE_URL=https://adjudication-dev.acrncloud.com   # or the prod URL on the prod server
```

Then redeploy (`./scripts/deploy-dev.sh` or `./scripts/deploy-prod.sh`).

**Before the first deploy after this feature ships**, run the schema migration against that server's Postgres database (this does not happen automatically):

```
psql "$DATABASE_URL" -f backend/migrations/versions/20260812_05_sso_login.sql
```

## Provisioning a user

Microsoft SSO only lets in users who already have a `PortalUser` record. An Admin creates one via the Admin portal's user management (`POST /api/auth/users`), specifying:
- `email` — must exactly match the user's Microsoft work account email.
- `role` — `ADMIN`, `MONITOR`, or `ADJUDICATOR`.
- `portal_role` — required for `ADMIN`/`MONITOR` accounts (e.g. `TECHNICAL_ADMIN`, `MONITOR_QC_REVIEWER`); leave unset for `ADJUDICATOR`.
- `study_scope` — comma-separated study codes, or `*` for all studies (default).

No password is set — the account authenticates purely through Microsoft.
