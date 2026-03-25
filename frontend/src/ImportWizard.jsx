/**
 * ImportWizard.jsx — Redesigned smart import with two flows:
 *
 *  Quick Parse  — just extract the raw rows, show them to the user (no journaling)
 *  Full Pipeline — parse  normalize  dedup  categorize  review  commit to DB
 *
 * Intelligence:
 *  - On file drop we immediately call POST /pipeline/detect to identify the bank/source and
 *  - The parse API also runs server-side detection; we surface the result with confidence.
 *  - If a PDF is encrypted the first parse attempt returns an error and we ask for the password.
 *  - Account is auto-matched from the detected source where possible; user can override.
 *  - We only show account / source-type pickers when detection confidence is low.
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Upload, FileText, CheckCircle2, XCircle, AlertTriangle,
  ChevronRight, ChevronDown, ChevronUp, RotateCcw, Sparkles,
  Database, Zap, Eye, Check, X, Lock, RefreshCw, Info,
  ArrowRight, ArrowLeft, Pencil,
} from 'lucide-react';
import { API } from './api.js';

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(n ?? 0);
const pct = (v) => `${Math.round((v ?? 0) * 100)}%`;

// ---------------------------------------------------------------------------
// Confidence band styles
// ---------------------------------------------------------------------------

const BAND = {
  GREEN:  { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', dot: 'bg-emerald-500', bar: 'bg-emerald-500' },
  YELLOW: { bg: 'bg-amber-50',   border: 'border-amber-200',   text: 'text-amber-700',   dot: 'bg-amber-400',  bar: 'bg-amber-400'  },
  RED:    { bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-700',     dot: 'bg-red-500',    bar: 'bg-red-500'    },
};

function BandDot({ band }) {
  const s = BAND[band?.toUpperCase()] ?? BAND.YELLOW;
  return <span className={`inline-block w-2 h-2 rounded-full ${s.dot}`} />;
}

function ConfidencePill({ band, score }) {
  const s = BAND[band?.toUpperCase()] ?? BAND.YELLOW;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${s.bg} ${s.border} ${s.text}`}>
      <BandDot band={band} />
      {band}{score != null ? `  ${Math.round(score * 100)}%` : ''}
    </span>
  );
}

// (client-side filename guessing removed — server /detect is used instead)

// ---------------------------------------------------------------------------
// Shared UI primitives
// ---------------------------------------------------------------------------

function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-100 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

function Spinner({ sm }) {
  return (
    <span
      className={`animate-spin border-2 border-current border-t-transparent rounded-full inline-block ${sm ? 'w-3.5 h-3.5' : 'w-4 h-4'}`}
    />
  );
}

function ErrorBanner({ msg }) {
  if (!msg) return null;
  return (
    <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
      <XCircle size={15} className="mt-0.5 shrink-0" />
      <span>{msg}</span>
    </div>
  );
}

function StatTile({ label, value, color = 'text-slate-800' }) {
  return (
    <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
      <p className={`font-bold text-xl leading-tight ${color}`}>{value}</p>
      <p className="text-xs text-slate-400 mt-0.5">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mode tab
// ---------------------------------------------------------------------------

function ModeTab({ value, current, onChange, icon: Icon, label, sub }) {
  const active = value === current;
  return (
    <button
      onClick={() => onChange(value)}
      className={`flex-1 flex items-start gap-3 px-4 py-3 rounded-xl border-2 transition-all text-left ${
        active
          ? 'border-indigo-500 bg-indigo-50'
          : 'border-slate-100 bg-white hover:border-slate-200'
      }`}
    >
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
          active ? 'bg-indigo-600' : 'bg-slate-100'
        }`}
      >
        <Icon size={15} className={active ? 'text-white' : 'text-slate-500'} />
      </div>
      <div>
        <div className={`text-sm font-bold ${active ? 'text-indigo-700' : 'text-slate-700'}`}>
          {label}
        </div>
        <div className="text-xs text-slate-400 leading-snug mt-0.5">{sub}</div>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Drop zone
// ---------------------------------------------------------------------------

function DropZone({ file, onFile }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef();

  const pick = (f) => { if (f) onFile(f); };

  return (
    <div
      onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer?.files?.[0]); }}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onClick={() => ref.current?.click()}
      className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center gap-2 cursor-pointer transition-all ${
        drag
          ? 'border-indigo-400 bg-indigo-50'
          : file
          ? 'border-indigo-200 bg-indigo-50/40'
          : 'border-slate-200 bg-slate-50 hover:border-indigo-300'
      }`}
    >
      <input
        ref={ref}
        type="file"
        className="hidden"
        accept=".csv,.xls,.xlsx,.pdf"
        onChange={(e) => {
          pick(e.target.files?.[0]);
          if (e.target) e.target.value = '';
        }}
      />
      {file ? (
        <>
          <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
            <FileText size={20} className="text-indigo-600" />
          </div>
          <p className="text-sm font-semibold text-slate-800">{file.name}</p>
          <p className="text-xs text-slate-400">
            {(file.size / 1024).toFixed(1)} KB  click to change
          </p>
        </>
      ) : (
        <>
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center">
            <Upload size={20} className="text-slate-400" />
          </div>
          <p className="text-sm font-semibold text-slate-600">Drop your statement here</p>
          <p className="text-xs text-slate-400">Bank PDF  CSV  XLS  XLSX — up to 20 MB</p>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detection card — shows server /detect result with metadata
// ---------------------------------------------------------------------------

function MetaRow({ icon: Icon, label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon size={11} className="text-slate-400 shrink-0" />
      <span className="text-slate-500">{label}:</span>
      <span className="font-semibold text-slate-700">{value}</span>
    </div>
  );
}

function DetectionCard({
  file, serverDetection, detectLoading, detectError,
  accounts, sourceTypes,
  userAccountNum, setUserAccountNum,
  userIFSC, setUserIFSC,
  bankAccountOverride, setBankAccountOverride,
  overrideAccount, setOverrideAccount,
  overrideSource,  setOverrideSource,
  showOverrides,   setShowOverrides,
}) {
  if (!file) return null;

  const sd = serverDetection;
  const meta = sd?.metadata ?? {};
  const hasHighConf = sd && !sd.needs_password && sd.confidence >= 0.70;
  const hasLowConf  = sd && !sd.needs_password && sd.confidence < 0.70;
  const missingAccNum = sd && !meta.account_number;
  const missingIFSC   = sd && !meta.ifsc_code;

  // Resolved account to display (override wins over detect result)
  const displayAcct = bankAccountOverride
    ? accounts.find(a => (a.code ?? a.account_id) === bankAccountOverride)
    : null;
  const acctCode  = displayAcct?.code   ?? sd?.bank_account_code  ?? '1102';
  const acctName  = displayAcct?.name   ?? sd?.bank_account_name  ?? 'Savings Account';
  const acctClass = displayAcct?.account_type ?? sd?.bank_account_class ?? 'ASSET';
  const isLiability = acctClass === 'LIABILITY';

  return (
    <div className="space-y-2">
      <Card className="px-4 py-3">
        <div className="flex items-start gap-3">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
              detectLoading ? 'bg-slate-100 animate-pulse'
              : hasHighConf ? 'bg-indigo-100'
              : 'bg-slate-100'
            }`}
          >
            {detectLoading
              ? <Spinner sm />
              : <FileText size={16} className={hasHighConf ? 'text-indigo-600' : 'text-slate-400'} />}
          </div>

          <div className="flex-1 min-w-0">
            {detectLoading ? (
              <>
                <p className="text-sm font-semibold text-slate-600">Scanning file…</p>
                <p className="text-xs text-slate-400">Identifying bank and extracting details</p>
              </>
            ) : hasHighConf ? (
              <>
                <p className="text-sm font-semibold text-slate-800">
                  <span className="text-indigo-600">{sd.source_type_label ?? sd.source_type}</span>
                  <span className="ml-2 text-xs font-normal text-slate-400">
                    {sd.file_format} · {Math.round(sd.confidence * 100)}% confident
                  </span>
                </p>
                <div className="mt-1 space-y-0.5">
                  <MetaRow icon={Info} label="A/C"    value={meta.account_number} />
                  <MetaRow icon={Info} label="Holder" value={meta.account_holder} />
                  <MetaRow icon={Info} label="IFSC"   value={meta.ifsc_code} />
                  <MetaRow icon={Info} label="Period" value={
                    meta.statement_from
                      ? `${meta.statement_from} → ${meta.statement_to ?? '?'}`
                      : null
                  } />
                  <MetaRow icon={Info} label="Branch" value={meta.branch_name} />
                </div>
              </>
            ) : hasLowConf ? (
              <>
                <p className="text-sm font-semibold text-amber-700">Bank not recognised</p>
                <p className="text-xs text-slate-400">Please choose the source type below</p>
              </>
            ) : sd?.needs_password ? (
              <>
                <p className="text-sm font-semibold text-amber-700">🔒 Encrypted file</p>
                <p className="text-xs text-slate-400">Enter the password below to continue</p>
                {sd.password_hint && (
                  <p className="text-xs text-indigo-600 mt-1">💡 {sd.password_hint}</p>
                )}
              </>
            ) : detectError ? (
              <>
                <p className="text-sm font-semibold text-slate-700">File ready</p>
                <p className="text-xs text-amber-600">{detectError}</p>
              </>
            ) : (
              <>
                <p className="text-sm font-semibold text-slate-700">File ready</p>
                <p className="text-xs text-slate-400">Bank / source will be detected automatically</p>
              </>
            )}
          </div>

          {!detectLoading && (
            <button
              onClick={() => setShowOverrides((v) => !v)}
              className="text-xs text-slate-400 hover:text-indigo-600 flex items-center gap-0.5 shrink-0 mt-0.5"
            >
              Override {showOverrides ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>

        {/* Mapped ledger account — shown as soon as detect returns */}
        {hasHighConf && (
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="text-xs text-slate-400 mb-1">Posts to ledger account</p>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded text-slate-600">
                  {acctCode}
                </span>
                <span className="text-sm font-bold text-slate-800">{acctName}</span>
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full border ${
                  isLiability
                    ? 'bg-orange-50 border-orange-200 text-orange-700'
                    : 'bg-sky-50 border-sky-200 text-sky-700'
                }`}>
                  {acctClass}
                </span>
              </div>
            </div>
            {accounts.length > 0 && (
              <select
                value={bankAccountOverride}
                onChange={(e) => setBankAccountOverride(e.target.value)}
                className="border border-slate-200 rounded-lg px-2 py-1 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 shrink-0"
              >
                <option value="">Default ({sd.bank_account_code} — {sd.bank_account_name})</option>
                {accounts.map((a) => (
                  <option key={a.account_id} value={a.code ?? a.account_id}>
                    {a.code} — {a.name} ({a.account_type})
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {showOverrides && (
          <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1 block">Link to account</label>
              <select
                value={overrideAccount}
                onChange={(e) => setOverrideAccount(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                <option value="">— auto-detect —</option>
                {accounts.map((a) => (
                  <option key={a.account_id} value={a.code ?? a.account_id}>
                    {a.name}{a.code ? ` (${a.code})` : ''}  {a.account_type}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1 block">Source / parser</label>
              <select
                value={overrideSource}
                onChange={(e) => setOverrideSource(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                <option value="">— auto-detect —</option>
                {sourceTypes.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label} ({s.format})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </Card>

      {/* Manual entry for fields the server couldn't extract */}
      {hasHighConf && (missingAccNum || missingIFSC) && (
        <Card className="px-4 py-3 border-amber-100 bg-amber-50">
          <p className="text-xs font-semibold text-amber-800 mb-2">
            Some details weren't found in the file — fill them in if you know them:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {missingAccNum && (
              <div>
                <label className="text-xs font-semibold text-slate-600 mb-1 block">Account Number</label>
                <input
                  type="text"
                  value={userAccountNum}
                  onChange={(e) => setUserAccountNum(e.target.value)}
                  placeholder="e.g. 50100123456789"
                  className="w-full border border-amber-300 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                />
              </div>
            )}
            {missingIFSC && (
              <div>
                <label className="text-xs font-semibold text-slate-600 mb-1 block">IFSC Code</label>
                <input
                  type="text"
                  value={userIFSC}
                  onChange={(e) => setUserIFSC(e.target.value.toUpperCase())}
                  placeholder="e.g. HDFC0001234"
                  maxLength={11}
                  className="w-full border border-amber-300 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono uppercase"
                />
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
// Password prompt — only shown when server tells us the PDF is encrypted
// ---------------------------------------------------------------------------

function PasswordPrompt({ onSubmit, loading, error, fileFormat, hint }) {
  const [pw, setPw] = useState('');
  const isXlsx = fileFormat && fileFormat.toUpperCase() === 'XLSX';
  const label = isXlsx ? 'spreadsheet' : 'PDF';
  return (
    <Card className="px-4 py-4 border-amber-200 bg-amber-50">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg bg-amber-200 flex items-center justify-center shrink-0">
          <Lock size={14} className="text-amber-700" />
        </div>
        <div>
          <p className="text-sm font-bold text-amber-900">This {label} is password-protected</p>
          <p className="text-xs text-amber-700 mt-0.5">
            Enter the password your bank uses. We never store it.
          </p>
        </div>
      </div>
      {hint && (
        <div className="flex items-start gap-1.5 text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2 mb-3">
          <Info size={12} className="mt-0.5 shrink-0" />
          {hint}
        </div>
      )}
      <div className="flex gap-2">
        <input
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && pw && onSubmit(pw)}
          placeholder={`${label.charAt(0).toUpperCase() + label.slice(1)} password`}
          className="flex-1 border border-amber-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
          autoFocus
        />
        <button
          onClick={() => onSubmit(pw)}
          disabled={!pw || loading}
          className="px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 disabled:opacity-40 flex items-center gap-1.5"
        >
          {loading ? <Spinner sm /> : <ArrowRight size={14} />}
          Unlock
        </button>
      </div>
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// LLM provider selector (compact toggle row)
// ---------------------------------------------------------------------------

function LlmRow({ providers, providerId, setProviderId, useLlm, setUseLlm }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3 bg-violet-50 border border-violet-100 rounded-xl">
      <div className="flex items-center gap-2">
        <Sparkles size={14} className="text-violet-500 shrink-0" />
        <div>
          <p className="text-xs font-semibold text-slate-700">AI categorisation</p>
          <p className="text-xs text-slate-400">Helps with tricky or ambiguous transactions</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {useLlm && providers.length > 0 && (
          <select
            value={providerId ?? ''}
            onChange={(e) => setProviderId(e.target.value || null)}
            className="border border-violet-200 rounded-lg px-2 py-1 text-xs bg-white focus:outline-none"
          >
            {providers.map((p) => (
              <option key={p.provider_id} value={p.provider_id}>
                {p.display_name || p.provider_name}{p.is_default ? ' ' : ''}
              </option>
            ))}
          </select>
        )}
        {useLlm && providers.length === 0 && (
          <span className="text-xs text-amber-600">No API key — add in Settings</span>
        )}
        <button
          onClick={() => setUseLlm((v) => !v)}
          className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${
            useLlm ? 'bg-violet-600' : 'bg-slate-200'
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
              useLlm ? 'translate-x-5' : ''
            }`}
          />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Parsed rows table — shown in Quick Look after parse
// ---------------------------------------------------------------------------

const RAW_PAGE = 25;

function RawRowsTable({ batchId }) {
  const [rows, setRows]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage]       = useState(0);

  useEffect(() => {
    API.pipeline.rawRows(batchId)
      .then(d => setRows(d.items ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [batchId]);

  if (loading) return (
    <div className="flex items-center justify-center gap-2 py-4 text-slate-400 text-sm">
      <Spinner sm /> Loading rows…
    </div>
  );
  if (!rows.length) return null;

  const totalPages = Math.ceil(rows.length / RAW_PAGE);
  const pageRows   = rows.slice(page * RAW_PAGE, (page + 1) * RAW_PAGE);

  return (
    <div className="space-y-2">
      <div className="rounded-xl border border-slate-100 overflow-hidden">
        <div className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 340px)' }}>
        <table className="w-full table-fixed text-xs">
          <colgroup>
            <col className="w-24" />
            <col />
            <col className="w-28" />
            <col className="w-28" />
          </colgroup>
          <thead className="sticky top-0 z-10 bg-slate-50 text-slate-500 border-b border-slate-100 shadow-sm">
            <tr>
              <th className="px-3 py-2 text-left font-semibold">Date</th>
              <th className="px-3 py-2 text-left font-semibold">Description</th>
              <th className="px-3 py-2 text-right font-semibold text-rose-400">Debit (DR)</th>
              <th className="px-3 py-2 text-right font-semibold text-emerald-500">Credit (CR)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {pageRows.map(r => (
              <tr key={r.row_id} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-400">{r.raw_date ?? '—'}</td>
                <td className="px-3 py-2 text-slate-700">
                  <span className="block truncate" title={r.raw_narration}>{r.raw_narration ?? '—'}</span>
                </td>
                <td className="px-3 py-2 text-right font-mono text-rose-600">
                  {r.raw_debit ? `₹${r.raw_debit}` : <span className="text-slate-200">—</span>}
                </td>
                <td className="px-3 py-2 text-right font-mono text-emerald-600">
                  {r.raw_credit ? `₹${r.raw_credit}` : <span className="text-slate-200">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-slate-400">
            Rows {page * RAW_PAGE + 1}–{Math.min((page + 1) * RAW_PAGE, rows.length)} of {rows.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30"
            >‹ Prev</button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={`w-6 h-6 text-xs rounded border transition-colors ${
                  i === page ? 'bg-indigo-600 border-indigo-600 text-white' : 'border-slate-200 text-slate-500 hover:bg-slate-50'
                }`}
              >{i + 1}</button>
            ))}
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30"
            >Next ›</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quick Parse result
// ---------------------------------------------------------------------------

function ParseOnlyResult({ result, onReset }) {
  return (
    <div className="space-y-4">
      <Card className="px-4 py-4">
        <div className="flex items-center gap-2 mb-4">
          {result.txn_found > 0 ? (
            <CheckCircle2 size={18} className="text-emerald-500 shrink-0" />
          ) : (
            <XCircle size={18} className="text-red-500 shrink-0" />
          )}
          <span className="font-semibold text-slate-800">
            {result.txn_found > 0
              ? `Found ${result.txn_found} transaction${result.txn_found !== 1 ? 's' : ''}`
              : "Couldn't find any transactions"}
          </span>
          <button
            onClick={onReset}
            className="ml-auto text-xs text-slate-400 hover:text-indigo-600 flex items-center gap-1"
          >
            <RotateCcw size={11} /> Start over
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <p className="text-xs text-slate-400 mb-0.5">Source detected</p>
            <p className="text-sm font-bold text-slate-800">
              {result.source_type?.replace(/_/g, ' ') ?? '—'}
            </p>
            <p className="text-xs text-slate-400">{pct(result.source_type_confidence)} confident</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <p className="text-xs text-slate-400 mb-0.5">Parse quality</p>
            <p className="text-sm font-bold text-slate-800">{pct(result.parse_confidence)}</p>
            <p className="text-xs text-slate-400">
              {result.llm_used_for_parse ? 'AI-assisted' : 'Standard parser'}
            </p>
          </div>
        </div>

        {result.warnings?.map((w, i) => (
          <div
            key={i}
            className="flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2"
          >
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />
            {w}
          </div>
        ))}
      </Card>

      {result.txn_found > 0 && (
        <>
          <div>
            <p className="text-xs font-semibold text-slate-500 mb-2 px-1">
              {result.txn_found} rows extracted — scroll to inspect
            </p>
            <RawRowsTable batchId={result.batch_id} />
          </div>
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3 text-sm text-indigo-800">
            To categorise and save these, switch to <strong>Smart Import ✨</strong> mode.
          </div>
        </>
      )}

      <button
        onClick={onReset}
        className="w-full py-2.5 rounded-xl font-semibold text-slate-600 border border-slate-200 hover:bg-slate-50 text-sm flex items-center justify-center gap-2"
      >
        <RotateCcw size={14} /> Import another file
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Processed step (pipeline band stats)
// ---------------------------------------------------------------------------

function ProcessedStep({ result, onReview }) {
  const {
    green_count, yellow_count, red_count,
    new_count, duplicate_count, proposals_generated,
    llm_enhanced_count, warnings,
  } = result;
  const total = (green_count ?? 0) + (yellow_count ?? 0) + (red_count ?? 0);

  return (
    <div className="space-y-4">
      <Card className="px-4 py-4">
        <div className="flex items-center gap-2 mb-4">
          <CheckCircle2 size={18} className="text-emerald-500" />
          <span className="font-semibold text-slate-800">Pipeline done — here's what we found</span>
          {llm_enhanced_count > 0 && (
            <span className="ml-auto flex items-center gap-1 text-xs font-semibold text-violet-600 bg-violet-50 border border-violet-200 rounded-full px-2 py-0.5">
              <Sparkles size={11} /> AI helped
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <StatTile label="Transactions" value={total} />
          <StatTile label="New (not yet saved)" value={new_count ?? 0} color="text-indigo-600" />
          <StatTile label="Already in ledger" value={duplicate_count ?? 0} color="text-slate-400" />
          <StatTile label="Ready to review" value={proposals_generated ?? 0} color="text-emerald-600" />
        </div>

        <p className="text-xs font-bold text-slate-600 mb-2">Confidence breakdown</p>
        <div className="space-y-2">
          {[
            { label: 'Sorted automatically', count: green_count ?? 0,  band: 'GREEN',  tip: 'High confidence — no action needed' },
            { label: 'Worth a quick look',   count: yellow_count ?? 0, band: 'YELLOW', tip: 'Moderate confidence — glance before saving' },
            { label: 'Need your input',      count: red_count ?? 0,    band: 'RED',    tip: 'Low confidence — assign the category yourself' },
          ].map(({ label, count, band, tip }) => {
            const s = BAND[band];
            const w = total > 0 ? (count / total) * 100 : 0;
            return (
              <div key={band} className={`rounded-lg border px-3 py-2 ${s.bg} ${s.border}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-semibold flex items-center gap-1.5 ${s.text}`}>
                    <BandDot band={band} />{label}
                  </span>
                  <span className={`text-xs font-bold ${s.text}`}>{count}</span>
                </div>
                <div className="h-1 bg-white/60 rounded-full overflow-hidden">
                  <div className={`h-full ${s.bar} rounded-full`} style={{ width: `${w}%` }} />
                </div>
                <p className="text-xs text-slate-400 mt-1">{tip}</p>
              </div>
            );
          })}
        </div>

        {llm_enhanced_count > 0 && (
          <div className="mt-3 flex items-center gap-1.5 text-xs text-violet-700 bg-violet-50 border border-violet-200 rounded-lg px-3 py-2">
            <Sparkles size={12} />
            {llm_enhanced_count} transactions given a helping hand by AI
          </div>
        )}
        {warnings?.map((w, i) => (
          <div
            key={i}
            className="flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2"
          >
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />{w}
          </div>
        ))}
      </Card>

      <button
        onClick={onReview}
        className="w-full py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
      >
        <Eye size={16} /> Review {proposals_generated ?? 0} proposals before saving
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Proposal row helpers
// ---------------------------------------------------------------------------

function acctTypeFromCode(code) {
  const n = parseInt(code, 10);
  if (n >= 1000 && n < 2000) return 'ASSET';
  if (n >= 2000 && n < 3000) return 'LIABILITY';
  if (n >= 3000 && n < 4000) return 'EQUITY';
  if (n >= 4000 && n < 5000) return 'INCOME';
  if (n >= 5000 && n < 6000) return 'EXPENSE';
  return null;
}

const ACCT_STYLE = {
  ASSET:     'bg-sky-50 border-sky-200 text-sky-700',
  LIABILITY: 'bg-orange-50 border-orange-200 text-orange-700',
  EQUITY:    'bg-teal-50 border-teal-200 text-teal-700',
  INCOME:    'bg-emerald-50 border-emerald-200 text-emerald-700',
  EXPENSE:   'bg-rose-50 border-rose-200 text-rose-700',
};

// Returns the "category" line (income/expense/liability) from a proposal's journal lines.
// Bank/asset source lines (1100-1299) are skipped so the user sees what to review.
function getCategoryLine(lines) {
  if (!lines?.length) return null;
  const nonAsset = lines.find(l => parseInt(l.account_code, 10) >= 2000);
  if (nonAsset) return nonAsset;
  const nonBank  = lines.find(l => { const c = parseInt(l.account_code, 10); return !(c >= 1100 && c < 1300); });
  return nonBank ?? lines[lines.length - 1];
}

function AccountCard({ line, side }) {
  const acctType = acctTypeFromCode(line.account_code);
  const cls = ACCT_STYLE[acctType] ?? 'bg-slate-50 border-slate-200 text-slate-600';
  const amount = side === 'DR' ? line.debit : line.credit;
  return (
    <div className={`rounded-lg border p-2.5 ${cls}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="text-xs font-mono opacity-60">{line.account_code}</span>
          {acctType && (
            <span className={`ml-1.5 text-xs font-semibold rounded-full px-1.5 py-0.5 border ${cls}`}>
              {acctType}
            </span>
          )}
          <p className="text-sm font-semibold mt-0.5 leading-tight">{line.account_name}</p>
        </div>
        <span className="text-sm font-bold shrink-0">₹{fmt(amount)}</span>
      </div>
    </div>
  );
}

function JournalPanel({ lines, is_balanced }) {
  const drLines = (lines ?? []).filter((l) => parseFloat(l.debit) > 0);
  const crLines = (lines ?? []).filter((l) => parseFloat(l.credit) > 0);
  const totalDr = drLines.reduce((s, l) => s + parseFloat(l.debit), 0);
  const totalCr = crLines.reduce((s, l) => s + parseFloat(l.credit), 0);
  return (
    <div>
      <div
        className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold mb-3 ${
          is_balanced
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}
      >
        {is_balanced ? (
          <><CheckCircle2 size={12} /> Balanced — DR = CR = ₹{fmt(totalDr)}</>
        ) : (
          <><AlertTriangle size={12} /> Unbalanced — DR ₹{fmt(totalDr)}  CR ₹{fmt(totalCr)}</>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-xs font-bold text-blue-600 mb-1.5">Debit (DR)</p>
          <div className="space-y-1.5">
            {drLines.map((l, i) => <AccountCard key={i} line={l} side="DR" />)}
          </div>
        </div>
        <div>
          <p className="text-xs font-bold text-violet-600 mb-1.5">Credit (CR)</p>
          <div className="space-y-1.5">
            {crLines.map((l, i) => <AccountCard key={i} line={l} side="CR" />)}
          </div>
        </div>
      </div>
    </div>
  );
}

// Editable account cell — custom filtered combobox (no datalist)
function EditableAccountCell({ line, lineIdx, allAccounts, proposalId, side, onUpdateLine }) {
  const [editing, setEditing]       = useState(false);
  const [query, setQuery]           = useState('');
  const [highlighted, setHighlighted] = useState(0);
  const inputRef = useRef();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allAccounts.slice(0, 8);
    return allAccounts
      .filter(a => {
        const code = String(a.code ?? a.account_id ?? '');
        const name = (a.name ?? a.account_name ?? '').toLowerCase();
        return code.startsWith(q) || name.includes(q);
      })
      .slice(0, 8);
  }, [query, allAccounts]);

  const startEdit = () => {
    setQuery('');
    setHighlighted(0);
    setEditing(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const commit = (acct) => {
    setEditing(false);
    setQuery('');
    if (!acct || !line || lineIdx < 0) return;
    const code = acct.code ?? acct.account_id;
    if (code !== line?.account_code)
      onUpdateLine(proposalId, lineIdx, code, acct.name ?? acct.account_name ?? code);
  };

  const cancel = () => { setEditing(false); setQuery(''); };

  const amt = line ? (side === 'dr' ? parseFloat(line.debit) : parseFloat(line.credit)) : 0;

  return (
    <div className="relative min-w-0">
      {editing ? (
        <>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search by code or name…"
            value={query}
            onChange={e => { setQuery(e.target.value); setHighlighted(0); }}
            onBlur={() => setTimeout(cancel, 160)}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setHighlighted(h => Math.min(h + 1, filtered.length - 1)); }
              if (e.key === 'ArrowUp')   { e.preventDefault(); setHighlighted(h => Math.max(h - 1, 0)); }
              if (e.key === 'Enter')     { e.preventDefault(); commit(filtered[highlighted]); }
              if (e.key === 'Escape')    cancel();
            }}
            className="w-full text-xs border border-indigo-300 rounded px-1.5 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
          {filtered.length > 0 && (
            <ul className="absolute z-50 top-full left-0 right-0 mt-0.5 bg-white border border-slate-200 rounded-lg shadow-xl overflow-hidden">
              {filtered.map((a, i) => {
                const code = a.code ?? a.account_id;
                const name = a.name ?? a.account_name ?? '';
                return (
                  <li
                    key={a.account_id ?? code}
                    onMouseDown={e => { e.preventDefault(); commit(a); }}
                    onMouseEnter={() => setHighlighted(i)}
                    className={`flex items-center gap-2 px-2.5 py-1.5 cursor-pointer text-xs transition-colors ${
                      i === highlighted ? 'bg-indigo-50' : 'hover:bg-slate-50'
                    }`}
                  >
                    <span className={`font-mono shrink-0 w-10 text-right text-[10px] ${
                      i === highlighted ? 'text-indigo-500' : 'text-slate-400'
                    }`}>{code}</span>
                    <span className={`truncate ${
                      i === highlighted ? 'text-indigo-700 font-medium' : 'text-slate-700'
                    }`}>{name}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ) : (
        <div className="group/cell min-w-0">
          {line ? (
            <>
              {/* Row 1: amount — prominent */}
              <span className={`block font-bold text-sm font-mono leading-tight ${
                side === 'dr' ? 'text-rose-600' : 'text-emerald-600'
              }`}>
                ₹{fmt(amt)}
              </span>
              {/* Row 2: code · name · pencil */}
              <div className="flex items-center gap-1 min-w-0 mt-0.5">
                <span className="text-[10px] font-mono text-slate-400 shrink-0">{line.account_code}</span>
                <span className="text-[10px] text-slate-500 truncate min-w-0" title={line.account_name}>{line.account_name}</span>
                <button
                  onClick={startEdit}
                  className="shrink-0 opacity-0 group-hover/cell:opacity-100 text-slate-300 hover:text-indigo-500 transition-all"
                  title="Edit account"
                ><Pencil size={9} /></button>
              </div>
            </>
          ) : <span className="text-slate-200 text-xs">—</span>}
        </div>
      )}
    </div>
  );
}

const PROPOSAL_PAGE = 25;

function ProposalTableRow({ proposal, approved, rejected, onApprove, onReject, allAccounts, onUpdateLine }) {
  const { narration, txn_date, lines, overall_confidence, confidence_band, proposal_id } = proposal;
  const allLines = lines ?? [];
  const drLine  = allLines.find(l => parseFloat(l.debit)  > 0);
  const crLine  = allLines.find(l => parseFloat(l.credit) > 0);
  const drIdx   = drLine ? allLines.indexOf(drLine) : -1;
  const crIdx   = crLine ? allLines.indexOf(crLine) : -1;
  const s       = BAND[confidence_band?.toUpperCase()] ?? BAND.YELLOW;

  return (
    <tr className={`border-b border-slate-100 transition-colors ${
      approved ? 'bg-emerald-50' : rejected ? 'bg-red-50/50' : 'bg-white hover:bg-slate-50'
    }`}>
      {/* Select */}
      <td className="pl-3 pr-1 py-2">
        <button
          onClick={onApprove}
          className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
            approved ? 'bg-indigo-600 border-indigo-600' : rejected ? 'border-red-300' : 'border-slate-300 hover:border-indigo-400'
          }`}
        >
          {approved && <Check size={10} className="text-white" />}
        </button>
      </td>
      {/* Date */}
      <td className="px-2 py-2 text-xs text-slate-400 whitespace-nowrap">{txn_date ?? '—'}</td>
      {/* Narration */}
      <td className="px-2 py-2 text-xs text-slate-800">
        <p className="truncate" title={narration}>{narration}</p>
      </td>
      {/* DR account + amount */}
      <td className="px-2 py-2">
        <EditableAccountCell
          line={drLine} lineIdx={drIdx}
          allAccounts={allAccounts} proposalId={proposal_id}
          side="dr" onUpdateLine={onUpdateLine}
        />
      </td>
      {/* CR account + amount */}
      <td className="px-2 py-2">
        <EditableAccountCell
          line={crLine} lineIdx={crIdx}
          allAccounts={allAccounts} proposalId={proposal_id}
          side="cr" onUpdateLine={onUpdateLine}
        />
      </td>
      {/* Confidence */}
      <td className="px-2 py-2 whitespace-nowrap">
        <span className={`inline-flex items-center gap-1 text-xs font-semibold px-1.5 py-0.5 rounded-full border ${s.bg} ${s.border} ${s.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
          {Math.round((overall_confidence ?? 0) * 100)}%
        </span>
      </td>
      {/* Reject */}
      <td className="pl-1 pr-3 py-2">
        <button
          onClick={onReject}
          className={`w-5 h-5 rounded-full border flex items-center justify-center transition-all ${
            rejected ? 'bg-red-500 border-red-500 text-white' : 'border-slate-200 text-slate-300 hover:border-red-300 hover:text-red-400'
          }`}
        >
          <X size={9} />
        </button>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Review step — journal table with inline account editing
// ---------------------------------------------------------------------------

const FILTER_OPTS = [
  { key: 'ALL',    label: 'All' },
  { key: 'GREEN',  label: 'Auto-sorted',  tip: 'High confidence — AI sorted these automatically' },
  { key: 'YELLOW', label: 'Check',        tip: 'Moderate confidence — worth a glance' },
  { key: 'RED',    label: 'Needs input',  tip: 'Low confidence — please set the category' },
];

function ReviewStep({ batchId, onCommit }) {
  const [proposals, setProposals]   = useState([]);
  const [allAccounts, setAllAccounts] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [selected, setSelected]     = useState(new Set());
  const [rejected, setRejected]     = useState(new Set());
  const [committing, setCommitting] = useState(false);
  const [filter, setFilter]         = useState('ALL');
  const [page, setPage]             = useState(0);

  useEffect(() => {
    Promise.allSettled([
      API.proposals.list(batchId),
      API.accounts.list(),
    ]).then(([pr, ar]) => {
      if (pr.status === 'fulfilled') {
        const data = pr.value ?? [];
        setProposals(data);
        // Pre-select everything except RED
        setSelected(new Set(data.filter(p => p.confidence_band !== 'RED').map(p => p.proposal_id)));
      } else {
        setError(pr.reason?.message ?? 'Failed to load proposals');
      }
      if (ar.status === 'fulfilled') setAllAccounts(ar.value ?? []);
    }).finally(() => setLoading(false));
  }, [batchId]);

  const toggle = (id) => {
    setSelected(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
    setRejected(prev => { const n = new Set(prev); n.delete(id); return n; });
  };
  const reject = (id) => {
    setRejected(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
    setSelected(prev => { const n = new Set(prev); n.delete(id); return n; });
  };

  const handleUpdateLine = async (proposalId, lineIndex, accountCode, accountName) => {
    try {
      const updated = await API.proposals.updateLine(batchId, proposalId, lineIndex, accountCode, accountName);
      setProposals(prev => prev.map(p => p.proposal_id === proposalId ? updated : p));
    } catch (e) {
      setError(`Could not update account: ${e.message}`);
    }
  };

  const visible     = proposals.filter(p => filter === 'ALL' || p.confidence_band === filter);
  const totalPages  = Math.ceil(visible.length / PROPOSAL_PAGE);
  const pageVisible = visible.slice(page * PROPOSAL_PAGE, (page + 1) * PROPOSAL_PAGE);

  // Reset to page 0 when filter changes
  const setFilterAndPage = (f) => { setFilter(f); setPage(0); };

  const handleCommit = async () => {
    if (!selected.size) return;
    setCommitting(true);
    setError(null);
    try {
      await API.proposals.approve(batchId, [...selected]);
      const res = await API.proposals.commit(batchId);
      onCommit(res);
    } catch (err) {
      setError(err?.body?.detail?.message || err.message || 'Commit failed');
    } finally {
      setCommitting(false);
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center py-12 gap-3 text-slate-400">
      <Spinner /> Loading proposals…
    </div>
  );

  return (
    <div className="space-y-3">
      {/* Filter bar + legend */}
      <Card className="px-3 py-2.5 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-0.5 bg-slate-100 rounded-lg p-0.5">
            {FILTER_OPTS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilterAndPage(key)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                  filter === key ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {key === 'ALL' ? `All (${proposals.length})` : (
                  <span className="flex items-center gap-1">
                    <BandDot band={key} />
                    {label} ({proposals.filter(p => p.confidence_band === key).length})
                  </span>
                )}
              </button>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-2 text-xs">
            <span className="text-slate-400">
              <span className="font-semibold text-indigo-600">{selected.size}</span> / {proposals.length} selected
            </span>
            <button onClick={() => setSelected(new Set(visible.map(p => p.proposal_id)))} className="text-indigo-600 hover:underline">
              Select all
            </button>
            <button onClick={() => setSelected(new Set())} className="text-slate-400 hover:underline">Clear</button>
          </div>
        </div>
        {/* Color legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 border-t border-slate-100">
          {FILTER_OPTS.filter(f => f.tip).map(({ key, tip }) => (
            <span key={key} className="flex items-center gap-1 text-xs text-slate-400">
              <BandDot band={key} />{tip}
            </span>
          ))}
        </div>
      </Card>

      {/* Proposals ledger table */}
      <Card className="overflow-hidden p-0">
        {visible.length === 0 ? (
          <p className="text-center py-8 text-slate-400 text-sm">Nothing for this filter.</p>
        ) : (
          <div className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 300px)' }}>
            <table className="w-full table-fixed text-xs">
              <colgroup>
                <col className="w-8" />
                <col className="w-24" />
                <col className="w-[22%]" />
                <col className="w-[28%]" />
                <col className="w-[28%]" />
                <col className="w-16" />
                <col className="w-8" />
              </colgroup>
              <thead className="sticky top-0 z-10 bg-slate-50 border-b border-slate-100 shadow-sm">
                <tr className="text-xs font-semibold text-slate-500 text-left">
                  <th className="pl-3 pr-1 py-2" />
                  <th className="px-2 py-2">Date</th>
                  <th className="px-2 py-2">Description</th>
                  <th className="px-2 py-2 text-rose-400">Debit (DR) — Account</th>
                  <th className="px-2 py-2 text-emerald-500">Credit (CR) — Account</th>
                  <th className="px-2 py-2">Conf.</th>
                  <th className="pl-1 pr-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {pageVisible.map(p => (
                  <ProposalTableRow
                    key={p.proposal_id}
                    proposal={p}
                    approved={selected.has(p.proposal_id)}
                    rejected={rejected.has(p.proposal_id)}
                    onApprove={() => toggle(p.proposal_id)}
                    onReject={() => reject(p.proposal_id)}
                    allAccounts={allAccounts}
                    onUpdateLine={handleUpdateLine}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-slate-400">
            Rows {page * PROPOSAL_PAGE + 1}–{Math.min((page + 1) * PROPOSAL_PAGE, visible.length)} of {visible.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30"
            >‹ Prev</button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={`w-6 h-6 text-xs rounded border transition-colors ${
                  i === page ? 'bg-indigo-600 border-indigo-600 text-white' : 'border-slate-200 text-slate-500 hover:bg-slate-50'
                }`}
              >{i + 1}</button>
            ))}
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30"
            >Next ›</button>
          </div>
        </div>
      )}

      <ErrorBanner msg={error} />

      <button
        onClick={handleCommit}
        disabled={!selected.size || committing}
        className="w-full py-3 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {committing ? (
          <><Spinner /> Saving…</>
        ) : (
          <><Database size={15} /> Save {selected.size} transactions to ledger</>
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Done step
// ---------------------------------------------------------------------------

function DoneStep({ result, onAnother, onComplete }) {
  const { committed, skipped, already_posted, transaction_ids } = result;
  return (
    <div className="space-y-4">
      <Card className="px-4 py-6 text-center">
        <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-3">
          <CheckCircle2 size={28} className="text-emerald-500" />
        </div>
        <h3 className="text-lg font-bold text-slate-800 mb-1">All saved!</h3>
        <p className="text-sm text-slate-400">Your transactions are now in the ledger.</p>
        <div className="grid grid-cols-3 gap-3 mt-5">
          <StatTile label="Saved"           value={committed ?? 0}      color="text-emerald-600" />
          <StatTile label="Skipped"         value={skipped ?? 0}        color="text-slate-400"   />
          <StatTile label="Already existed" value={already_posted ?? 0} color="text-amber-500"   />
        </div>
        {transaction_ids?.length > 0 && (
          <p className="text-xs text-slate-300 mt-3">
            IDs: {transaction_ids.slice(0, 5).join(', ')}
            {transaction_ids.length > 5 ? ` +${transaction_ids.length - 5} more` : ''}
          </p>
        )}
      </Card>
      {onComplete && (
        <button
          onClick={onComplete}
          className="w-full py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
        >
          Continue to dashboard 
        </button>
      )}
      <button
        onClick={onAnother}
        className="w-full py-2.5 rounded-xl font-semibold text-indigo-600 border-2 border-indigo-100 hover:bg-indigo-50 transition-colors text-sm flex items-center justify-center gap-2"
      >
        <Upload size={14} /> Import another statement
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function StepDots({ steps, current }) {
  return (
    <div className="flex items-center gap-1 mb-6">
      {steps.map((label, i) => {
        const idx    = i + 1;
        const done   = idx < current;
        const active = idx === current;
        return (
          <React.Fragment key={label}>
            <div className="flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
                  done
                    ? 'bg-indigo-600 border-indigo-600 text-white'
                    : active
                    ? 'bg-white border-indigo-500 text-indigo-600'
                    : 'bg-white border-slate-200 text-slate-400'
                }`}
              >
                {done ? <Check size={12} /> : idx}
              </div>
              <span
                className={`text-xs mt-1 font-medium whitespace-nowrap ${
                  active ? 'text-indigo-600' : done ? 'text-indigo-400' : 'text-slate-300'
                }`}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`flex-1 h-0.5 mb-4 mx-1 ${idx < current ? 'bg-indigo-500' : 'bg-slate-100'}`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root wizard
// ---------------------------------------------------------------------------

const PARSE_STEPS    = ['Upload', 'Result'];
const PIPELINE_STEPS = ['Upload', 'Analysed', 'Processed', 'Review', 'Done'];

export default function ImportWizard({ onImportComplete, onNavigate }) {
  //  UI state 
  const [mode, setMode]                   = useState('pipeline'); // 'parse' | 'pipeline'
  const [step, setStep]                   = useState(1);

  //  File + detection
  const [file, setFile]                       = useState(null);
  const [serverDetection, setServerDetection] = useState(null); // result from /detect
  const [detectLoading, setDetectLoading]     = useState(false);
  const [detectError, setDetectError]         = useState(null);
  const [detectedPassword, setDetectedPassword] = useState(''); // password confirmed via /detect
  const [userAccountNum, setUserAccountNum]   = useState('');
  const [userIFSC, setUserIFSC]               = useState('');
  const [bankAccountOverride, setBankAccountOverride] = useState(''); // CoA code override for process step
  const [showOverrides, setShowOverrides]     = useState(false);
  const [overrideAccount, setOverrideAccount] = useState('');
  const [overrideSource,  setOverrideSource]  = useState('');

  //  LLM 
  const [useLlm, setUseLlm]               = useState(false);
  const [providerId, setProviderId]       = useState(null);

  //  Async state 
  const [loading, setLoading]             = useState(false);
  const [parseError, setParseError]       = useState(null);
  const [needsPassword, setNeedsPassword] = useState(false);
  const [pwError, setPwError]             = useState(null);

  //  Results 
  const [parseResult, setParseResult]     = useState(null);
  const [batchOpts, setBatchOpts]         = useState({});
  const [processResult, setProcessResult] = useState(null);
  const [commitResult, setCommitResult]   = useState(null);

  //  Reference data 
  const [accounts, setAccounts]           = useState([]);
  const [sourceTypes, setSourceTypes]     = useState([]);
  const [providers, setProviders]         = useState([]);

  // Bootstrap reference data on mount
  useEffect(() => {
    Promise.allSettled([
      API.accounts.bankable(),
      API.pipeline.sourceTypes(),
      API.llm.list(),
    ]).then(([a, s, p]) => {
      if (a.status === 'fulfilled') setAccounts(a.value ?? []);
      if (s.status === 'fulfilled') setSourceTypes(s.value ?? []);
      if (p.status === 'fulfilled') {
        const pv = p.value ?? [];
        setProviders(pv);
        const def = pv.find((x) => x.is_default) ?? pv[0];
        if (def) setProviderId(def.provider_id);
        if (pv.length > 0) setUseLlm(true);
      }
    });
  }, []);

  //  Actions 

  const reset = () => {
    setStep(1); setFile(null); setServerDetection(null);
    setDetectLoading(false); setDetectError(null); setDetectedPassword('');
    setUserAccountNum(''); setUserIFSC('');
    setBankAccountOverride('');
    setShowOverrides(false); setOverrideAccount(''); setOverrideSource('');
    setNeedsPassword(false); setPwError(null); setParseError(null);
    setParseResult(null); setBatchOpts({}); setProcessResult(null); setCommitResult(null);
  };

  // Run /detect immediately when a file is dropped
  const onFileSelect = async (f) => {
    setFile(f);
    setServerDetection(null);
    setDetectError(null);
    setDetectedPassword('');
    setUserAccountNum('');
    setUserIFSC('');
    setNeedsPassword(false);
    setPwError(null);
    setParseError(null);

    setDetectLoading(true);
    try {
      const result = await API.pipeline.detect(f);
      setServerDetection(result);
      if (result.needs_password) {
        setNeedsPassword(true);
      }
    } catch (_err) {
      setDetectError('Could not pre-scan the file. Bank detection will run during parse.');
    } finally {
      setDetectLoading(false);
    }
  };

  // Called by PasswordPrompt — routes to /detect (if not yet identified) or to /parse
  const onPasswordSubmit = async (pw) => {
    if (!serverDetection || serverDetection.needs_password) {
      setDetectLoading(true);
      setPwError(null);
      try {
        const result = await API.pipeline.detect(file, { password: pw });
        if (result.needs_password) {
          setPwError('Wrong password — please try again.');
          return;
        }
        setServerDetection(result);
        setDetectedPassword(pw);
        setNeedsPassword(false);
      } catch (err) {
        const code = err?.body?.detail?.error;
        if (code === 'WRONG_PASSWORD') {
          setPwError('Wrong password — please try again.');
        } else {
          setPwError(err?.body?.detail?.message || err.message || 'Error unlocking file.');
        }
      } finally {
        setDetectLoading(false);
      }
    } else {
      await runParse(pw);
    }
  };

  // Core parse — also used for password retries
  const runParse = async (password = '') => {
    setLoading(true);
    setParseError(null);
    setPwError(null);
    const opts = {
      accountId:      overrideAccount,
      sourceTypeHint: overrideSource || serverDetection?.source_type || '',
      password:       password || detectedPassword,
      useLlm:         mode === 'pipeline' ? useLlm : false,
      providerId:     mode === 'pipeline' ? providerId : null,
    };
    setBatchOpts(opts);
    try {
      const result = await API.pipeline.parse(file, opts);
      setParseResult(result);
      setNeedsPassword(false);
      setStep(2);
    } catch (err) {
      const code = err?.body?.detail?.error;
      const msg  = err?.body?.detail?.message || err.message;
      if (code === 'WRONG_PASSWORD') {
        setPwError('Wrong password — try again.');
        return;
      }
      if (
        code === 'PDF_ENCRYPTED' ||
        msg?.toLowerCase().includes('encrypt') ||
        msg?.toLowerCase().includes('password')
      ) {
        setNeedsPassword(true);
        return;
      }
      setParseError(msg || 'Parse failed. Please check the file and try again.');
    } finally {
      setLoading(false);
    }
  };

  // Run smart pipeline after parse
  const runProcess = async () => {
    setLoading(true);
    setParseError(null);
    // Resolve the bank account to post against:
    // 1. user explicitly picked a CoA account in step 2  -> bankAccountOverride
    // 2. server resolved it from source_map              -> parseResult.bank_account_code
    // 3. fallback hardcoded default                      -> "1102"
    const resolvedBankAcct = bankAccountOverride || parseResult?.bank_account_code || '1102';
    try {
      const res = await API.pipeline.process(parseResult.batch_id, {
        useLlm,
        providerId:    useLlm ? providerId : null,
        llmForRedOnly: false,
        bankAccountId: resolvedBankAcct,
        accountId:     resolvedBankAcct,
      });
      setProcessResult(res);
      setStep(3);
    } catch (err) {
      setParseError(err?.body?.detail?.message || err.message || 'Processing failed');
    } finally {
      setLoading(false);
    }
  };

  const currentSteps = mode === 'parse' ? PARSE_STEPS : PIPELINE_STEPS;

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6">
      <div className="max-w-4xl mx-auto">

        {/*  Header  */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-lg font-bold text-slate-800"> Time to add some data 🚀</h2>
            {onNavigate && (
              <button
                type="button"
                onClick={() => onNavigate('dashboard')}
                className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 transition-colors"
              >
                <ArrowLeft size={15} />
                Dashboard
              </button>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Drop your statements here — we'll handle the heavy lifting.
          </p>
        </div>

        {/*  Mode selector (only at step 1)  */}
        {step === 1 && (
          <div className="flex gap-2 mb-5">
            <ModeTab
              value="pipeline" current={mode}
              onChange={(m) => { setMode(m); reset(); }}
              icon={Zap} label="Smart Import ✨"
              sub="We'll read, categorize, and safely add it to your ledger"
            />
            <ModeTab
              value="parse" current={mode}
              onChange={(m) => { setMode(m); reset(); }}
              icon={FileText} label="Quick Look ⚡️"
              sub="Just peek at the data without saving anything"
            />
          </div>
        )}

        <StepDots steps={currentSteps} current={step} />

        {/* 
            Step 1 — Upload
            */}
        {step === 1 && (
          <div className="space-y-4">
            <DropZone file={file} onFile={onFileSelect} />

            {file && (
              <DetectionCard
                file={file}
                serverDetection={serverDetection}
                detectLoading={detectLoading}
                detectError={detectError}
                accounts={accounts}
                sourceTypes={sourceTypes}
                userAccountNum={userAccountNum}
                setUserAccountNum={setUserAccountNum}
                userIFSC={userIFSC}
                setUserIFSC={setUserIFSC}
                bankAccountOverride={bankAccountOverride}
                setBankAccountOverride={setBankAccountOverride}
                overrideAccount={overrideAccount}
                setOverrideAccount={setOverrideAccount}
                overrideSource={overrideSource}
                setOverrideSource={setOverrideSource}
                showOverrides={showOverrides}
                setShowOverrides={setShowOverrides}
              />
            )}

            {/* Password prompt — only appears when server says it's encrypted */}
            {needsPassword && (
              <PasswordPrompt
                loading={loading || detectLoading}
                error={pwError}
                onSubmit={onPasswordSubmit}
                fileFormat={serverDetection?.file_format ?? file?.name?.split('.').pop()?.toUpperCase()}
                hint={serverDetection?.password_hint}
              />
            )}

            {/* LLM row — pipeline mode only */}
            {mode === 'pipeline' && file && !needsPassword && (
              <LlmRow
                providers={providers}
                providerId={providerId}
                setProviderId={setProviderId}
                useLlm={useLlm}
                setUseLlm={setUseLlm}
              />
            )}

            <ErrorBanner msg={parseError} />

            {!needsPassword && (
              <button
                onClick={() => runParse('')}
                disabled={!file || loading || detectLoading}
                className="w-full py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <><Spinner /> Reading the file</>
                ) : detectLoading ? (
                  <><Spinner /> Scanning file…</>
                ) : mode === 'pipeline' ? (
                  <><Zap size={16} /> Start import</>
                ) : (
                  <><FileText size={16} /> Parse statement</>
                )}
              </button>
            )}
          </div>
        )}

        {/* 
            Step 2 — Result (Quick Parse mode)
            */}
        {step === 2 && mode === 'parse' && parseResult && (
          <ParseOnlyResult result={parseResult} onReset={reset} />
        )}

        {/* 
            Step 2 — Analysed (Pipeline mode): confirm detection, run pipeline
            */}
        {step === 2 && mode === 'pipeline' && parseResult && (
          <div className="space-y-4">
            <Card className="px-4 py-4">
              <div className="flex items-center gap-2 mb-3">
                {parseResult.txn_found > 0 ? (
                  <CheckCircle2 size={18} className="text-emerald-500 shrink-0" />
                ) : (
                  <XCircle size={18} className="text-red-500 shrink-0" />
                )}
                <span className="text-sm font-bold text-slate-800">
                  {parseResult.txn_found > 0
                    ? `Found ${parseResult.txn_found} transaction${parseResult.txn_found !== 1 ? 's' : ''}`
                    : "Couldn't find any transactions in this file"}
                </span>
                <button
                  onClick={reset}
                  className="ml-auto text-xs text-slate-400 hover:text-indigo-600 flex items-center gap-1"
                >
                  <RotateCcw size={11} /> Different file
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400">Detected source</p>
                  <p className="text-sm font-bold text-slate-800 mt-0.5">
                    {parseResult.source_type?.replace(/_/g, ' ') ?? '—'}
                  </p>
                  <p className="text-xs text-slate-400">
                    {pct(parseResult.source_type_confidence)} confident
                  </p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400">Parse quality</p>
                  <p className="text-sm font-bold text-slate-800 mt-0.5">
                    {pct(parseResult.parse_confidence)}
                  </p>
                  <p className="text-xs text-slate-400">
                    {parseResult.llm_used_for_parse ? 'AI-assisted' : 'Standard parser'}
                  </p>
                </div>
              </div>

              {/* Mapped account — always shown so the user knows where entries will land */}
              <div className="mt-3 pt-3 border-t border-slate-100">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-xs text-slate-400 mb-1">Transactions will be posted to</p>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-slate-600">
                        {bankAccountOverride || parseResult.bank_account_code}
                      </span>
                      <span className="text-sm font-bold text-slate-800">
                        {bankAccountOverride
                          ? (accounts.find(a => (a.code ?? a.account_id) === bankAccountOverride)?.name ?? bankAccountOverride)
                          : parseResult.bank_account_name}
                      </span>
                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full border ${
                        (bankAccountOverride ? '' : parseResult.bank_account_class) === 'LIABILITY'
                          ? 'bg-orange-50 border-orange-200 text-orange-700'
                          : 'bg-sky-50 border-sky-200 text-sky-700'
                      }`}>
                        {bankAccountOverride
                          ? (accounts.find(a => (a.code ?? a.account_id) === bankAccountOverride)?.account_type ?? '')
                          : parseResult.bank_account_class}
                      </span>
                    </div>
                  </div>
                  {accounts.length > 0 && (
                    <div className="shrink-0">
                      <select
                        value={bankAccountOverride}
                        onChange={(e) => setBankAccountOverride(e.target.value)}
                        className="border border-slate-200 rounded-lg px-2 py-1 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
                      >
                        <option value="">Default ({parseResult.bank_account_code} — {parseResult.bank_account_name})</option>
                        {accounts.map((a) => (
                          <option key={a.account_id} value={a.code ?? a.account_id}>
                            {a.code} — {a.name} ({a.account_type})
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              </div>

              {/* Low-confidence: offer source override inline */}
              {parseResult.source_type_confidence < 0.7 && (
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-start gap-1.5">
                    <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                    We're not fully sure about the source — pick one if you know it.
                  </p>
                  <select
                    value={overrideSource}
                    onChange={(e) => setOverrideSource(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  >
                    <option value="">
                      Keep auto-detected ({parseResult.source_type?.replace(/_/g, ' ')})
                    </option>
                    {sourceTypes.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label} ({s.format})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {parseResult.warnings?.map((w, i) => (
                <div
                  key={i}
                  className="flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2"
                >
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  {w}
                </div>
              ))}
            </Card>

            {parseResult.txn_found === 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
                <p className="font-semibold mb-1">Nothing was extracted</p>
                <p className="text-xs text-amber-700">
                  This often happens with scanned / image PDFs. Try exporting a CSV from your
                  bank portal instead.
                </p>
              </div>
            )}

            {parseResult.txn_found > 0 && (
              <LlmRow
                providers={providers}
                providerId={providerId}
                setProviderId={setProviderId}
                useLlm={useLlm}
                setUseLlm={setUseLlm}
              />
            )}

            <ErrorBanner msg={parseError} />

            {parseResult.txn_found > 0 ? (
              <button
                onClick={runProcess}
                disabled={loading}
                className="w-full py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <><Spinner /> Running pipeline</>
                ) : (
                  <><Zap size={15} /> Categorise &amp; analyse {parseResult.txn_found} transactions</>
                )}
              </button>
            ) : (
              <button
                onClick={reset}
                className="w-full py-2.5 rounded-xl font-semibold border border-slate-200 text-slate-600 hover:bg-slate-50 text-sm flex items-center justify-center gap-2"
              >
                <RotateCcw size={14} /> Try a different file
              </button>
            )}
          </div>
        )}

        {/* 
            Step 3 — Processed (Pipeline mode)
            */}
        {step === 3 && processResult && (
          <ProcessedStep result={processResult} onReview={() => setStep(4)} />
        )}

        {/* 
            Step 4 — Review proposals (Pipeline mode)
            */}
        {step === 4 && parseResult && (
          <ReviewStep
            batchId={parseResult.batch_id}
            onCommit={(r) => { setCommitResult(r); setStep(5); }}
          />
        )}

        {/* 
            Step 5 — Done (Pipeline mode)
            */}
        {step === 5 && commitResult && (
          <DoneStep
            result={commitResult}
            onAnother={reset}
            onComplete={onImportComplete}
          />
        )}

      </div>
    </div>
  );
}
