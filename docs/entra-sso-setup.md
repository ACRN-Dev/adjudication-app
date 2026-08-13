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

Then redeploy: `./scripts/init-prod.sh` on prod, `./scripts/deploy-dev.sh` on dev.

**On prod**, `init-prod.sh` applies the schema migrations for you — nothing else to do.

**On dev**, `deploy-dev.sh` does not run migrations, so before the first deploy after this feature ships, apply the SSO migration by hand against the dev database:

```
psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=$DB_SSL_MODE" \
  -f backend/migrations/versions/20260812_05_sso_login.sql
```

This backfills every existing ADMIN account to the broad `ADMIN` sub-role and every existing MONITOR account to `MONITOR_QC_REVIEWER`, so nobody is locked out on redeploy — review and narrow individual accounts' sub-roles afterward via the Admin portal's user management screen if needed.

## How accounts are created

**Anyone in the Entra tenant can sign in.** The App Registration is single-tenant, so obtaining a token already proves an ACRN work account. On a first successful Microsoft sign-in with no matching `PortalUser`, one is created automatically:

- `role` = `ADJUDICATOR`, `portal_role` = none, `study_scope` = `*`, `status` = `ACTIVE`
- no local password — the account authenticates purely through Microsoft
- audited as `SSO_USER_AUTO_PROVISIONED`

A new adjudicator account reaches only the adjudication workbench, which lists nothing until an Admin explicitly assigns cases to it. An Admin then raises or narrows the account from the Admin portal's user management screen.

Two accounts are never auto-created this way: one that already exists keeps whatever role it has (signing in never escalates or resets it), and one an Admin has deactivated stays out — it is redirected with `sso_error=account_inactive` rather than being silently reactivated.

The bootstrap administrators in `BOOTSTRAP_ADMINS` at the top of [../backend/scripts/init_prod.py](../backend/scripts/init_prod.py) are provisioned by `./scripts/init-prod.sh`, since a freshly initialised database would otherwise have no one able to grant roles.

An Admin can also create an account ahead of the person's first sign-in via `POST /api/auth/users`, specifying:
- `email` — must exactly match the user's Microsoft work account email.
- `role` — `ADMIN`, `MONITOR`, or `ADJUDICATOR`.
- `portal_role` — required for `ADMIN`/`MONITOR` accounts (e.g. `TECHNICAL_ADMIN`, `MONITOR_QC_REVIEWER`); leave unset for `ADJUDICATOR`.
- `study_scope` — comma-separated study codes, or `*` for all studies (default).

No password is set — the account authenticates purely through Microsoft.
