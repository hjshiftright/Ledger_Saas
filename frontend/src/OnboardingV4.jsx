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
function inr(v) {
  const n = typeof v === 'number' ? v : num(v);
  const abs = Math.abs(n).toLocaleString('en-IN');
  return n < 0 ? `-₹${abs}` : `₹${abs}`;
}

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

// ─── Add Item Dialog ──────────────────────────────────────────────────────
const ASSET_TYPES  = [
  { type: 'bank',     label: 'Bank / FD',       icon: Landmark,   placeholder: 'e.g. HDFC Savings Account' },
  { type: 'property', label: 'Property',         icon: Home,       placeholder: 'e.g. Apartment in Pune' },
  { type: 'stocks',   label: 'Stocks / Funds',   icon: TrendingUp, placeholder: 'e.g. Zerodha Portfolio' },
  { type: 'other',    label: 'Gold / Other',     icon: Gem,        placeholder: 'e.g. Gold Jewellery' },
];
const LIAB_TYPES   = [
  { type: 'loan',   label: 'Home Loan',      icon: Home,       placeholder: 'e.g. SBI Home Loan' },
  { type: 'loan',   label: 'Personal Loan',  icon: User,       placeholder: 'e.g. HDFC Personal Loan' },
  { type: 'loan',   label: 'Car Loan',       icon: Car,        placeholder: 'e.g. Axis Car Loan' },
  { type: 'credit', label: 'Credit Card',    icon: CreditCard, placeholder: 'e.g. HDFC Credit Card' },
  { type: 'other',  label: 'Other Debt',     icon: AlertCircle,placeholder: 'e.g. Family loan' },
];

