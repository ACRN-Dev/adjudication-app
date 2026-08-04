import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, ShieldAlert } from 'lucide-react';

/**
 * CsvUploader — Change record items #5 and #6:
 *   - Required column checks: SUBJID, GA_EVENT (or GA), SBP, DBP, EVENT_DT (or Date)
 *   - Biomarker column rejection (sFlt-1, PlGF, sEng, treatment allocation, POC)
 *   - One-participant-per-upload enforcement (demo mode)
 *   - Proper quoted CSV parser: handles quoted fields, escaped quotes, commas inside quotes, CRLF/LF
 *   - Auto-calculates UPCR from Spot Urine Protein / Spot Urine Creatinine if present
 *   - Built-in canonical synthetic CSV
 *   - Calls dvEngine for derivation when available
 */

// ── Blinding guardrails ───────────────────────────────────────────────────────
const BLINDED_COLUMN_PATTERNS = [
  'sflt', 'sflt-1', 'sflt1', 'plgf', 'pigf', 'placental growth',
  'seng', 's_eng', 'soluble endoglin',
  'ratio', 'angiogenic', 'biomarker',
  'poc', 'poc_result', 'poc result',
  'treatment', 'allocation', 'randomis', 'randomiz',
  'arm', 'study_drug', 'study drug', 'blinded',
];

// Site-recorded PE status/diagnosis is not clinical evidence and must never seed adjudication.
// These fields may be retained only in a restricted Monitor comparison store, never this uploader.
const RECORDED_OUTCOME_PATTERNS = [
  'preeclampsia status', 'pre-eclampsia status', 'pe_status', 'pe status',
  'preeclampsia diagnosis', 'pre-eclampsia diagnosis', 'pe_diagnosis', 'pe diagnosis',
  'preeclampsia diagnosed', 'pre-eclampsia diagnosed', 'pe diagnosed',
  'recorded_pe', 'recorded pe', 'pe_outcome', 'pe outcome',
  'diagnosis_date', 'diagnosis date', 'final_diagnosis', 'final diagnosis'
];

function isBlindedColumn(colName) {
  const lower = (colName || '').toLowerCase().replace(/[_\-\s]/g, '');
  return BLINDED_COLUMN_PATTERNS.some(p => lower.includes(p.replace(/[_\-\s]/g, '')));
}

function isRecordedOutcomeColumn(colName) {
  const lower = (colName || '').toLowerCase().replace(/[_\-\s]/g, '');
  return RECORDED_OUTCOME_PATTERNS.some(p => lower.includes(p.replace(/[_\-\s]/g, '')));
}

// ── Required columns (aliases accepted) ─────────────────────────────────────
const REQUIRED_COLUMN_ALIASES = {
  SUBJID:    ['SUBJID', 'SubjectID', 'ParticipantID', 'SUBJECT_ID', 'PtID'],
  GA_EVENT:  ['GA_EVENT', 'GA', 'GestationalAge', 'GA_AT_EVENT'],
  SBP:       ['SBP', 'SystolicBP', 'Systolic'],
  DBP:       ['DBP', 'DiastolicBP', 'Diastolic'],
  EVENT_DT:  ['EVENT_DT', 'Date', 'EVENT_DATE', 'VisitDate', 'DateOfVisit'],
};

function resolveColumn(headers, aliases) {
  for (const alias of aliases) {
    const found = headers.find(h => h.trim().toUpperCase() === alias.toUpperCase());
    if (found) return found;
  }
  return null;
}

// ── Proper RFC 4180 CSV parser ────────────────────────────────────────────────
function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ',') {
        row.push(field);
        field = '';
      } else if (ch === '\n' || (ch === '\r' && next === '\n')) {
        if (ch === '\r') i++;
        row.push(field);
        field = '';
        if (row.some(c => c.trim())) rows.push(row);
        row = [];
      } else if (ch === '\r') {
        row.push(field);
        field = '';
        if (row.some(c => c.trim())) rows.push(row);
        row = [];
      } else {
        field += ch;
      }
    }
  }
  if (field || row.length) {
    row.push(field);
    if (row.some(c => c.trim())) rows.push(row);
  }
  return rows;
}

