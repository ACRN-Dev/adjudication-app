# ACRN portal button and control reference

This guide describes the interactive controls available in standalone demonstration mode. Demo actions use synthetic records, show confirmations or status messages, and may download clearly named `*-DEMO.csv` files. They do not represent Microsoft Entra authentication or connected production systems.

## Common Admin Portal controls

| Control | Function in demo mode | Production control |
|---|---|---|
| ACRN Admin navigation items | Opens the corresponding `/admin/...` register without reloading the application. | The backend independently checks role and study scope for every API request. |
| Collapse/expand navigation | Changes the full navigation into an icon rail and restores it. | Device-local display preference only. |
| Admin breadcrumb | Returns to the Admin Dashboard. | No change to records. |
| Sign out icon | Ends the current demo session and returns to sign-in. | Entra logout and token/session revocation. |
| Search field | Filters the visible table immediately across all displayed values. | Server-side indexed search for large registers. |
| Status filter | Limits tables to rows containing Active, Pending, Draft or Warning status. | Server-side validated filter parameters. |
| Clear filters | Removes search text and status filtering. | No audit required because it changes only the view. |
| New controlled draft / Create draft record | Requests confirmation and a required reason, then confirms creation of a demo successor draft. | Permission check, study-scope check, version creation and immutable audit event. Active records are never edited in place. |
| Export register | Downloads the current synthetic register as a CSV file with `DEMO` in the filename. | Controlled export permission, study scoping, export audit event and approved destination. |

## Dashboard

| Control | Function |
|---|---|
| Metric tiles | Opens the relevant register: studies, sites, users, training, access reviews or integrations. |
| Approve pending user access | Opens Users so an authorised administrator can review the request. |
| Review expiring access | Opens Access Reviews for confirmation, modification or revocation. |
| Review incomplete training | Opens Training and COI. |
| Resolve integration warnings | Opens Integrations. |

## Users

| Control | Function |
|---|---|
| Invite user | Prompts for a demo email/UPN and prepares a pending invitation. Production requires Entra identity resolution, training and independent approval. |
| Export access register | Downloads all synthetic user-access rows as CSV. |
| View | Displays the selected user's identity, role and delegated study scope. |
| Review | Requires confirmation and a reason and records a simulated access-review action. |
| Suspend | Requires confirmation and a reason and simulates account suspension. It never deletes the user. |

Self-approval is prohibited. Administrators cannot grant permissions they do not hold. Suspension, reinstatement, deactivation, role assignment, study access and expiry changes are server-audited in production.

## Roles and Permissions

| Control | Function |
|---|---|
| Draft custom role | Creates a simulated successor role draft after confirmation and reason entry. |

The permission matrix is read-only. High-risk combinations are blocked or flagged, including Technical Administrator plus Adjudicator, Monitor/QC plus independent reviewer, reviewer plus release approver, user administrator plus self-approver, and committee membership plus incompatible operational access.

## Studies and Sites

| Control | Function |
|---|---|
| New controlled draft | Simulates creation of a new study or site configuration draft. Active study configuration is never edited in place. |
| Export register | Downloads the synthetic study or site register. |

Only a site's approved blinded display name is supplied to adjudicators. Operational site identity remains an administrative concern.

## DV Rule Versions

| Control | Function |
|---|---|
| New controlled draft | Starts a successor DV-rule draft and requests a change reason. |
| Compare versions | Opens a demo explanation of version comparison. |
| Export register | Downloads the DV-01–DV-30 register. |

Activation is blocked unless regression/synthetic tests pass and clinical plus QA approval exists. Active rules are immutable, and arbitrary browser-entered executable code is prohibited. The Python DV engine remains authoritative.

## Canonical Field Mappings

| Control | Function |
|---|---|
| New controlled draft | Starts a successor mapping version. |
| Test sample CSV | Runs a synthetic mapping validation message. |
| Export register | Downloads the mapping specification. |

