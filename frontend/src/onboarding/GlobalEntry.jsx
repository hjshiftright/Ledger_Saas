import React, { useState } from 'react';
import { Sparkles, Shield, Building2, ChevronRight, EyeOff, Eye, X } from 'lucide-react';
import { FadeIn, Button, Input } from './components';
import { PERSONAS } from './constants';
import { API } from '../api';

export const WelcomeScreen = ({ onNext }) => (
  <div className="max-w-md mx-auto py-12 px-6 flex flex-col h-full justify-center">
    <FadeIn delay={0.1}>
      <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg mb-8">
        <Sparkles className="text-white" size={32} />
      </div>
      <h1 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">Welcome to your financial cockpit.</h1>
      <p className="text-lg text-slate-600 mb-8 leading-relaxed">See where you stand, plan where you're going, and make every rupee count.</p>
    </FadeIn>
    
    <div className="space-y-4 mb-10">
      <FadeIn delay={0.2} className="flex gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
        <Shield className="text-emerald-500 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-bold text-slate-800">Your data stays on this device.</h3>
          <p className="text-sm text-slate-500 mt-0.5">We process your numbers locally. No uploads, no snooping.</p>
        </div>
      </FadeIn>
      <FadeIn delay={0.3} className="flex gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
        <Building2 className="text-indigo-500 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-bold text-slate-800">Done in short steps.</h3>
          <p className="text-sm text-slate-500 mt-0.5">Set up at your own pace. You can always refine values later.</p>
        </div>
      </FadeIn>
    </div>
    
    <FadeIn delay={0.4} className="mt-auto pt-6">
      <Button onClick={onNext}>
        Get started <ChevronRight size={18} />
      </Button>
    </FadeIn>
  </div>
);

export const SignupScreen = ({ onNext, onAuthenticated }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e) => {
    e.preventDefault();
    if(password !== confirmPassword) { setError("Passwords don't match"); return; }
    if(password.length < 4) { setError("Password too short"); return; }
    
    setLoading(true); setError(null);
    try {
      const res = await API.auth.signup({ email, password });
      const firstTenant = res.tenants?.[0];
      if (firstTenant) {
         const tokenRes = await API.auth.selectTenant({ userId: res.user_id, tenantId: firstTenant.tenant_id });
         sessionStorage.setItem('ledger_auth_token', tokenRes.access_token);
      }
      sessionStorage.setItem('ledger_user_email', res.email);
      sessionStorage.setItem('ledger_user_id', String(res.user_id));
      localStorage.removeItem('onboarding_v2_complete');
      localStorage.removeItem('onboarding_v2_data');
      if(onAuthenticated) onAuthenticated(res);
      onNext();
    } catch(err) {
      setError(err?.body?.detail?.message || err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12 px-6 flex flex-col h-full justify-center">
      <FadeIn>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Account Setup</span>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Create your account.</h2>
        <p className="text-slate-500 mb-8">This securely links your local ledger state.</p>
        
        <form onSubmit={handleSignup} className="space-y-4">
          <Input label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" required />
          <div className="relative">
            <Input label="Password" type={showPassword ? 'text' : 'password'} value={password} onChange={setPassword} placeholder="••••••••" required />
            <button type="button" onClick={() => setShowPassword(v => !v)} className="absolute right-3 top-9 text-slate-400">
               {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
           <Input label="Confirm Password" type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={setConfirmPassword} placeholder="••••••••" required />
           
           {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
              <X size={14} className="flex-shrink-0" /> {error}
            </div>
           )}

           <div className="pt-4">
            <Button type="submit" disabled={loading || !email || !password || !confirmPassword}>
               {loading ? 'Creating...' : 'Continue'}
            </Button>
           </div>
        </form>
      </FadeIn>
    </div>
  );
};

export const TriageScreen = ({ data, updateData, onNext }) => {
  const isFilled = data.persona && data.timeAvailable;
  return (
    <div className="max-w-xl mx-auto py-12 px-6">
      <FadeIn>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-8">Help us tailor the experience.</h2>
      </FadeIn>
      
      <div className="space-y-8">
        <FadeIn delay={0.1}>
          <label className="block text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Which best describes you?</label>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {PERSONAS.map(p => {
              const Icon = p.icon;
              const isSelected = data.persona === p.id;
              return (
                <button 
                  key={p.id} onClick={() => updateData({ persona: p.id })}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${isSelected ? 'border-indigo-600 bg-indigo-50/50 shadow-sm' : 'border-slate-100 bg-white hover:border-slate-200'}`}
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${isSelected ? 'bg-indigo-600' : p.color}`}>
                    <Icon size={20} className={isSelected ? 'text-white' : ''} />
                  </div>
                  <p className={`font-semibold text-sm ${isSelected ? 'text-indigo-900' : 'text-slate-700'}`}>{p.label}</p>
                </button>
              );
            })}
          </div>
        </FadeIn>

        <FadeIn delay={0.2}>
          <label className="block text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">How much time do you have right now?</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { id: 'browsing', label: "Just browsing (2-3 mins)" },
              { id: '10mins', label: "I can give around 10 minutes" }
            ].map(t => (
               <button 
                key={t.id} onClick={() => updateData({ timeAvailable: t.id })}
                className={`py-4 px-5 rounded-xl border-2 transition-all ${data.timeAvailable === t.id ? 'border-indigo-600 bg-indigo-50/50 text-indigo-800 font-bold' : 'border-slate-100 bg-white text-slate-600 font-semibold hover:border-slate-200'}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </FadeIn>
      </div>

      <FadeIn delay={0.3} className="mt-12">
        <Button onClick={onNext} disabled={!isFilled}>Continue</Button>
      </FadeIn>
    </div>
  );
};
