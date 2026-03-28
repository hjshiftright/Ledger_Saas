/**
 * SettingsPage.jsx
 *
 * User-facing settings screen. Sections:
 *   - AI / LLM Providers  — add, edit, test, delete, set default
 *
 * All LLM provider data lives in-memory on the backend (until DB persistence
 * is added). Users should re-enter keys after a server restart.
 */

import React, { useState, useEffect } from 'react';
import {
  Sparkles, Plus, Trash2, CheckCircle2, XCircle, RefreshCw,
  Eye, EyeOff, Star, ChevronDown, ChevronUp, AlertTriangle,
  Cpu,
} from 'lucide-react';
import { API } from './api.js';

// ── Constants ────────────────────────────────────────────────────────────────

// Known models per provider — shown as datalist suggestions in the model fields.
// User can still type any model ID manually.
const PROVIDER_MODELS = {
  gemini: [
    'gemini-3-flash-preview',
    'gemini-2.5-flash-preview',   // recommended default
    'gemini-2.0-flash',           // stable
    'gemini-2.5-pro-preview-03-25', // most capable Gemini as of March 2026
    'gemini-2.0-flash-lite',      // ultra-low cost
    'gemini-1.5-pro',             // legacy
    'gemini-1.5-flash',           // legacy fast
  ],
  openai: [
    'gpt-4o',                     // recommended — multimodal, JSON mode
    'gpt-4.1',                    // latest flagship (March 2025+)
    'gpt-4o-mini',                // lower cost
    'gpt-4-turbo',                // legacy
    'o3-mini',                    // reasoning model (not ideal for extraction)
  ],
  anthropic: [
    'claude-3-7-sonnet-20250219', // recommended — latest (Feb 2025)
    'claude-3-5-sonnet-20241022', // previous generation
    'claude-3-5-haiku-20241022',  // fast + cheap
    'claude-3-opus-20240229',     // most capable (expensive)
  ],
};

const PROVIDER_META = {
  gemini: {
    label: 'Google Gemini',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    defaultTextModel: 'gemini-3-flash-preview',
    defaultVisionModel: 'gemini-3-flash-preview',
    keyPlaceholder: 'AIza…',
    keyHint: 'Get from aistudio.google.com → Get API key',
  },
  openai: {
    label: 'OpenAI',
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    defaultTextModel: 'gpt-4o',
    defaultVisionModel: 'gpt-4o',
    keyPlaceholder: 'sk-…',
    keyHint: 'Get from platform.openai.com → API keys',
  },
  anthropic: {
    label: 'Anthropic Claude',
    color: 'text-violet-600',
    bg: 'bg-violet-50',
    border: 'border-violet-200',
    defaultTextModel: 'claude-3-7-sonnet-20250219',
    defaultVisionModel: 'claude-3-7-sonnet-20250219',
    keyPlaceholder: 'sk-ant-…',
    keyHint: 'Get from console.anthropic.com → API keys',
  },
};

// ── Small shared components ───────────────────────────────────────────────────