The backend permanently rejects mappings involving sFlt-1, PlGF, sEng, biomarker results, POC results, treatment allocation or configured unblinding fields.

## Forms and Templates

| Control | Function |
|---|---|
| New controlled draft | Starts a versioned form/template draft. |
| Export register | Downloads the controlled form register. |

Forms already used by a case cannot be overwritten.

## Workflow Configuration

| Control | Function |
|---|---|
| New workflow draft | Requests confirmation and reason for a successor workflow version. |

Activation validation prevents import-to-adjudication shortcuts, release before Final QC, modification after lock and uncontrolled reopening.

## Integrations

| Control | Function |
|---|---|
| New controlled draft | Starts a new configuration version without exposing credentials. |
| Test connection | Returns a synthetic successful or warning result based on the displayed integration state. |
| Export register | Downloads integration status metadata only. |

Production credentials must remain in an approved secret store and are never displayed or embedded in frontend code.

## Audit Trail

| Control | Function |
|---|---|
| Controlled export | Downloads synthetic immutable audit events as CSV. |
| Search/status/clear filters | Filters the visible audit rows without changing audit history. |

There are intentionally no edit or delete buttons for audit events.

## Access Reviews

| Control | Function |
|---|---|
| Generate campaign | Requests confirmation and reason for a new demonstration campaign. |

A production campaign selects portal/study scope, assigns an independent reviewer, records confirm/modify/revoke decisions, locks the completed campaign and exports evidence.

## Reports

Each report tile downloads a small, scoped demonstration CSV identifying the report, environment, scope and generation time. Available reports are user access, role permissions, study configuration, active rules, active mappings, forms/templates, access reviews, training compliance, configuration changes, integration incidents, import failures and audit summary.

## Generic controlled registers

Training and COI, Endpoints and Windows, Units and Terminology, Clinical Dictionaries, Import Contracts, SOP References, and Environment and Health contain a **Create draft record** button. In demo mode it requires confirmation and a reason. Production activation depends on approved governance ownership and source contracts.

## Adjudicator Portal buttons

The existing adjudicator controls remain functional and separate from administration:

| Control | Function |
|---|---|
| Access Portal | Signs into the selected demo role-specific portal. |
| Request access | Displays the ACRN administrator contact route. |
| Subject Queue / eSource Evidence / Approve and Sign / Locked eTMF | Navigates the four adjudication steps; the locked record is enabled only after signing. |
| Committee Review | Opens the discordance and committee-consensus screen. |
| QC Portal and Gates | Opens evidence/QC review. |
| SOP Library / User Guide | Opens controlled SOP reference content or help guidance. |
| Load demonstration subjects / sample data | Loads synthetic blinded case records into the queue. |
| Subject or recent-subject selection | Selects the active blinded case. |
| Search | Selects a matching loaded subject or case number. |
| Review eSource / View source documents | Opens the blinded source-document viewer and its Ultrasound, LIMS, Vitals and Delivery tabs. |
| Previous / Next | Moves between workflow steps without changing a signed decision. |
| Recuse | Opens FORM-ADJ-08 and records a reasoned recusal before rerouting. |
| Raise data query | Opens the query form and submits a simulated coordinator-reviewed query. |
| Regenerate narrative | Regenerates the editable blinded narrative from current synthetic evidence. |
| Approve and sign | Opens electronic-signature confirmation and locks the demo determination after submission. |
| Resend OTP | Simulates sending a new step-up authentication code; production will use Entra ID and will not expose the code in the browser. |
| Download PDF | Requests the case PDF export from the backend. |
| Next case | Selects the next unsigned case. |
| Adopt Reviewer A / Reviewer B | Selects the committee outcome to adopt. |
| Sign and lock final committee classification | Requires the committee rationale and locks the selected consensus outcome. |
| Close / Cancel buttons | Closes the current modal without saving the proposed action. |

Administrators do not receive these clinical-decision controls merely because they can access the Admin Portal.
