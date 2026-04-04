/**
 * LandingPage.jsx — Auth screen matching the OnboardingV4 navy/serif theme.
 */
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Eye, EyeOff, Check, Shield, ChevronDown, Sparkles, AlertTriangle, RefreshCw, X } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { API } from './api.js';

const NAVY = '#2C4A70';
const GREEN_BG = '#E9F0EC';
const GREEN_TEXT = '#526B5C';

const LLM_PROVIDERS = [
  { key: 'gemini',    label: 'Google Gemini', placeholder: 'AIza…',    hint: 'aistudio.google.com → Get API key' },
  { key: 'openai',    label: 'OpenAI',        placeholder: 'sk-…',     hint: 'platform.openai.com → API keys' },
  { key: 'anthropic', label: 'Anthropic',     placeholder: 'sk-ant-…', hint: 'console.anthropic.com → API keys' },
];

const inputCls = `w-full bg-white border-2 border-slate-200 rounded-2xl px-5 py-3.5 text-slate-800
  placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10
  transition-all text-sm`;

function AuthField({ label, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-bold text-slate-500 tracking-widest uppercase">{label}</label>
      {children}
    </div>
  );
}

function AuthForm({ mode, onSuccess, onSwitchMode, hasExistingUsers, onResetDb }) {
  const [email, setEmail]                   = useState('');
  const [password, setPassword]             = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword]     = useState(false);
  const [showLlm, setShowLlm]               = useState(false);
  const [llmProvider, setLlmProvider]       = useState('gemini');
  const [llmApiKey, setLlmApiKey]           = useState('');
  const [error, setError]                   = useState(null);
  const [loading, setLoading]               = useState(false);
  const [googleLoading, setGoogleLoading]   = useState(false);

  const isSignup = mode === 'signup';
  const selectedProvider = LLM_PROVIDERS.find(p => p.key === llmProvider);

  // Google Sign-In: GoogleLogin component returns { credential } which is a signed ID token
  const handleGoogleSuccess = async ({ credential }) => {
    setError(null);
    setGoogleLoading(true);
    try {
      const res = await API.auth.google({ credential });
      const firstTenant = res.tenants?.[0];
      if (!firstTenant) throw new Error('No accessible tenant found.');
      const tokenRes = await API.auth.selectTenant({ userId: res.user_id, tenantId: firstTenant.tenant_id });
      sessionStorage.setItem('ledger_auth_token', tokenRes.access_token);
      sessionStorage.setItem('ledger_user_email', res.email);
      sessionStorage.setItem('ledger_user_id', String(res.user_id));
      onSuccess(res);
    } catch (err) {
      const detail = err?.body?.detail;
      setError(detail?.message || err.message || 'Google sign-in failed.');
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (isSignup && password !== confirmPassword) { setError('Passwords do not match.'); return; }
    if (password.length < 4) { setError('Password must be at least 4 characters.'); return; }

    setLoading(true);
    try {
      let res;
      if (isSignup) {
        res = await API.auth.signup({
          email, password,
          llmProviderName: showLlm && llmApiKey ? llmProvider : null,
          llmApiKey: showLlm && llmApiKey ? llmApiKey : null,
        });
      } else {
        res = await API.auth.login({ email, password });
      }

      // Auto-select first tenant to get scoped JWT
      const firstTenant = res.tenants?.[0];
      if (!firstTenant) throw new Error('No accessible tenant found.');
      const tokenRes = await API.auth.selectTenant({ userId: res.user_id, tenantId: firstTenant.tenant_id });

      sessionStorage.setItem('ledger_auth_token', tokenRes.access_token);
      sessionStorage.setItem('ledger_user_email', res.email);
      sessionStorage.setItem('ledger_user_id', String(res.user_id));

      if (isSignup) {
        localStorage.removeItem('onboarding_v4_complete');
        localStorage.removeItem('onboarding_v4_sections');
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
    <motion.div key={mode} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.3 }}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="mb-6">
          <h2 className="text-2xl font-serif font-black text-[#2C4A70] mb-1">
            {isSignup ? 'Create your ledger.' : 'Welcome back.'}
          </h2>
          <p className="text-sm text-slate-500">
            {isSignup ? 'Set up your private finance cockpit.' : 'Sign in to access your vault.'}
          </p>
        </div>

        {isSignup && hasExistingUsers && (
          <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-50 border border-amber-200">
            <AlertTriangle size={15} className="text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-bold text-amber-800">Existing data detected.</p>
              <p className="text-xs text-amber-700 mt-0.5">
                <button type="button" onClick={() => onSwitchMode('login')} className="underline font-semibold">Sign in</button>
                {' '}or{' '}
                <button type="button" onClick={onResetDb} className="underline font-semibold text-red-600">start fresh</button>.
              </p>
            </div>
          </div>
        )}

        <AuthField label="Email">
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"
            required autoFocus className={inputCls} />
        </AuthField>

        <AuthField label="Password">
          <div className="relative">
            <input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required minLength={4} className={inputCls + ' pr-12'} />
            <button type="button" onClick={() => setShowPassword(v => !v)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </AuthField>

        {isSignup && (
          <AuthField label="Confirm Password">
            <input type={showPassword ? 'text' : 'password'} value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)} placeholder="••••••••"
              required minLength={4} className={inputCls} />
          </AuthField>
        )}

        {isSignup && (
          <div>
            <button type="button" onClick={() => setShowLlm(v => !v)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#2C4A70] transition-colors font-semibold">
              <Sparkles size={12} />
              Add AI provider key (optional)
              <ChevronDown size={12} className={`transition-transform ${showLlm ? 'rotate-180' : ''}`} />
            </button>
            <AnimatePresence>
              {showLlm && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="mt-3 p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                    <div className="flex gap-2">
                      {LLM_PROVIDERS.map(p => (
                        <button key={p.key} type="button" onClick={() => setLlmProvider(p.key)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border
                            ${llmProvider === p.key ? 'bg-[#2C4A70] text-white border-[#2C4A70]' : 'bg-white text-slate-500 border-slate-200 hover:border-[#2C4A70]'}`}>
                          {p.label}
                        </button>
                      ))}
                    </div>
                    <input type="password" value={llmApiKey} onChange={e => setLlmApiKey(e.target.value)}
                      placeholder={selectedProvider?.placeholder} className={inputCls} />
                    <p className="text-[10px] text-slate-400">{selectedProvider?.hint}</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-2xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
            <X size={13} className="shrink-0" /> {error}
          </div>
        )}

        <button type="submit" disabled={loading}
          className="w-full rounded-full py-4 bg-[#2C4A70] hover:bg-[#1F344F] text-white font-semibold text-sm
            transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 mt-2">
          {loading
            ? <><span className="animate-spin block border-2 border-white border-t-transparent rounded-full w-4 h-4" />
                {isSignup ? 'Creating vault…' : 'Signing in…'}</>
            : <>{isSignup ? 'Create vault' : 'Sign in'} <ArrowRight size={16} /></>
          }
        </button>

        {/* Google Sign-In */}
        <div className="relative flex items-center gap-3 my-1">
          <div className="flex-1 h-px bg-slate-200" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest shrink-0">or</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>

        <div className={`flex justify-center transition-opacity ${googleLoading ? 'opacity-50 pointer-events-none' : ''}`}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google sign-in was cancelled or failed.')}
            text={isSignup ? 'signup_with' : 'signin_with'}
            shape="pill"
            theme="outline"
            size="large"
            width="360"
          />
        </div>
        {googleLoading && (
          <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
            <span className="animate-spin block border-2 border-slate-300 border-t-[#2C4A70] rounded-full w-3.5 h-3.5" />
            Signing in with Google…
          </div>
        )}

        <p className="text-center text-xs text-slate-500">
          {isSignup
            ? <>Already have a vault?{' '}<button type="button" onClick={() => onSwitchMode('login')} className="text-[#2C4A70] font-bold hover:underline">Sign in</button></>
            : <>No vault yet?{' '}<button type="button" onClick={() => onSwitchMode('signup')} className="text-[#2C4A70] font-bold hover:underline">Create one</button></>
          }
        </p>
      </form>
    </motion.div>
  );
}

function ResetConfirmModal({ onConfirm, onCancel, resetting }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <motion.div initial={{ scale: 0.92 }} animate={{ scale: 1 }} exit={{ scale: 0.92 }}
        className="bg-white rounded-3xl shadow-2xl p-8 max-w-sm w-full mx-4">
        <div className="flex items-start gap-3 mb-5">
          <div className="w-10 h-10 rounded-2xl bg-red-50 flex items-center justify-center shrink-0">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <div>
            <h3 className="font-bold text-slate-800">Start fresh?</h3>
            <p className="text-sm text-slate-500 mt-1">
              This will <span className="font-semibold text-red-600">permanently delete</span> all data. This cannot be undone.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} disabled={resetting} className="px-4 py-2 text-sm text-slate-600 font-medium hover:text-slate-800">Cancel</button>
          <button onClick={onConfirm} disabled={resetting}
            className="px-5 py-2 rounded-full bg-red-600 text-white text-sm font-bold hover:bg-red-700 disabled:opacity-50 flex items-center gap-2 transition-colors">
            {resetting
              ? <><span className="animate-spin block border-2 border-white border-t-transparent rounded-full w-3.5 h-3.5" /> Resetting…</>
              : <><RefreshCw size={14} /> Reset & Start Fresh</>
            }
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function LandingPage({ onAuthenticated }) {
  const [authMode, setAuthMode]           = useState(null);
  const [hasExistingUsers, setHasUsers]   = useState(false);
  const [checking, setChecking]           = useState(true);
  const [showResetModal, setShowReset]    = useState(false);
  const [resetting, setResetting]         = useState(false);

  useEffect(() => {
    API.auth.status()
      .then(res => { setHasUsers(res.has_users); setAuthMode(res.has_users ? 'login' : 'signup'); })
      .catch(() => setAuthMode('signup'))
      .finally(() => setChecking(false));
  }, []);

  const handleResetDb = async () => {
    setResetting(true);
    try {
      await API.auth.resetDb();
      setHasUsers(false);
      setShowReset(false);
      setAuthMode('signup');
      ['ledger_auth_token','ledger_user_email','ledger_user_id','onboarding_v4_complete','onboarding_v4_sections'].forEach(k => {
        localStorage.removeItem(k); sessionStorage.removeItem(k);
      });
    } catch (err) {
      alert('Failed to reset: ' + (err?.body?.detail?.message || err.message));
    } finally { setResetting(false); }
  };

  const features = [
    'Your data stays on this device — we never upload it.',
    'Set up in short steps, at your own pace.',
    'See useful insights in minutes.',
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row font-sans" style={{ background: '#F7F8F9' }}>
      {/* Left — Brand & Value */}
      <div className="w-full md:w-[45%] bg-white p-10 md:p-16 flex flex-col justify-between min-h-screen border-r border-slate-100">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-xl italic font-serif font-bold tracking-tight" style={{ color: NAVY }}>
            The Private Ledger
          </h1>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="max-w-md my-12">
          <div className="flex items-center gap-3 text-xs font-bold text-slate-400 tracking-widest uppercase mb-6">
            <div className="h-px bg-slate-200 w-8" /> Vault &amp; Vellum Security
          </div>
          <h2 className="text-5xl md:text-6xl font-serif font-black leading-[1.1] mb-6" style={{ color: NAVY }}>
            Welcome to your financial cockpit.
          </h2>
          <p className="text-lg text-slate-500 mb-10 leading-relaxed">
            See where you stand, plan where you're going, and make every rupee count with complete privacy.
          </p>
          <div className="space-y-4">
            {features.map((f, i) => (
              <div key={i} className="flex items-start gap-4">
                <div className="mt-0.5 p-1 rounded-full" style={{ background: GREEN_BG }}>
                  <Check size={14} strokeWidth={3} style={{ color: GREEN_TEXT }} />
                </div>
                <p className="font-medium text-slate-700 text-sm">{f}</p>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          className="p-5 rounded-3xl flex gap-4 items-center" style={{ background: '#F0F4F8' }}>
          <div className="w-12 h-12 bg-white rounded-2xl shadow-sm flex items-center justify-center shrink-0">
            <Shield size={20} style={{ color: NAVY }} />
          </div>
          <div>
            <h4 className="font-bold italic font-serif text-sm" style={{ color: NAVY }}>The Vellum Guarantee</h4>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
              Your ledger is encrypted locally. Not even we can see your balances.
            </p>
          </div>
        </motion.div>
      </div>

      {/* Right — Auth Form */}
      <div className="w-full md:w-[55%] flex flex-col items-center justify-center p-10 md:p-16">
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}
          className="w-full max-w-md">


          <div className="bg-white rounded-[2rem] shadow-xl shadow-slate-200/50 border border-slate-100 p-8 md:p-10">
            {checking ? (
              <div className="flex items-center justify-center gap-3 py-12 text-sm text-slate-400">
                <span className="animate-spin block border-2 border-slate-300 border-t-[#2C4A70] rounded-full w-5 h-5" />
                Checking vault…
              </div>
            ) : (
              <AnimatePresence mode="wait">
                {authMode && (
                  <AuthForm
                    mode={authMode}
                    onSuccess={onAuthenticated}
                    onSwitchMode={setAuthMode}
                    hasExistingUsers={hasExistingUsers}
                    onResetDb={() => setShowReset(true)}
                  />
                )}
              </AnimatePresence>
            )}
          </div>
        </motion.div>
      </div>

      <AnimatePresence>
        {showResetModal && (
          <ResetConfirmModal onConfirm={handleResetDb} onCancel={() => setShowReset(false)} resetting={resetting} />
        )}
      </AnimatePresence>
    </div>
  );
}
