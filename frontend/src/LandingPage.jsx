/**
 * LandingPage.jsx
 *
 * Premium landing page with hero section + signup/login authentication flow.
 * Inspired by modern fintech landing pages — clean, confident, minimal.
 *
 * Flow:
 *   1. On mount, calls GET /auth/status to check if users exist
 *   2. First-time: shows signup form (with optional LLM API key)
 *   3. Returning user: shows login form
 *   4. If existing data detected during signup: offers "Start Fresh" (DB reset)
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Eye, EyeOff, ChevronDown, Sparkles,
  Shield, TrendingUp, BarChart2, CheckCircle2, AlertTriangle,
  RefreshCw, X,
} from 'lucide-react';
import { API } from './api.js';

// ── Provider metadata (reused from SettingsPage) ─────────────────────────────

const LLM_PROVIDERS = [
  { key: 'gemini',    label: 'Google Gemini', placeholder: 'AIza…',      hint: 'aistudio.google.com → Get API key' },
  { key: 'openai',    label: 'OpenAI',        placeholder: 'sk-…',       hint: 'platform.openai.com → API keys' },
  { key: 'anthropic', label: 'Anthropic',     placeholder: 'sk-ant-…',   hint: 'console.anthropic.com → API keys' },
];

// ── Animated background blobs ────────────────────────────────────────────────

function BackgroundBlobs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
      <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-indigo-100/60 to-purple-100/40 blur-3xl" />
      <div className="absolute -bottom-40 -left-40 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-blue-100/50 to-cyan-100/30 blur-3xl" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full bg-gradient-to-r from-pink-50/30 to-indigo-50/30 blur-3xl" />
    </div>
  );
}

// ── Mini reconciliation preview card (similar to the reference screenshot) ────

function PreviewCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.8, delay: 0.3 }}
      className="relative"
    >
      <div className="bg-white rounded-2xl shadow-2xl shadow-indigo-200/40 border border-slate-100 p-5 w-[340px]">
        {/* Card header */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">Real-Time Reconciliation</span>
          <div className="flex gap-1">
            <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
          </div>
        </div>

        {/* Mock rows */}
        <div className="space-y-3">
          {[
            { icon: '✓', iconColor: 'text-emerald-500 bg-emerald-50', bars: ['bg-slate-200 w-20', 'bg-slate-200 w-12', 'bg-emerald-400 w-24'] },
            { icon: '✓', iconColor: 'text-emerald-500 bg-emerald-50', bars: ['bg-slate-200 w-16', '', 'bg-emerald-400 w-28'] },
            { icon: '⟳', iconColor: 'text-amber-500 bg-amber-50',    bars: ['bg-slate-200 w-14', 'bg-slate-200 w-10', 'bg-amber-300 w-20'] },
          ].map((row, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${row.iconColor}`}>
                {row.icon}
              </div>
              <div className="flex gap-2 flex-1">
                {row.bars.map((bar, j) => bar && <div key={j} className={`h-2.5 rounded-full ${bar}`} />)}
              </div>
            </div>
          ))}
        </div>

        {/* Balance synced status */}
        <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
          <div>
            <p className="text-[9px] font-bold tracking-widest text-slate-400 uppercase">Balance Status</p>
            <p className="text-sm font-bold text-indigo-700">Perfectly Synced</p>
          </div>
          <div className="w-10 h-10 rounded-xl border-2 border-indigo-200 flex items-center justify-center">
            <CheckCircle2 size={18} className="text-indigo-500" />
          </div>
        </div>
      </div>

      {/* Floating arrow */}
      <div className="absolute -right-8 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white shadow-lg border border-slate-100 flex items-center justify-center">
        <ArrowRight size={16} className="text-slate-400" />
      </div>
    </motion.div>
  );
}

// ── Feature pills ────────────────────────────────────────────────────────────

function FeaturePills() {
  const features = [
    { icon: Shield, label: 'Double-Entry Accounting' },
    { icon: Sparkles, label: 'AI-Powered Import' },
    { icon: TrendingUp, label: 'Wealth Insights' },
    { icon: BarChart2, label: 'Smart Reports' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.6 }}
      className="flex flex-wrap gap-2 mt-8"
    >
      {features.map(({ icon: Icon, label }) => (
        <span
          key={label}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/80 backdrop-blur border border-slate-100 text-xs font-medium text-slate-600 shadow-sm"
        >
          <Icon size={13} className="text-indigo-500" />
          {label}
        </span>
      ))}
    </motion.div>
  );
}

// ── Auth Form (signup or login) ──────────────────────────────────────────────

function AuthForm({ mode, onSuccess, onSwitchMode, hasExistingUsers, onResetDb }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // LLM provider (signup only)
  const [showLlm, setShowLlm] = useState(false);
  const [llmProvider, setLlmProvider] = useState('gemini');
  const [llmApiKey, setLlmApiKey] = useState('');

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const isSignup = mode === 'signup';
  const selectedProvider = LLM_PROVIDERS.find((p) => p.key === llmProvider);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (isSignup && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 4) {
      setError('Password must be at least 4 characters.');
      return;
    }

    setLoading(true);
    try {
      let res;
      if (isSignup) {
        res = await API.auth.signup({
          email,
          password,
          llmProviderName: showLlm && llmApiKey ? llmProvider : null,
          llmApiKey: showLlm && llmApiKey ? llmApiKey : null,
        });
      } else {
        res = await API.auth.login({ email, password });
      }
      // Store session (non-persistent across browser sessions)
      sessionStorage.setItem('ledger_auth_token', res.token);
      sessionStorage.setItem('ledger_user_email', res.email);
      sessionStorage.setItem('ledger_user_id', String(res.user_id));

      if (isSignup) {
        localStorage.removeItem('onboarding_v2_complete');
        localStorage.removeItem('onboarding_v2_data');
      }

      onSuccess(res);
    } catch (err) {
      const detail = err?.body?.detail;
      setError(detail?.message || err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      key={mode}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.35 }}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-800 font-display">
            {isSignup ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {isSignup
              ? 'Set up your personal finance ledger in seconds.'
              : 'Sign in to access your ledger.'}
          </p>
        </div>

        {/* Existing data warning (only on signup) */}
        {isSignup && hasExistingUsers && (
          <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-50 border border-amber-200">
            <AlertTriangle size={16} className="text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-xs font-semibold text-amber-800">Existing data detected</p>
              <p className="text-xs text-amber-700 mt-0.5">
                An account already exists. You can{' '}
                <button
                  type="button"
                  onClick={() => onSwitchMode('login')}
                  className="underline font-semibold hover:text-amber-900"
                >
                  sign in
                </button>{' '}
                or{' '}
                <button
                  type="button"
                  onClick={onResetDb}
                  className="underline font-semibold text-red-600 hover:text-red-700"
                >
                  start fresh
                </button>{' '}
                (resets all data).
              </p>
            </div>
          </div>
        )}

        {/* Email */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1.5">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoFocus
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400
                       placeholder:text-slate-300 transition-all"
          />
        </div>

        {/* Password */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1.5">Password</label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={4}
              className="w-full px-4 py-2.5 pr-10 rounded-xl border border-slate-200 bg-white text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400
                         placeholder:text-slate-300 transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </div>

        {/* Confirm password (signup) */}
        {isSignup && (
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Confirm Password</label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={4}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400
                         placeholder:text-slate-300 transition-all"
            />
          </div>
        )}

        {/* Optional LLM API Key (signup only) */}
        {isSignup && (
          <div>
            <button
              type="button"
              onClick={() => setShowLlm((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 transition-colors font-medium"
            >
              <ChevronDown size={13} className={`transition-transform ${showLlm ? 'rotate-180' : ''}`} />
              <Sparkles size={13} />
              Add AI provider key (optional)
            </button>

            <AnimatePresence>
              {showLlm && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 space-y-3">
                    <div className="flex gap-2">
                      {LLM_PROVIDERS.map((p) => (
                        <button
                          key={p.key}
                          type="button"
                          onClick={() => setLlmProvider(p.key)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
                            ${llmProvider === p.key
                              ? 'bg-indigo-600 text-white shadow-sm'
                              : 'bg-white text-slate-500 border border-slate-200 hover:border-indigo-300'}`}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                    <div>
                      <input
                        type="password"
                        value={llmApiKey}
                        onChange={(e) => setLlmApiKey(e.target.value)}
                        placeholder={selectedProvider?.placeholder}
                        className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm
                                   focus:outline-none focus:ring-2 focus:ring-indigo-400
                                   placeholder:text-slate-300"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">{selectedProvider?.hint}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
            <X size={13} className="flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-indigo-600 text-white font-bold text-sm
                     hover:bg-indigo-700 active:scale-[0.98] transition-all
                     disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center justify-center gap-2 shadow-lg shadow-indigo-200/50"
        >
          {loading ? (
            <>
              <span className="animate-spin block border-2 border-white border-t-transparent rounded-full w-4 h-4" />
              {isSignup ? 'Creating account…' : 'Signing in…'}
            </>
          ) : (
            <>
              {isSignup ? 'Get Started' : 'Sign In'}
              <ArrowRight size={15} />
            </>
          )}
        </button>

        {/* Switch mode */}
        <p className="text-center text-xs text-slate-500">
          {isSignup ? (
            <>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => onSwitchMode('login')}
                className="text-indigo-600 font-semibold hover:underline"
              >
                Sign in
              </button>
            </>
          ) : (
            <>
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => onSwitchMode('signup')}
                className="text-indigo-600 font-semibold hover:underline"
              >
                Create one
              </button>
            </>
          )}
        </p>
      </form>
    </motion.div>
  );
}

