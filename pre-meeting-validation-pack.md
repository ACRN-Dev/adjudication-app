# Draft pre-meeting validation pack

## Adjudication Portal Session 8 — Final Review & UAT Sign-off

Prepared for Tinotenda Chibongore and Panashe Leif Phiri. Draft only; not a UAT sign-off, implementation clearance, task update, comment, attachment, or request to Tariro.

### Source basis and evidence boundary

Verified records reviewed:

- [Session 8 UAT task](https://app.clickup.com/t/869f1dbw9): status `to do`; two comments; no attachments, subtasks, checklists, linked tasks, or execution results returned by the connected record.
- [Narrative-template task](https://app.clickup.com/t/869f3et6g): status `review/in discussion`; five comments; eight screenshot attachments; no approval artifact or linked evidence returned.
- [Tariro feedback compilation](https://app.clickup.com/90121257130/docs/2kxuag5a-1012492/2kxuag5a-555132): defect tracker records 14 findings, evidence requirements, and unresolved dating/protocol/EOPE-definition questions.
- [Latest blinded case review pack](https://app.clickup.com/90121257130/docs/2kxuag5a-1015632/2kxuag5a-557812): records upload 7 October 2026 14:05, 14 blinded participants, 46,821 source rows, 133 reconstructed visits, mapping `RT-MAP-3.1`, narrative `FORM-ADJ-PROSE-v2.0`, and import status `AUTO_QC_COMPLETE`.
- [15 September portal review notes](https://app.clickup.com/90121257130/docs/2kxuag5a-916032/2kxuag5a-500172) and the Session 8 task comments.

`AUTO_QC_COMPLETE`, `ASSIGNED`, `ACCEPTED_WITH_WARNINGS`, a screenshot, or a generated pack is not treated as executed UAT evidence or clinical approval. Where no execution record was available, status is `not run` or `unable to verify`.

## 1. Findings-response table

The count is verified as 14, not assumed. Findings 1–9 were recorded in Tariro's 1 October review; findings 10–14 in the 6 October review.

| # | Original finding | Required / expected behaviour | Team response or change made | Status | Evidence available | Evidence still required | Proposed owner | Question / decision needed |
|---:|---|---|---|---|---|---|---|---|
| 1 | Ongoing pregnancy rendered as “Nulligravida”. | Map gravidity from the correct source; do not guess. | 7 Oct pack displays G/P values, but mapping proof is not attached. | unable to verify | 7 Oct pack index and case narratives. | Field-to-source mapping, code list, source-row trace and executed test. | Tinotenda | Confirm canonical gravidity field and precedence. |
| 2 | Visit 1 summary claims hypertension/proteinuria not supported by Visit 1 data. | Diagnostic statements must use dated evidence and approved deterministic criteria. | Pack labels Visit 1 evidence and presents BP/protein by visit; no rule execution log. | partly fixed | Pack chronology and per-visit output. | Rule version, inputs, expected/actual comparison, clinical review. | Tinotenda | Does narrative state facts only, leaving adjudication to the reviewer? |
| 3 | Literal placeholder “# - No” for estimated fetal weight passed QC. | Missing data must say unavailable/cannot be determined; placeholders fail QC. | Pack uses explicit unavailable wording in Case 01 and dash convention. | partly fixed | Pack says missing values are not normal/negative/zero. | Negative test execution showing placeholder rejection across cases. | Tinotenda | Exact approved missing-data wording? |
| 4 | 39-week viable-fetus ultrasound appeared in a 4-week postpartum section. | Bind every finding to its actual assessment date/visit; label historical results. | Pack separates V01–V06 and labels postpartum; no full cross-case reconciliation report. | partly fixed | Pack chronology; V06 marked postpartum/GA unavailable. | Executed historical-timepoint test and source-row audit. | Tinotenda | What is the approved dating anchor? |
| 5 | Gestational age was not reconciled across visits. | One approved dating source; deterministic GA calculation; visible discrepancy. | Pack records weeks+days and unresolved source issues, but no approved source is named. | open | Pack states reviewers must confirm dating anchor. | Protocol/charter citation, calculation log, discrepancy output. | Panashe / Tariro decision | Which gestational-age source takes priority? |
| 6 | ALT 47.2 called normal in one place and hepatic dysfunction elsewhere. | Show value, unit, reference interval, date; separate observation from interpretation. | Pack displays laboratory values and source-row markers; the flagged example's exact corrected output is not evidenced. | unable to verify | Laboratory convention and source markers in pack. | Lab-spec reference ranges, exact 47.2 rerun, expected/actual review. | Tinotenda | Which reference-range version applies? |
| 7 | Delivery mode mixed with maternal/neonatal outcomes; “normal” unqualified. | Separate delivery, maternal outcome, neonatal outcome; qualify claims with evidence. | Pack separates delivery and outcome prose in Case 01. | partly fixed | Case 01 V05 presentation. | Full output review against all 14 cases and executed positive/negative tests. | Tinotenda | Is “normal” allowed, and what evidence threshold supports it? |
| 8 | No readable chronological narrative, source references, or unresolved-questions section. | Narrative at top, chronological by visit, source provenance, unresolved questions. | Pack has overall/per-visit narratives, source markers and unresolved issues. | partly fixed | 7 Oct pack structure. | Editable template/prompts, UI evidence, reviewer execution record. | Tinotenda | Confirm acceptance criteria for readability and 10-minute review. |
| 9 | Global “QC passed” label despite contradictions. | QC label only after consistency checks pass; contradictions remain visible. | Pack import status is `AUTO_QC_COMPLETE` while Case 01 is `ACCEPTED_WITH_WARNINGS` and has source conflicts. | open | Pack metadata and warnings. | QC rule definition, failure log, proof that contradictory cases cannot pass. | Tinotenda / Panashe | Should warning cases be blocked from adjudication? |
| 10 | Two participants had identical narrative text. | Isolate participant/visit context; no copied/default narrative. | Pack contains 14 participant-specific outputs; no duplicate-detection result supplied. | unable to verify | 14-participant index and outputs. | Hash/diff report, executed two-case isolation test, screenshots/logs. | Tinotenda | What constitutes an acceptable duplicate (e.g., boilerplate only)? |
| 11 | Prose values differed from structured data: GA, HR, temperature, weight. | Every number must trace to the correct dated canonical field. | Pack includes source-row markers and chronology; no automated prose-vs-canonical comparison. | partly fixed | Pack source markers and structured chronology. | Machine comparison report for all numeric values and flagged example. | Tinotenda | Required tolerance/rounding policy? |
| 12 | GA drifted from 27w0d to 27w2d over 13 days. | GA calculated deterministically; LLM cannot calculate or silently reconcile. | Pack uses weeks+days, but dating algorithm/version is not evidenced. | open | Pack chronology. | Calculation formula, anchor, test output and discrepancy handling. | Tinotenda / Tariro decision | Confirm priority source and discrepancy display. |
| 13 | Fetal heart rate rendered as 1 bpm, likely coded/missing value. | Decode code values; validate units and plausible range; never convert code/missing to measurement. | Pack Case 01 shows a plausible 148 bpm where available, but no coded-value negative test. | partly fixed | Case 01 V03 output and source marker. | Codelist, mapping, unit validation and negative test for code `1`. | Tinotenda | What should code `1` display as? |
| 14 | “Viable fetus” and “normal” lacked explicit source support. | Claims require cited source observations; otherwise say unavailable/observed only. | Pack cites source rows for labs and states unresolved issues; claim-level provenance is not shown. | unable to verify | Pack source-row convention and selected prose. | Sentence-level provenance review and executed unsupported-claim test. | Tinotenda | Define approved vocabulary and evidence threshold for “normal/viable”. |

## 2. Test cases

No case below is marked passed: the connected records contain no actual execution evidence for these tests. `Tester` and `test date` are intentionally blank for the meeting.

### Positive tests — complete, valid data

| Test ID | Objective | Input / source record | Preconditions | Steps | Expected result | Actual result | Status | Evidence link / required | Tester / date | Related Tariro finding |
|---|---|---|---|---|---|---|---|---|---|---|
| POS-01 | Generate a complete chronological narrative. | 7 Oct pack; a participant with V01–V06, labs, delivery and postpartum data. | Approved template, mapping, protocol version and clean test case loaded. | Load case; generate; inspect overall and each visit; compare to source rows. | One participant-specific narrative, correct dates/GA, separated delivery/maternal/neonatal sections, source references, unresolved section. | No execution record found. | not run | [7 Oct pack](https://app.clickup.com/90121257130/docs/2kxuag5a-1015632/2kxuag5a-557812); require screen recording, output, source comparison. | Tinotenda / ____ | 4, 5, 7, 8, 11, 12, 14 |
| POS-02 | Preserve valid numeric and lab values. | 17 Feb example / corresponding blinded case; BP, HR, temperature, weight, ALT and ranges. | Canonical source rows and lab specification available. | Generate; compare every value, unit, date and range to canonical record. | Exact values and units; no cross-visit substitution; interpretation separate from observation. | No execution record found. | not run | Require machine comparison report and reviewer trace. | Tinotenda / ____ | 6, 11 |
| POS-03 | Render a valid positive PE evidence pattern without making the final adjudication. | Synthetic/approved positive case with qualifying BP, proteinuria and supporting labs. | Approved clinical criteria and protocol version fixed. | Load; generate; inspect criteria summary and adjudication fields. | Criteria evidence shown with dates/sources; narrative remains neutral; adjudicator answers PE and onset. | No execution record found. | not run | Require controlled synthetic input, output, rule log and clinical review. | Tinotenda + Tariro/authorised reviewer / ____ | 2, 8, 12 |
| POS-04 | Maintain participant isolation across two valid cases. | Two distinct participants with different histories and visits. | Fresh session/cache cleared; two source records available. | Generate A; generate B; compare outputs and source references. | No copied participant text except approved boilerplate; IDs, dates, values and history remain distinct. | No duplicate-detection execution evidence found. | not run | Require A/B outputs, hash/diff report, recording/log. | Panashe / ____ | 10, 11 |

### Negative tests — invalid, conflicting or impossible data

| Test ID | Objective | Input / source record | Preconditions | Steps | Expected result | Actual result | Status | Evidence link / required | Tester / date | Related Tariro finding |
|---|---|---|---|---|---|---|---|---|---|---|
| NEG-01 | Detect chronology conflict. | Case with delivery 2 May and V05 assessment 4 May displayed as 37w2d. | Dating source and protocol rule configured. | Import; generate; inspect chronology and QC. | Conflict is visible and case is warned/blocked per rule; no silent reconciliation. | Pack itself records the mismatch, but no executed gate evidence. | unable to verify | Require source rows, rule log, warning/block screenshot. | Tinotenda / ____ | 4, 5, 12 |
| NEG-02 | Reject coded fetal heart rate as a measurement. | FHR source value/code `1` or missing, with no numeric bpm. | Codelist and unit validation loaded. | Import; generate; inspect FHR. | Code is decoded or shown unavailable; never “1 bpm”; QC flags ambiguity. | No execution evidence found. | not run | Require codelist, mapping output and negative-test log. | Tinotenda / ____ | 13 |
| NEG-03 | Block unsupported normal/viable claims. | Record with missing fetal assessment or only coded “available”. | Claim vocabulary and provenance rule configured. | Generate; search prose for unsupported claims. | Claim omitted or explicitly unavailable; no unreferenced “normal/viable”. | No execution evidence found. | not run | Require output, claim-level provenance and QC result. | Tinotenda / ____ | 3, 14 |
| NEG-04 | Prevent QC pass when contradictions remain. | Case with conflicting age, incomplete event description and missing fetal weight. | QC rules and status transition available. | Import; run QC; attempt adjudication/release. | QC fails or remains warning; release/sign cannot proceed until resolved. | `AUTO_QC_COMPLETE` plus warnings is present in pack; gate execution not evidenced. | unable to verify | Require QC rule/version, audit trail and blocked-release evidence. | Panashe / ____ | 1, 3, 9 |

### Missing-data tests — missing remains visibly missing

| Test ID | Objective | Input / source record | Preconditions | Steps | Expected result | Actual result | Status | Evidence link / required | Tester / date | Related Tariro finding |
|---|---|---|---|---|---|---|---|---|---|---|
| MIS-01 | Preserve missing estimated fetal weight. | Case 01 V03: assessed but no numeric weight. | Missingness convention configured. | Generate; inspect overall/per-visit output and labs. | “Unavailable/cannot be determined”; no dash interpreted as normal, zero or negative. | Pack states this convention and uses unavailable wording; no execution proof. | partly fixed | [Case 01 pack](https://app.clickup.com/90121257130/docs/2kxuag5a-1015632/2kxuag5a-557812); require run log and screenshot. | Tinotenda / ____ | 3 |
| MIS-02 | Preserve missing adverse-event description. | Case 01 V03: event/change indicated, description absent. | Source row and missing-data rule loaded. | Generate; inspect narrative and unresolved section. | Missing description called out; no invented event or severity. | Pack calls for source clarification; no execution proof. | partly fixed | Require source row, output and review record. | Tinotenda / ____ | 3, 14 |
| MIS-03 | Preserve missing GA where postpartum calculation is not permitted. | V06 postpartum follow-up with GA unavailable. | Postpartum rule and delivery date loaded. | Generate; inspect V06. | V06 is labelled postpartum/GA unavailable; no fabricated antenatal GA. | Pack displays postpartum/GA unavailable in Case 01; no execution proof across cases. | partly fixed | Require cross-case test output and automated check. | Tinotenda / ____ | 4, 5, 12 |
| MIS-04 | Preserve missing BP pairing and interval. | Visit with systolic-only repeat or unavailable repeat interval. | Pairing rule configured. | Import; generate; inspect BP. | Unpaired value/interval remains explicit; no inferred diastolic or timing. | Pack contains such source patterns, but no executed result. | not run | Require source comparison and negative/missing-data test evidence. | Tinotenda / ____ | 2, 11 |

## 3. Outstanding-items register

Dates and owners below are proposals for confirmation, not commitments.

| ID | Outstanding item | Current evidence / risk | Proposed owner | Proposed next action | Proposed target date | Confirmation needed |
|---|---|---|---|---|---|---|
| OI-01 | Participant 1 V05 chronology mismatch: visit dated 4 May at 37w2d although delivery is recorded as 2 May. | Explicitly visible in 7 Oct pack; not resolved. | Tinotenda + Panashe | Reconcile source dates, define display rule, rerun exact case, retain discrepancy if unresolved. | 12 Oct 2026 | Confirm correct event date and whether V05 is delivery or post-delivery assessment. |
| OI-02 | Gestational-age source priority. | Pack says approved dating anchor but names none. | Tariro / authorised clinical owner | Identify source in protocol/charter; record hierarchy and discrepancy rule. | 12 Oct 2026 | Clinical decision required. |
| OI-03 | Applicable protocol/charter version. | Evidence pack checklist requests exact version; not present in reviewed task records. | Panashe | Obtain controlled protocol/charter and cite version/date in pack. | 12 Oct 2026 | Confirm source document and effective date. |
| OI-04 | Early-onset definition/cutoff. | Compilation notes unresolved tension: previous discussion guessed <32 weeks; ACOG reference mentioned <34; protocol controls. | Tariro / authorised clinical owner | Confirm study definition and encode deterministic rule with citation. | 12 Oct 2026 | Clinical decision required; do not infer from general guidance. |
| OI-05 | Editable template, prompts/rules and mapping table. | Requested twice; not attached or linked in reviewed tasks. | Tinotenda | Attach/link exact version, mapping, prompt, model, rule and source-field provenance. | 12 Oct 2026 | Tinotenda approval before any ClickUp attachment. |
| OI-06 | Full execution evidence for positive/negative/missing tests. | 7 Oct pack is review material, not proof of test execution. | Tinotenda (execution), Panashe (evidence register) | Run cases; capture inputs, outputs, logs, tester/date and expected-vs-actual. | 14 Oct 2026 | Agree acceptance threshold and evidence format. |
| OI-07 | Duplicate/isolation proof. | 14 outputs are listed; no duplicate hash/diff or run log. | Tinotenda | Run two-case isolation test and attach diff/audit evidence. | 14 Oct 2026 | Define acceptable boilerplate. |
| OI-08 | QC gate semantics. | `AUTO_QC_COMPLETE` coexists with warnings; release-blocking rule unclear. | Panashe + Tinotenda | Define warning vs failure, release gating and audit evidence. | 14 Oct 2026 | Decide whether any unresolved contradiction blocks adjudication. |
| OI-09 | Lab reference ranges, units and claim vocabulary. | Pack says metadata applies; governing laboratory specification and “normal/viable” threshold not linked. | Tinotenda + clinical owner | Link lab specification; test ALT conflict and unsupported claims. | 14 Oct 2026 | Confirm approved vocabulary and range version. |
| OI-10 | Clinical review/approval record. | Design task requires Tariro approval; no approval artifact returned. | Panashe | Prepare approval request only after Tinotenda approval of pack; preserve draft status. | After evidence completion | Tariro sign-off must not be requested yet. |
| OI-11 | Demo vs production evidence and permissions/notifications. | Session 8 requests non-demo notification and permission tests; no execution evidence reviewed. | Panashe | Separate environments and run role/permission/notification tests with audit evidence. | 14 Oct 2026 | Confirm production-like environment and roles. |

## 4. Proposed meeting agenda

1. Agree acceptance criteria, status definitions and evidence standard.
2. Walk through the positive, negative and missing-data test cases.
3. Assign execution, recording, source-comparison and evidence-register responsibilities.
4. Review all 14 Tariro findings and confirm each response/status.
5. Resolve or assign outstanding items OI-01 to OI-11, including dating source, protocol version and EOPE cutoff.
6. Confirm what must be escalated to Tariro: clinical rules, protocol interpretation, acceptance of unresolved discrepancies, and approval of the narrative framework.
7. Confirm post-meeting completion date and the gate for requesting implementation clearance.

## 5. Tinotenda and Panashe completion checklist

Before requesting implementation clearance, both must complete and retain evidence for every applicable item:

- [ ] Confirm the approved protocol/charter version and exact early-onset definition.
- [ ] Confirm gestational-age source priority and discrepancy handling.
- [ ] Freeze the editable narrative template, prompts, rules, mapping, model and version identifiers.
- [ ] Link each narrative element to source field/code/unit/date/visit.
- [ ] Run and record every listed positive, negative and missing-data test; fill actual result, pass/fail/not run, tester and date.
- [ ] Re-run the flagged 10 February, 17 February and Participant 1/V05 examples.
- [ ] Prove participant/visit isolation with two distinct cases and a duplicate-detection result.
- [ ] Prove numeric, unit, lab-range and coded-value fidelity against source rows.
- [ ] Prove that missing data is visible and never silently converted to normal/negative/zero.
- [ ] Prove that contradictions trigger the agreed QC warning/block and cannot be released silently.
- [ ] Separate demo evidence from production-like evidence, including permissions and notifications.
- [ ] Obtain an authorised clinical review of the narrative framework and unresolved clinical-rule decisions.
- [ ] Update the response table and outstanding-items register with evidence links and confirmed owners/dates.
- [ ] Obtain Tinotenda’s approval of this pack before any ClickUp posting, attachment, status change or request for Tariro’s sign-off.

**Clearance rule for this draft:** do not request implementation clearance while any finding is open/partly fixed without an agreed risk acceptance, any required test is not run, or the protocol/dating/EOPE decisions remain unconfirmed.