// ── Built-in canonical synthetic CSV ────────────────────────────────────────
const CANONICAL_SYNTHETIC_CSV = `SUBJID,GA_EVENT,EVENT_DT,SBP,DBP,UPCR,Platelets,Creatinine,AST,ALT,LDH,EFW_Centile
SYNTH-DEMO-9901,32+4,2026-07-14,162,108,1.42,88,1.31,96,78,714,6
SYNTH-DEMO-9901,32+4,2026-07-14,167,112,1.42,88,1.31,96,78,714,6
SYNTH-DEMO-9901,32+5,2026-07-15,158,104,1.42,88,1.31,96,78,714,6
`;

export default function CsvUploader({ onCsvParsed }) {
  const [uploadStatus, setUploadStatus] = useState(null);
  const [fileName, setFileName] = useState('');
  const [blindingWarning, setBlindingWarning] = useState(null);
  const fileRef = useRef(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (evt) => parseCsvText(evt.target.result, file.name);
    reader.readAsText(file, 'UTF-8');
  };

  const parseCsvText = (csvContent, name) => {
    setBlindingWarning(null);
    setUploadStatus(null);

    try {
      // ── Parse ────────────────────────────────────────────────────────────
      const parsed = parseCSV(csvContent.trim());
      if (parsed.length < 2) {
        setUploadStatus({ error: 'CSV file is empty or missing header rows.' });
        return;
      }

      const headers = parsed[0].map(h => h.trim());
      const outcomeColumns = headers.filter(isRecordedOutcomeColumn);
      if (outcomeColumns.length) {
        setUploadStatus({ error: `Adjudication outcome field(s) rejected: ${outcomeColumns.join(', ')}. Recorded PE status/diagnosis cannot be imported as evidence or used to derive the adjudication answer.` });
        return;
      }

      // ── Blinding guardrail (change record #6) ────────────────────────────
      const blindedCols = headers.filter(isBlindedColumn);
      if (blindedCols.length > 0) {
        setBlindingWarning(
          `FORM-ADJ-09 BLINDING ALERT: The following column(s) may contain ` +
          `unblinded biomarker or treatment allocation data and have been REJECTED: ` +
          `${blindedCols.join(', ')}. ` +
          `This import has been blocked per SOP-ADJ-002. ` +
          `If you believe this is a false positive, escalate to the Adjudication Coordinator.`
        );
        return;
      }

      // ── Required column checks (change record #5) ────────────────────────
      const colMap = {};
      for (const [key, aliases] of Object.entries(REQUIRED_COLUMN_ALIASES)) {
        const found = resolveColumn(headers, aliases);
        if (!found) {
          setUploadStatus({
            error: `Required column missing: "${key}" (accepted names: ${aliases.join(', ')}). ` +
              `Please check your CSV header row.`
          });
          return;
        }
        colMap[key] = found;
      }

      // ── Build row objects ─────────────────────────────────────────────────
      const dataRows = parsed.slice(1).map(values => {
        return headers.reduce((obj, h, i) => {
          obj[h] = values[i] ?? '';
          return obj;
        }, {});
      }).filter(r => r[colMap.SUBJID]?.trim());

      if (dataRows.length === 0) {
        setUploadStatus({ error: 'CSV file has no usable participant rows (SUBJID column is empty).' });
        return;
      }

      // ── One-participant-per-upload (demo mode, change record #5) ─────────
      const uniqueIds = [...new Set(dataRows.map(r => r[colMap.SUBJID]?.trim()).filter(Boolean))];
      if (uniqueIds.length > 1) {
        setUploadStatus({
          error: `This demonstration upload supports one participant at a time. ` +
            `Your file contains ${uniqueIds.length} participants (${uniqueIds.slice(0, 3).join(', ')}...). ` +
            `Please filter to a single SUBJID before uploading.`
        });
        return;
      }

      const subjId = uniqueIds[0];
      const firstRow = dataRows[0];

      // ── Build BP log from all rows ────────────────────────────────────────
      const bpLog = dataRows
        .filter(r => r[colMap.SBP] && r[colMap.DBP])
        .map(r => {
          const sbp = parseInt(r[colMap.SBP]) || 0;
          const dbp = parseInt(r[colMap.DBP]) || 0;
          return {
            date: r[colMap.EVENT_DT] || '',
            ga: r[colMap.GA_EVENT] || '',
            sbp, dbp,
            severe: sbp >= 160 || dbp >= 110,
            source: 'Uploaded EDC/eSource CSV',
          };
        });

      // ── Auto-calculate UPCR ───────────────────────────────────────────────
      let parsedUpcr = null;
      let protSource = 'Uploaded LIMS CSV';
      const rawUpcr = firstRow.UPCR || firstRow.UrineProteinRatio || firstRow.upcr;
      const uProt = parseFloat(firstRow.UrineProtein || firstRow.SpotUrineProtein || firstRow.PROT || 0);
      const uCreat = parseFloat(firstRow.UrineCreatinine || firstRow.SpotUrineCreatinine || firstRow.CREAT_URINE || 0);

      if (rawUpcr) {
        parsedUpcr = parseFloat(rawUpcr);
      } else if (uProt > 0 && uCreat > 0) {
        parsedUpcr = Math.round((uProt / uCreat) * 100) / 100;
        protSource = `UPCR auto-calculated from Protein (${uProt}) / Creatinine (${uCreat}) per study protocol`;
      }

      const parsedDipstick = firstRow.Dipstick || firstRow.UrineProteinDipstick || firstRow.DIPSTICK || null;

      const protResult = parsedUpcr != null
        ? `${parsedUpcr} g/g${parsedUpcr >= 0.3 ? ' (≥0.3 g/g — threshold met)' : ' (below 0.3 g/g threshold)'}`
        : parsedDipstick
          ? `Dipstick ${parsedDipstick}`
          : '[Not documented — not assessable]';

      // ── Build lab log ─────────────────────────────────────────────────────
      const labLog = [];
      const addLab = (analyte, key, unit, refRange) => {
        const aliases = [key, key.toLowerCase(), key.toUpperCase()];
        for (const a of aliases) {
          if (firstRow[a]) {
            labLog.push({ analyte, result: firstRow[a], unit, refRange, source: 'Uploaded LIMS CSV' });
            return;
          }
        }
      };
      addLab('Platelet Count', 'Platelets', '×10³/µL', '150–450');
      addLab('Platelet Count', 'PLATELET_COUNT', '×10³/µL', '150–450');
      addLab('Creatinine', 'Creatinine', 'mg/dL', '0.50–0.90');
      addLab('AST', 'AST', 'U/L', '<40');
      addLab('ALT', 'ALT', 'U/L', '<35');
      addLab('LDH', 'LDH', 'IU/L', '<250');

      // ── Build case object ─────────────────────────────────────────────────
      const importedCase = {
        id: subjId,
        caseNo: `ADJ-CSV-${subjId.slice(-4)}`,
        site: '[Site blinded per SOP-ADJ-002]',
        status: 'Pending Review',
        trigger: 'CSV Upload — Derivation Pending',
        pktScore: null,   // Will be set by dvEngine
        gaAtEvent: firstRow[colMap.GA_EVENT] || '',
        gaAtEnrollment: firstRow[colMap.GA_EVENT] || '',
        edd: firstRow.EDD || '[Not documented]',
        firstUssGa: firstRow.USS_GA || firstRow.FirstUSSGA || null,
        firstUssDate: firstRow.USS_Date || firstRow.FirstUSSDate || null,
        lnmp: firstRow.LNMP || null,
        biomarkers: {
          sFlt1: 'BLINDED — Withheld per SOP-ADJ-002',
          plgf: 'BLINDED — Withheld per SOP-ADJ-002',
          ratio: 'BLINDED — Withheld per SOP-ADJ-002',
          pocResult: 'BLINDED — Withheld per SOP-ADJ-002',
        },
        bpLog,
        proteinuriaLog: parsedUpcr != null || parsedDipstick ? [{
          date: firstRow[colMap.EVENT_DT] || '',
          method: parsedUpcr != null ? 'UPCR' : 'Dipstick',
          result: protResult,
          numeric: parsedUpcr,
          source: protSource,
        }] : [],
        labLog,
        upcr: parsedUpcr,
        dipstick_raw: parsedDipstick,
        platelet_count: parseFloat(firstRow.Platelets || firstRow.PLATELET_COUNT) || null,
        creatinine: parseFloat(firstRow.Creatinine) || null,
        creatinine_unit: firstRow.Creatinine_Unit || 'mg/dL',
        ast: parseFloat(firstRow.AST) || null,
        alt: parseFloat(firstRow.ALT) || null,
        ldh: parseFloat(firstRow.LDH) || null,
        efw_centile: parseFloat(firstRow.EFW_Centile || firstRow.EFW_CENTILE) || null,
        derivedSubtype: null,
        derivedSeverity: null,
        derivedOnset: null,
        narrativeForm: 'FORM-ADJ-15A',
        aiNarrative: '',
        criteria: [],
        sourceDocs: {
          ultrasound: firstRow.USS_Date ? `USS dated ${firstRow.USS_Date}` : null,
          lims: labLog.length > 0 ? csvContent.slice(0, 500) : null,
          vitals: bpLog.length > 0 ? `${bpLog.length} BP reading(s) from uploaded CSV` : null,
          delivery: firstRow.DELIVERY_DATE || null,
        },
        weightLog: [],
        medicationLog: [],
        delivery_date: firstRow.DELIVERY_DATE || null,
        ga_at_delivery: firstRow.GA_DELIVERY || null,
        gravidity: parseInt(firstRow.Gravidity || firstRow.GRAVIDITY) || null,
        parity: parseInt(firstRow.Parity || firstRow.PARITY) || null,
      };

      // ── Run dvEngine derivation in browser ────────────────────────────────
      try {
        import('../services/dvEngine.js').then(({ runDvEngine }) => {
          const dvResult = runDvEngine(importedCase);
          importedCase.pktScore = dvResult.evidenceScore;
          importedCase.trigger = dvResult.trigger?.triggered
            ? `DV-30: ${dvResult.trigger.reasons?.join(', ')}`
            : 'DV-30: Not triggered';
          importedCase.dvResults = dvResult;
          onCsvParsed && onCsvParsed(importedCase);
        }).catch(() => {
          // dvEngine not yet available — pass case without derivation
          onCsvParsed && onCsvParsed(importedCase);
        });
      } catch {
        onCsvParsed && onCsvParsed(importedCase);
      }

      setUploadStatus({
        success: `Successfully imported ${dataRows.length} row(s) for participant ${subjId} from "${name}". Derivation running...`
      });

    } catch (err) {
      setUploadStatus({ error: 'Failed to parse CSV: ' + err.message });
    }
  };

  const loadBuiltInCsv = () => {
    setFileName('canonical_synthetic_demo.csv');
    parseCsvText(CANONICAL_SYNTHETIC_CSV, 'canonical_synthetic_demo.csv');
  };

  return (
    <div style={{ marginTop: '20px' }}>
      <label className="csv-dropzone" style={{ display: 'block', cursor: 'pointer' }}>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
          id="csv-upload-input"
          aria-label="Upload canonical patient CSV data file"
        />
        <UploadCloud size={36} color="var(--acrn-orange-primary)" style={{ margin: '0 auto 8px', display: 'block' }} />
        <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--acrn-navy-dark)' }}>
          Click to Upload Patient CSV Data File
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
          Required columns: SUBJID, GA_EVENT, EVENT_DT, SBP, DBP
          &nbsp;·&nbsp;One participant per upload (demo mode)
          &nbsp;·&nbsp;Biomarker columns auto-rejected
        </div>
      </label>

      <div style={{ textAlign: 'center', marginBottom: '12px' }}>
        <button
          type="button"
          onClick={loadBuiltInCsv}
          style={{
            background: 'none', border: 'none',
            color: 'var(--acrn-sky-blue)',
            fontSize: '13px', fontWeight: 600,
            cursor: 'pointer', textDecoration: 'underline'
          }}
        >
          Or load the built-in canonical synthetic CSV
        </button>
      </div>

      {/* Blinding alert (change record #6) */}
      {blindingWarning && (
        <div style={{
          background: '#fff7ed', border: '1px solid #fed7aa',
          color: '#9a3412', padding: '12px 14px',
          borderRadius: '6px', fontSize: '13px',
          display: 'flex', alignItems: 'flex-start', gap: '10px',
          marginBottom: '8px'
        }}>
          <ShieldAlert size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
          <div>
            <strong>FORM-ADJ-09 Blinding Alert</strong>
            <div style={{ marginTop: '4px' }}>{blindingWarning}</div>
          </div>
        </div>
      )}

      {uploadStatus?.success && (
        <div style={{
          background: '#f0fdf4', color: '#15803d',
          padding: '12px', borderRadius: '6px',
          fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <CheckCircle2 size={18} />
          {uploadStatus.success}
        </div>
      )}

      {uploadStatus?.error && (
        <div style={{
          background: '#fef2f2', color: '#dc2626',
          padding: '12px', borderRadius: '6px',
          fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <AlertCircle size={18} />
          {uploadStatus.error}
        </div>
      )}
    </div>
  );
}
