# ACRN Demo Accounts

Enable local demo accounts with:

```powershell
$env:ENABLE_DEMO_ACCOUNTS="true"
 .\.venv\Scripts\python.exe backend\scripts\seed_demo_accounts.py
```

Authorized testers may use these fixed demo identities in local demo mode only:

| Email | Role |
|---|---|
| admin@acrnhealth.com | Admin |
| monitor1@acrnhealth.com | Monitor |
| monitor2@acrnhealth.com | Monitor |
| adjudicatora@acrnhealth.com | Adjudicator |
| adjudicatorb@acrnhealth.com | Adjudicator |
| adjudicatorc@acrnhealth.com | Adjudicator |
| adjudicatord@acrnhealth.com | Adjudicator |

The shared local default password is configured by `DEMO_DEFAULT_PASSWORD` and defaults to the value in the implementation brief. It is hashed before storage and must never be used for production accounts.

For hosted or UAT-like environments, set `DEMO_FORCE_PASSWORD_CHANGE=true` and `AUTH_COOKIE_SECURE=true`.