function AddItemDialog({ kind: initialKind = 'asset', onAdd, onClose }) {
  const [kind, setKind] = useState(initialKind);
  const types = kind === 'asset' ? ASSET_TYPES : LIAB_TYPES;
  const [selectedType, setSelectedType] = useState(types[0]);
  const [name, setName]   = useState('');
  const [value, setValue] = useState('');
  const [detail, setDetail] = useState('');

  // reset type when kind changes
  const switchKind = (k) => { setKind(k); setSelectedType(k === 'asset' ? ASSET_TYPES[0] : LIAB_TYPES[0]); setName(''); };

  const Icon = selectedType.icon;
  const canAdd = name.trim() && num(value) > 0;

  const handleAdd = () => {
    onAdd({ name: name.trim(), value: num(value), type: selectedType.type, detail: detail.trim() }, kind);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2 }}
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden z-10"
      >
        {/* Header strip — updates when kind toggle changes */}
        <div className={`h-1.5 transition-all ${kind === 'asset' ? 'bg-gradient-to-r from-[#2C4A70] to-emerald-400' : 'bg-gradient-to-r from-rose-400 to-orange-300'}`} />

        <div className="p-8">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-xl font-serif font-black text-[#2C4A70]">Add Item</h3>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors text-lg leading-none">×</button>
          </div>

          {/* Asset / Liability toggle */}
          <div className="flex gap-2 mb-5 bg-slate-100 rounded-xl p-1">
            {['asset', 'liability'].map(k => (
              <button key={k} onClick={() => switchKind(k)}
                className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all capitalize
                  ${kind === k ? (k === 'asset' ? 'bg-[#2C4A70] text-white shadow-sm' : 'bg-rose-500 text-white shadow-sm') : 'text-slate-500 hover:text-slate-700'}`}>
                {k === 'asset' ? 'Asset' : 'Liability'}
              </button>
            ))}
          </div>

          {/* Type selector */}
          <div className="mb-5">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Category</label>
            <div className="grid grid-cols-2 gap-2">
              {types.map(t => {
                const TIcon = t.icon;
                const active = selectedType.label === t.label;
                return (
                  <button key={t.label} onClick={() => { setSelectedType(t); setName(''); }}
                    className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all text-left
                      ${active ? 'border-[#2C4A70] bg-indigo-50 text-[#2C4A70]' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}>
                    <TIcon size={15} className={active ? 'text-[#2C4A70]' : 'text-slate-400'} />
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Name */}
          <div className="mb-4">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Name</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder={selectedType.placeholder}
              className="w-full border-2 border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
          </div>

          {/* Value */}
          <div className="mb-4">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
              {kind === 'asset' ? 'Current Value' : 'Outstanding Amount'}
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
              <input value={value} onChange={e => setValue(e.target.value)} placeholder="0" type="text" inputMode="numeric"
                className="w-full border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
            </div>
            {value && <p className="text-xs text-slate-400 mt-1 pl-1">{inr(value)}</p>}
          </div>

          {/* Note */}
          <div className="mb-7">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
              Note <span className="text-slate-300 font-normal normal-case">(optional)</span>
            </label>
            <input value={detail} onChange={e => setDetail(e.target.value)} placeholder="e.g. interest rate, tenure, institution…"
              className="w-full border-2 border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
          </div>

          <div className="flex gap-3">
            <button onClick={onClose} className="flex-1 py-3 rounded-full border-2 border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-colors">
              Cancel
            </button>
            <button onClick={handleAdd} disabled={!canAdd}
              className={`flex-1 py-3 rounded-full font-semibold text-sm transition-all shadow-md
                ${kind === 'asset'
                  ? 'bg-[#2C4A70] text-white hover:bg-[#1F344F] disabled:opacity-40'
                  : 'bg-rose-500 text-white hover:bg-rose-600 disabled:opacity-40'}
                disabled:cursor-not-allowed`}>
              Add {kind === 'asset' ? 'Asset' : 'Liability'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

// ─── Mapping Section ──────────────────────────────────────────────────────

const ASSET_ICONS = { bank: Landmark, property: Home, stocks: TrendingUp, other: Wallet };
const LIABILITY_ICONS = { loan: Building2, credit: CreditCard, other: TrendingDown };

// Dummy data seeded by perspective — all IDs are negative to distinguish from user-added
const DUMMY_DATA = {
  salaried: {
    assets: [
      { id: -1, name: 'HDFC Savings Account',    value: 850000,   type: 'bank',     detail: 'Primary salary account' },
      { id: -2, name: 'EPF / PF Corpus',          value: 450000,   type: 'other',    detail: 'Employer provident fund' },
      { id: -3, name: 'Nifty 50 Index Fund',      value: 320000,   type: 'stocks',   detail: 'SIP — monthly ₹5,000' },
    ],
    liabilities: [
      { id: -4, name: 'Credit Card (HDFC)',        value: 28000,    type: 'credit',   detail: 'Current billing cycle' },
    ],
  },
  business: {
    assets: [
      { id: -1, name: 'Current Account (ICICI)',   value: 1200000,  type: 'bank',     detail: 'Business operating account' },
      { id: -2, name: 'Commercial Property',       value: 8500000,  type: 'property', detail: 'Office / warehouse' },
      { id: -3, name: 'Equity Portfolio',          value: 600000,   type: 'stocks',   detail: 'Personal investments' },
      { id: -4, name: 'Fixed Deposits',            value: 500000,   type: 'bank',     detail: 'Short-term FDs' },
    ],
    liabilities: [
      { id: -5, name: 'Business Loan (SBI)',       value: 2500000,  type: 'loan',     detail: 'Working capital loan, 11%' },
      { id: -6, name: 'Credit Card (Amex)',        value: 75000,    type: 'credit',   detail: 'Business expenses' },
    ],
  },
  homemaker: {
    assets: [
      { id: -1, name: 'Joint Savings (SBI)',       value: 350000,   type: 'bank',     detail: 'Household savings account' },
      { id: -2, name: 'Gold & Jewellery',          value: 800000,   type: 'other',    detail: 'Approx. current market value' },
      { id: -3, name: 'Residential Apartment',     value: 6500000,  type: 'property', detail: 'Self-occupied home' },
      { id: -4, name: 'RD / SIP',                  value: 120000,   type: 'other',    detail: 'Recurring deposit' },
    ],
    liabilities: [
      { id: -5, name: 'Home Loan (LIC Housing)',   value: 3200000,  type: 'loan',     detail: '8.6% fixed, 18 yrs remaining' },
    ],
  },
  investor: {
    assets: [
      { id: -1, name: 'Zerodha Demat Portfolio',  value: 4500000,  type: 'stocks',   detail: 'Equity + ETFs' },
      { id: -2, name: 'Mutual Funds (HDFC)',       value: 2200000,  type: 'stocks',   detail: 'Large-cap & flexi-cap' },
      { id: -3, name: 'Residential Property',     value: 12000000, type: 'property', detail: 'Rental income asset' },
      { id: -4, name: 'Savings Account',          value: 600000,   type: 'bank',     detail: 'HDFC / ICICI liquid funds' },
      { id: -5, name: 'NPS Corpus',               value: 900000,   type: 'other',    detail: 'National Pension Scheme' },
    ],
    liabilities: [
      { id: -6, name: 'Home Loan (Axis)',         value: 5500000,  type: 'loan',     detail: '9.1% floating, 15 yrs remaining' },
      { id: -7, name: 'Margin Loan (Zerodha)',    value: 300000,   type: 'loan',     detail: 'Pledged securities' },
    ],
  },
};

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

function MappingSection({ data, setData, perspective = 'salaried', onComplete }) {
  // Seed dummy data once on first mount if empty
  const [isDummy, setIsDummy] = useState(() => {
    const hasUserData = (data.assets?.length || data.liabilities?.length);
    if (!hasUserData) {
      const seed = DUMMY_DATA[perspective] || DUMMY_DATA.salaried;
      setData(d => ({ ...d, assets: seed.assets, liabilities: seed.liabilities }));
      return true;
    }
    // All negative IDs = still dummy
    const allNeg = [...(data.assets || []), ...(data.liabilities || [])].every(i => i.id < 0);
    return allNeg && (data.assets?.length > 0 || data.liabilities?.length > 0);
  });

  const [messages, setMessages] = useState([
    { role: 'ai', text: "I've pre-filled a starting map based on your profile. You can edit any entry, remove what doesn't apply, or just tell me what you own and owe in plain language." }
  ]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const clearDummy = () => {
    setData(d => ({ ...d, assets: [], liabilities: [] }));
    setIsDummy(false);
    setMessages(m => [...m, { role: 'ai', text: "Cleared! Start fresh — tell me about your accounts, investments, and any debts." }]);
  };

  const [dialog, setDialog] = useState(null); // 'asset' | 'liability' | null

  const assets      = data.assets      || [];
  const liabilities = data.liabilities || [];
  const addAsset = (item) => { setIsDummy(false); setData(d => ({ ...d, assets: [...(d.assets || []), { ...item, id: Date.now() + Math.random() }] })); };
  const addLib   = (item) => { setIsDummy(false); setData(d => ({ ...d, liabilities: [...(d.liabilities || []), { ...item, id: Date.now() + Math.random() }] })); };

  const handleDialogAdd = (kind, item) => {
    if (kind === 'asset') {
      addAsset(item);
      setMessages(m => [...m, { role: 'ai', text: `Added **${item.name}** (${inr(item.value)}) to your assets. Anything else?` }]);
    } else {
      addLib(item);
      setMessages(m => [...m, { role: 'ai', text: `Recorded **${item.name}** (${inr(item.value)}) as a liability. Anything else to add?` }]);
    }
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

  const removeAsset = (id) => { setIsDummy(false); setData(d => ({ ...d, assets: d.assets.filter(a => a.id !== id) })); };
  const removeLib   = (id) => { setIsDummy(false); setData(d => ({ ...d, liabilities: d.liabilities.filter(a => a.id !== id) })); };
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

      {/* ── Dummy data disclaimer ───────────────────────────────────── */}
      {isDummy && (
        <div className="bg-amber-50 border-b border-amber-200 px-8 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 text-amber-700">
            <span className="text-base">⚠️</span>
            <p className="text-sm font-medium">
              These are <strong>sample figures</strong> based on your profile — not your real data. Edit each entry or clear all and start fresh.
            </p>
          </div>
          <button onClick={clearDummy}
            className="text-xs font-bold text-amber-700 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ml-4">
            Clear & Start Fresh
          </button>
        </div>
      )}

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
        <div className={`rounded-2xl p-6 shadow-xl ${netWorth >= 0 ? 'bg-[#2C4A70] shadow-[#2C4A70]/20' : 'bg-rose-600 shadow-rose-600/20'}`}>
          <p className={`text-[10px] font-bold uppercase tracking-[2px] mb-2 ${netWorth >= 0 ? 'text-indigo-200' : 'text-rose-200'}`}>My Net Worth</p>
          <p className="text-4xl font-black text-white">{inr(netWorth)}</p>
          {netWorth < 0 && <p className="text-[10px] text-rose-200 mt-1">Liabilities exceed assets</p>}
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
              
              <div className="mt-8">
                <button
                  onClick={() => setDialog('add')}
                  className="px-6 py-2.5 bg-indigo-50 text-[#2C4A70] font-bold text-sm rounded-xl border border-indigo-100 hover:bg-indigo-100 transition-colors"
                >
                  <Plus size={14} className="inline mr-1" /> Add
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
                  
                  <button onClick={() => setDialog('add')}
                    className="text-xs font-bold text-[#2C4A70] flex items-center gap-1 px-3 py-1.5 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors">
                    <Plus size={14} /> Add
                  </button>
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

                  <button onClick={() => setDialog('add')}
                    className="text-xs font-bold text-slate-500 flex items-center gap-1 px-3 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors">
                    <Plus size={14} /> Add
                  </button>
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

      {/* Add Item Dialog */}
      <AnimatePresence>
        {dialog && (
          <AddItemDialog
            kind="asset"
            onAdd={(item, kind) => handleDialogAdd(kind, item)}
            onClose={() => setDialog(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Goal Dialog ─────────────────────────────────────────────────────────
const TIMELINE_OPTS = [
  { label: '6 months',  months: 6   },
  { label: '1 year',    months: 12  },
  { label: '2 years',   months: 24  },
  { label: '3 years',   months: 36  },
  { label: '5 years',   months: 60  },
  { label: '10 years',  months: 120 },
  { label: '15 years',  months: 180 },
  { label: '20+ years', months: 240 },
];

function GoalDialog({ goal, existing, onSave, onRemove, onClose }) {
  const Icon = goal.icon;
  const seed = existing || {};
  const [targetAmount, setTargetAmount] = useState(seed.targetAmount ? String(seed.targetAmount) : '');
  const [timelineMonths, setTimelineMonths] = useState(seed.timelineMonths || 12);
  const [priority, setPriority]   = useState(seed.priority   || 'medium');
  const [note, setNote]           = useState(seed.note       || '');

  const canSave = num(targetAmount) > 0;
  const monthlySaving = timelineMonths > 0 ? Math.ceil(num(targetAmount) / timelineMonths) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2 }}
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden z-10"
      >
        <div className="h-1.5 bg-gradient-to-r from-[#2C4A70] to-[#526B5C]" />
        <div className="p-8">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-[#2C4A70]/10 flex items-center justify-center">
                <Icon size={22} className="text-[#2C4A70]" />
              </div>
              <div>
                <h3 className="text-xl font-serif font-black text-[#2C4A70]">{goal.label}</h3>
                <p className="text-xs text-slate-400">{goal.desc}</p>
              </div>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors text-lg leading-none">×</button>
          </div>

          <div className="space-y-5">
            {/* Target amount */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Target Amount</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
                <input value={targetAmount} onChange={e => setTargetAmount(e.target.value)} placeholder="0" inputMode="numeric"
                  className="w-full border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
              </div>
              {num(targetAmount) > 0 && <p className="text-xs text-slate-400 mt-1 pl-1">{inr(num(targetAmount))}</p>}
            </div>

            {/* Timeline */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Timeline</label>
              <div className="grid grid-cols-4 gap-2">
                {TIMELINE_OPTS.map(t => (
                  <button key={t.months} onClick={() => setTimelineMonths(t.months)}
                    className={`py-2 px-1 rounded-xl text-xs font-bold border-2 transition-all text-center
                      ${timelineMonths === t.months ? 'border-[#2C4A70] bg-indigo-50 text-[#2C4A70]' : 'border-slate-200 text-slate-500 hover:border-slate-300'}`}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Monthly savings preview */}
            {canSave && (
              <div className="bg-slate-50 rounded-2xl px-5 py-4 border border-slate-100 flex items-center justify-between">
                <p className="text-sm text-slate-500 font-medium">Monthly saving needed</p>
                <p className="text-lg font-black text-[#2C4A70]">{inr(monthlySaving)}</p>
              </div>
            )}

            {/* Priority */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Priority</label>
              <div className="flex gap-2">
                {[
                  { id: 'high',   label: 'High',   color: 'border-rose-400 bg-rose-50 text-rose-600' },
                  { id: 'medium', label: 'Medium', color: 'border-amber-400 bg-amber-50 text-amber-600' },
                  { id: 'low',    label: 'Low',    color: 'border-slate-300 bg-slate-50 text-slate-500' },
                ].map(p => (
                  <button key={p.id} onClick={() => setPriority(p.id)}
                    className={`flex-1 py-2 rounded-xl border-2 text-xs font-bold transition-all
                      ${priority === p.id ? p.color : 'border-slate-200 text-slate-400 hover:border-slate-300'}`}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Note */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
                Note <span className="text-slate-300 font-normal normal-case">(optional)</span>
              </label>
              <input value={note} onChange={e => setNote(e.target.value)} placeholder="E.g. down payment for a 2BHK in Pune…"
                className="w-full border-2 border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 mt-7">
            {existing && (
              <button onClick={() => { onRemove(goal.id); onClose(); }}
                className="px-4 py-3 rounded-full border-2 border-rose-200 text-rose-500 hover:bg-rose-50 text-sm font-semibold transition-colors">
                Remove
              </button>
            )}
            <button onClick={onClose} className="flex-1 py-3 rounded-full border-2 border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-colors">
              Cancel
            </button>
            <button onClick={() => { onSave({ id: goal.id, targetAmount: num(targetAmount), timelineMonths, priority, note }); onClose(); }}
              disabled={!canSave}
              className="flex-1 py-3 rounded-full bg-[#2C4A70] text-white font-semibold text-sm hover:bg-[#1F344F] disabled:opacity-40 disabled:cursor-not-allowed shadow-md transition-all">
              {existing ? 'Update Goal' : 'Add Goal'}
            </button>
          </div>
        </div>
      </motion.div>
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

// Dummy goals seeded per perspective — ids are strings starting with 'dummy_'
const DUMMY_GOALS = {
  salaried: [
    { id: 'emergency', targetAmount: 300000,  timelineMonths: 12, note: '3× monthly salary as safety net' },
    { id: 'retire',    targetAmount: 10000000, timelineMonths: 240, note: 'FIRE target at 50' },
    { id: 'home',      targetAmount: 2000000,  timelineMonths: 48, note: 'Down payment for home purchase' },
  ],
  business: [
    { id: 'emergency', targetAmount: 1000000,  timelineMonths: 6,   note: 'Business continuity reserve — 6 months ops cost' },
    { id: 'debt',      targetAmount: 2500000,  timelineMonths: 36,  note: 'Clear working capital loan' },
    { id: 'retire',    targetAmount: 20000000, timelineMonths: 180, note: 'Exit corpus target' },
  ],
  homemaker: [
    { id: 'emergency', targetAmount: 200000,  timelineMonths: 12, note: 'Household emergency buffer' },
    { id: 'education', targetAmount: 1500000, timelineMonths: 96, note: "Children's higher education fund" },
    { id: 'home',      targetAmount: 500000,  timelineMonths: 24, note: 'Home renovation fund' },
  ],
  investor: [
    { id: 'retire',    targetAmount: 50000000, timelineMonths: 120, note: 'FIRE corpus — 25× annual expenses' },
    { id: 'custom',    targetAmount: 5000000,  timelineMonths: 60,  note: 'Passive income portfolio target' },
    { id: 'debt',      targetAmount: 5500000,  timelineMonths: 48,  note: 'Prepay home loan early' },
  ],
};

const GOALS_AI_PROMPTS = [
  'How much should I save monthly for retirement?',
  'Which goal should I prioritise first?',
  'Am I on track with my emergency fund?',
  'How can I reach my home goal faster?',
];

function GoalsSection({ data, setData, perspective = 'salaried', onComplete }) {
  // Seed dummy goals on first load
  const [isDummyGoals, setIsDummyGoals] = useState(() => {
    if (!data.goals?.length) {
      const seed = DUMMY_GOALS[perspective] || DUMMY_GOALS.salaried;
      setData(d => ({ ...d, goals: seed.map(g => g.id), dummyGoalDetails: seed }));
      return true;
    }
    return Boolean(data.dummyGoalDetails?.length);
  });

  const [goalDialog, setGoalDialog] = useState(null);
  const [goalMessages, setGoalMessages] = useState([
    { role: 'ai', text: "I'm your Goal Advisor. Ask me anything about saving strategies, timelines, or how to prioritise your financial milestones." }
  ]);
  const [goalInput, setGoalInput] = useState('');
  const [goalThinking, setGoalThinking] = useState(false);
  const goalChatEndRef = useRef(null);
  const goalInputRef = useRef(null);

  useEffect(() => { goalChatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [goalMessages]);

  const clearDummyGoals = () => {
    setData(d => ({ ...d, goals: [], goalDetails: {}, dummyGoalDetails: [] }));
    setIsDummyGoals(false);
    setGoalMessages(m => [...m, { role: 'ai', text: "Cleared! Now configure the goals that actually matter to you — click any goal card to set your target and timeline." }]);
  };

  const saveGoalDetail = (detail) => {
    setIsDummyGoals(false);
    setData(d => ({
      ...d,
      goals: d.goals.includes(detail.id) ? d.goals : [...(d.goals || []), detail.id],
      goalDetails: { ...(d.goalDetails || {}), [detail.id]: detail },
      dummyGoalDetails: [],
    }));
    const opt = GOAL_OPTS.find(o => o.id === detail.id);
    setGoalMessages(m => [...m, { role: 'ai', text: `Great — **${opt?.label || 'Goal'}** configured: ${inr(detail.targetAmount)} in ${detail.timelineMonths >= 12 ? `${detail.timelineMonths / 12} years` : `${detail.timelineMonths} months`}. Monthly savings needed: ${inr(Math.ceil(detail.targetAmount / detail.timelineMonths))}.` }]);
  };

  const removeGoal = (id) => {
    setData(d => {
      const details = { ...(d.goalDetails || {}) };
      delete details[id];
      return { ...d, goals: (d.goals || []).filter(g => g !== id), goalDetails: details };
    });
  };

  const sendGoalMessage = (text) => {
    if (!text.trim()) return;
    setGoalMessages(m => [...m, { role: 'user', text }]);
    setGoalInput('');
    setGoalThinking(true);
    setTimeout(() => {
      const lower = text.toLowerCase();
      let reply = "That's a thoughtful question. Based on your goals, I'd suggest reviewing your emergency fund first — it's the foundation everything else rests on. Once that's set, allocate surplus income toward your highest-priority goal using a SIP or recurring deposit.";
      if (lower.includes('retire')) reply = "For retirement, the rule of thumb is to save 15–20% of monthly income. With a 20-year horizon, even ₹10,000/month compounding at 12% grows to ~₹1 crore. Start early, stay consistent.";
      if (lower.includes('home') || lower.includes('house')) reply = "For a home purchase, target a 20% down payment to avoid PMI and keep EMIs manageable. If your goal is ₹20L down payment in 5 years, you need to save ~₹27,000/month at 8% returns.";
      if (lower.includes('emergency')) reply = "Emergency fund goal: 6 months of expenses in a liquid account. For most households, ₹3–6L is a good target. Prioritise this before any investment-linked goal.";
      if (lower.includes('priorit')) reply = "Priority order: 1) Emergency fund 2) High-interest debt clearance 3) Retirement (start early for compounding) 4) Medium-term goals like education or home down payment.";
      setGoalMessages(m => [...m, { role: 'ai', text: reply }]);
      setGoalThinking(false);
      goalInputRef.current?.focus();
    }, 900);
  };

  const handleComplete = () => { const u = { ...data, completed: true }; setData(u); saveJson(SK.goals, u); onComplete(); };

  const configuredGoals = Object.keys(data.goalDetails || {});
  const dummyGoalDetails = data.dummyGoalDetails || [];
  const totalTarget = [...configuredGoals.map(id => (data.goalDetails[id]?.targetAmount || 0)),
    ...dummyGoalDetails.map(g => g.targetAmount || 0)].reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">

      {/* ── Top bar ──────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 px-8 py-5 flex items-start justify-between shrink-0">
        <div>
          <h2 className="text-3xl font-serif font-black text-[#2C4A70] leading-tight">Your Financial Milestones</h2>
          <p className="text-slate-400 text-sm mt-1">Configure the goals that matter most — set targets, timelines, and priorities.</p>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-6 text-sm text-slate-500 font-medium">
          <span className="bg-[#2C4A70]/10 text-[#2C4A70] font-bold px-3 py-1.5 rounded-full text-xs">
            {configuredGoals.length + (isDummyGoals ? dummyGoalDetails.length : 0)} goals
          </span>
          {totalTarget > 0 && (
            <span className="bg-slate-100 text-slate-600 font-bold px-3 py-1.5 rounded-full text-xs">
              Total: {inr(totalTarget)}
            </span>
          )}
        </div>
      </div>

      {/* ── Disclaimer ───────────────────────────────────────────── */}
      {isDummyGoals && (
        <div className="bg-amber-50 border-b border-amber-200 px-8 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 text-amber-700">
            <span className="text-base">⚠️</span>
            <p className="text-sm font-medium">
              These are <strong>suggested goals</strong> based on your profile — not saved. Click any card to configure and save.
            </p>
          </div>
          <button onClick={clearDummyGoals}
            className="text-xs font-bold text-amber-700 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ml-4">
            Clear & Start Fresh
          </button>
        </div>
      )}

      {/* ── Main split pane ──────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* LEFT — Goal cards */}
        <div className="flex flex-col w-[55%] border-r border-slate-200 overflow-y-auto">
          <div className="p-6 grid grid-cols-2 gap-4 content-start">

            {/* Dummy goal cards */}
            {isDummyGoals && dummyGoalDetails.map(gd => {
              const opt = GOAL_OPTS.find(o => o.id === gd.id);
              if (!opt) return null;
              const Icon = opt.icon;
              return (
                <button key={gd.id} onClick={() => setGoalDialog(opt)}
                  className="flex flex-col gap-3 p-5 rounded-2xl border-2 border-amber-200 bg-amber-50/60 text-left hover:border-amber-300 hover:shadow-sm transition-all">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center shrink-0">
                      <Icon size={17} className="text-amber-700" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-sm text-slate-800">{opt.label}</p>
                      <p className="text-xs text-slate-400 truncate">{gd.note}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between bg-white/80 rounded-xl px-3 py-2 border border-amber-100">
                    <p className="text-xs font-black text-[#2C4A70]">{inr(gd.targetAmount)}</p>
                    <p className="text-[10px] text-slate-400 font-semibold">
                      {gd.timelineMonths >= 12 ? `${gd.timelineMonths / 12}yr` : `${gd.timelineMonths}mo`}
                    </p>
                    <p className="text-[10px] text-slate-400">~{inr(Math.ceil(gd.targetAmount / gd.timelineMonths))}/mo</p>
                  </div>
                  <p className="text-[10px] text-amber-600 font-semibold flex items-center gap-1"><Pencil size={9} /> Click to configure</p>
                </button>
              );
            })}

            {/* Configured goal cards */}
            {!isDummyGoals && GOAL_OPTS.map(g => {
              const active = (data.goals || []).includes(g.id);
              const detail = (data.goalDetails || {})[g.id];
              const Icon = g.icon;
              return (
                <button key={g.id} onClick={() => setGoalDialog(g)}
                  className={`flex flex-col gap-3 p-5 rounded-2xl border-2 text-left transition-all
                    ${active ? 'border-[#526B5C] bg-[#526B5C]/5 shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${active ? 'bg-[#526B5C] text-white' : 'bg-slate-100 text-slate-400'}`}>
                      <Icon size={17} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`font-bold text-sm ${active ? 'text-[#2C4A70]' : 'text-slate-700'}`}>{g.label}</p>
                      <p className="text-xs text-slate-400 truncate">{g.desc}</p>
                    </div>
                    {active && (
                      <span className="bg-[#526B5C] text-white rounded-full p-0.5 shrink-0">
                        <Check size={11} strokeWidth={3} />
                      </span>
                    )}
                  </div>
                  {detail ? (
                    <div className="flex items-center justify-between bg-white/80 rounded-xl px-3 py-2 border border-[#526B5C]/15">
                      <p className="text-xs font-black text-[#2C4A70]">{inr(detail.targetAmount)}</p>
                      <p className="text-[10px] text-slate-400 font-semibold">
                        {detail.timelineMonths >= 12 ? `${detail.timelineMonths / 12}yr` : `${detail.timelineMonths}mo`}
                      </p>
                      <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full
                        ${detail.priority === 'high' ? 'bg-rose-50 text-rose-500' : detail.priority === 'low' ? 'bg-slate-100 text-slate-400' : 'bg-amber-50 text-amber-500'}`}>
                        {detail.priority}
                      </span>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-300 flex items-center gap-1"><Plus size={10} /> Click to configure</p>
                  )}
                </button>
              );
            })}
          </div>

          {/* Continue footer */}
          <div className="mt-auto border-t border-slate-200 bg-white px-6 py-4 flex justify-end shrink-0">
            <Btn onClick={handleComplete} disabled={!data.goals?.length}>
              Looks good, continue <ArrowRight size={18} />
            </Btn>
          </div>
        </div>

        {/* RIGHT — Goal Advisor AI chat */}
        <div className="flex flex-col w-[45%] bg-white">
          {/* Chat header */}
          <div className="px-6 py-4 border-b border-slate-100 shrink-0 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#526B5C] flex items-center justify-center">
              <Target size={17} className="text-white" />
            </div>
            <div>
              <p className="font-bold text-sm text-slate-800">Goal Advisor</p>
              <p className="text-xs text-slate-400">AI-powered goal planning</p>
            </div>
            <span className="ml-auto w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]" />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {goalMessages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed
                  ${m.role === 'user'
                    ? 'bg-[#526B5C] text-white rounded-br-sm'
                    : 'bg-slate-100 text-slate-700 rounded-bl-sm'}`}>
                  {m.text.split('**').map((part, pi) =>
                    pi % 2 === 1 ? <strong key={pi}>{part}</strong> : part
                  )}
                </div>
              </div>
            ))}
            {goalThinking && (
              <div className="flex justify-start">
                <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1.5 items-center">
                  {[0, 1, 2].map(i => (
                    <motion.span key={i} className="w-1.5 h-1.5 rounded-full bg-[#526B5C]"
                      animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={goalChatEndRef} />
          </div>

          {/* Quick prompts */}
          <div className="px-4 py-2 flex gap-2 flex-wrap border-t border-slate-100 shrink-0">
            {GOALS_AI_PROMPTS.map((p, i) => (
              <button key={i} onClick={() => sendGoalMessage(p)}
                className="text-[11px] font-semibold bg-[#526B5C]/10 text-[#526B5C] border border-[#526B5C]/20 hover:bg-[#526B5C]/20 px-3 py-1.5 rounded-full transition-colors whitespace-nowrap">
                {p}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="px-4 pb-4 pt-2 shrink-0">
            <div className="flex gap-2 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-2 focus-within:border-[#526B5C] focus-within:ring-4 focus-within:ring-[#526B5C]/10 transition-all">
              <input ref={goalInputRef} value={goalInput} onChange={e => setGoalInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendGoalMessage(goalInput)}
                placeholder="Ask about saving strategies, timelines…"
                className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none" />
              <button onClick={() => sendGoalMessage(goalInput)} disabled={!goalInput.trim()}
                className="w-8 h-8 rounded-xl bg-[#526B5C] disabled:bg-slate-200 flex items-center justify-center transition-colors shrink-0">
                <Send size={14} className="text-white" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Goal dialog */}
      <AnimatePresence>
        {goalDialog && (
          <GoalDialog
            goal={goalDialog}
            existing={(data.goalDetails || {})[goalDialog.id]}
            onSave={saveGoalDetail}
            onRemove={removeGoal}
            onClose={() => setGoalDialog(null)}
          />
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
              <MappingSection data={mappingData} setData={setMappingData} perspective={profileData.perspective} onComplete={() => completeSection('mapping')} />
            </motion.div>
          )}
          {active === 'goals' && (
            <motion.div key="goals" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
              <GoalsSection data={goalsData} setData={setGoalsData} perspective={profileData.perspective} onComplete={() => completeSection('goals')} />
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
