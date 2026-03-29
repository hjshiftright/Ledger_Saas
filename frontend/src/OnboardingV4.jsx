import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Check, ArrowRight, Shield, Briefcase, Store, Home, TrendingUp,
  AlertCircle, GraduationCap, CreditCard, Plus, Lock, LogOut,
  User, LayoutDashboard, Upload, PiggyBank, Target, BarChart2,
  Settings, Layers, RefreshCw, ChevronRight, Edit2,
  Send, Sparkles, Trash2, Pencil, Building2, TrendingDown, Wallet, Landmark, Gem, Car
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';
import PersonalDashboard from './PersonalDashboard';
import WealthDashboard from './WealthDashboard';
import BudgetsPage from './BudgetsPage';
import GoalsPage from './GoalsPage';
import ReportsPage from './ReportsPage';
import ImportWizard from './ImportWizard';
import SettingsPage from './SettingsPage';

// ─── Storage helpers ──────────────────────────────────────────────────────
const SK = {
  sections: 'onboarding_v4_sections',
  profile:  'onboarding_v4_profile',
  mapping:  'onboarding_v4_mapping',
  goals:    'onboarding_v4_goals',
};
const loadJson = (key, fb) => { try { return JSON.parse(localStorage.getItem(key)) || fb; } catch { return fb; } };
const saveJson = (key, val) => localStorage.setItem(key, JSON.stringify(val));

function num(s) { return parseInt(String(s).replace(/\D/g, '')) || 0; }
function inr(v) { return '₹' + num(v).toLocaleString('en-IN'); }

// ─── Shared primitives ────────────────────────────────────────────────────
const FadeIn = ({ children, className = '', delay = 0 }) => (
  <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay }} className={className}>
    {children}
  </motion.div>
);

const Btn = ({ onClick, children, disabled, variant = 'primary', className = '' }) => {
  const base = 'rounded-full py-3 px-7 font-semibold transition-all flex items-center justify-center gap-2 outline-none text-base';
  const v = {
    primary:   'bg-[#2C4A70] hover:bg-[#1F344F] text-white shadow-md disabled:opacity-40 disabled:cursor-not-allowed',
    secondary: 'bg-white border-2 border-slate-200 text-slate-700 hover:border-[#2C4A70] hover:text-[#2C4A70]',
    ghost:     'text-slate-500 hover:text-[#2C4A70] hover:bg-indigo-50 px-3',
  };
  return <button onClick={onClick} disabled={disabled} className={`${base} ${v[variant]} ${className}`}>{children}</button>;
};