// ── Reset DB confirmation modal ──────────────────────────────────────────────

function ResetConfirmModal({ onConfirm, onCancel, resetting }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4"
      >
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center flex-shrink-0">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <div>
            <h3 className="font-bold text-slate-800">Start fresh?</h3>
            <p className="text-sm text-slate-500 mt-1">
              This will <span className="font-semibold text-red-600">permanently delete</span> all
              existing data — accounts, transactions, and settings.
              This cannot be undone.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onCancel}
            disabled={resetting}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 font-medium"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={resetting}
            className="px-5 py-2 rounded-xl bg-red-600 text-white text-sm font-bold
                       hover:bg-red-700 disabled:opacity-50 flex items-center gap-2 transition-colors"
          >
            {resetting ? (
              <>
                <span className="animate-spin block border-2 border-white border-t-transparent rounded-full w-3.5 h-3.5" />
                Resetting…
              </>
            ) : (
              <>
                <RefreshCw size={14} />
                Reset & Start Fresh
              </>
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Main Landing Page ────────────────────────────────────────────────────────

export default function LandingPage({ onAuthenticated }) {
  const [authMode, setAuthMode] = useState(null); // null=hero, 'signup', 'login'
  const [hasExistingUsers, setHasExistingUsers] = useState(false);
  const [checking, setChecking] = useState(true);

  // Reset DB confirmation
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetting, setResetting] = useState(false);

  // Check auth status on mount
  useEffect(() => {
    API.auth.status()
      .then((res) => {
        setHasExistingUsers(res.has_users);
        // Auto-show appropriate form
        setAuthMode(res.has_users ? 'login' : 'signup');
      })
      .catch(() => {
        setAuthMode('signup');
      })
      .finally(() => setChecking(false));
  }, []);

  const handleResetDb = async () => {
    setResetting(true);
    try {
      await API.auth.resetDb();
      setHasExistingUsers(false);
      setShowResetModal(false);
      setAuthMode('signup');
      // Clear any stale localStorage
      localStorage.removeItem('ledger_auth_token');
      localStorage.removeItem('ledger_user_email');
      localStorage.removeItem('ledger_user_id');
      localStorage.removeItem('onboarding_v2_complete');
      localStorage.removeItem('onboarding_v2_data');
    } catch (err) {
      alert('Failed to reset database: ' + (err?.body?.detail?.message || err.message));
    } finally {
      setResetting(false);
    }
  };

  const showingForm = authMode === 'signup' || authMode === 'login';

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50 relative overflow-hidden">
      <BackgroundBlobs />

      {/* Top navigation */}
      <header className="relative z-10">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <span className="text-xl font-bold text-slate-800 font-display tracking-tight">Ledger</span>

          <nav className="hidden md:flex items-center gap-8">
            {['Features', 'How it Works', 'Pricing'].map((item) => (
              <span
                key={item}
                className="text-sm text-slate-500 hover:text-slate-800 cursor-default font-medium transition-colors"
              >
                {item}
              </span>
            ))}
          </nav>

          {!showingForm && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={() => setAuthMode(hasExistingUsers ? 'login' : 'signup')}
              className="px-5 py-2 rounded-xl bg-indigo-600 text-white text-sm font-bold
                         hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200/50
                         active:scale-95"
            >
              Get Started
            </motion.button>
          )}
        </div>
      </header>

      {/* Hero + Auth */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 pt-8 md:pt-16 pb-20">
        <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">

          {/* Left — Hero text */}
          <div className="flex-1 max-w-xl">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7 }}
            >
              <h1 className="text-4xl md:text-5xl lg:text-[3.4rem] font-extrabold text-slate-900 leading-[1.1] font-display tracking-tight">
                Your finances, in{' '}
                <span className="text-gradient bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-500 bg-clip-text text-transparent italic">
                  perfect balance.
                </span>
              </h1>

              <p className="mt-6 text-base md:text-lg text-slate-500 leading-relaxed max-w-lg">
                Democratizing personal wealth management with double-entry
                accounting and AI. Precision of an institutional ledger,
                simplicity of a modern app.
              </p>

              {/* CTA button (only when form not shown) */}
              {!showingForm && !checking && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="mt-8 flex gap-3"
                >
                  <button
                    onClick={() => setAuthMode(hasExistingUsers ? 'login' : 'signup')}
                    className="px-7 py-3.5 rounded-2xl bg-indigo-600 text-white font-bold text-sm
                               hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-200/60
                               active:scale-95 flex items-center gap-2"
                  >
                    Get Started <ArrowRight size={16} />
                  </button>
                </motion.div>
              )}

              <FeaturePills />
            </motion.div>
          </div>

          {/* Right — Preview card or Auth form */}
          <div className="flex-shrink-0 w-full lg:w-auto flex justify-center">
            <AnimatePresence mode="wait">
              {checking ? (
                <motion.div
                  key="checking"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 text-sm text-slate-400"
                >
                  <span className="animate-spin block border-2 border-slate-300 border-t-indigo-500 rounded-full w-5 h-5" />
                  Checking…
                </motion.div>
              ) : showingForm ? (
                <motion.div
                  key="auth-form"
                  initial={{ opacity: 0, x: 40 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -40 }}
                  transition={{ duration: 0.4 }}
                  className="w-full max-w-sm"
                >
                  <div className="bg-white/80 backdrop-blur-xl rounded-2xl border border-slate-100
                                  shadow-2xl shadow-indigo-100/40 p-7">
                    <AuthForm
                      mode={authMode}
                      onSuccess={onAuthenticated}
                      onSwitchMode={setAuthMode}
                      hasExistingUsers={hasExistingUsers}
                      onResetDb={() => setShowResetModal(true)}
                    />
                  </div>
                </motion.div>
              ) : (
                <PreviewCard key="preview" />
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>

      {/* Bottom section hint */}
      <div className="relative z-10 text-center pb-10">
        <p className="text-[10px] font-bold tracking-[0.2em] text-indigo-500 uppercase">The Dashboard</p>
        <p className="text-xl md:text-2xl font-bold text-slate-800 font-display mt-1">Precision Intelligence</p>
        <p className="text-xs text-slate-400 mt-1">Every paisa accounted for across all Indian asset classes.</p>
      </div>

      {/* Reset DB modal */}
      <AnimatePresence>
        {showResetModal && (
          <ResetConfirmModal
            onConfirm={handleResetDb}
            onCancel={() => setShowResetModal(false)}
            resetting={resetting}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