function SectionCard({ title, subtitle, icon: Icon, children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm">
      <div className="px-6 py-5 border-b border-slate-100 flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center flex-shrink-0">
          <Icon size={18} className="text-indigo-600" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-slate-800">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

function Badge({ children, color = 'slate' }) {
  const map = {
    slate:  'bg-slate-100 text-slate-600',
    indigo: 'bg-indigo-100 text-indigo-700',
    emerald:'bg-emerald-100 text-emerald-700',
    amber:  'bg-amber-100 text-amber-700',
    red:    'bg-red-100 text-red-700',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${map[color] ?? map.slate}`}>
      {children}
    </span>
  );
}

// ── Provider row (existing) ──────────────────────────────────────────────────

function ProviderRow({ provider, onUpdated, onDeleted }) {
  const meta = PROVIDER_META[provider.provider_name] ?? PROVIDER_META.gemini;
  const [expanded, setExpanded] = useState(false);

  // Edit state
  const [displayName, setDisplayName] = useState(provider.display_name);
  const [apiKey, setApiKey] = useState('');            // blank = keep existing
  const [showKey, setShowKey] = useState(false);
  const [textModel, setTextModel] = useState(provider.text_model || meta.defaultTextModel);
  const [visionModel, setVisionModel] = useState(provider.vision_model || meta.defaultVisionModel);

  // Status
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null); // {ok, latency_ms, error}
  const [deleting, setDeleting] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await API.llm.update(provider.provider_id, {
        displayName,
        apiKey: apiKey || undefined,
        textModel,
        visionModel,
      });
      onUpdated(updated);
      setApiKey('');
      setExpanded(false);
    } catch (err) {
      setSaveError(err?.body?.detail?.message || err.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await API.llm.test(provider.provider_id);
      setTestResult(res);
    } catch (err) {
      setTestResult({ ok: false, error: err?.body?.detail?.message || err.message });
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Remove "${provider.display_name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await API.llm.delete(provider.provider_id);
      onDeleted(provider.provider_id);
    } catch (err) {
      alert(err?.body?.detail?.message || err.message || 'Delete failed');
      setDeleting(false);
    }
  };

  const handleSetDefault = async () => {
    try {
      const updated = await API.llm.update(provider.provider_id, { isDefault: true });
      onUpdated(updated);
    } catch (err) {
      alert(err?.body?.detail?.message || err.message || 'Failed to set default');
    }
  };

  return (
    <div className={`rounded-2xl border ${meta.border} ${meta.bg} overflow-hidden`}>
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`font-semibold text-sm ${meta.color}`}>{meta.label}</span>
            <span className="text-xs text-slate-500 truncate">{provider.display_name}</span>
            {provider.is_default && <Badge color="indigo">Default</Badge>}
          </div>
          <p className="text-xs text-slate-400 mt-0.5 truncate">
            {provider.text_model || meta.defaultTextModel} · ····················
          </p>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Test button */}
          <button
            onClick={handleTest}
            disabled={testing}
            title="Test connection"
            className="p-1.5 rounded-lg hover:bg-white/70 text-slate-500 hover:text-indigo-600 transition-colors disabled:opacity-40"
          >
            {testing
              ? <span className="animate-spin block border-2 border-indigo-400 border-t-transparent rounded-full w-4 h-4" />
              : <RefreshCw size={15} />}
          </button>

          {/* Set default */}
          {!provider.is_default && (
            <button
              onClick={handleSetDefault}
              title="Set as default"
              className="p-1.5 rounded-lg hover:bg-white/70 text-slate-400 hover:text-amber-500 transition-colors"
            >
              <Star size={15} />
            </button>
          )}

          {/* Delete */}
          <button
            onClick={handleDelete}
            disabled={deleting}
            title="Remove provider"
            className="p-1.5 rounded-lg hover:bg-white/70 text-slate-400 hover:text-red-500 transition-colors disabled:opacity-40"
          >
            <Trash2 size={15} />
          </button>

          {/* Expand/collapse */}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 rounded-lg hover:bg-white/70 text-slate-400 hover:text-slate-700 transition-colors"
          >
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        </div>
      </div>

      {/* Test result banner */}
      {testResult && (
        <div className={`mx-4 mb-2 flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium
          ${testResult.ok ? 'bg-emerald-50 border border-emerald-200 text-emerald-700' : 'bg-red-50 border border-red-200 text-red-700'}`}>
          {testResult.ok
            ? <><CheckCircle2 size={13} /> Connected — {testResult.latency_ms}ms</>
            : <><XCircle size={13} /> {testResult.error || 'Connection failed'}</>}
        </div>
      )}

      {/* Expanded edit form */}
      {expanded && (
        <div className="border-t border-white/60 px-4 py-4 bg-white/50 space-y-3">
          {/* Display name */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Display Name</label>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          {/* API Key */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              API Key <span className="text-slate-400 font-normal">(leave blank to keep current)</span>
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={meta.keyPlaceholder}
                className="w-full border border-slate-300 rounded-xl px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1">{meta.keyHint}</p>
          </div>

          {/* Models */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Text Model</label>
              <input
                value={textModel}
                onChange={(e) => setTextModel(e.target.value)}
                placeholder={meta.defaultTextModel}
                className="w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Vision Model</label>
              <input
                value={visionModel}
                onChange={(e) => setVisionModel(e.target.value)}
                placeholder={meta.defaultVisionModel}
                className="w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          </div>

          {saveError && (
            <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
              <XCircle size={13} /> {saveError}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setExpanded(false); setSaveError(null); setApiKey(''); }}
              className="text-sm text-slate-500 hover:text-slate-700 px-4 py-2"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-sm font-semibold bg-indigo-600 text-white px-5 py-2 rounded-xl hover:bg-indigo-700 disabled:opacity-40 transition-colors"
            >
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Add provider form ─────────────────────────────────────────────────────────

function AddProviderForm({ onAdded, onCancel }) {
  const [providerName, setProviderName] = useState('gemini');
  const [displayName, setDisplayName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [textModel, setTextModel] = useState('');
  const [visionModel, setVisionModel] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const meta = PROVIDER_META[providerName];

  // Reset model placeholders when provider changes
  useEffect(() => {
    setTextModel('');
    setVisionModel('');
  }, [providerName]);

  const handleAdd = async () => {
    if (!apiKey.trim()) { setError('API key is required'); return; }
    setSaving(true);
    setError(null);
    try {
      const p = await API.llm.register({
        providerName,
        apiKey: apiKey.trim(),
        displayName: displayName || meta.label,
        isDefault,
      });
      // If user specified custom models, patch them in
      if (textModel || visionModel) {
        const updated = await API.llm.update(p.provider_id, {
          textModel: textModel || undefined,
          visionModel: visionModel || undefined,
        });
        onAdded(updated);
      } else {
        onAdded(p);
      }
    } catch (err) {
      setError(err?.body?.detail?.message || err.message || 'Registration failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5 space-y-4">
      <p className="text-sm font-semibold text-slate-700">Add New Provider</p>

      {/* Provider selector */}
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(PROVIDER_META).map(([key, m]) => (
          <button
            key={key}
            onClick={() => setProviderName(key)}
            className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all
              ${providerName === key
                ? `${m.bg} ${m.border} ${m.color} ring-2 ring-offset-1 ring-indigo-300`
                : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'}`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Display name */}
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Display Name <span className="text-slate-400 font-normal">(optional)</span>
        </label>
        <input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder={meta.label}
          className="w-full border border-slate-300 rounded-xl px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>

      {/* API Key */}
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          API Key <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={meta.keyPlaceholder}
            className="w-full border border-slate-300 rounded-xl px-3 py-2 pr-10 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />
          <button
            type="button"
            onClick={() => setShowKey((v) => !v)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-1">{meta.keyHint}</p>
      </div>

      {/* Models (advanced — collapsible) */}
      <details className="group">
        <summary className="text-xs text-slate-500 cursor-pointer hover:text-indigo-600 select-none list-none flex items-center gap-1">
          <ChevronDown size={12} className="group-open:rotate-180 transition-transform" />
          Advanced: override models (optional)
        </summary>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Text Model</label>
            <input
              value={textModel}
              onChange={(e) => setTextModel(e.target.value)}
              placeholder={meta.defaultTextModel}
              className="w-full border border-slate-300 rounded-xl px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Vision Model</label>
            <input
              value={visionModel}
              onChange={(e) => setVisionModel(e.target.value)}
              placeholder={meta.defaultVisionModel}
              className="w-full border border-slate-300 rounded-xl px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
        </div>
      </details>

      {/* Set as default checkbox */}
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={isDefault}
          onChange={(e) => setIsDefault(e.target.checked)}
          className="w-4 h-4 rounded accent-indigo-600"
        />
        <span className="text-xs text-slate-600">Set as default provider for AI-assisted import</span>
      </label>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
          <XCircle size={13} /> {error}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <button
          onClick={() => { onCancel(); }}
          className="text-sm text-slate-500 hover:text-slate-700 px-4 py-2"
        >
          Cancel
        </button>
        <button
          onClick={handleAdd}
          disabled={saving || !apiKey.trim()}
          className="text-sm font-semibold bg-indigo-600 text-white px-5 py-2 rounded-xl hover:bg-indigo-700 disabled:opacity-40 transition-colors flex items-center gap-2"
        >
          {saving ? (
            <><span className="animate-spin block border-2 border-white border-t-transparent rounded-full w-4 h-4" /> Saving…</>
          ) : (
            <><Plus size={15} /> Add Provider</>
          )}
        </button>
      </div>
    </div>
  );
}

// ── LLM Providers section ────────────────────────────────────────────────────

function LlmProvidersSection() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    API.llm.list()
      .then((data) => setProviders(data ?? []))
      .catch(() => setProviders([]))
      .finally(() => setLoading(false));
  }, []);

  const handleAdded = (p) => {
    setProviders((prev) => [...prev, p]);
    setShowAddForm(false);
  };

  const handleUpdated = (updated) => {
    setProviders((prev) => prev.map((p) => {
      // If the updated one is now default, demote all others
      if (updated.is_default && p.provider_id !== updated.provider_id) {
        return { ...p, is_default: false };
      }
      return p.provider_id === updated.provider_id ? updated : p;
    }));
  };

  const handleDeleted = (providerId) => {
    setProviders((prev) => prev.filter((p) => p.provider_id !== providerId));
  };

  return (
    <SectionCard
      title="AI / LLM Providers"
      subtitle="Configure your API keys for AI-assisted transaction categorisation. Keys are stored in memory — re-enter after server restart."
      icon={Sparkles}
    >
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-400 py-2">
          <span className="animate-spin block border-2 border-slate-300 border-t-indigo-500 rounded-full w-4 h-4" />
          Loading…
        </div>
      ) : (
        <div className="space-y-3">
          {/* Existing providers */}
          {providers.length === 0 && !showAddForm && (
            <p className="text-sm text-slate-400 py-2">
              No providers configured. Add one below to enable AI-assisted categorisation during import.
            </p>
          )}
          {providers.map((p) => (
            <ProviderRow
              key={p.provider_id}
              provider={p}
              onUpdated={handleUpdated}
              onDeleted={handleDeleted}
            />
          ))}

          {/* Add form or button */}
          {showAddForm ? (
            <AddProviderForm onAdded={handleAdded} onCancel={() => setShowAddForm(false)} />
          ) : (
            <button
              onClick={() => setShowAddForm(true)}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 border-dashed border-slate-300 text-sm font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition-colors"
            >
              <Plus size={15} /> Add Provider
            </button>
          )}
        </div>
      )}
    </SectionCard>
  );
}

// ── Root SettingsPage ─────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-10 space-y-6">
        <div className="mb-2">
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Cpu size={22} className="text-indigo-600" />
            Settings
          </h1>
          <p className="text-slate-500 text-sm mt-1">Configure providers and application preferences.</p>
        </div>

        <LlmProvidersSection />
      </div>
    </div>
  );
}
