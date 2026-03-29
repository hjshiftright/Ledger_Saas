import React, { useState } from 'react';
import { Eye, EyeOff, X } from 'lucide-react';
import { FadeIn, Button, Input } from './components';
import { HOUSEHOLD_TYPES } from './constants';
import { API } from '../api';

export const BP1Screen = ({ data, updateData, onNext, onAuthenticated }) => {
  const needsAuth = !data.email;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const isFilled = data.name.trim().length > 0 && (!needsAuth || (email && password.length >= 4));

  const handleNext = async () => {
    if (!needsAuth) { onNext(); return; }
    
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
      updateData({ email: res.email });
      onNext();
    } catch(err) {
      setError(err?.body?.detail?.message || err.message || 'Something went wrong while creating account.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto py-12 px-6">
      <FadeIn>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Step 1 of 3</span>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">A bit about you.</h2>
        <p className="text-slate-500 mb-8">This helps us show examples and suggestions that match your life.</p>
        
        <div className="space-y-6">
          <Input label="What should we call you?" value={data.name} onChange={(v) => updateData({ name: v })} placeholder="e.g. Rahul" info="Stored only on this device." />
          
          {needsAuth && (
            <div className="bg-slate-50 border border-slate-200 p-5 rounded-2xl space-y-4">
              <label className="block text-sm font-bold text-slate-700">Account Setup</label>
              <Input type="email" value={email} onChange={setEmail} placeholder="you@example.com" required />
              <div className="relative">
                <Input type={showPassword ? 'text' : 'password'} value={password} onChange={setPassword} placeholder="Password (min 4 chars)" required />
                <button type="button" onClick={() => setShowPassword(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                   {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
             <Input label="Country" value={data.country} onChange={(v) => updateData({ country: v })} />
             <Input label="Currency" value={data.currency} onChange={(v) => updateData({ currency: v })} />
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
              <X size={14} className="flex-shrink-0" /> {error}
            </div>
          )}

        </div>
        
        <div className="mt-10"><Button onClick={handleNext} disabled={!isFilled || loading}>{loading ? 'Creating Account securely...' : 'Next'}</Button></div>
      </FadeIn>
    </div>
  );
};

export const BP2Screen = ({ data, updateData, onNext }) => {
  const isFilled = data.householdType;
  return (
    <div className="max-w-md mx-auto py-12 px-6">
      <FadeIn>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Step 2 of 3</span>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Who do you manage money for?</h2>
        <p className="text-slate-500 mb-8 bg-slate-50 p-4 rounded-xl border border-slate-100 text-sm">
          <strong className="text-slate-700 block mb-1">Why we ask:</strong>
          Knowing your household helps us suggest realistic goals like education, emergency buffers, and shared expenses.
        </p>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-3">Household type</label>
            <div className="grid grid-cols-2 gap-3">
              {HOUSEHOLD_TYPES.map(t => (
                <button
                  key={t.id} onClick={() => updateData({ householdType: t.id })}
                  className={`py-3 px-4 rounded-xl border-2 transition-all font-semibold ${data.householdType === t.id ? 'border-indigo-600 bg-indigo-50/50 text-indigo-700' : 'border-slate-100 bg-white text-slate-600 hover:border-slate-200'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
             <Input label="Dependents (optional)" type="number" value={data.dependents} onChange={(v) => updateData({ dependents: v })} placeholder="0" />
            {['couple', 'family'].includes(data.householdType) && (
              <Input label="Partner's Name" value={data.partnerName} onChange={(v) => updateData({ partnerName: v })} placeholder="Optional" />
            )}
          </div>
        </div>
        <div className="mt-10"><Button onClick={onNext} disabled={!isFilled}>Next</Button></div>
      </FadeIn>
    </div>
  );
};

export const BP3Screen = ({ data, updateData, onNext }) => (
  <div className="max-w-md mx-auto py-12 px-6">
    <FadeIn>
      <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Step 3 of 3</span>
      <h2 className="text-3xl font-extrabold text-slate-900 mb-2">A couple of preferences.</h2>
      <p className="text-slate-500 mb-8 bg-slate-50 p-4 rounded-xl border border-slate-100 text-sm">
        <strong className="text-slate-700 block mb-1">Why we ask:</strong>
        Small things like number format and financial year matter for reports.
      </p>

      <div className="space-y-6 mt-8">
        <div>
           <label className="block text-sm font-semibold text-slate-700 mb-3">Preferred number format</label>
           <div className="flex bg-slate-100 p-1 rounded-xl">
             <button onClick={() => updateData({ numberFormat: 'lakhs' })} className={`flex-1 py-2.5 rounded-lg text-sm font-bold transition-all ${data.numberFormat === 'lakhs' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`}>Lakhs / Crores</button>
             <button onClick={() => updateData({ numberFormat: 'thousands' })} className={`flex-1 py-2.5 rounded-lg text-sm font-bold transition-all ${data.numberFormat === 'thousands' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`}>Millions (1M)</button>
           </div>
        </div>
        
        <Input label="Financial Year Start Month" value={data.financialYearStart} onChange={(v) => updateData({ financialYearStart: v })} />
        
        <div>
           <label className="block text-sm font-semibold text-slate-700 mb-3">Do you currently piece together your finances in another tool?</label>
           <select 
             className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
             value={data.previousTool || ''}
             onChange={(e) => updateData({ previousTool: e.target.value })}
           >
             <option value="">Start fresh (nothing)</option>
             <option value="spreadsheet">Spreadsheet</option>
             <option value="app">Another app</option>
             <option value="paper">Pen and paper</option>
           </select>
        </div>
      </div>
      <div className="mt-10"><Button onClick={onNext}>Let's map your finances</Button></div>
    </FadeIn>
  </div>
);