const Field = ({ label, value, onChange, placeholder, type = 'text', prefix }) => (
  <div className="flex flex-col gap-1.5">
    {label && <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">{label}</label>}
    <div className="relative">
      {prefix && <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">{prefix}</span>}
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className={`w-full bg-white border-2 border-slate-200 rounded-xl px-4 py-3 text-slate-800 placeholder-slate-400 text-sm
          focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all ${prefix ? 'pl-9' : ''}`} />
    </div>
  </div>
);

const Textarea = ({ value, onChange, placeholder }) => (
  <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={3}
    className="w-full bg-white border-2 border-slate-200 rounded-xl p-4 text-sm text-slate-800 placeholder-slate-400
      focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all resize-none" />
);

// ─── Full-screen Profile Setup ────────────────────────────────────────────
const PERSPECTIVES = [
  { id: 'salaried',  icon: Briefcase, title: 'Salaried',        desc: 'Monthly payroll & tax management' },
  { id: 'business',  icon: Store,     title: 'Business Owner',  desc: 'Separate personal & entity flows' },
  { id: 'homemaker', icon: Home,      title: 'Homemaker',       desc: 'Optimise household allocation' },
  { id: 'investor',  icon: TrendingUp,title: 'Investor',        desc: 'Track multi-asset performance' },
];

function ProfileScreen({ initial, onDone }) {
  const [data, setData] = useState(initial);
  const set = (k, v) => setData(d => ({ ...d, [k]: v }));
  const canSubmit = data.perspective && data.legalName;

  return (
    <div className="min-h-screen bg-[#F7F8F9] flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between px-10 pt-8 pb-0">
        <span className="text-lg italic font-serif font-bold text-[#2C4A70]">The Private Ledger</span>
        <div className="flex items-center gap-2 bg-white border border-slate-200 px-4 py-1.5 rounded-full shadow-sm text-xs font-semibold text-slate-500">
          <Shield size={13} className="text-[#526B5C]" /> Local-Only Mode
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-5xl">

          {/* Heading */}
          <FadeIn className="text-center mb-10">
            <h1 className="text-4xl md:text-5xl font-serif font-black text-[#2C4A70] leading-tight mb-3">
              Welcome to your financial cockpit.
            </h1>
            <p className="text-slate-500 text-lg max-w-xl mx-auto">
              A few quick details help us personalise everything for you.
            </p>
          </FadeIn>

          {/* Perspective — 4 cards in a row */}
          <FadeIn delay={0.08}>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 text-center">
              I primarily manage money as a…
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {PERSPECTIVES.map(({ id, icon: Icon, title, desc }) => {
                const active = data.perspective === id;
                return (
                  <button key={id} onClick={() => set('perspective', id)}
                    className={`relative flex flex-col items-center text-center p-6 rounded-2xl border-2 transition-all cursor-pointer
                      ${active
                        ? 'border-[#2C4A70] bg-white shadow-lg ring-4 ring-[#2C4A70]/10'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'}`}
                  >
                    {active && (
                      <span className="absolute top-3 right-3 bg-[#526B5C] text-white rounded-full p-0.5">
                        <Check size={11} strokeWidth={3} />
                      </span>
                    )}
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-3
                      ${active ? 'bg-[#2C4A70] text-white' : 'bg-slate-100 text-slate-400'}`}>
                      <Icon size={22} />
                    </div>
                    <h3 className={`font-bold text-sm mb-1 ${active ? 'text-[#2C4A70]' : 'text-slate-700'}`}>{title}</h3>
                    <p className="text-xs text-slate-400 leading-snug">{desc}</p>
                  </button>
                );
              })}
            </div>
          </FadeIn>

          {/* Bottom row — name fields + time + optional textarea */}
          <FadeIn delay={0.16}>
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-7 grid md:grid-cols-2 gap-6">

              {/* Left column */}
              <div className="space-y-5">
                <Field label="Your Name *" value={data.legalName} onChange={v => set('legalName', v)} placeholder="Full name" />
                <Field label="Partner's Name" value={data.partnerName} onChange={v => set('partnerName', v)} placeholder="Optional" />

                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2.5">Time available today</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { id: 'express', time: '2–3 min', label: 'Express Sync' },
                      { id: 'deep',    time: '10 min',  label: 'Deep Setup'   },
                    ].map(({ id, time, label }) => {
                      const active = data.timeAvailable === id;
                      return (
                        <button key={id} onClick={() => set('timeAvailable', id)}
                          className={`py-3 px-4 rounded-xl border-2 text-left transition-all
                            ${active ? 'border-[#2C4A70] bg-blue-50/40 shadow-sm' : 'border-slate-200 bg-slate-50 hover:border-slate-300'}`}
                        >
                          <p className={`text-xl font-black font-serif ${active ? 'text-[#2C4A70]' : 'text-slate-600'}`}>{time}</p>
                          <p className="text-xs font-semibold text-slate-400 mt-0.5">{label}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right column */}
              <div className="space-y-5">
                <div>
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
                    Describe your situation <span className="text-slate-300 font-normal normal-case">(optional)</span>
                  </label>
                  <Textarea value={data.householdFor} onChange={v => set('householdFor', v)}
                    placeholder="E.g. Married with two kids, managing joint finances and a rental property…" />
                </div>

                {/* Vellum guarantee */}
                <div className="flex gap-4 items-start bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="w-9 h-9 bg-white rounded-xl shadow-sm flex items-center justify-center shrink-0 mt-0.5">
                    <Shield size={18} className="text-[#2C4A70]" />
                  </div>
                  <div>
                    <p className="font-bold italic font-serif text-[#2C4A70] text-sm">The Vellum Guarantee</p>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                      Your data is encrypted locally. We never see your balances.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>

          {/* CTA */}
          <FadeIn delay={0.22} className="flex justify-center mt-8">
            <Btn onClick={() => onDone(data)} disabled={!canSubmit} className="px-12 py-4 text-lg">
              Set up my Ledger <ArrowRight size={20} />
            </Btn>
          </FadeIn>
        </div>
      </main>
    </div>
  );
}

// ─── Mapping Section ──────────────────────────────────────────────────────

const ASSET_ICONS = { bank: Landmark, property: Home, stocks: TrendingUp, other: Wallet };
const LIABILITY_ICONS = { loan: Building2, credit: CreditCard, other: TrendingDown };

const SUGGESTED_PROMPTS = [
  "I have a savings account with ₹3L in HDFC",
  "I own a flat worth ₹45L in Bangalore",
  "I have a home loan of ₹28L at SBI",
  "My Zerodha portfolio is around ₹12L",
  "Credit card dues of ₹40K on HDFC",
];

// Simulated parser — in prod this would call the API
function parseMessage(text) {
  const t = text.toLowerCase();
  const assets = [];
  const liabilities = [];

  // Simple heuristic detection
  const liabilityKeywords = ['loan', 'emi', 'credit card', 'dues', 'debt', 'owe', 'owing', 'outstanding', 'mortgage'];
  const isLiability = liabilityKeywords.some(k => t.includes(k));

  // Extract amount
  const amountMatch = text.match(/[₹]?\s*(\d[\d,.]*)\s*(l|lakh|lac|k|cr|crore)?/i);
  let value = 0;
  if (amountMatch) {
    const raw = parseFloat(amountMatch[1].replace(/,/g, ''));
    const unit = (amountMatch[2] || '').toLowerCase();
    if (unit === 'l' || unit === 'lakh' || unit === 'lac') value = raw * 100000;
    else if (unit === 'cr' || unit === 'crore') value = raw * 10000000;
    else if (unit === 'k') value = raw * 1000;
    else value = raw;
  }

  // Extract name
  const bankMatch = text.match(/(hdfc|sbi|icici|axis|kotak|idfc|yes bank|bob|pnb|canara|federal|indusind|amex|citi|hsbc|zerodha|groww|upstox|kite|paytm|nps|epf|ppf|lic|bajaj|tata|reliance|idbi)/i);
  const nameHint = bankMatch ? bankMatch[1].toUpperCase() : '';

  let name = '';
  let type = 'other';

  if (t.includes('saving') || t.includes('current') || t.includes('account') || t.includes('fd') || t.includes('fixed deposit')) {
    name = nameHint ? `${nameHint} Savings Account` : 'Bank Account';
    type = 'bank';
  } else if (t.includes('flat') || t.includes('house') || t.includes('apartment') || t.includes('property') || t.includes('plot') || t.includes('land')) {
    name = 'Property';
    type = 'property';
  } else if (t.includes('stock') || t.includes('mf') || t.includes('mutual fund') || t.includes('portfolio') || t.includes('equity') || t.includes('shares') || t.includes('demat')) {
    name = nameHint ? `${nameHint} Portfolio` : 'Equity Portfolio';
    type = 'stocks';
  } else if (t.includes('gold') || t.includes('jewel')) {
    name = 'Gold / Jewellery'; type = 'other';
  } else if (isLiability && (t.includes('home loan') || t.includes('mortgage'))) {
    name = nameHint ? `Home Loan (${nameHint})` : 'Home Loan'; type = 'loan';
  } else if (isLiability && (t.includes('car loan') || t.includes('vehicle'))) {
    name = 'Car Loan'; type = 'loan';
  } else if (isLiability && t.includes('personal loan')) {
    name = 'Personal Loan'; type = 'loan';
  } else if (isLiability && t.includes('credit card')) {
    name = nameHint ? `Credit Card (${nameHint})` : 'Credit Card'; type = 'credit';
  } else if (isLiability) {
    name = 'Loan / Debt'; type = 'other';
  } else {
    name = nameHint || 'Asset'; type = 'other';
  }

  if (value === 0) return null;

  if (isLiability) {
    return { kind: 'liability', item: { id: Date.now(), name, value, type, detail: text } };
  } else {
    return { kind: 'asset', item: { id: Date.now(), name, value, type, detail: text } };
  }
}

function MappingSection({ data, setData, onComplete }) {
  const [messages, setMessages] = useState(() => {
    const hasData = (data.assets?.length || data.liabilities?.length);
    return hasData ? [] : [
      { role: 'ai', text: "I'll help you map your financial picture. Tell me about any account, investment, property, or debt — in plain language. You can add as many as you like." }
    ];
  });
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const assets      = data.assets      || [];
  const liabilities = data.liabilities || [];
  const addAsset = (item) => setData(d => ({ ...d, assets: [...(d.assets || []), { ...item, id: Date.now() + Math.random() }] }));
  const addLib = (item) => setData(d => ({ ...d, liabilities: [...(d.liabilities || []), { ...item, id: Date.now() + Math.random() }] }));

  const handleQuickAdd = (kind, label = 'New Item', type = 'other') => {
    const item = { name: label, value: 0, type };
    if (kind === 'asset') addAsset(item);
    else addLib(item);

    setMessages(prev => [...prev, { 
      role: 'assistant', 
      text: `Got it! I've added a **${label}** placeholder to your list. Could you tell me its current balance or value?`
    }]);
  };

  const simulateAIResponse = (text) => {
    const lowercaseText = text.toLowerCase();
    let message = "I've analyzed your message and mapped the details to your ledger below. ";
    let count = 0;

    // Helper to parse values like "50k", "5L", "20,000"
    const parseValue = (valStr, unitStr) => {
      let val = parseInt(valStr.replace(/,/g, ''));
      if (unitStr) {
        const u = unitStr.toLowerCase();
        if (u.includes('k')) val *= 1000;
        if (u.includes('l') || u.includes('lakh')) val *= 100000;
        if (u.includes('cr') || u.includes('crore')) val *= 10000000;
      }
      return val;
    };

    // 1. ASSETS - Bank Accounts / Savings / FD
    const bankRegex = /(?:i have|savings in|account with|at)\s+([\w\s]+?)\s*(?:(?:savings|bank|account|fd))\s*(?:with|of)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    let match;
    while ((match = bankRegex.exec(lowercaseText)) !== null) {
      const name = match[1].trim().toUpperCase() + " Bank Account";
      const value = parseValue(match[2], match[3]);
      addAsset({ type: 'bank', name, value });
      count++;
    }

    // 2. ASSETS - Property / Real Estate / Flats
    const propertyRegex = /(?:own|plot|flat|property|home|worth)\s*(?:of|in|at)?\s+([\w\s]+?)\s*(?:worth)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = propertyRegex.exec(lowercaseText)) !== null) {
      const name = match[1].trim().toUpperCase() + " Property";
      const value = parseValue(match[2], match[3]);
      addAsset({ type: 'property', name, value });
      count++;
    }

    // 3. ASSETS - Stocks / Portfolio
    const stockRegex = /(?:stocks?|shares?|portfolio|invested in)\s+([\w\s]+?)\s*(?:of|at)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = stockRegex.exec(lowercaseText)) !== null) {
      const name = match[1].trim().toUpperCase() + " Portfolio";
      const value = parseValue(match[2], match[3]);
      addAsset({ type: 'stocks', name, value });
      count++;
    }

    // 4. LIABILITIES - Loans / Mortgages
    const loanRegex = /([\w\s]+?)\s*(?:home|personal|auto|student)?\s*(?:loan|mortgage)\s*(?:of|with|at)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = loanRegex.exec(lowercaseText)) !== null) {
      const name = match[1].trim().toUpperCase() + " Loan";
      const value = parseValue(match[2], match[3]);
      addLib({ type: 'loan', name, detail: 'Fixed rate mortgage', value });
      count++;
    }

    // 5. LIABILITIES - Credit Cards / Dues
    const cardRegex = /([\w\s]+?)\s*(?:credit card|card|debt|dues)\s*(?:of|with|at)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = cardRegex.exec(lowercaseText)) !== null) {
      const name = match[1].trim().toUpperCase() + " Due";
      const value = parseValue(match[2], match[3]);
      addLib({ type: 'card', name, detail: 'Statement balance', value });
      count++;
    }

    if (count === 0) {
      message = "I couldn't quite catch the specific amounts or institutions. Try saying something like 'I have a savings account with 5L in HDFC' or 'HDFC home loan of 30L'.";
    }

    setMessages(prev => [...prev, { role: 'assistant', text: message }]);
  };

  const totalA      = assets.reduce((s, a) => s + a.value, 0);
  const totalL      = liabilities.reduce((s, a) => s + a.value, 0);
  const netWorth    = totalA - totalL;

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = (text) => {
    if (!text.trim()) return;
    const userMsg = { role: 'user', text };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setThinking(true);

    setTimeout(() => {
      simulateAIResponse(text);
      setThinking(false);
      inputRef.current?.focus();
    }, 800);
  };

  const removeAsset = (id) => setData(d => ({ ...d, assets: d.assets.filter(a => a.id !== id) }));
  const removeLib   = (id) => setData(d => ({ ...d, liabilities: d.liabilities.filter(a => a.id !== id) }));
  const handleComplete = () => { saveJson(SK.mapping, data); onComplete(); };
  const hasAny = assets.length > 0 || liabilities.length > 0;

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">

      {/* ── Top bar ─────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 px-8 py-5 flex items-start justify-between shrink-0">
        <div>
          <h2 className="text-3xl font-serif font-black text-[#2C4A70] leading-tight">
            Here's what we understood.
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            We have synthesized your digital footprint into a private architectural view of your wealth.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-6">
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-4 py-2 rounded-full text-[10px] font-bold tracking-widest text-slate-500 uppercase">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span> Safe & Local
          </div>
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-4 py-2 rounded-full text-[10px] font-bold tracking-widest text-slate-500 uppercase">
            <Shield size={12} className="text-[#2C4A70]" /> End-to-End Encrypted
          </div>
        </div>
      </div>

      {/* ── Summary cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-6 px-8 py-6 bg-white border-b border-slate-100 shrink-0">
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[2px] mb-2">What I own</p>
          <div className="flex items-baseline gap-2">
            <p className="text-4xl font-black text-[#2C4A70]">{inr(totalA)}</p>
            <span className="text-[10px] font-bold text-emerald-500 bg-emerald-50 px-1.5 py-0.5 rounded">+2.4%</span>
          </div>
        </div>
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[2px] mb-2">What I owe</p>
          <div className="flex items-baseline gap-2">
            <p className="text-4xl font-black text-[#2C4A70]">{inr(totalL)}</p>
            <span className="text-[10px] font-bold text-rose-500 bg-rose-50 px-1.5 py-0.5 rounded flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" /> Fixed
            </span>
          </div>
        </div>
        <div className="bg-[#2C4A70] rounded-2xl p-6 shadow-xl shadow-[#2C4A70]/20">
          <p className="text-[10px] font-bold text-indigo-200 uppercase tracking-[2px] mb-2">My Net Worth</p>
          <p className="text-4xl font-black text-white">{inr(netWorth)}</p>
        </div>
      </div>

      {/* ── Main split ──────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left — financial map */}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {!hasAny ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-16">
              <div className="w-16 h-16 bg-white rounded-2xl border-2 border-dashed border-slate-200 flex items-center justify-center mb-4">
                <Layers size={28} className="text-slate-300" />
              </div>
              <p className="text-slate-400 font-medium font-serif italic text-lg text-slate-400">Your financial map will appear here.</p>
              <p className="text-slate-300 text-sm mt-2">Start chatting on the right to build your ledger →</p>
              
              <div className="mt-8 flex gap-4">
                <button 
                  onClick={() => handleQuickAdd('asset')}
                  className="px-6 py-2.5 bg-indigo-50 text-[#2C4A70] font-bold text-sm rounded-xl border border-indigo-100 hover:bg-indigo-100 transition-colors"
                >
                  + What I own
                </button>
                <button 
                  onClick={() => handleQuickAdd('liability')}
                  className="px-6 py-2.5 bg-rose-50 text-rose-600 font-bold text-sm rounded-xl border border-rose-100 hover:bg-rose-100 transition-colors"
                >
                  + What I owe
                </button>
              </div>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-x-12 gap-y-10 items-start">
              {/* What I Own Column */}
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-[#2C4A70] rounded flex items-center justify-center text-white">
                      <Wallet size={14} />
                    </div>
                    <h3 className="text-xl font-serif font-black text-[#2C4A70]">What I own</h3>
                  </div>
                  
                  <div className="relative group">
                    <button className="text-xs font-bold text-[#2C4A70] flex items-center gap-1 px-3 py-1.5 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors">
                      <Plus size={14} /> Add
                    </button>
                    <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-xl py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
                      {[
                        { label: 'Bank Account', type: 'bank', icon: Landmark },
                        { label: 'Property / Home', type: 'property', icon: Home },
                        { label: 'Stocks / Funds', type: 'stocks', icon: TrendingUp },
                        { label: 'Gold / Jewelry', type: 'other', icon: Gem },
                        { label: 'Other Asset', type: 'other', icon: Wallet },
                      ].map((opt) => (
                        <button 
                          key={opt.label}
                          onClick={() => handleQuickAdd('asset', opt.label, opt.type)}
                          className="w-full flex items-center gap-2.5 px-4 py-2 hover:bg-slate-50 text-sm font-medium text-slate-700 transition-colors"
                        >
                          <opt.icon size={14} className="text-slate-400" /> {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
                  {assets.map((a) => {
                    const Icon = ASSET_ICONS[a.type] || Wallet;
                    return (
                      <div key={a.id} className="group flex items-center gap-4 px-6 py-5 hover:bg-slate-50 transition-colors">
                        <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0">
                          <Icon size={18} className="text-slate-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Title</p>
                          <p className={`font-bold text-sm truncate ${a.value === 0 ? 'text-slate-400 italic' : 'text-[#2C4A70]'}`}>
                            {a.name}
                          </p>
                        </div>
                        <div className="text-right px-4">
                          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Value</p>
                          <p className={`font-black text-sm ${a.value === 0 ? 'text-rose-400' : 'text-slate-800'}`}>
                            {a.value === 0 ? 'Pending...' : inr(a.value)}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => removeAsset(a.id)} className="text-slate-300 hover:text-red-400 transition-colors p-1.5">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* What I Owe Column */}
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-rose-500 rounded flex items-center justify-center text-white">
                      <Landmark size={14} />
                    </div>
                    <h3 className="text-xl font-serif font-black text-[#2C4A70]">What I owe</h3>
                  </div>

                  <div className="relative group">
                    <button className="text-xs font-bold text-rose-500 flex items-center gap-1 px-3 py-1.5 bg-rose-50 rounded-lg hover:bg-rose-100 transition-colors">
                      <Plus size={14} /> Add
                    </button>
                    <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-xl py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
                      {[
                        { label: 'Home Loan', type: 'loan', icon: Home },
                        { label: 'Personal Loan', type: 'loan', icon: User },
                        { label: 'Car Loan', type: 'loan', icon: Car },
                        { label: 'Credit Card', type: 'card', icon: CreditCard },
                        { label: 'Other Debt', type: 'other', icon: AlertCircle },
                      ].map((opt) => (
                        <button 
                          key={opt.label}
                          onClick={() => handleQuickAdd('liability', opt.label, opt.type)}
                          className="w-full flex items-center gap-2.5 px-4 py-2 hover:bg-slate-50 text-sm font-medium text-slate-700 transition-colors"
                        >
                          <opt.icon size={14} className="text-slate-400" /> {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  {liabilities.map(l => {
                    const isLoan = l.type === 'loan';
                    const isPending = l.value === 0;
                    return (
                      <div key={l.id} className="group bg-white rounded-2xl border border-slate-200 shadow-sm p-6 relative overflow-hidden transition-all hover:shadow-md">
                        {isLoan && <div className="absolute top-0 left-0 bottom-0 w-1 bg-rose-300" />}
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h4 className={`font-bold text-base ${isPending ? 'text-slate-400 italic' : 'text-slate-800'}`}>
                              {l.name}
                            </h4>
                            {!isPending && (
                              <p className="text-[10px] text-slate-400 mt-0.5 font-medium tracking-wide">
                                {isLoan ? '8.4% FIXED RATE' : 'CURRENT BILLING CYCLE'}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {!isPending && <button className="text-slate-300 hover:text-[#2C4A70] p-1.5"><Pencil size={15} /></button>}
                            <button onClick={() => removeLib(l.id)} className="text-slate-300 hover:text-red-400 p-1.5"><Trash2 size={15} /></button>
                          </div>
                        </div>
                        <div className="flex items-end justify-between">
                          <p className={`text-2xl font-black tracking-tight ${isPending ? 'text-rose-400' : 'text-slate-800'}`}>
                            {isPending ? 'Pending balance...' : inr(l.value)}
                          </p>
                          {!isPending && (
                            <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded
                              ${isLoan ? 'text-rose-500' : 'text-slate-400'}`}>
                              {isLoan ? 'Outstanding' : 'Statement'}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-px bg-slate-200 shrink-0" />

        {/* Right — AI assistant sidebar */}
        <div className="w-[380px] shrink-0 flex flex-col bg-white border-l border-slate-100">
          {/* Assistant Header */}
          <div className="px-6 py-5 border-b border-slate-50 flex items-center justify-between bg-white z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#2C4A70] rounded-2xl flex items-center justify-center shadow-lg shadow-[#2C4A70]/20">
                <Sparkles size={18} className="text-white" />
              </div>
              <div>
                <p className="text-sm font-black text-[#2C4A70] tracking-tight">Ledger Assistant</p>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Processing Local</p>
                </div>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.role === 'ai' && (
                  <div className="w-6 h-6 bg-[#2C4A70] rounded-full flex items-center justify-center shrink-0 mr-2 mt-0.5">
                    <Sparkles size={11} className="text-white" />
                  </div>
                )}
                <div className={`max-w-[260px] px-4 py-3 rounded-2xl text-sm leading-relaxed
                  ${m.role === 'user'
                    ? 'bg-[#2C4A70] text-white rounded-tr-sm'
                    : 'bg-slate-100 text-slate-700 rounded-tl-sm'}`}
                  dangerouslySetInnerHTML={{
                    __html: m.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>')
                  }}
                />
              </div>
            ))}
            {thinking && (
              <div className="flex justify-start">
                <div className="w-6 h-6 bg-[#2C4A70] rounded-full flex items-center justify-center shrink-0 mr-2 mt-0.5">
                  <Sparkles size={11} className="text-white" />
                </div>
                <div className="bg-slate-100 px-4 py-3 rounded-2xl rounded-tl-sm flex gap-1 items-center">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Suggested prompts — only before any entries */}
          {!hasAny && messages.length <= 1 && (
            <div className="px-4 pb-2 flex flex-wrap gap-2">
              {SUGGESTED_PROMPTS.slice(0, 3).map((p, i) => (
                <button key={i} onClick={() => sendMessage(p)}
                  className="text-xs bg-slate-50 border border-slate-200 rounded-full px-3 py-1.5 text-slate-500 hover:border-[#2C4A70] hover:text-[#2C4A70] transition-all">
                  {p}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="px-4 pb-4 pt-2 border-t border-slate-100">
            <div className="flex gap-2 items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
                placeholder="E.g. HDFC savings ₹3L, home loan ₹28L…"
                rows={2}
                className="flex-1 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 resize-none focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all"
              />
              <button onClick={() => sendMessage(input)} disabled={!input.trim() || thinking}
                className="w-10 h-10 bg-[#2C4A70] hover:bg-[#1F344F] disabled:opacity-40 rounded-xl flex items-center justify-center transition-all shadow-md shrink-0">
                <Send size={16} className="text-white" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Sticky Footer ───────────────────────────────────────────── */}
      <div className="bg-white border-t border-slate-200 px-8 py-5 flex items-center justify-between shrink-0 shadow-[0_-4px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center gap-2 text-slate-400">
          <AlertCircle size={14} className="text-slate-300" />
          <p className="text-[11px] font-medium">
            All data is kept on your device. We do not store any ledger details on our servers.
          </p>
        </div>
        
        <Btn onClick={handleComplete} disabled={!hasAny} className="px-10 py-4 shadow-xl shadow-[#2C4A70]/20 min-w-[240px]">
          Looks good, continue <ArrowRight size={20} />
        </Btn>
      </div>
    </div>
  );
}

// ─── Goals Section ────────────────────────────────────────────────────────
const GOAL_OPTS = [
  { id: 'emergency', icon: AlertCircle,   label: 'Emergency Fund', desc: 'Prepare for the unexpected' },
  { id: 'home',      icon: Home,          label: 'Buy a Home',     desc: 'Down payment planning' },
  { id: 'retire',    icon: TrendingUp,    label: 'Retire Early',   desc: 'Secure your future' },
  { id: 'education', icon: GraduationCap, label: 'Education',      desc: 'College or upskilling' },
  { id: 'debt',      icon: CreditCard,    label: 'Pay off Debt',   desc: 'Clear loans faster' },
  { id: 'custom',    icon: Plus,          label: 'Custom Goal',    desc: 'Anything else' },
];

function GoalsSection({ data, setData, onComplete }) {
  const [step, setStep] = useState(data.completed ? 2 : 0);

  const toggleGoal = id => setData(d => ({
    ...d, goals: d.goals.includes(id) ? d.goals.filter(g => g !== id) : [...d.goals, id],
  }));

  const totExp = Object.values(data.expenses || {}).reduce((a, b) => a + num(b), 0);
  const inc = num(data.incomeString);
  const surplus = inc - totExp;
  const needs   = Math.min(inc * 0.5, totExp);
  const wants   = Math.min(inc * 0.3, Math.max(0, totExp - needs));
  const savings = Math.max(0, inc - needs - wants);
  const budgetData = [
    { name: 'Needs',          value: needs,   color: '#2C4A70' },
    { name: 'Wants',          value: wants,   color: '#526B5C' },
    { name: 'Savings / Goals',value: savings, color: '#38A169' },
  ];

  const handleComplete = () => { const u = { ...data, completed: true }; setData(u); saveJson(SK.goals, u); onComplete(); };

  const STEPS = ['Goals', 'Cash Flow', 'Budget'];

  return (
    <div className="max-w-2xl mx-auto py-10 px-6 space-y-8">
      <FadeIn>
        <h2 className="text-3xl font-serif font-black text-[#2C4A70]">{STEPS[step]}</h2>
        <p className="text-slate-500 mt-1">
          {step === 0 ? 'Select the milestones that matter most.' : step === 1 ? 'Your monthly income and commitments.' : 'A 50/30/20 starting point.'}
        </p>
      </FadeIn>

      <div className="flex gap-2">
        {STEPS.map((_, i) => (
          <div key={i} className={`h-1.5 flex-1 rounded-full transition-all ${i <= step ? 'bg-[#2C4A70]' : 'bg-slate-200'}`} />
        ))}
      </div>

      <AnimatePresence mode="wait">
        {step === 0 && (
          <motion.div key="g0" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">
            <div className="grid grid-cols-2 gap-3">
              {GOAL_OPTS.map(g => {
                const active = (data.goals || []).includes(g.id);
                return (
                  <button key={g.id} onClick={() => toggleGoal(g.id)}
                    className={`relative flex items-center gap-4 p-4 rounded-2xl border-2 text-left transition-all
                      ${active ? 'border-[#2C4A70] bg-blue-50/30 shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                    {active && <span className="absolute top-2.5 right-2.5 bg-[#526B5C] text-white rounded-full p-0.5"><Check size={11} strokeWidth={3} /></span>}
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${active ? 'bg-[#2C4A70] text-white' : 'bg-slate-100 text-slate-400'}`}>
                      <g.icon size={18} />
                    </div>
                    <div>
                      <p className={`font-bold text-sm ${active ? 'text-[#2C4A70]' : 'text-slate-700'}`}>{g.label}</p>
                      <p className="text-xs text-slate-400">{g.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="flex justify-end">
              <Btn onClick={() => setStep(1)} disabled={!data.goals?.length}>Next: Cash Flow <ArrowRight size={18} /></Btn>
            </div>
          </motion.div>
        )}

        {step === 1 && (
          <motion.div key="g1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-5">
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <Field label="Monthly Income" value={data.incomeString || ''} onChange={v => setData(d => ({ ...d, incomeString: v }))} placeholder="150000" prefix="₹" />
              <div className="grid grid-cols-2 gap-4">
                {Object.keys(data.expenses || {}).map(k => (
                  <Field key={k} label={k} value={data.expenses[k]} prefix="₹"
                    onChange={v => setData(d => ({ ...d, expenses: { ...d.expenses, [k]: v } }))} placeholder="0" />
                ))}
              </div>
            </div>
            {inc > 0 && (
              <div className={`rounded-2xl p-4 flex justify-between items-center border ${surplus >= 0 ? 'bg-emerald-50 border-emerald-100' : 'bg-rose-50 border-rose-100'}`}>
                <span className="text-sm font-semibold text-slate-600">Monthly surplus</span>
                <span className={`text-xl font-black ${surplus >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {surplus >= 0 ? '+' : ''}{inr(surplus)}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <Btn variant="ghost" onClick={() => setStep(0)}>← Back</Btn>
              <Btn onClick={() => setStep(2)} disabled={!data.incomeString}>View Budget <ArrowRight size={18} /></Btn>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div key="g2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-5">
            <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm">
              <div className="flex flex-col sm:flex-row items-center gap-8">
                <div className="w-44 h-44 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={budgetData} innerRadius={50} outerRadius={78} paddingAngle={4} dataKey="value" stroke="none">
                        {budgetData.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <RechartsTooltip formatter={v => inr(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-3 w-full">
                  {budgetData.map(d => (
                    <div key={d.name} className="flex items-center gap-3 bg-slate-50 rounded-xl p-3 border border-slate-100">
                      <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                      <div className="flex-1">
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{d.name}</p>
                        <p className="text-lg font-black text-slate-800">{inr(d.value)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-between">
              <Btn variant="ghost" onClick={() => setStep(1)}>← Back</Btn>
              <Btn onClick={handleComplete}>Complete Goals <Check size={18} /></Btn>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Dashboards Section ───────────────────────────────────────────────────
const DASH_TABS = [
  { id: 'overview',  label: 'Dashboard', icon: LayoutDashboard },
  { id: 'import',    label: 'Import',    icon: Upload          },
  { id: 'budgets',   label: 'Budgets',   icon: PiggyBank       },
  { id: 'goals',     label: 'Goals',     icon: Target          },
  { id: 'wealth',    label: 'Insights',  icon: TrendingUp      },
  { id: 'reports',   label: 'Reports',   icon: BarChart2       },
  { id: 'settings',  label: 'Settings',  icon: Settings        },
];

function DashboardsSection({ onboardingData }) {
  const [tab, setTab] = useState('overview');
  return (
    <div className="flex flex-col h-full">
      {/* Sub-tab bar */}
      <div className="bg-white border-b border-slate-200 px-6 flex items-center gap-0.5 overflow-x-auto shrink-0">
        {DASH_TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-3.5 text-sm font-semibold whitespace-nowrap border-b-2 transition-all
              ${tab === id ? 'border-[#2C4A70] text-[#2C4A70]' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}>
            <Icon size={15} />{label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-[1600px] mx-auto">
          {tab === 'overview'  && <PersonalDashboard onboardingData={onboardingData} onStartImport={() => setTab('import')} onNavigate={setTab} />}
          {tab === 'import'    && <ImportWizard onImportComplete={() => setTab('overview')} onNavigate={setTab} />}
          {tab === 'budgets'   && <BudgetsPage />}
          {tab === 'goals'     && <GoalsPage />}
          {tab === 'wealth'    && <WealthDashboard />}
          {tab === 'reports'   && <ReportsPage />}
          {tab === 'settings'  && <SettingsPage />}
        </div>
      </div>
    </div>
  );
}

// ─── Hub Sidebar + Content ────────────────────────────────────────────────
const NAV = [
  { id: 'mapping',    label: 'Mapping',    icon: Layers,        desc: 'Assets & liabilities' },
  { id: 'goals',      label: 'Goals',      icon: Target,        desc: 'Financial milestones'  },
  { id: 'dashboards', label: 'Dashboards', icon: LayoutDashboard,desc: 'Your financial overview' },
];

const DEFAULT_PROFILE  = { perspective: '', timeAvailable: '', legalName: '', partnerName: '', householdFor: '' };
const DEFAULT_MAPPING  = { rawAssetsMap: '', assets: [], liabilities: [] };
const DEFAULT_GOALS    = { goals: [], incomeString: '', expenses: { housing: '', transport: '', food: '', utilities: '', other: '' }, completed: false };

function Hub({ sections, setSections, profileData, setProfileData, userEmail, onLogout }) {
  const [mappingData, setMappingData] = useState(() => loadJson(SK.mapping, DEFAULT_MAPPING));
  const [goalsData,   setGoalsData]   = useState(() => loadJson(SK.goals,   DEFAULT_GOALS));
  const [active, setActive] = useState(() => {
    if (!sections.mapping) return 'mapping';
    if (!sections.goals)   return 'goals';
    return 'dashboards';
  });

  const canAccess = {
    mapping:    true,
    goals:      Boolean(sections.mapping),
    dashboards: true,   // accessible once hub loads (profiling done)
  };

  const completeSection = (id) => {
    const updated = { ...sections, [id]: true };
    setSections(updated);
    saveJson(SK.sections, updated);
    if (id === 'mapping')    setActive('goals');
    if (id === 'goals')      setActive('dashboards');
  };

  const resetAll = () => {
    Object.values(SK).forEach(k => localStorage.removeItem(k));
    localStorage.removeItem('onboarding_v2_complete');
    localStorage.removeItem('onboarding_v2_data');
    window.location.reload();
  };

  const firstName = profileData.legalName?.split(' ')[0] || '';

  return (
    <div className="flex h-screen bg-[#F7F8F9] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-slate-200 flex flex-col shrink-0">
        {/* Brand */}
        <div className="h-16 flex items-center px-5 border-b border-slate-100">
          <span className="text-base italic font-serif font-bold text-[#2C4A70] leading-tight">The Private Ledger</span>
        </div>

        {/* Profile summary */}
        {firstName && (
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#2C4A70] text-white flex items-center justify-center text-sm font-bold shrink-0">
              {firstName[0].toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-700 truncate">{firstName}</p>
              <button onClick={() => { setSections(s => ({ ...s, profiling: false })); }}
                className="text-xs text-slate-400 hover:text-[#2C4A70] flex items-center gap-1 transition-colors">
                <Edit2 size={10} /> Edit profile
              </button>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {NAV.map(({ id, label, icon: Icon, desc }) => {
            const enabled = canAccess[id];
            const done    = sections[id];
            const isActive = active === id;
            return (
              <button key={id} onClick={() => enabled && setActive(id)} disabled={!enabled} title={!enabled ? 'Complete the previous step first' : desc}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all
                  ${isActive ? 'bg-[#2C4A70] text-white shadow-md shadow-[#2C4A70]/20'
                    : enabled ? 'text-slate-600 hover:text-[#2C4A70] hover:bg-indigo-50'
                    : 'text-slate-300 cursor-not-allowed'}`}>
                <Icon size={17} className="shrink-0" />
                <span className="flex-1 text-left">{label}</span>
                {done && !isActive && <Check size={13} className="text-[#526B5C]" strokeWidth={3} />}
                {!enabled && <Lock size={13} />}
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-slate-100 space-y-0.5">
          {userEmail && <p className="px-4 py-1 text-xs text-slate-400 truncate" title={userEmail}>{userEmail}</p>}
          <button onClick={resetAll} className="w-full flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
            <RefreshCw size={13} /> Reset Setup
          </button>
          {onLogout && (
            <button onClick={onLogout} className="w-full flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors">
              <LogOut size={13} /> Sign Out
            </button>
          )}
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto flex flex-col">
        <AnimatePresence mode="wait">
          {active === 'mapping' && (
            <motion.div key="mapping" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
              <MappingSection data={mappingData} setData={setMappingData} onComplete={() => completeSection('mapping')} />
            </motion.div>
          )}
          {active === 'goals' && (
            <motion.div key="goals" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
              <GoalsSection data={goalsData} setData={setGoalsData} onComplete={() => completeSection('goals')} />
            </motion.div>
          )}
          {active === 'dashboards' && (
            <motion.div key="dashboards" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1 flex flex-col h-full">
              <DashboardsSection onboardingData={profileData} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

// ─── Root export ──────────────────────────────────────────────────────────
export default function OnboardingV4({ userEmail = '', onLogout, onComplete }) {
  const [sections, setSections]       = useState(() => loadJson(SK.sections, {}));
  const [profileData, setProfileData] = useState(() => loadJson(SK.profile,  DEFAULT_PROFILE));

  const handleProfileDone = (data) => {
    setProfileData(data);
    saveJson(SK.profile, data);
    const updated = { ...sections, profiling: true };
    setSections(updated);
    saveJson(SK.sections, updated);
    if (onComplete) onComplete(data);
  };

  // Show the full-screen profile setup until profiling is complete
  if (!sections.profiling) {
    return (
      <AnimatePresence mode="wait">
        <motion.div key="profile" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: 0.35 }}>
          <ProfileScreen initial={profileData} onDone={handleProfileDone} />
        </motion.div>
      </AnimatePresence>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div key="hub" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }} className="h-screen">
        <Hub
          sections={sections}
          setSections={setSections}
          profileData={profileData}
          setProfileData={setProfileData}
          userEmail={userEmail}
          onLogout={onLogout}
        />
      </motion.div>
    </AnimatePresence>
  );
}
