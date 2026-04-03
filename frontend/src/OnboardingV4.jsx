import React, { useState, useRef, useEffect } from 'react';
import { API } from './api.js';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Check, ArrowRight, Shield, Briefcase, Store, Home, TrendingUp,
  AlertCircle, GraduationCap, CreditCard, Plus, Lock, LogOut,
  User, Users, LayoutDashboard, Upload, PiggyBank, Target, BarChart2,
  Settings, Layers, RefreshCw, ChevronRight, Edit2,
  Send, Sparkles, Trash2, Pencil, Building2, TrendingDown, Wallet, Landmark, Gem, Car,
  Utensils, Zap, Bell, Activity
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';
import PersonalDashboard from './PersonalDashboard';
import WealthDashboard from './WealthDashboard';
import BudgetsPage from './BudgetsPage';
import GoalsPage from './GoalsPage';
import ReportsPage from './ReportsPage';
import ImportWizard from './ImportWizard';
import SettingsPage from './SettingsPage';
import { FinnyInline } from './FinnyAssistant.jsx';

// ─── Storage helpers ──────────────────────────────────────────────────────
const SK = {
  sections:       'onboarding_v4_sections',
  profile:        'onboarding_v4_profile',
  mapping:        'onboarding_v4_mapping',
  goals:          'onboarding_v4_goals',
  cashflow:       'onboarding_v4_cashflow',
  annualexpenses: 'onboarding_v4_annualexpenses',
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

                {/* Household Type */}
                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2.5">Household Type</p>
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    {[
                      { id: 'single', label: 'Single',  Icon: User  },
                      { id: 'couple', label: 'Couple',  Icon: Users },
                      { id: 'family', label: 'Family',  Icon: Users },
                    ].map(({ id, label, Icon }) => {
                      const active = data.householdType === id;
                      return (
                        <button key={id} onClick={() => set('householdType', id)}
                          className={`flex flex-col items-center gap-1.5 py-3 rounded-xl border-2 transition-all
                            ${active ? 'border-[#2C4A70] bg-blue-50/40 shadow-sm' : 'border-slate-200 bg-slate-50 hover:border-slate-300'}`}>
                          <div className={`w-9 h-9 rounded-xl flex items-center justify-center
                            ${active ? 'bg-[#2C4A70] text-white' : 'bg-white text-slate-400 border border-slate-200'}`}>
                            <Icon size={id === 'family' ? 18 : 16} strokeWidth={id === 'family' ? 1.5 : 2} />
                          </div>
                          <span className={`text-xs font-bold ${active ? 'text-[#2C4A70]' : 'text-slate-500'}`}>{label}</span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Dependents counter */}
                  <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-700">Dependents</p>
                      <p className="text-xs text-slate-400">Children or others financially reliant on you</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => set('dependents', Math.max(0, (data.dependents || 0) - 1))}
                        className="w-7 h-7 rounded-full bg-white border border-slate-300 flex items-center justify-center text-slate-500 hover:bg-slate-100 transition-colors font-bold text-base leading-none">
                        −
                      </button>
                      <span className="w-5 text-center font-black text-slate-800 text-base">{data.dependents || 0}</span>
                      <button
                        onClick={() => set('dependents', (data.dependents || 0) + 1)}
                        className="w-7 h-7 rounded-full bg-white border border-slate-300 flex items-center justify-center text-slate-500 hover:bg-slate-100 transition-colors font-bold text-base leading-none">
                        +
                      </button>
                    </div>
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
const ITEM_TYPES = [
  { type: 'bank',     kind: 'asset',     label: 'Bank / Savings',   icon: Landmark,   placeholder: 'e.g. HDFC Savings Account' },
  { type: 'property', kind: 'asset',     label: 'Property',         icon: Home,       placeholder: 'e.g. Apartment in Pune' },
  { type: 'stocks',   kind: 'asset',     label: 'Investments',      icon: TrendingUp, placeholder: 'e.g. Zerodha Portfolio' },
  { type: 'other',    kind: 'asset',     label: 'Gold / Jewellery', icon: Gem,        placeholder: 'e.g. Gold & ornaments' },
  { type: 'loan',     kind: 'liability', label: 'Loan',             icon: Building2,  placeholder: 'e.g. Home Loan – SBI' },
  { type: 'credit',   kind: 'liability', label: 'Credit Card',      icon: CreditCard, placeholder: 'e.g. HDFC Credit Card' },
  { type: 'other',    kind: 'asset',     label: 'Other',            icon: Wallet,     placeholder: 'e.g. Other item' },
];

function AddItemDialog({ onAdd, onClose, initial = null }) {
  const [selectedType, setSelectedType] = useState(initial ? ITEM_TYPES.find(t => t.type === initial.type && t.kind === initial._kind) || ITEM_TYPES[0] : ITEM_TYPES[0]);
  const [name,   setName]   = useState(initial?.name || '');
  const [value,  setValue]  = useState(initial?.value ? String(initial.value) : '');
  const [detail, setDetail] = useState(initial?.detail || '');

  const canAdd = name.trim() && num(value) > 0;

  const handleAdd = () => {
    onAdd({ name: name.trim(), value: num(value), type: selectedType.type, detail: detail.trim() }, selectedType.kind);
    onClose();
  };

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
        <div className="h-1.5 bg-gradient-to-r from-[#2C4A70] to-emerald-400" />

        <div className="p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-serif font-black text-[#2C4A70]">{initial ? 'Edit Item' : 'Add Item'}</h3>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors text-lg leading-none">×</button>
          </div>

          {/* Category grid */}
          <div className="mb-5">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Category</label>
            <div className="grid grid-cols-2 gap-2">
              {ITEM_TYPES.map(t => {
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
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Amount</label>
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
              className="flex-1 py-3 rounded-full font-semibold text-sm transition-all shadow-md bg-[#2C4A70] text-white hover:bg-[#1F344F] disabled:opacity-40 disabled:cursor-not-allowed">
              {initial ? 'Save Changes' : 'Add'}
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

  const finnyRef = useRef(null);

  const clearDummy = () => {
    setData(d => ({ ...d, assets: [], liabilities: [] }));
    setIsDummy(false);
    finnyRef.current?.addMessage({ role: 'finny', content: "Cleared! Start fresh — tell me about your accounts, investments, and any debts." });
  };

  const [dialog, setDialog] = useState(false);
  const [editItem, setEditItem] = useState(null);

  const assets      = data.assets      || [];
  const liabilities = data.liabilities || [];
  const addAsset = (item) => { setIsDummy(false); setData(d => ({ ...d, assets: [...(d.assets || []), { ...item, id: Date.now() + Math.random() }] })); };
  const addLib   = (item) => { setIsDummy(false); setData(d => ({ ...d, liabilities: [...(d.liabilities || []), { ...item, id: Date.now() + Math.random() }] })); };

  const handleDialogEdit = (item, kind) => {
    const id = editItem.id;
    if (kind === 'asset') {
      setData(d => ({ ...d, assets: d.assets.map(a => a.id === id ? { ...item, id, _kind: 'asset' } : a) }));
    } else {
      setData(d => ({ ...d, liabilities: d.liabilities.map(l => l.id === id ? { ...item, id, _kind: 'liability' } : l) }));
    }
    setIsDummy(false);
    setEditItem(null);
  };

  const handleDialogAdd = (item, kind) => {
    if (kind === 'asset') {
      addAsset(item);
      finnyRef.current?.addMessage({ role: 'finny', content: `Added **${item.name}** (${inr(item.value)}). Anything else?` });
    } else {
      addLib(item);
      finnyRef.current?.addMessage({ role: 'finny', content: `Recorded **${item.name}** (${inr(item.value)}). Anything else to add?` });
    }
    setDialog(false);
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

    return message;
  };

  const totalA   = assets.reduce((s, a) => s + a.value, 0);
  const totalL   = liabilities.reduce((s, a) => s + a.value, 0);
  const netWorth = totalA - totalL;

  const handleFinnySend = async (text) => {
    await new Promise(r => setTimeout(r, 800));
    return simulateAIResponse(text);
  };

  const removeAsset = (id) => { setIsDummy(false); setData(d => ({ ...d, assets: d.assets.filter(a => a.id !== id) })); };
  const removeLib   = (id) => { setIsDummy(false); setData(d => ({ ...d, liabilities: d.liabilities.filter(a => a.id !== id) })); };
  const handleComplete = () => { saveJson(SK.mapping, data); onComplete(); };
  const hasAny = assets.length > 0 || liabilities.length > 0;

  const PERSPECTIVE_TIPS = {
    salaried: [
      { id: 'epf',      check: (a) => !a.some(x => /epf|pf|provident/i.test(x.name)), emoji: '🏦', text: 'As a salaried employee, your EPF corpus is likely your largest retirement asset. Add it under investments.' },
      { id: 'fd',       check: (a) => !a.some(x => /fd|fixed.deposit/i.test(x.name)),  emoji: '💰', text: 'Most salaried professionals keep a Fixed Deposit as an emergency buffer. Don\'t forget to add it.' },
      { id: 'creditcard', check: (_, l) => !l.some(x => x.type === 'credit' || /credit.card/i.test(x.name)), emoji: '💳', text: 'Credit card outstanding is often overlooked. Add your current card balance under what you owe.' },
    ],
    business: [
      { id: 'currentacc', check: (a) => !a.some(x => /current.account|business.account/i.test(x.name)), emoji: '🏦', text: 'Add your business current account separately from personal savings for accurate net worth tracking.' },
      { id: 'gst',        check: (_, l) => !l.some(x => /gst|tax/i.test(x.name)),                        emoji: '📋', text: 'Business owners often have GST payables. Add any tax liabilities under what you owe.' },
    ],
    homemaker: [
      { id: 'gold',    check: (a) => !a.some(x => /gold|jewel/i.test(x.name)),      emoji: '🪙', text: 'Gold and jewellery are significant assets for most Indian households. Add their estimated current value.' },
      { id: 'rd',      check: (a) => !a.some(x => /rd|recurring/i.test(x.name)),    emoji: '📅', text: 'If you have an RD (Recurring Deposit), add it — it counts as a liquid savings asset.' },
    ],
    investor: [
      { id: 'nps',     check: (a) => !a.some(x => /nps|pension/i.test(x.name)),     emoji: '🎯', text: 'NPS corpus is often missed. Add it under investments for accurate retirement projection.' },
      { id: 'demat',   check: (a) => !a.some(x => /demat|portfolio|zerodha|groww/i.test(x.name)), emoji: '📊', text: 'Your demat/equity portfolio is likely your largest asset. Add its current market value.' },
    ],
  };

  const activeTips = (PERSPECTIVE_TIPS[perspective] || []).filter(t => t.check(assets, liabilities));

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
          {netWorth < 0 && <p className="text-[10px] text-rose-200 mt-1">Debts exceed savings</p>}
        </div>
      </div>

      {/* Perspective-aware tips */}
      {activeTips.length > 0 && (
        <div className="shrink-0 bg-amber-50 border-b border-amber-100 px-8 py-3 flex flex-wrap gap-2">
          {activeTips.map(tip => (
            <div key={tip.id} className="flex items-start gap-2 text-amber-800 text-xs bg-white border border-amber-200 rounded-xl px-3 py-2 max-w-sm">
              <span className="shrink-0">{tip.emoji}</span>
              <span>{tip.text}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Insights strip ──────────────────────────────────────────── */}
      {(() => {
        const hints = [];
        const hasProperty = assets.some(a => a.type === 'property');
        const hasHomeLoan = liabilities.some(l => /home|housing|mortgage/i.test(l.name));
        const hasVehicle  = assets.some(a => a.type === 'vehicle' || /\bcar\b|\bbike\b|\bvehicle\b/i.test(a.name));
        const hasVehicleLoan = liabilities.some(l => /\bcar\s*loan\b|\bvehicle\s*loan\b|\bauto\s*loan\b|\bbike\s*loan\b/i.test(l.name));

        if (hasHomeLoan && !hasProperty)
          hints.push({ emoji: '🏠', text: "You've added a home loan — don't forget to add the property under What I own." });
        if (hasProperty && !hasHomeLoan)
          hints.push({ emoji: '💡', text: "You own a property. If there's a home loan against it, add it under What I owe." });
        if (hasVehicleLoan && !hasVehicle)
          hints.push({ emoji: '🚗', text: "You have a vehicle loan — consider adding the vehicle itself under What I own." });
        if (hasVehicle && !hasVehicleLoan)
          hints.push({ emoji: '💡', text: "You've listed a vehicle. If there's an auto loan on it, add it under What I owe." });

        return hints.length > 0 ? (
          <div className="shrink-0 bg-indigo-50 border-b border-indigo-100 px-8 py-3 space-y-1.5">
            {hints.map((h, i) => (
              <div key={i} className="flex items-start gap-2.5 text-indigo-700 text-xs font-medium">
                <span className="text-sm shrink-0">{h.emoji}</span>
                <span>{h.text}</span>
              </div>
            ))}
          </div>
        ) : null;
      })()}

      {/* ── Main split ──────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left — financial map */}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {!hasAny ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-16">
              <div className="w-16 h-16 bg-white rounded-2xl border-2 border-dashed border-slate-200 flex items-center justify-center mb-4">
                <Layers size={28} className="text-slate-300" />
              </div>
              <p className="font-serif italic text-lg text-slate-400">Your financial map will appear here.</p>
              <p className="text-slate-300 text-sm mt-2">Start chatting on the right, or click Add to enter manually.</p>
              <button onClick={() => setDialog(true)} className="mt-8 px-6 py-2.5 bg-indigo-50 text-[#2C4A70] font-bold text-sm rounded-xl border border-indigo-100 hover:bg-indigo-100 transition-colors">
                <Plus size={14} className="inline mr-1" /> Add
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-500">{assets.length + liabilities.length} item{assets.length + liabilities.length !== 1 ? 's' : ''}</p>
                <button onClick={() => setDialog(true)} className="text-xs font-bold text-[#2C4A70] flex items-center gap-1 px-3 py-1.5 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors">
                  <Plus size={13} /> Add
                </button>
              </div>

              {/* Two-column layout */}
              <div className="grid grid-cols-2 gap-5">
                {/* Assets column */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full bg-[#2C4A70]" />
                    <p className="text-xs font-bold text-[#2C4A70] uppercase tracking-widest">What I own</p>
                    <span className="ml-auto text-xs font-bold text-slate-400">{assets.length} item{assets.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
                    {assets.length === 0 ? (
                      <div className="px-5 py-8 text-center text-slate-300 text-xs italic">No assets added yet</div>
                    ) : assets.map(item => {
                      const iconMap = { bank: Landmark, property: Home, stocks: TrendingUp, loan: Building2, credit: CreditCard };
                      const Icon = iconMap[item.type] || Wallet;
                      return (
                        <div key={item.id} className="group flex items-center gap-3 px-4 py-3.5 hover:bg-slate-50 transition-colors">
                          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-[#2C4A70]/8 border border-[#2C4A70]/10">
                            <Icon size={15} className="text-[#2C4A70]" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-bold text-sm text-slate-800 truncate">{item.name}</p>
                            {item.detail && <p className="text-xs text-slate-400 truncate">{item.detail}</p>}
                          </div>
                          <p className="font-black text-sm shrink-0 text-[#2C4A70]">{inr(item.value)}</p>
                          <button onClick={() => setEditItem({ ...item, _kind: 'asset' })}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-[#2C4A70] p-1 shrink-0">
                            <Edit2 size={14} />
                          </button>
                          <button onClick={() => removeAsset(item.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-rose-400 p-1 shrink-0">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      );
                    })}
                    <div className="px-4 py-2.5 bg-[#2C4A70]/4 border-t border-[#2C4A70]/10">
                      <p className="text-xs font-black text-[#2C4A70] text-right">{inr(totalA)} total</p>
                    </div>
                  </div>
                </div>

                {/* Liabilities column */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full bg-rose-400" />
                    <p className="text-xs font-bold text-rose-500 uppercase tracking-widest">What I owe</p>
                    <span className="ml-auto text-xs font-bold text-slate-400">{liabilities.length} item{liabilities.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
                    {liabilities.length === 0 ? (
                      <div className="px-5 py-8 text-center text-slate-300 text-xs italic">No liabilities added yet</div>
                    ) : liabilities.map(item => {
                      const iconMap = { loan: Building2, card: CreditCard, credit: CreditCard };
                      const Icon = iconMap[item.type] || TrendingDown;
                      return (
                        <div key={item.id} className="group flex items-center gap-3 px-4 py-3.5 hover:bg-rose-50/40 transition-colors">
                          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-rose-50 border border-rose-100">
                            <Icon size={15} className="text-rose-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-bold text-sm text-slate-800 truncate">{item.name}</p>
                            {item.detail && <p className="text-xs text-slate-400 truncate">{item.detail}</p>}
                          </div>
                          <p className="font-black text-sm shrink-0 text-rose-500">−{inr(item.value)}</p>
                          <button onClick={() => setEditItem({ ...item, _kind: 'liability' })}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-[#2C4A70] p-1 shrink-0">
                            <Edit2 size={14} />
                          </button>
                          <button onClick={() => removeLib(item.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-rose-400 p-1 shrink-0">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      );
                    })}
                    <div className="px-4 py-2.5 bg-rose-50/60 border-t border-rose-100">
                      <p className="text-xs font-black text-rose-500 text-right">−{inr(totalL)} total</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-px bg-slate-200 shrink-0" />

        {/* Right — Finny assistant sidebar */}
        <div className="w-[380px] shrink-0 flex flex-col border-l border-slate-100">
          <FinnyInline
            ref={finnyRef}
            subtitle="Your financial companion"
            placeholder="E.g. HDFC savings ₹3L, home loan ₹28L…"
            prompts={!hasAny ? SUGGESTED_PROMPTS.slice(0, 3) : []}
            initialMessage="I've pre-filled a starting map based on your profile. You can edit any entry, remove what doesn't apply, or just tell me what you own and owe in plain language."
            onSend={handleFinnySend}
          />
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
            onAdd={handleDialogAdd}
            onClose={() => setDialog(false)}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {editItem && (
          <AddItemDialog
            initial={editItem}
            onAdd={handleDialogEdit}
            onClose={() => setEditItem(null)}
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

function GoalDialog({ goal, existing, assets = [], onSave, onRemove, onClose }) {
  const Icon = goal.icon;
  const seed = existing || {};
  const [targetAmount, setTargetAmount] = useState(seed.targetAmount ? String(seed.targetAmount) : '');
  const [timelineMonths, setTimelineMonths] = useState(seed.timelineMonths || 12);
  const [priority, setPriority]   = useState(seed.priority   || 'medium');
  const [note, setNote]           = useState(seed.note       || '');

  const computePrefill = () => {
    if (existing?.alreadySaved) return String(existing.alreadySaved);
    const match = {
      emergency: (a) => a.filter(x => /saving|bank|liquid|fd|fixed.deposit/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      retire:    (a) => a.filter(x => /epf|ppf|nps|pension|provident|pf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      home:      (a) => a.filter(x => /home|property|real.estate|flat|house/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      vehicle:   (a) => a.filter(x => /car|vehicle|bike|auto/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      education: (a) => a.filter(x => /education|college|sukanya|ppf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
    };
    const fn = match[goal.id];
    const prefilled = fn ? fn(assets) : 0;
    return prefilled > 0 ? String(prefilled) : '';
  };
  const [alreadySaved, setAlreadySaved] = useState(computePrefill);
  const prefillAmt = (() => {
    const match = {
      emergency: (a) => a.filter(x => /saving|bank|liquid|fd|fixed.deposit/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      retire:    (a) => a.filter(x => /epf|ppf|nps|pension|provident|pf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      home:      (a) => a.filter(x => /home|property|real.estate|flat|house/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      vehicle:   (a) => a.filter(x => /car|vehicle|bike|auto/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      education: (a) => a.filter(x => /education|college|sukanya|ppf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
    };
    const fn = match[goal.id];
    return fn ? fn(assets) : 0;
  })();

  const canSave = num(targetAmount) > 0;
  const remaining = Math.max(0, num(targetAmount) - num(alreadySaved));
  const monthlySaving = timelineMonths > 0 ? Math.ceil(remaining / timelineMonths) : 0;

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

            {/* Already saved */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
                Already Saved <span className="text-slate-300 font-normal normal-case">(optional)</span>
              </label>
              {prefillAmt > 0 && !existing && (
                <div className="mb-2 flex items-center gap-2 bg-indigo-50 border border-indigo-100 rounded-xl px-3 py-2">
                  <span className="text-indigo-500 text-xs">💡</span>
                  <p className="text-xs text-indigo-700 flex-1">
                    We found <strong>{inr(prefillAmt)}</strong> from your assets that may count towards this goal.
                  </p>
                  <button onClick={() => setAlreadySaved(String(prefillAmt))}
                    className="text-xs font-bold text-indigo-600 hover:underline shrink-0">Use this</button>
                </div>
              )}
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
                <input value={alreadySaved} onChange={e => setAlreadySaved(e.target.value)} placeholder="0" inputMode="numeric"
                  className="w-full border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
              </div>
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
            <button onClick={() => { onSave({ id: goal.id, targetAmount: num(targetAmount), alreadySaved: num(alreadySaved), timelineMonths, priority, note }); onClose(); }}
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

function GoalsSection({ data, setData, perspective = 'salaried', assets = [], onComplete }) {
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

  const handleGoalFinnySend = async (text) => {
    await new Promise(r => setTimeout(r, 900));
    const lower = text.toLowerCase();
    let reply = "That's a thoughtful question. Based on your goals, I'd suggest reviewing your emergency fund first — it's the foundation everything else rests on. Once that's set, allocate surplus income toward your highest-priority goal using a SIP or recurring deposit.";
    if (lower.includes('retire')) reply = "For retirement, the rule of thumb is to save 15–20% of monthly income. With a 20-year horizon, even ₹10,000/month compounding at 12% grows to ~₹1 crore. Start early, stay consistent.";
    if (lower.includes('home') || lower.includes('house')) reply = "For a home purchase, target a 20% down payment to avoid PMI and keep EMIs manageable. If your goal is ₹20L down payment in 5 years, you need to save ~₹27,000/month at 8% returns.";
    if (lower.includes('emergency')) reply = "Emergency fund goal: 6 months of expenses in a liquid account. For most households, ₹3–6L is a good target. Prioritise this before any investment-linked goal.";
    if (lower.includes('priorit')) reply = "Priority order: 1) Emergency fund 2) High-interest debt clearance 3) Retirement (start early for compounding) 4) Medium-term goals like education or home down payment.";
    return reply;
  };

  const GOAL_TYPE_MAP = {
    emergency: 'EMERGENCY', home: 'HOME', retire: 'RETIREMENT',
    education: 'EDUCATION', vehicle: 'VEHICLE', vacation: 'VACATION',
    wedding: 'WEDDING', debt: 'OTHERS', custom: 'OTHERS',
  };

  const handleComplete = async () => {
    const u = { ...data, completed: true };
    setData(u);
    saveJson(SK.goals, u);

    // Persist goals to database — use configured details, fall back to dummies
    const toSave = Object.keys(u.goalDetails || {}).length > 0
      ? Object.values(u.goalDetails)
      : (u.dummyGoalDetails || []);

    for (const d of toSave) {
      const targetDate = new Date();
      targetDate.setMonth(targetDate.getMonth() + (d.timelineMonths || 12));
      try {
        await API.goals.create({
          name: GOAL_OPTS.find(o => o.id === d.id)?.label || d.id,
          goal_type: GOAL_TYPE_MAP[d.id] || 'OTHERS',
          target_amount: d.targetAmount,
          current_amount: 0,
          target_date: targetDate.toISOString().slice(0, 10),
          notes: d.note || null,
        });
      } catch (_) { /* non-blocking */ }
    }

    onComplete();
  };

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
                <div key={gd.id} className="relative group">
                  <button onClick={() => setGoalDialog(opt)}
                    className="w-full flex flex-col gap-3 p-5 rounded-2xl border-2 border-amber-200 bg-amber-50/60 text-left hover:border-amber-300 hover:shadow-sm transition-all">
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
                  <button
                    onClick={e => { e.stopPropagation(); setData(d => ({ ...d, dummyGoalDetails: (d.dummyGoalDetails || []).filter(x => x.id !== gd.id) })); }}
                    className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-300 hover:text-rose-500 hover:border-rose-200 shadow-sm">
                    <Trash2 size={11} />
                  </button>
                </div>
              );
            })}

            {/* Configured goal cards */}
            {!isDummyGoals && GOAL_OPTS.map(g => {
              const active = (data.goals || []).includes(g.id);
              const detail = (data.goalDetails || {})[g.id];
              const Icon = g.icon;
              return (
                <div key={g.id} className="relative group">
                  <button onClick={() => setGoalDialog(g)}
                    className={`w-full flex flex-col gap-3 p-5 rounded-2xl border-2 text-left transition-all
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
                  {active && (
                    <button
                      onClick={e => { e.stopPropagation(); removeGoal(g.id); }}
                      className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-300 hover:text-rose-500 hover:border-rose-200 shadow-sm">
                      <Trash2 size={11} />
                    </button>
                  )}
                </div>
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

        {/* RIGHT — Finny goal assistant */}
        <div className="w-[380px] shrink-0 flex flex-col border-l border-slate-100">
          <FinnyInline
            subtitle="Your financial companion"
            placeholder="Ask about saving strategies, timelines…"
            prompts={GOALS_AI_PROMPTS}
            showPromptsAlways
            initialMessage="I'm Finny, your financial companion. Ask me anything about saving strategies, timelines, or how to prioritise your financial milestones."
            onSend={handleGoalFinnySend}
          />
        </div>
      </div>

      {/* Goal dialog */}
      <AnimatePresence>
        {goalDialog && (
          <GoalDialog
            goal={goalDialog}
            existing={(data.goalDetails || {})[goalDialog.id]}
            assets={assets}
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

function DashboardsSection({ onboardingData, completedSections = {}, onNavigate }) {
  const [tab, setTab] = useState('overview');

  const missing = [
    !completedSections.mapping  && { id: 'mapping',  label: 'Mapping',   desc: 'your assets & liabilities' },
    !completedSections.goals    && { id: 'goals',     label: 'Goals',     desc: 'your financial goals'      },
    !completedSections.cashflow && { id: 'cashflow',  label: 'Cash Flow', desc: 'your income & expenses'    },
  ].filter(Boolean);

  return (
    <div className="flex flex-col h-full">

      {/* Sample data disclaimer */}
      {missing.length > 0 && (
        <div className="shrink-0 bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-start gap-2.5">
            <span className="text-base shrink-0 mt-0.5">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-amber-800">
                You're viewing sample data — this is not your real financial picture.
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                Complete{' '}
                {missing.map((s, i) => (
                  <span key={s.id}>
                    <button onClick={() => onNavigate(s.id)}
                      className="font-bold underline underline-offset-2 hover:text-amber-900 transition-colors">
                      {s.label}
                    </button>
                    {i < missing.length - 2 ? ', ' : i === missing.length - 2 ? ' and ' : ''}
                  </span>
                ))}
                {' '}to see your actual numbers.
              </p>
            </div>
          </div>
          {missing.length === 1 && (
            <button onClick={() => onNavigate(missing[0].id)}
              className="shrink-0 text-xs font-bold text-amber-800 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
              Go to {missing[0].label} →
            </button>
          )}
        </div>
      )}

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

// ─── Annual Irregular Expenses ────────────────────────────────────────────
const MONTHS_SHORT = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];

const ANNUAL_ITEM_ICONS = {
  insurance: Shield,
  vacation:  Briefcase,
  festival:  Bell,
  school:    GraduationCap,
  custom:    CreditCard,
};

const DEFAULT_ANNUAL_ITEMS = [];

const DUMMY_ANNUAL_ITEMS = [
  { id: 'dummy_1', label: 'Health Insurance Premium',   desc: 'Annual family floater policy renewal',     amount: '25000',  months: ['APR'],        iconKey: 'insurance' },
  { id: 'dummy_2', label: 'Vehicle Insurance',          desc: 'Car / two-wheeler insurance renewal',      amount: '12000',  months: ['JAN'],        iconKey: 'insurance' },
  { id: 'dummy_3', label: 'Family Vacation',            desc: 'Summer holiday travel & stay',             amount: '60000',  months: ['MAY'],        iconKey: 'vacation'  },
  { id: 'dummy_4', label: 'Diwali & Festive Spending',  desc: 'Gifts, sweets, home décor, new clothes',   amount: '30000',  months: ['OCT','NOV'],  iconKey: 'festival'  },
  { id: 'dummy_5', label: 'School / Tuition Fees',      desc: 'Annual school admission & tuition',        amount: '80000',  months: ['APR','JUN'],  iconKey: 'school'    },
  { id: 'dummy_6', label: 'Annual Subscriptions',       desc: 'OTT, cloud storage, software renewals',    amount: '8000',   months: ['JAN'],        iconKey: 'custom'    },
];

const DEFAULT_ANNUAL = { items: DEFAULT_ANNUAL_ITEMS, completed: false };

function AnnualExpensesView({ data, setData, onBack, onComplete }) {
  const [isDummy, setIsDummy] = useState(() => {
    if (!data.items?.length) {
      return true;  // will seed on first render
    }
    return data.items.every(i => String(i.id).startsWith('dummy_'));
  });
  const [items, setItems] = useState(() => {
    if (!data.items?.length) return DUMMY_ANNUAL_ITEMS;
    return data.items;
  });
  const [showAdd, setShowAdd] = useState(false);
  const [newItem, setNewItem] = useState({ label: '', desc: '', amount: '', months: [] });
  const [editId,  setEditId]  = useState(null);
  const [editItem, setEditItem] = useState(null);
  const [saving, setSaving] = useState(false);

  const clearDummy = () => {
    setItems([]);
    setIsDummy(false);
  };

  useEffect(() => {
    API.dashboard.load()
      .then(d => {
        if (d?.annualExpenses?.length) {
          setItems(d.annualExpenses);
          setData(prev => ({ ...prev, items: d.annualExpenses }));
          saveJson(SK.annualexpenses, { ...data, items: d.annualExpenses });
        }
      })
      .catch(() => {});
  }, []);

  const totalOutlay = items.reduce((acc, item) => acc + (parseFloat(item.amount) || 0), 0);
  const monthlyReserve = Math.round(totalOutlay / 12);
  const monthsWithExpenses = new Set(items.flatMap(item => item.months));

  const toggleMonth = (m) =>
    setNewItem(prev => ({
      ...prev,
      months: prev.months.includes(m) ? prev.months.filter(x => x !== m) : [...prev.months, m],
    }));

  const addItem = () => {
    if (!newItem.label.trim() || !newItem.amount) return;
    setIsDummy(false);
    setItems(prev => [...prev, { ...newItem, id: `custom_${Date.now()}`, iconKey: 'custom' }]);
    setNewItem({ label: '', desc: '', amount: '', months: [] });
    setShowAdd(false);
  };

  const removeItem = (id) => { setIsDummy(false); setItems(prev => prev.filter(i => i.id !== id)); };

  const startEdit = (item) => {
    setEditId(item.id);
    setEditItem({ label: item.label, desc: item.desc || '', amount: String(item.amount), months: [...item.months] });
    setShowAdd(false);
  };
  const cancelEdit = () => { setEditId(null); setEditItem(null); };
  const saveEdit = () => {
    if (!editItem.label.trim() || !editItem.amount) return;
    setIsDummy(false);
    const newId = String(editId).startsWith('dummy_') ? `custom_${Date.now()}` : editId;
    setItems(prev => prev.map(i => i.id === editId ? { ...i, ...editItem, id: newId } : i));
    cancelEdit();
  };
  const toggleEditMonth = (m) =>
    setEditItem(prev => ({
      ...prev,
      months: prev.months.includes(m) ? prev.months.filter(x => x !== m) : [...prev.months, m],
    }));

  const persist = async (extra = {}) => {
    const updated = { ...data, items, ...extra };
    setData(updated);
    saveJson(SK.annualexpenses, updated);
    setSaving(true);
    try {
      await API.dashboard.save({ annualExpenses: updated.items });
    } catch (_) {
      // silent — localStorage is the fallback
    } finally {
      setSaving(false);
    }
    return updated;
  };

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">

      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-base italic font-serif font-bold text-[#2C4A70]">The Private Ledger</span>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-sm font-semibold text-slate-600">Annual Irregular Expense Mapping</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-[#2C4A70] flex items-center justify-center">
            <User size={14} className="text-white" />
          </div>
        </div>
      </div>

      {/* Scroll area */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <FadeIn>
          <h1 className="text-4xl font-serif font-black text-[#2C4A70] leading-tight mb-2">
            Some expenses don't happen every month.
          </h1>
          <p className="text-slate-500 mb-4 max-w-2xl text-[15px]">
            Think about insurance premiums, annual subscriptions, festival spending, vacations, and school admissions. These "lumpy" costs often derail monthly budgets.
          </p>

          {isDummy && (
            <div className="mb-6 flex items-center justify-between bg-amber-50 border border-amber-200 rounded-2xl px-5 py-3.5">
              <div className="flex items-center gap-2.5 text-amber-700">
                <span className="text-base">⚠️</span>
                <p className="text-sm font-medium">
                  These are <strong>sample expenses</strong> to help you get started — not your real data. Edit any entry, remove what doesn't apply, or clear all and start fresh.
                </p>
              </div>
              <button onClick={clearDummy}
                className="ml-4 shrink-0 text-xs font-bold text-amber-700 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
                Clear & Start Fresh
              </button>
            </div>
          )}

          <div className="flex gap-6 items-start">

            {/* ── LEFT: Projected Annual Outlays ── */}
            <div className="flex-1 flex flex-col gap-4">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                  <h3 className="text-[15px] font-bold text-slate-800">Projected Annual Outlays</h3>
                  <div className="flex items-center gap-2">
                    {items.length > 0 && (
                      <button
                        onClick={clearDummy}
                        className="text-xs font-bold text-slate-400 hover:text-rose-500 hover:bg-rose-50 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        Clear all
                      </button>
                    )}
                    <button
                      onClick={() => { setShowAdd(v => !v); setEditId(null); setEditItem(null); }}
                      className="flex items-center gap-1.5 text-xs font-bold text-[#2C4A70] hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      <Plus size={13} /> Add New
                    </button>
                  </div>
                </div>

                <div className="divide-y divide-slate-100">
                  {items.length === 0 && (
                    <div className="px-6 py-8 text-center">
                      <div className="w-12 h-12 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200 flex items-center justify-center mx-auto mb-3">
                        <Bell size={20} className="text-slate-300" />
                      </div>
                      <p className="text-sm font-semibold text-slate-500 mb-1">No annual expenses added yet</p>
                      <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
                        Add things like insurance premiums, school fees, vacations, or festival budgets — expenses that hit once a year and catch you off guard.
                      </p>
                    </div>
                  )}
                  {items.map(item => {
                    const Icon = ANNUAL_ITEM_ICONS[item.iconKey] || CreditCard;
                    const amt = parseFloat(item.amount) || 0;
                    const isEditing = editId === item.id;
                    return (
                      <div key={item.id}>
                        {/* Normal row */}
                        {!isEditing && (
                          <div className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/60 transition-colors group">
                            <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center shrink-0 text-slate-500">
                              <Icon size={16} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <p className="text-sm font-bold text-slate-800 truncate">{item.label}</p>
                                {String(item.id).startsWith('dummy_') && (
                                  <span className="text-[9px] font-bold bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded tracking-wider shrink-0">SAMPLE</span>
                                )}
                              </div>
                              <p className="text-xs text-slate-400 truncate">{item.desc}</p>
                            </div>
                            <div className="text-right shrink-0">
                              <p className="text-sm font-black text-[#2C4A70]">₹{amt.toLocaleString('en-IN')}</p>
                              <div className="flex gap-1 justify-end mt-1">
                                {item.months.map(m => (
                                  <span key={m} className="text-[9px] font-bold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded tracking-widest">{m}</span>
                                ))}
                              </div>
                            </div>
                            <div className="opacity-0 group-hover:opacity-100 transition-opacity ml-2 flex items-center gap-1">
                              <button onClick={() => startEdit(item)} className="text-slate-300 hover:text-[#2C4A70] p-1">
                                <Edit2 size={14} />
                              </button>
                              <button onClick={() => removeItem(item.id)} className="text-slate-300 hover:text-rose-500 p-1">
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Inline edit form */}
                        {isEditing && (
                          <div className="px-6 py-4 bg-indigo-50/40 border-t border-indigo-100">
                            <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3">Edit Item</p>
                            <div className="flex gap-3 mb-3">
                              <input type="text" placeholder="Expense name" value={editItem.label}
                                onChange={e => setEditItem(p => ({ ...p, label: e.target.value }))}
                                className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10" />
                              <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">₹</span>
                                <input type="number" placeholder="0" value={editItem.amount}
                                  onChange={e => setEditItem(p => ({ ...p, amount: e.target.value }))}
                                  className="w-32 text-sm border border-slate-200 rounded-lg pl-7 pr-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                              </div>
                            </div>
                            <input type="text" placeholder="Short description (optional)" value={editItem.desc}
                              onChange={e => setEditItem(p => ({ ...p, desc: e.target.value }))}
                              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 mb-3" />
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {MONTHS_SHORT.map(m => (
                                <button key={m} onClick={() => toggleEditMonth(m)}
                                  className={`text-[10px] font-bold px-2.5 py-1 rounded-full transition-colors ${
                                    editItem.months.includes(m) ? 'bg-[#2C4A70] text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                                  }`}>{m}</button>
                              ))}
                            </div>
                            <div className="flex justify-end gap-2">
                              <button onClick={cancelEdit} className="text-xs font-semibold text-slate-400 hover:text-slate-600 px-3 py-1.5 transition-colors">Cancel</button>
                              <button onClick={saveEdit} disabled={!editItem.label.trim() || !editItem.amount}
                                className="text-xs font-bold bg-[#2C4A70] text-white px-4 py-1.5 rounded-lg hover:bg-[#1e3557] disabled:opacity-40 transition-colors">
                                Save Changes
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Add new item form */}
                {showAdd && (
                  <div className="px-6 py-4 bg-indigo-50/40 border-t border-indigo-100">
                    <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3">New Annual Outlay</p>
                    <div className="flex gap-3 mb-3">
                      <input
                        type="text"
                        placeholder="Expense name"
                        value={newItem.label}
                        onChange={e => setNewItem(p => ({ ...p, label: e.target.value }))}
                        className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10"
                      />
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">₹</span>
                        <input
                          type="number"
                          placeholder="0"
                          value={newItem.amount}
                          onChange={e => setNewItem(p => ({ ...p, amount: e.target.value }))}
                          className="w-32 text-sm border border-slate-200 rounded-lg pl-7 pr-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                        />
                      </div>
                    </div>
                    <input
                      type="text"
                      placeholder="Short description (optional)"
                      value={newItem.desc}
                      onChange={e => setNewItem(p => ({ ...p, desc: e.target.value }))}
                      className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 mb-3"
                    />
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {MONTHS_SHORT.map(m => (
                        <button
                          key={m}
                          onClick={() => toggleMonth(m)}
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-full transition-colors ${
                            newItem.months.includes(m)
                              ? 'bg-[#2C4A70] text-white'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setShowAdd(false)} className="text-xs font-semibold text-slate-400 hover:text-slate-600 px-3 py-1.5 transition-colors">Cancel</button>
                      <button
                        onClick={addItem}
                        disabled={!newItem.label.trim() || !newItem.amount}
                        className="text-xs font-bold bg-[#2C4A70] text-white px-4 py-1.5 rounded-lg hover:bg-[#1e3557] disabled:opacity-40 transition-colors"
                      >
                        Add Outlay
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* ── RIGHT: Intensity grid + cards ── */}
            <div className="w-[340px] shrink-0 flex flex-col gap-4">

              {/* Cash Outflow Intensity */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <h3 className="text-[15px] font-bold text-slate-800 mb-4">Cash Outflow Intensity</h3>
                <div className="grid grid-cols-4 gap-2 mb-6">
                  {MONTHS_SHORT.map(m => {
                    const active = monthsWithExpenses.has(m);
                    return (
                      <div key={m} className={`rounded-xl py-3 flex flex-col items-center gap-1.5 border transition-colors ${
                        active ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-100'
                      }`}>
                        <span className={`text-[10px] font-bold tracking-widest ${active ? 'text-green-700' : 'text-slate-400'}`}>{m}</span>
                        {active && <div className="w-1.5 h-1.5 rounded-full bg-green-500" />}
                      </div>
                    );
                  })}
                </div>
                <div className="border-t border-slate-100 pt-4">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Total Non-Monthly Outlay</p>
                  <p className="text-3xl font-black text-[#2C4A70]">₹{totalOutlay.toLocaleString('en-IN')}</p>
                  <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                    Requires a monthly reserve of ~₹{monthlyReserve.toLocaleString('en-IN')} to remain liquid.
                  </p>
                </div>
              </div>

              {/* Sinking Fund Strategy */}
              <div className="bg-[#2C4A70] rounded-2xl p-6 text-white relative overflow-hidden">
                <div className="absolute top-4 right-4 w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-sm">💡</div>
                <h3 className="text-[15px] font-bold mb-2">A Sinking Fund Strategy</h3>
                <p className="text-sm text-white/70 mb-5 leading-relaxed">
                  By identifying ₹{totalOutlay.toLocaleString('en-IN')} in annual costs now, we can structure your monthly cash flow to automatically set aside funds. This prevents high-interest debt when the bills arrive.
                </p>
                <button className="w-full bg-white text-[#2C4A70] font-bold text-sm py-3 rounded-xl hover:bg-slate-100 transition-colors">
                  Enable Automatic Reserves
                </button>
              </div>

              {/* Data Sovereignty */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-[#526B5C]/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Shield size={13} className="text-[#526B5C]" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-800 mb-1">Data Sovereignty</p>
                  <p className="text-xs text-slate-500 leading-relaxed">Calculations for your irregular expenses are processed entirely on this device. No financial data ever leaves your local environment.</p>
                </div>
              </div>

            </div>
          </div>
        </FadeIn>
      </div>

      {/* Footer nav */}
      <div className="bg-white border-t border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-[#2C4A70] transition-colors uppercase tracking-wide"
        >
          <ArrowRight size={14} className="rotate-180" /> Back to Cash Flow
        </button>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full border-2 border-[#2C4A70] flex items-center justify-center text-[11px] font-black text-[#2C4A70]">2/2</div>
            <div>
              <p className="text-[10px] font-bold text-[#2C4A70] uppercase tracking-widest leading-none">Step 2 of 2</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Annual Irregular Expense Mapping</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => persist()}
              className="px-5 py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors uppercase tracking-wide"
            >
              Save Draft
            </button>
            <Btn disabled={saving} onClick={async () => { await persist({ completed: true }); onComplete(); }}>
              {saving ? 'Saving…' : 'Proceed to Mapping'}
            </Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Cash Flow Section ────────────────────────────────────────────────────
const DEFAULT_CF_CATS = [
  { id: 'housing',   icon: Home,     label: 'Housing',   sub: 'RENT / MORTGAGE',  color: 'bg-blue-100 text-blue-600',    amount: '' },
  { id: 'lifestyle', icon: Utensils, label: 'Lifestyle', sub: 'FOOD & DINING',    color: 'bg-orange-100 text-orange-600',amount: '' },
  { id: 'transport', icon: Car,      label: 'Transport', sub: 'FUEL & TRANSIT',   color: 'bg-slate-100 text-slate-600',  amount: '' },
  { id: 'wellness',  icon: Activity, label: 'Wellness',  sub: 'HEALTH & INSURE',  color: 'bg-teal-100 text-teal-600',   amount: '' },
  { id: 'utilities', icon: Zap,      label: 'Utilities', sub: 'DIGITAL & HOME',   color: 'bg-purple-100 text-purple-600',amount: '' },
];

const DEFAULT_CASHFLOW = { primaryIncome: '', secondaryIncome: '', categories: DEFAULT_CF_CATS, completed: false };

function CashFlowSection({ data, setData, annualData, setAnnualData, onBack, onComplete }) {
  const [step, setStep] = useState(1);
  const [primaryIncome,   setPrimaryIncome]   = useState(data.primaryIncome   || '');
  const [secondaryIncome, setSecondaryIncome] = useState(data.secondaryIncome || '');
  const [categories,      setCategories]      = useState(
    data.categories?.length ? data.categories.map(c => ({ ...c, icon: DEFAULT_CF_CATS.find(d => d.id === c.id)?.icon || Plus })) : DEFAULT_CF_CATS
  );
  const [showAddCat, setShowAddCat] = useState(false);
  const [newCatName,  setNewCatName]  = useState('');

  if (step === 2) {
    return (
      <AnnualExpensesView
        data={annualData}
        setData={setAnnualData}
        onBack={() => setStep(1)}
        onComplete={onComplete}
      />
    );
  }

  const income        = parseFloat(String(primaryIncome).replace(/[^0-9.]/g, '')) || 0;
  const totalExpenses = categories.reduce((acc, c) => acc + (parseFloat(c.amount) || 0), 0);
  const surplus       = income - totalExpenses;
  const surplusGoal   = income * 0.15;

  const updateAmt = (id, val) => setCategories(cats => cats.map(c => c.id === id ? { ...c, amount: val } : c));

  const addCategory = () => {
    if (!newCatName.trim()) return;
    setCategories(cats => [...cats, { id: `custom_${Date.now()}`, icon: Plus, label: newCatName.trim(), sub: 'CUSTOM', color: 'bg-indigo-100 text-indigo-600', amount: '' }]);
    setNewCatName('');
    setShowAddCat(false);
  };

  const persist = (extra = {}) => {
    const updated = { ...data, primaryIncome, secondaryIncome, categories: categories.map(({ icon, ...rest }) => rest), ...extra };
    setData(updated);
    saveJson(SK.cashflow, updated);
    return updated;
  };

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">

      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-base italic font-serif font-bold text-[#2C4A70]">The Private Ledger</span>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-sm font-semibold text-slate-600">Cash Flow Discovery</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-[#2C4A70] flex items-center justify-center">
            <User size={14} className="text-white" />
          </div>
        </div>
      </div>

      {/* Scroll area */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <FadeIn>
          <h1 className="text-4xl font-serif font-black text-[#2C4A70] leading-tight mb-2">
            Let's understand how money moves each month.
          </h1>
          <p className="text-slate-500 mb-8 max-w-2xl text-[15px]">
            Rough monthly averages are perfect. This helps us calibrate your architectural financial model without needing every receipt.
          </p>

          <div className="flex gap-6 items-start">

            {/* ── LEFT column ── */}
            <div className="w-[40%] flex flex-col gap-5 shrink-0">

              {/* Income Stream */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-[15px] font-bold text-slate-800">Income Stream</h3>
                  <TrendingUp size={16} className="text-emerald-400" />
                </div>
                <p className="text-xs text-slate-400 mb-5">Describe your monthly inflows. Use natural language or direct figures.</p>

                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 block">Primary Monthly Take-Home</label>
                <div className="relative mb-5">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-sm">₹</span>
                  <input
                    type="text"
                    value={primaryIncome}
                    onChange={e => setPrimaryIncome(e.target.value)}
                    placeholder="0.00"
                    className="w-full bg-white border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-slate-800 placeholder-slate-300 text-sm font-semibold focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all"
                  />
                </div>

                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 block">Secondary / Variable Inflows</label>
                <textarea
                  value={secondaryIncome}
                  onChange={e => setSecondaryIncome(e.target.value)}
                  placeholder="e.g. Dividend payouts around ₹400 or freelance side-work"
                  rows={3}
                  className="w-full bg-white border-2 border-slate-200 rounded-xl p-4 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all resize-none"
                />

                <div className="mt-4 flex items-start gap-2.5 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3">
                  <AlertCircle size={13} className="text-slate-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-slate-500">We factor in historical volatility for variable income automatically.</p>
                </div>
              </div>

              {/* Monthly Surplus Goal */}
              <div className="bg-[#2C4A70] rounded-2xl p-6 text-white shadow-md">
                <h3 className="text-[15px] font-bold mb-1">Monthly Surplus Goal</h3>
                <p className="text-sm text-white/60 mb-5">Aiming for 15% retention for long-term growth.</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-black">₹{Math.round(surplusGoal).toLocaleString('en-IN')}</span>
                  <span className="text-sm text-white/50 font-medium">Target</span>
                </div>
              </div>
            </div>

            {/* ── RIGHT column ── */}
            <div className="flex-1 flex flex-col gap-5">

              {/* Monthly Commitments */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-[15px] font-bold text-slate-800">Monthly Commitments</h3>
                  <span className="text-[10px] font-bold text-slate-400 tracking-widest">AVERAGES ONLY</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {categories.map(cat => {
                    const Icon = cat.icon;
                    return (
                      <div key={cat.id} className="flex items-center gap-3 border border-slate-200 rounded-xl p-3.5 bg-white hover:border-slate-300 transition-colors">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${cat.color}`}>
                          <Icon size={15} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-bold text-slate-800 leading-tight">{cat.label}</p>
                          <p className="text-[10px] text-slate-400 font-medium tracking-wide truncate">{cat.sub}</p>
                        </div>
                        <div className="flex items-center gap-0.5 shrink-0">
                          <span className="text-xs text-slate-400 font-medium">₹</span>
                          <input
                            type="number"
                            value={cat.amount}
                            onChange={e => updateAmt(cat.id, e.target.value)}
                            placeholder="0"
                            className="w-16 text-right text-sm font-bold text-slate-700 bg-transparent border-0 outline-none placeholder-slate-300 focus:ring-0 [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                          />
                        </div>
                      </div>
                    );
                  })}

                  {/* Add Category */}
                  {showAddCat ? (
                    <div className="flex items-center gap-2 border-2 border-dashed border-indigo-200 rounded-xl p-3.5 bg-indigo-50/40">
                      <input
                        autoFocus
                        type="text"
                        value={newCatName}
                        onChange={e => setNewCatName(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') addCategory(); if (e.key === 'Escape') setShowAddCat(false); }}
                        placeholder="Category name"
                        className="flex-1 text-sm bg-transparent outline-none text-slate-700 placeholder-slate-400 min-w-0"
                      />
                      <button onClick={addCategory} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 shrink-0">Add</button>
                      <button onClick={() => setShowAddCat(false)} className="text-xs text-slate-400 hover:text-slate-600 shrink-0">✕</button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowAddCat(true)}
                      className="flex items-center justify-center gap-2 border-2 border-dashed border-slate-200 rounded-xl p-3.5 text-sm font-semibold text-slate-400 hover:border-[#2C4A70] hover:text-[#2C4A70] transition-colors bg-white"
                    >
                      <Plus size={14} /> ADD CATEGORY
                    </button>
                  )}
                </div>
              </div>

              {/* Totals row */}
              <div className="bg-white rounded-2xl border border-slate-200 px-6 py-4 shadow-sm flex items-center gap-6">
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Total Income</p>
                  <p className="text-xl font-black text-slate-800">₹{Math.round(income).toLocaleString('en-IN')}</p>
                </div>
                <div className="w-px h-9 bg-slate-100 shrink-0" />
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Total Expenses</p>
                  <p className="text-xl font-black text-rose-600">₹{Math.round(totalExpenses).toLocaleString('en-IN')}</p>
                </div>
                <div className="w-px h-9 bg-slate-100 shrink-0" />
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Monthly Surplus</p>
                  <p className={`text-xl font-black ${surplus >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {surplus >= 0 ? '' : '-'}₹{Math.round(Math.abs(surplus)).toLocaleString('en-IN')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>

      {/* Footer nav */}
      <div className="bg-white border-t border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-[#2C4A70] transition-colors uppercase tracking-wide"
        >
          <ArrowRight size={14} className="rotate-180" /> Back to Goals
        </button>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full border-2 border-[#2C4A70] flex items-center justify-center text-[11px] font-black text-[#2C4A70]">1/2</div>
            <div>
              <p className="text-[10px] font-bold text-[#2C4A70] uppercase tracking-widest leading-none">Step 1 of 2</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Monthly Cash Flow</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => persist()}
              className="px-5 py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors uppercase tracking-wide"
            >
              Save Draft
            </button>
            <Btn onClick={() => { persist(); setStep(2); }}>Next: Annual Expenses</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Hub Sidebar + Content ────────────────────────────────────────────────
const NAV = [
  { id: 'mapping',    label: 'Mapping',    icon: Layers,         desc: 'Assets & liabilities'    },
  { id: 'goals',      label: 'Goals',      icon: Target,         desc: 'Financial milestones'    },
  { id: 'cashflow',   label: 'Cash Flow',  icon: TrendingUp,     desc: 'Income & expenses'       },
  { id: 'dashboards', label: 'Dashboards', icon: LayoutDashboard,desc: 'Your financial overview' },
];

const DEFAULT_PROFILE  = { perspective: '', timeAvailable: '', legalName: '', partnerName: '', householdFor: '', householdType: '', dependents: 0 };
const DEFAULT_MAPPING  = { rawAssetsMap: '', assets: [], liabilities: [] };
const DEFAULT_GOALS    = { goals: [], incomeString: '', expenses: { housing: '', transport: '', food: '', utilities: '', other: '' }, completed: false };
// DEFAULT_CASHFLOW is defined above CashFlowSection

function Hub({ sections, setSections, profileData, setProfileData, userEmail, onLogout }) {
  // Start with empty defaults — never read localStorage.
  // useEffect below populates from the DB; until it resolves we show a spinner
  // so child sections (MappingSection etc.) don't mount with stale state.
  const [mappingData,      setMappingData]      = useState(DEFAULT_MAPPING);
  const [goalsData,        setGoalsData]        = useState(DEFAULT_GOALS);
  const [cashflowData,     setCashflowData]     = useState(DEFAULT_CASHFLOW);
  const [annualData,       setAnnualData]       = useState(DEFAULT_ANNUAL);
  const [dbReady,          setDbReady]          = useState(false);

  useEffect(() => {
    API.dashboard.load()
      .then(dbData => {
        if (!dbData) return;
        // Map assets/liabilities from DB format to flat arrays the form expects
        const flatAssets = Object.entries(dbData.assets || {}).flatMap(([cat, items]) =>
          items.map(a => ({ id: a.id, name: a.name, value: a.balance, type: cat }))
        );
        const flatLiabilities = Object.entries(dbData.liabilities || {}).flatMap(([cat, items]) =>
          items.map(l => ({ id: l.id, name: l.name, value: l.balance, type: cat }))
        );
        if (flatAssets.length || flatLiabilities.length) {
          setMappingData(d => ({ ...d, assets: flatAssets, liabilities: flatLiabilities }));
        }
        const mappedGoals = (dbData.goals || []).map(g => ({
          id: g.id, name: g.name, targetAmount: g.target,
          years: g.years, alreadySaved: g.current, status: 'Confirmed',
        }));
        if (mappedGoals.length) {
          setGoalsData(d => ({ ...d, goals: mappedGoals, completed: true }));
        }
      })
      .catch(() => {})  // new user — proceed with empty defaults
      .finally(() => setDbReady(true));
  }, []);
  const [active, setActive] = useState(() => {
    if (!sections.mapping)  return 'mapping';
    if (!sections.goals)    return 'goals';
    if (!sections.cashflow) return 'cashflow';
    return 'dashboards';
  });

  const canAccess = {
    mapping:    true,
    goals:      Boolean(sections.mapping),
    cashflow:   Boolean(sections.goals),
    dashboards: true,   // accessible once hub loads (profiling done)
  };

  const completeSection = (id) => {
    const updated = { ...sections, [id]: true };
    setSections(updated);
    saveJson(SK.sections, updated);
    if (id === 'mapping')  setActive('goals');
    if (id === 'goals')    setActive('cashflow');
    if (id === 'cashflow') setActive('dashboards');
  };

  const resetAll = () => {
    Object.values(SK).forEach(k => localStorage.removeItem(k));
    localStorage.removeItem('onboarding_v2_complete');
    localStorage.removeItem('onboarding_v2_data');
    window.location.reload();
  };

  const firstName = profileData.legalName?.split(' ')[0] || '';

  if (!dbReady) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F7F8F9]">
        <div className="w-8 h-8 rounded-full border-2 border-[#2C4A70] border-t-transparent animate-spin" />
      </div>
    );
  }

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
              <GoalsSection data={goalsData} setData={setGoalsData} perspective={profileData.perspective} assets={mappingData.assets || []} onComplete={() => completeSection('goals')} />
            </motion.div>
          )}
          {active === 'cashflow' && (
            <motion.div key="cashflow" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1 flex flex-col h-full">
              <CashFlowSection
                data={cashflowData}
                setData={setCashflowData}
                annualData={annualData}
                setAnnualData={setAnnualData}
                onBack={() => setActive('goals')}
                onComplete={() => completeSection('cashflow')}
              />
            </motion.div>
          )}
          {active === 'dashboards' && (
            <motion.div key="dashboards" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1 flex flex-col h-full">
              <DashboardsSection
                onboardingData={{ profile: profileData, mapping: mappingData, goals: goalsData, cashflow: cashflowData, annualExpenses: annualData }}
                completedSections={sections}
                onNavigate={setActive}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

// ─── Root export ──────────────────────────────────────────────────────────
export default function OnboardingV4({ userEmail = '', onLogout, onComplete }) {
  // Never read from localStorage — source of truth is the DB.
  // Start with empty state; a useEffect populates from DB if the user has been here before.
  const [sections, setSections]       = useState({});
  const [profileData, setProfileData] = useState(DEFAULT_PROFILE);
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    API.dashboard.load()
      .then(dbData => {
        if (!dbData) return;
        const hasName    = dbData.name && dbData.name !== 'Rahul';
        const hasAssets  = Object.values(dbData.assets  || {}).flat().length > 0;
        const hasGoals   = (dbData.goals || []).length > 0;
        if (hasName || hasAssets || hasGoals) {
          setProfileData(d => ({ ...d, legalName: dbData.name || d.legalName }));
          setSections({ profiling: true, mapping: hasAssets, goals: hasGoals });
        }
      })
      .catch(() => {})  // new user or not authenticated yet — show ProfileScreen
      .finally(() => setBootstrapping(false));
  }, []);

  const handleProfileDone = (data) => {
    setProfileData(data);
    saveJson(SK.profile, data);
    const updated = { ...sections, profiling: true };
    setSections(updated);
    saveJson(SK.sections, updated);
    if (onComplete) onComplete(data);
  };

  if (bootstrapping) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F7F8F9]">
        <div className="w-8 h-8 rounded-full border-2 border-[#2C4A70] border-t-transparent animate-spin" />
      </div>
    );
  }

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
