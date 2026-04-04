import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import {
  ArrowRight, ArrowLeft, Check, X, PlusCircle, CheckCircle2, Target, Zap, Send,
} from 'lucide-react';
import { API } from './api.js';

// ─── CONSTANTS ────────────────────────────────────────────────────────────────

const PROFILE_TYPES = [
  { id: 'salaried',  emoji: '💼', label: 'Salaried',    desc: 'Monthly income, tax planning, EPF/NPS' },
  { id: 'business',  emoji: '🏪', label: 'Business',    desc: 'Cash flow, GST, mixed personal/business' },
  { id: 'investor',  emoji: '📊', label: 'Investor',    desc: 'Stocks, mutual funds, compounding' },
  { id: 'retired',   emoji: '🌅', label: 'Retired',     desc: 'Corpus drawdown, fixed income' },
  { id: 'homemaker', emoji: '🏠', label: 'Homemaker',   desc: 'Household budgets, family goals' },
  { id: 'other',     emoji: '🌟', label: 'Exploring',   desc: "Not sure yet — let's find out together" },
];

const ASSET_CATS = [
  { id: 'banks',         emoji: '🏦', label: 'Bank Accounts',       sub: 'Savings, current, salary' },
  { id: 'sips',          emoji: '📦', label: 'Mutual Funds / SIPs', sub: 'Groww, Kuvera, Zerodha Coin' },
  { id: 'stocks',        emoji: '📈', label: 'Stocks',              sub: 'Direct equity — NSE / BSE / US' },
  { id: 'epfNps',        emoji: '🛡️', label: 'EPF / NPS',          sub: 'Provident fund, pension accounts' },
  { id: 'fixedDeposits', emoji: '🔒', label: 'Fixed Deposits',      sub: 'Bank FDs, recurring deposits' },
  { id: 'gold',          emoji: '🥇', label: 'Gold',               sub: 'Jewellery, coins, digital gold' },
  { id: 'realEstate',    emoji: '🏘️', label: 'Real Estate',        sub: 'Property, flat, land' },
  { id: 'foreign',       emoji: '🌍', label: 'Foreign / Crypto',    sub: 'US ETFs, NRI funds, crypto' },
  { id: 'moneyLent',     emoji: '🤝', label: 'Money Lent',          sub: 'Loans given to friends / family' },
  { id: 'otherAssets',   emoji: '➕', label: 'Other Assets',        sub: 'Vehicle, art, anything else' },
];

const LIABILITY_CATS = [
  { id: 'creditCards',    emoji: '💳', label: 'Credit Cards',    sub: 'Outstanding balance on cards' },
  { id: 'homeLoans',      emoji: '🏠', label: 'Home Loan',       sub: 'Outstanding principal + EMI' },
  { id: 'vehicleLoans',   emoji: '🚗', label: 'Vehicle Loan',    sub: 'Car, bike, commercial vehicle' },
  { id: 'educationLoans', emoji: '🎓', label: 'Education Loan',  sub: 'Self or child education' },
  { id: 'personalLoans',  emoji: '💸', label: 'Personal Loan',   sub: 'Bank, NBFC or fintech app' },
  { id: 'otherLoans',     emoji: '🤲', label: 'Other Debts',     sub: 'Friends, relatives, chit fund' },
];

// Pre-checked categories based on profile type
const PROFILE_PRESETS = {
  salaried:  { assets: ['banks', 'epfNps', 'sips'],                      liabilities: ['creditCards'] },
  business:  { assets: ['banks'],                                         liabilities: ['creditCards'] },
  investor:  { assets: ['banks', 'stocks', 'sips'],                      liabilities: ['creditCards'] },
  retired:   { assets: ['banks', 'fixedDeposits', 'epfNps', 'gold'],     liabilities: [] },
  homemaker: { assets: ['banks', 'gold'],                                 liabilities: [] },
  other:     { assets: ['banks'],                                         liabilities: [] },
};

// Pre-selected goal types by profile
const GOAL_PRESETS = {
  salaried:  ['emergency', 'retire'],
  business:  ['emergency', 'retire'],
  investor:  ['retire'],
  retired:   [],
  homemaker: ['emergency'],
  other:     ['emergency'],
};

const GOAL_CATS = [
  { id: 'retire',    iconBg: 'bg-orange-100', emoji: '🌅', label: 'RETIREMENT',        desc: 'Stop relying on a salary — build your retirement corpus.' },
  { id: 'emergency', iconBg: 'bg-red-100',    emoji: '🛡️', label: 'EMERGENCY FUND',   desc: '3–12 months of expenses, always liquid and ready.' },
  { id: 'education', iconBg: 'bg-purple-100', emoji: '🎓', label: 'EDUCATION',         desc: "Plan for your child's college or professional degree." },
  { id: 'home',      iconBg: 'bg-blue-100',   emoji: '🏠', label: 'HOME / BIG PURCHASE', desc: 'Down payment, new car, wedding — any big-ticket item.' },
  { id: 'vacation',  iconBg: 'bg-sky-100',    emoji: '✈️', label: 'HOLIDAYS',          desc: 'Put vacations on autopilot — any destination, any year.' },
  { id: 'custom',    iconBg: 'bg-amber-100',  emoji: '✨', label: 'SOMETHING ELSE',    desc: "Name your own goal and we'll build a plan around it." },
];

const BANKS        = ['HDFC Bank','SBI','ICICI Bank','Axis Bank','Kotak Mahindra Bank','Yes Bank','Bank of Baroda','Canara Bank','Standard Chartered','Bank of India','PNB','IndusInd Bank','Federal Bank','IDFC First Bank','Other'];
const BROKERS      = ['Zerodha','Groww','Angel One','Upstox','HDFC Securities','ICICI Direct','Other'];
const MF_PLATFORMS = ['Groww','Kuvera','Paytm Money','SBI MF','HDFC MF','Zerodha Coin','MF Central','Other'];
const CITIES       = ['Bengaluru','Mumbai','Delhi','Hyderabad','Chennai','Pune','Kolkata','Ahmedabad','Jaipur','Kochi','Other'];

const PERSONA_DEFAULTS = {
  salaried:  { bankAccounts: [{ _id: 1, nickname: 'Salary A/c', bank: 'HDFC Bank', balance: '' }], epf: { hasEpf: true, balance: '' } },
  business:  { bankAccounts: [{ _id: 1, nickname: 'Current A/c', bank: 'HDFC Bank', balance: '' }] },
  investor:  { bankAccounts: [{ _id: 1, nickname: 'Savings A/c', bank: 'HDFC Bank', balance: '' }], stocks: [{ _id: 1, broker: 'Zerodha', value: '' }], mutualFunds: [{ _id: 1, platform: 'Groww', value: '' }] },
  retired:   { bankAccounts: [{ _id: 1, nickname: 'Pension A/c', bank: 'SBI', balance: '' }], nps: { hasNps: true, balance: '' } },
  homemaker: { bankAccounts: [{ _id: 1, nickname: 'Family Savings', bank: 'SBI', balance: '' }] },
  other:     { bankAccounts: [{ _id: 1, nickname: 'Savings A/c', bank: 'HDFC Bank', balance: '' }] },
};

// Grouped screens for Phase 2 (previously Phase 3 one-per-category)
const CATEGORY_GROUPS = [
  { id: 'banking',      label: 'Banks & Cash',    emoji: '🏦', cats: ['banks'] },
  { id: 'investments',  label: 'Investments',     emoji: '📊', cats: ['sips', 'stocks', 'epfNps'] },
  { id: 'other-assets', label: 'Other Assets',    emoji: '💼', cats: ['fixedDeposits', 'gold', 'realEstate', 'foreign', 'moneyLent', 'otherAssets'] },
  { id: 'liabilities',  label: 'Loans & Debts',   emoji: '📋', cats: ['creditCards', 'homeLoans', 'vehicleLoans', 'educationLoans', 'personalLoans', 'otherLoans'] },
];

// ─── DEFAULT STATE ────────────────────────────────────────────────────────────

const D_PROFILE = { name: '', age: '', profileType: null, city: 'Bengaluru', maritalStatus: null, numChildren: 0 };

const D_OWNED = {
  bankAccounts: [], cashInHand: '',
  mutualFunds: [], stocks: [],
  epf: { hasEpf: null, balance: '' }, nps: { hasNps: null, balance: '' },
  fixedDeposits: [],
  gold: { jewellery: '', coins: '', digital: '' },
  realEstate: [],
  otherAssets: [], foreignInvestments: [], moneyLent: [],
};

const D_OWED = {
  creditCards: [], homeLoans: [], vehicleLoans: [],
  educationLoans: [], personalLoans: [], otherLoans: [],
};

const D_GOALS = {
  retire: { on: false }, emergency: { on: false, months: 6 },
  education: [], home: { on: false }, vacation: [], custom: [],
};

// ─── UTILS ────────────────────────────────────────────────────────────────────

function inr(n) {
  const num = parseInt(n) || 0;
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000)   return `₹${(num / 100000).toFixed(1)}L`;
  if (num >= 1000)     return `₹${(num / 1000).toFixed(0)}k`;
  return `₹${num.toLocaleString('en-IN')}`;
}

function sum(arr, key) {
  return (arr || []).reduce((s, i) => s + (parseInt(i[key]) || 0), 0);
}

function fmtINR(raw) {
  const digits = String(raw ?? '').replace(/\D/g, '');
  if (!digits) return '';
  return parseInt(digits, 10).toLocaleString('en-IN');
}

function firstName(name) { return (name || '').trim().split(' ')[0] || ''; }

function computeAssetTotal(owned) {
  return [
    sum(owned.bankAccounts, 'balance'), parseInt(owned.cashInHand) || 0,
    sum(owned.mutualFunds, 'value'), sum(owned.stocks, 'value'),
    parseInt(owned.epf?.balance) || 0, parseInt(owned.nps?.balance) || 0,
    sum(owned.fixedDeposits, 'amount'),
    (parseInt(owned.gold?.jewellery)||0) + (parseInt(owned.gold?.coins)||0) + (parseInt(owned.gold?.digital)||0),
    sum(owned.realEstate, 'value'), sum(owned.otherAssets, 'value'),
    sum(owned.foreignInvestments, 'amountInr'), sum(owned.moneyLent, 'amount'),
  ].reduce((a, b) => a + b, 0);
}

function computeLiabilityTotal(owed) {
  return [
    sum(owed.creditCards, 'outstanding'), sum(owed.homeLoans, 'outstanding'),
    sum(owed.vehicleLoans, 'outstanding'), sum(owed.educationLoans, 'outstanding'),
    sum(owed.personalLoans, 'outstanding'), sum(owed.otherLoans, 'amount'),
  ].reduce((a, b) => a + b, 0);
}

// ─── PRIMITIVES ───────────────────────────────────────────────────────────────

const INPUT_CLS = 'w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent bg-white transition';
const LABEL_CLS = 'block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wide';

function TI({ value, onChange, placeholder, autoFocus }) {
  return <input type="text" value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder} autoFocus={autoFocus} className={INPUT_CLS} />;
}

function NI({ value, onChange, placeholder, prefix, suffix }) {
  return (
    <div className="relative">
      {prefix && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400 pointer-events-none">{prefix}</span>}
      <input type="text" inputMode="numeric"
        value={fmtINR(value)} onChange={e => onChange(e.target.value.replace(/\D/g, ''))}
        placeholder={placeholder}
        className={INPUT_CLS + (prefix ? ' pl-7' : '') + (suffix ? ' pr-14' : '')} />
      {suffix && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 pointer-events-none">{suffix}</span>}
    </div>
  );
}

function SI({ value, onChange, options, placeholder }) {
  return (
    <select value={value || ''} onChange={e => onChange(e.target.value)}
      className={INPUT_CLS + ' cursor-pointer ' + (!value ? 'text-slate-400' : '')}>
      <option value="">{placeholder}</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

function Toggle({ value, onChange, opts }) {
  return (
    <div className="flex flex-wrap gap-2">
      {opts.map(o => (
        <button key={o.v} onClick={() => onChange(o.v)}
          className={`px-4 py-2 rounded-xl text-sm font-medium border transition ${value === o.v ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm' : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-600'}`}>
          {o.l}
        </button>
      ))}
    </div>
  );
}

function SmToggle({ value, onChange, opts }) {
  return (
    <div className="flex flex-wrap gap-1">
      {opts.map(o => (
        <button key={o.v} onClick={() => onChange(o.v)}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition ${value === o.v ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'}`}>
          {o.l}
        </button>
      ))}
    </div>
  );
}

function ChipPicker({ value, onChange, options, placeholder = 'Type here...' }) {
  const chips = options[options.length - 1] === 'Other' ? options.slice(0, -1) : options;
  const [otherMode, setOtherMode] = useState(value && !chips.includes(value));
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {chips.map(opt => (
          <button key={opt} type="button" onClick={() => { setOtherMode(false); onChange(opt); }}
            className={`px-2.5 py-1 rounded-full text-xs font-medium border transition ${!otherMode && value === opt ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'}`}>
            {opt}
          </button>
        ))}
        <button type="button" onClick={() => { setOtherMode(true); onChange(''); }}
          className={`px-2.5 py-1 rounded-full text-xs font-medium border transition ${otherMode ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-500 border-dashed border-slate-300 hover:border-indigo-300'}`}>
          + Other
        </button>
      </div>
      {otherMode && <input type="text" value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder} autoFocus className={INPUT_CLS} />}
    </div>
  );
}

function ListBuilder({ items, onChange, blank, addLabel, renderRow }) {
  const add = () => onChange([...items, { ...blank, _id: Date.now() }]);
  const rm  = i => onChange(items.filter((_, idx) => idx !== i));
  const up  = (i, k, v) => onChange(items.map((item, idx) => idx === i ? { ...item, [k]: v } : item));
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={item._id || i} className="relative bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <button onClick={() => rm(i)} className="absolute top-3 right-3 text-slate-300 hover:text-red-400 transition p-0.5"><X size={14} /></button>
          {renderRow(item, i, (k, v) => up(i, k, v))}
        </div>
      ))}
      <button onClick={add} className="flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition py-1">
        <PlusCircle size={15} />{addLabel}
      </button>
    </div>
  );
}

// ─── AI GUIDE ─────────────────────────────────────────────────────────────────

const AI_SUGGESTED = {
  1: ["I'm Priya, 28, software engineer in Bangalore, married with 2 kids", "I run a small business in Pune, 45 years old", "I'm 62, retired, living in Chennai"],
  2: ["HDFC savings ₹2 lakhs, SBI ₹50k, EPF ₹8 lakhs", "Zerodha stocks worth ₹3 lakhs, Groww MF ₹5 lakhs", "Home loan ₹35 lakhs outstanding, EMI ₹32,000"],
  3: ["Retire at 58 with ₹70k/month expenses", "Emergency fund 6 months, spend ₹55k/month", "Save ₹20 lakhs for daughter's college in 12 years"],
  4: [],
};

const AI_WELCOME = {
  1: "👋 Hi! Tell me about yourself and I'll fill in the form for you.",
  2: "Tell me the values for each account or loan — I'll fill them in.",
  3: "What are you saving for? Tell me your plans and I'll set them up.",
  4: "Your picture is ready! Click the button below to enter your Ledger.",
};

function parseAIForPhase(text, phase, currentCatId) {
  const t = text, lo = text.toLowerCase();
  const fills = {};

  if (phase === 1) {
    const nm = t.match(/(?:i(?:'m| am)|my name is|call me)\s+([A-Z][a-z]{1,20})/i) || t.match(/^([A-Z][a-z]{1,20})[,\s]/);
    if (nm) fills.name = nm[1];
    const ag = t.match(/(\d{2})\s*(?:years? old|yr)/i) || t.match(/,\s*(\d{2})\s*[,\s]/);
    if (ag) { const a = parseInt(ag[1]); if (a >= 18 && a <= 90) fills.age = String(a); }
    if (/software|engineer|developer|salaried|employee|works? (?:at|for)/i.test(lo)) fills.profileType = 'salaried';
    else if (/business|entrepreneur|owner|shop/i.test(lo)) fills.profileType = 'business';
    else if (/investor|stocks|trading/i.test(lo)) fills.profileType = 'investor';
    else if (/homemaker|housewife|stay.at.home/i.test(lo)) fills.profileType = 'homemaker';
    else if (/retire[d]/i.test(lo)) fills.profileType = 'retired';
    const city = ['Bengaluru','Mumbai','Delhi','Hyderabad','Chennai','Pune','Kolkata','Ahmedabad'].find(c => new RegExp('\\b' + c + '\\b', 'i').test(t));
    if (city) fills.city = city;
    if (/\bmarried\b/i.test(lo)) fills.maritalStatus = 'yes';
    else if (/\bsingle\b|\bnot married\b/i.test(lo)) fills.maritalStatus = 'no';
    const kd = t.match(/(\d)\s*(?:kid|child|son|daughter)/i);
    if (kd) fills.numChildren = parseInt(kd[1]);
    else if (/no kids|no children/i.test(lo)) fills.numChildren = 0;
  }

  if (phase === 2) {
    const parseAmt = (numStr, ctx = '') => {
      const n = parseInt((numStr || '').replace(/,/g, '')) || 0;
      const c = ctx.toLowerCase();
      if (/cr(ore)?/.test(c)) return n * 10000000;
      if (/lakh|lac/.test(c)) return n * 100000;
      if (/\bk\b|thousand/.test(c)) return n * 1000;
      return n;
    };
    // Bank balance
    const bk = t.match(/(?:hdfc|sbi|icici|axis|kotak|savings?)[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (bk) fills.bankBalance = String(parseAmt(bk[1], bk[0]));
    // Generic amount
    const amt = t.match(/₹\s*([\d,]+)\s*(lakh|lac|k|cr)?/i) || t.match(/rs\.?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (amt) fills.amount = String(parseAmt(amt[1], amt[0]));
    // EPF
    const epf = t.match(/epf[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (epf) fills.epfBalance = String(parseAmt(epf[1], epf[0]));
    // Outstanding (loans)
    const out = t.match(/outstanding[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (out) fills.outstanding = String(parseAmt(out[1], out[0]));
    // EMI
    const emi = t.match(/emi[^₹\d]*?₹?\s*([\d,]+)/i);
    if (emi) fills.emi = String(parseAmt(emi[1], emi[0]));
  }

  if (phase === 3) {
    const parseAmt = (n, ctx) => { const v = parseInt((n||'').replace(/,/g,''))||0; return /lakh|lac/i.test(ctx) ? v*100000 : /k\b/i.test(ctx) ? v*1000 : v; };
    const ra = t.match(/retire[^at]*?at\s*(\d{2})/i);
    if (ra) fills.retireAge = ra[1];
    const rm = t.match(/(?:₹|rs?\.?)\s*([\d,]+)\s*(k|lakh)?.*?(?:per month|\/month|monthly)/i);
    if (rm) fills.retireMonthly = String(parseAmt(rm[1], rm[0]));
    const em = t.match(/emergency.*?(\d+)\s*months?/i) || t.match(/(\d+)\s*months?.*?emergency/i);
    if (em) fills.emergencyMonths = em[1];
    const me = t.match(/(?:spend|expenses?)[^₹\d]*?(?:₹|rs?\.?)\s*([\d,]+)\s*(k|lakh)?.*?(?:per month|\/month|monthly)/i);
    if (me) fills.monthlyExpense = String(parseAmt(me[1], me[0]));
  }

  return fills;
}

function aiReplyText(fills, phase, currentCatId) {
  if (!Object.keys(fills).length) return AI_WELCOME[phase] || "Tell me more and I'll fill the form!";
  const lines = [];
  if (phase === 1) {
    if (fills.name) lines.push(`✅ Name: **${fills.name}**`);
    if (fills.age) lines.push(`✅ Age: **${fills.age}**`);
    if (fills.profileType) lines.push(`✅ Profile: **${fills.profileType}**`);
    if (fills.city) lines.push(`✅ City: **${fills.city}**`);
    if (fills.maritalStatus) lines.push(`✅ Married: **${fills.maritalStatus === 'yes' ? 'Yes' : 'No'}**`);
    if (fills.numChildren !== undefined) lines.push(`✅ Children: **${fills.numChildren}**`);
  }
  if (phase === 2) {
    if (fills.bankBalance) lines.push(`✅ Bank balance: **₹${parseInt(fills.bankBalance).toLocaleString('en-IN')}**`);
    if (fills.amount) lines.push(`✅ Amount: **₹${parseInt(fills.amount).toLocaleString('en-IN')}**`);
    if (fills.epfBalance) lines.push(`✅ EPF balance: **₹${parseInt(fills.epfBalance).toLocaleString('en-IN')}**`);
    if (fills.outstanding) lines.push(`✅ Outstanding: **₹${parseInt(fills.outstanding).toLocaleString('en-IN')}**`);
    if (fills.emi) lines.push(`✅ EMI: **₹${parseInt(fills.emi).toLocaleString('en-IN')}/mo**`);
  }
  if (phase === 3) {
    if (fills.retireAge) lines.push(`✅ Retire at: **${fills.retireAge} yrs**`);
    if (fills.retireMonthly) lines.push(`✅ Monthly expense: **₹${parseInt(fills.retireMonthly).toLocaleString('en-IN')}**`);
    if (fills.emergencyMonths) lines.push(`✅ Emergency fund: **${fills.emergencyMonths} months**`);
    if (fills.monthlyExpense) lines.push(`✅ Monthly spend: **₹${parseInt(fills.monthlyExpense).toLocaleString('en-IN')}**`);
  }
  return `Got it!\n\n${lines.join('\n')}\n\nDoes this look right?`;
}

function AiPanel({ phase, currentCatId, onApply }) {
  const [msgs, setMsgs] = useState([{ role: 'ai', text: AI_WELCOME[phase] || '' }]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [showSugg, setShowSugg] = useState(true);
  const endRef = useRef(null);

  useEffect(() => {
    setMsgs([{ role: 'ai', text: AI_WELCOME[phase] || '' }]);
    setShowSugg(true);
    setInput('');
  }, [phase]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, typing]);

  const send = () => {
    const txt = input.trim();
    if (!txt) return;
    setInput('');
    setShowSugg(false);
    setMsgs(p => [...p, { role: 'user', text: txt }]);
    setTyping(true);
    setTimeout(() => {
      const fills = parseAIForPhase(txt, phase, currentCatId);
      const replyTxt = aiReplyText(fills, phase, currentCatId);
      const hasFills = Object.keys(fills).length > 0;
      setTyping(false);
      setMsgs(p => [...p, { role: 'ai', text: replyTxt, fills: hasFills ? fills : null }]);
    }, 600 + Math.random() * 300);
  };

  const apply = fills => {
    onApply(fills);
    setMsgs(p => [...p, { role: 'ai', text: '✅ Done! Check the form and edit anything if needed.' }]);
  };

  const renderLine = (line, j) => {
    if (!line) return <br key={j} />;
    const html = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    const cls = line.startsWith('✅') ? 'text-[11px] text-emerald-700 font-medium' : 'text-[11px] leading-relaxed';
    return <p key={j} className={cls} dangerouslySetInnerHTML={{ __html: html }} />;
  };

  const suggestions = AI_SUGGESTED[phase] || [];

  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-violet-50 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-xl bg-indigo-600 flex items-center justify-center text-sm shrink-0">🤖</div>
          <div>
            <p className="text-xs font-bold text-slate-800">Your Financial Guide</p>
            <p className="text-[10px] text-slate-400">Just talk — I'll fill the form</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {msgs.map((m, i) => {
          const isAi = m.role === 'ai';
          return (
            <div key={i} className={`flex ${isAi ? 'justify-start' : 'justify-end'}`}>
              <div className="max-w-[90%] space-y-1.5">
                {isAi && <div className="flex items-center gap-1 mb-0.5"><div className="w-4 h-4 rounded-full bg-indigo-100 flex items-center justify-center text-[9px]">🤖</div><span className="text-[9px] text-slate-400">Guide</span></div>}
                <div className={`rounded-2xl px-3 py-2.5 space-y-0.5 ${isAi ? 'bg-white border border-slate-200 text-slate-700 rounded-tl-sm' : 'bg-indigo-600 text-white rounded-tr-sm'}`}>
                  {isAi ? m.text.split('\n').map(renderLine) : <p className="text-[11px]">{m.text}</p>}
                </div>
                {isAi && m.fills && (
                  <div className="flex gap-1.5 flex-wrap">
                    <button onClick={() => apply(m.fills)} className="flex items-center gap-1 text-[10px] font-bold bg-emerald-600 text-white px-2.5 py-1.5 rounded-lg hover:bg-emerald-700 transition">
                      <Check size={9} /> Fill this in
                    </button>
                    <button onClick={() => setMsgs(p => [...p, { role: 'ai', text: "No problem — tell me again or fill it in manually." }])}
                      className="text-[10px] font-medium text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 transition">
                      ✏️ Tweak
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {typing && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-3.5 py-3">
              <div className="flex gap-1 items-center h-3">
                {[0, 150, 300].map(d => <span key={d} className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: d + 'ms' }} />)}
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Suggestions */}
      {showSugg && msgs.length <= 1 && suggestions.length > 0 && (
        <div className="px-3 pb-2 flex flex-col gap-1 shrink-0">
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => { setInput(s); setShowSugg(false); }}
              className="text-[10px] bg-slate-50 border border-slate-200 text-slate-600 px-2.5 py-1.5 rounded-lg hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition text-left leading-tight">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-slate-100 shrink-0">
        <div className="flex gap-2">
          <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Type anything here…"
            className="flex-1 border border-slate-200 rounded-xl px-3.5 py-2 text-[11px] text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 transition" />
          <button onClick={send} disabled={!input.trim()}
            className="w-8 h-8 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white flex items-center justify-center transition shrink-0">
            <Send size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── BALANCE SCALE ────────────────────────────────────────────────────────────

function BalanceScale({ assets, liabilities, compact = false }) {
  const max   = Math.max(assets, liabilities, 1);
  const ratio = (assets - liabilities) / max;       // -1 to +1
  const tilt  = Math.max(-13, Math.min(13, ratio * 13)); // degrees; positive = left (assets) side down
  const net   = assets - liabilities;

  return (
    <div className={compact ? 'py-1' : 'py-3'}>
      {/* Numbers row */}
      <div className="flex items-start justify-between px-1 mb-3">
        <div>
          <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-0.5">Assets</p>
          <motion.p key={assets} initial={{ scale: 0.95 }} animate={{ scale: 1 }}
            className={`font-black text-emerald-700 ${compact ? 'text-lg' : 'text-2xl'}`}>
            {inr(assets)}
          </motion.p>
        </div>
        <div className="text-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Net Worth</p>
          <motion.p key={net} initial={{ scale: 0.95 }} animate={{ scale: 1 }}
            className={`font-black ${compact ? 'text-lg' : 'text-2xl'} ${net >= 0 ? 'text-indigo-700' : 'text-red-600'}`}>
            {net < 0 ? '−' : ''}{inr(Math.abs(net))}
          </motion.p>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-0.5">Liabilities</p>
          <motion.p key={liabilities} initial={{ scale: 0.95 }} animate={{ scale: 1 }}
            className={`font-black text-red-500 ${compact ? 'text-lg' : 'text-2xl'}`}>
            {inr(liabilities)}
          </motion.p>
        </div>
      </div>

      {/* Scale drawing */}
      <div className="flex flex-col items-center">
        <div className="relative" style={{ width: compact ? 240 : 300, height: compact ? 58 : 70 }}>

          {/* Fulcrum pivot */}
          <div className="absolute left-1/2 -translate-x-1/2 top-0 w-3 h-3 bg-slate-500 rounded-full z-10" />

          {/* Animated beam + pans */}
          <motion.div
            animate={{ rotate: -tilt }}
            transition={{ type: 'spring', stiffness: 90, damping: 18 }}
            style={{ transformOrigin: '50% 6px', position: 'absolute', top: 0, left: 0, right: 0 }}
          >
            {/* Beam bar */}
            <div className="absolute rounded-full mx-6" style={{
              height: 5, top: 3, left: 0, right: 0,
              background: net === 0
                ? '#94a3b8'
                : `linear-gradient(to right, ${net > 0 ? '#10b981' : '#f87171'}, #94a3b8, #f87171)`,
            }} />

            {/* Left string */}
            <div className="absolute bg-slate-300" style={{ width: 1, height: compact ? 18 : 22, top: 8, left: '12%' }} />
            {/* Left pan (assets) */}
            <div className={`absolute rounded-xl border-2 flex items-center justify-center transition-colors ${assets > 0 ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'bg-slate-50 border-slate-200 text-slate-300'}`}
              style={{ width: compact ? 50 : 62, height: compact ? 22 : 26, top: compact ? 26 : 30, left: '2%' }}>
              <span className={`font-bold ${compact ? 'text-[9px]' : 'text-[10px]'}`}>
                {assets > 0 ? inr(assets) : '—'}
              </span>
            </div>

            {/* Right string */}
            <div className="absolute bg-slate-300" style={{ width: 1, height: compact ? 18 : 22, top: 8, right: '12%' }} />
            {/* Right pan (liabilities) */}
            <div className={`absolute rounded-xl border-2 flex items-center justify-center transition-colors ${liabilities > 0 ? 'bg-red-50 border-red-200 text-red-500' : 'bg-slate-50 border-slate-200 text-slate-300'}`}
              style={{ width: compact ? 50 : 62, height: compact ? 22 : 26, top: compact ? 26 : 30, right: '2%' }}>
              <span className={`font-bold ${compact ? 'text-[9px]' : 'text-[10px]'}`}>
                {liabilities > 0 ? inr(liabilities) : '—'}
              </span>
            </div>
          </motion.div>
        </div>

        {/* Post + base */}
        <div className="w-1.5 rounded-full bg-slate-400" style={{ height: compact ? 8 : 12, marginTop: -2 }} />
        <div className="rounded-full bg-slate-200" style={{ width: compact ? 36 : 48, height: compact ? 4 : 6 }} />
      </div>
    </div>
  );
}

// ─── PHASE 1: PROFILE + CATEGORY PICKER (merged) ─────────────────────────────

function Phase1_ProfileAndPick({ data, setData, selAssets, setSelAssets, selLiabilities, setSelLiabilities, onNext }) {
  const [errs, setErrs] = useState({});
  const up = (k, v) => setData(p => ({ ...p, [k]: v }));
  const name = firstName(data.name);

  const handleProfileType = (profileType) => {
    up('profileType', profileType);
    const preset = PROFILE_PRESETS[profileType] || PROFILE_PRESETS.other;
    setSelAssets(new Set(preset.assets));
    setSelLiabilities(new Set(preset.liabilities));
  };

  const toggleA = id => setSelAssets(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
  const toggleL = id => setSelLiabilities(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });

  const go = () => {
    const e = {};
    if (!data.name?.trim() || data.name.length < 2) e.name = 'Please enter your name';
    if (!data.age || parseInt(data.age) < 18 || parseInt(data.age) > 90) e.age = 'Enter a valid age (18–90)';
    if (!data.profileType) e.profileType = 'Please pick one that fits you';
    if (selAssets.size + selLiabilities.size === 0) e.cats = 'Select at least one category to continue';
    setErrs(e);
    if (!Object.keys(e).length) onNext();
  };

  return (
    <div className="max-w-3xl mx-auto w-full py-8 px-4 space-y-5">
      {/* Header */}
      <div>
        <AnimatePresence mode="wait">
          {name
            ? <motion.div key={name} initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
                <p className="text-2xl font-extrabold text-slate-900">Great to meet you, {name}!</p>
                <p className="text-slate-500 text-sm mt-0.5">Just a few more details to personalise your Ledger.</p>
              </motion.div>
            : <motion.div key="default" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <p className="text-2xl font-extrabold text-slate-900">Let's set up your Ledger.</p>
                <p className="text-slate-500 text-sm mt-0.5">Takes under 3 minutes. Estimates are totally fine.</p>
              </motion.div>
          }
        </AnimatePresence>
      </div>

      {/* Personal details card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">About you</p>
        <div className="grid grid-cols-4 gap-3">
          <div className="col-span-2">
            <label className={LABEL_CLS}>Your name</label>
            <TI value={data.name} onChange={v => up('name', v)} placeholder="e.g. Priya" autoFocus />
            {errs.name && <p className="text-xs text-red-500 mt-0.5">{errs.name}</p>}
          </div>
          <div>
            <label className={LABEL_CLS}>Age</label>
            <NI value={data.age} onChange={v => up('age', v)} placeholder="28" />
            {errs.age && <p className="text-xs text-red-500 mt-0.5">{errs.age}</p>}
          </div>
          <div>
            <label className={LABEL_CLS}>City</label>
            <SI value={data.city} onChange={v => up('city', v)} options={CITIES} placeholder="Select city" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLS}>Married?</label>
            <SmToggle value={data.maritalStatus} onChange={v => up('maritalStatus', v)}
              opts={[{ v: 'yes', l: 'Yes' }, { v: 'no', l: 'Not yet' }]} />
          </div>
          <div>
            <label className={LABEL_CLS}>Children</label>
            <SmToggle value={String(data.numChildren)} onChange={v => up('numChildren', parseInt(v))}
              opts={[{ v: '0', l: 'None' }, { v: '1', l: '1' }, { v: '2', l: '2' }, { v: '3', l: '3+' }]} />
          </div>
        </div>
      </div>

      {/* Profile type + reactive category picker */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-5">
        <div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Which of these fits you best?</p>
          {errs.profileType && <p className="text-xs text-red-500 mb-2">{errs.profileType}</p>}
          <div className="grid grid-cols-3 gap-2.5">
            {PROFILE_TYPES.map(p => (
              <button key={p.id} onClick={() => handleProfileType(p.id)}
                className={`flex items-start gap-2.5 p-3 rounded-xl border-2 transition-all text-left ${
                  data.profileType === p.id
                    ? 'border-indigo-500 bg-indigo-50/70 shadow-md ring-2 ring-indigo-100'
                    : 'border-slate-100 bg-white hover:border-indigo-200 hover:bg-slate-50 hover:shadow-sm'
                }`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-base shrink-0 ${data.profileType === p.id ? 'bg-indigo-100' : 'bg-slate-50'}`}>
                  {p.emoji}
                </div>
                <div className="min-w-0">
                  <p className={`text-sm font-bold leading-tight mb-0.5 ${data.profileType === p.id ? 'text-indigo-700' : 'text-slate-800'}`}>{p.label}</p>
                  <p className="text-[10px] text-slate-400 leading-relaxed">{p.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Category checkboxes — appear once profile type is selected */}
        <AnimatePresence>
          {data.profileType && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
              className="border-t border-slate-100 pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Tick what you have</p>
                <p className="text-[10px] text-slate-400">Pre-selected based on your profile — adjust freely</p>
              </div>
              {errs.cats && <p className="text-xs text-red-500">{errs.cats}</p>}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-2">Assets — what you own</p>
                  <div className="space-y-1.5">
                    {ASSET_CATS.map(cat => {
                      const on = selAssets.has(cat.id);
                      return (
                        <button key={cat.id} onClick={() => toggleA(cat.id)}
                          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg border transition-all text-left ${
                            on ? 'border-emerald-300 bg-emerald-50' : 'border-slate-100 bg-white hover:border-emerald-200 hover:bg-slate-50'
                          }`}>
                          <span className="text-sm shrink-0">{cat.emoji}</span>
                          <span className={`text-xs font-medium flex-1 ${on ? 'text-emerald-800' : 'text-slate-600'}`}>{cat.label}</span>
                          <div className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-all ${
                            on ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300 bg-white'
                          }`}>
                            {on && <Check size={9} className="text-white" />}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-red-500 uppercase tracking-widest mb-2">Liabilities — what you owe</p>
                  <div className="space-y-1.5">
                    {LIABILITY_CATS.map(cat => {
                      const on = selLiabilities.has(cat.id);
                      return (
                        <button key={cat.id} onClick={() => toggleL(cat.id)}
                          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg border transition-all text-left ${
                            on ? 'border-red-200 bg-red-50' : 'border-slate-100 bg-white hover:border-red-200 hover:bg-slate-50'
                          }`}>
                          <span className="text-sm shrink-0">{cat.emoji}</span>
                          <span className={`text-xs font-medium flex-1 ${on ? 'text-red-800' : 'text-slate-600'}`}>{cat.label}</span>
                          <div className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-all ${
                            on ? 'bg-red-400 border-red-400' : 'border-slate-300 bg-white'
                          }`}>
                            {on && <Check size={9} className="text-white" />}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                  {selLiabilities.size === 0 && (
                    <p className="text-[10px] text-slate-400 italic mt-2 px-1">No loans or debts? That's great!</p>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button onClick={go}
        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-indigo-100 transition flex items-center justify-center gap-2 group">
        {data.profileType ? 'Add my numbers' : (name ? `Looks good, ${name} — next` : "That's me — continue")}
        <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
      </button>

      <p className="text-center text-xs text-slate-400">🔒 Your data is encrypted and private</p>
    </div>
  );
}

// ─── PHASE 3: CATEGORY FORMS ──────────────────────────────────────────────────

// Persistent scale header shown at top of every Phase 3 screen
function ScaleHeader({ assets, liabilities, stepIdx, totalSteps, catLabel, catEmoji }) {
  return (
    <div className="bg-white border-b border-slate-200 shadow-sm px-6 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between gap-6">
          {/* Current category label */}
          <div className="flex items-center gap-2.5 shrink-0">
            <span className="text-xl">{catEmoji}</span>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Step {stepIdx + 1} of {totalSteps}
              </p>
              <p className="text-sm font-bold text-slate-800">{catLabel}</p>
            </div>
          </div>

          {/* Inline compact scale */}
          <div className="flex-1 max-w-md">
            <BalanceScale assets={assets} liabilities={liabilities} compact />
          </div>

          {/* Progress dots */}
          <div className="flex gap-1 shrink-0">
            {Array.from({ length: totalSteps }, (_, i) => (
              <div key={i} className={`h-1.5 rounded-full transition-all ${i < stepIdx ? 'w-4 bg-indigo-400' : i === stepIdx ? 'w-6 bg-indigo-600' : 'w-1.5 bg-slate-200'}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Renders the correct form for a given category id
function CategoryFormContent({ catId, owned, setOwned, owed, setOwed }) {
  const upO  = useCallback((k, v) => setOwned(p => ({ ...p, [k]: v })), [setOwned]);
  const upOw = useCallback((k, v) => setOwed(p => ({ ...p, [k]: v })), [setOwed]);

  const cardCls = 'bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4';

  switch (catId) {

    case 'banks': return (
      <div className="space-y-4">
        <div className={cardCls}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🏦 Bank Accounts</p>
          <div className="space-y-2">
            {(owned.bankAccounts || []).map((item, i) => {
              const u = (k, v) => { const arr = [...owned.bankAccounts]; arr[i] = { ...arr[i], [k]: v }; upO('bankAccounts', arr); };
              const accent = ['border-l-indigo-400','border-l-emerald-400','border-l-amber-400','border-l-rose-400'][i % 4];
              return (
                <div key={item._id || i} className={`border-l-4 ${accent} rounded-xl bg-slate-50 px-3 py-2.5 space-y-1.5`}>
                  <div className="flex items-center gap-2">
                    <input type="text" value={item.nickname || ''} onChange={e => u('nickname', e.target.value)}
                      placeholder="Account name (e.g. Salary A/c)"
                      className="flex-1 border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 transition" />
                    <button onClick={() => upO('bankAccounts', owned.bankAccounts.filter((_, j) => j !== i))}
                      className="w-5 h-5 rounded-full bg-slate-200 hover:bg-red-100 hover:text-red-500 flex items-center justify-center transition">
                      <X size={10} />
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <select value={item.bank || ''} onChange={e => u('bank', e.target.value)}
                      className="flex-1 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300">
                      <option value="">Select bank</option>
                      {BANKS.map(b => <option key={b} value={b}>{b}</option>)}
                    </select>
                    <div className="w-32 shrink-0">
                      <NI prefix="₹" value={item.balance} onChange={v => u('balance', v)} placeholder="Balance" />
                    </div>
                  </div>
                </div>
              );
            })}
            <button onClick={() => upO('bankAccounts', [...(owned.bankAccounts || []), { _id: Date.now(), nickname: '', bank: '', balance: '' }])}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 border-dashed border-indigo-200 text-indigo-500 hover:border-indigo-400 hover:bg-indigo-50/50 transition text-sm font-semibold">
              <PlusCircle size={15} /> Add bank account
            </button>
          </div>
        </div>
        <div className={cardCls}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">💵 Cash in Hand</p>
          <NI prefix="₹" value={owned.cashInHand} onChange={v => upO('cashInHand', v)} placeholder="e.g. 5,000" />
          <p className="text-xs text-slate-400">Wallet, purse, or cash kept at home</p>
        </div>
      </div>
    );

    case 'sips': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">📦 Mutual Funds & SIPs</p>
        <p className="text-xs text-slate-400">Add each platform separately</p>
        <ListBuilder items={owned.mutualFunds || []} onChange={v => upO('mutualFunds', v)}
          blank={{ platform: '', value: '' }} addLabel="Add MF platform"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <ChipPicker value={item.platform} onChange={v => u('platform', v)} options={MF_PLATFORMS} placeholder="Enter platform name" />
              <NI prefix="₹" value={item.value} onChange={v => u('value', v)} placeholder="Current market value" />
            </div>
          )} />
      </div>
    );

    case 'stocks': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">📈 Direct Stocks</p>
        <p className="text-xs text-slate-400">Add each broker / demat account</p>
        <ListBuilder items={owned.stocks || []} onChange={v => upO('stocks', v)}
          blank={{ broker: '', value: '' }} addLabel="Add broker"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <ChipPicker value={item.broker} onChange={v => u('broker', v)} options={BROKERS} placeholder="Enter broker name" />
              <NI prefix="₹" value={item.value} onChange={v => u('value', v)} placeholder="Current portfolio value" />
            </div>
          )} />
      </div>
    );

    case 'epfNps': return (
      <div className="grid grid-cols-2 gap-4">
        <div className={cardCls}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🛡️ EPF (Provident Fund)</p>
          <div className="flex items-center gap-3">
            <p className="text-sm text-slate-600 flex-1">PF deducted from salary?</p>
            <Toggle value={owned.epf?.hasEpf === null ? null : String(owned.epf?.hasEpf)}
              onChange={v => upO('epf', { ...owned.epf, hasEpf: v === 'true' })}
              opts={[{ v: 'true', l: 'Yes' }, { v: 'false', l: 'No' }]} />
          </div>
          <AnimatePresence>
            {owned.epf?.hasEpf && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden space-y-1">
                <label className={LABEL_CLS}>EPF balance today</label>
                <NI prefix="₹" value={owned.epf?.balance} onChange={v => upO('epf', { ...owned.epf, balance: v })} placeholder="e.g. 8,50,000" />
                <p className="text-[10px] text-slate-400">Check EPFO portal or salary slip</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className={cardCls}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🏛️ NPS (Pension)</p>
          <div className="flex items-center gap-3">
            <p className="text-sm text-slate-600 flex-1">Have an NPS account?</p>
            <Toggle value={owned.nps?.hasNps === null ? null : String(owned.nps?.hasNps)}
              onChange={v => upO('nps', { ...owned.nps, hasNps: v === 'true' })}
              opts={[{ v: 'true', l: 'Yes' }, { v: 'false', l: 'No' }]} />
          </div>
          <AnimatePresence>
            {owned.nps?.hasNps && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <NI prefix="₹" value={owned.nps?.balance} onChange={v => upO('nps', { ...owned.nps, balance: v })} placeholder="e.g. 1,50,000" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    );

    case 'fixedDeposits': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🔒 Fixed Deposits & RDs</p>
        <ListBuilder items={owned.fixedDeposits || []} onChange={v => upO('fixedDeposits', v)}
          blank={{ bank: '', type: 'FD', amount: '', maturity: '' }} addLabel="Add FD / RD"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <ChipPicker value={item.bank} onChange={v => u('bank', v)} options={BANKS} placeholder="Bank name" />
                <SmToggle value={item.type || 'FD'} onChange={v => u('type', v)} opts={[{ v: 'FD', l: 'FD' }, { v: 'RD', l: 'RD' }]} />
              </div>
              <NI prefix="₹" value={item.amount} onChange={v => u('amount', v)} placeholder="Amount deposited" />
            </div>
          )} />
      </div>
    );

    case 'gold': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🥇 Gold & Precious Metals</p>
        <p className="text-xs text-slate-400">Enter approximate current market value</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={LABEL_CLS}>Jewellery</label>
            <NI prefix="₹" value={owned.gold?.jewellery} onChange={v => upO('gold', { ...owned.gold, jewellery: v })} placeholder="2,00,000" />
          </div>
          <div>
            <label className={LABEL_CLS}>Gold Coins</label>
            <NI prefix="₹" value={owned.gold?.coins} onChange={v => upO('gold', { ...owned.gold, coins: v })} placeholder="50,000" />
          </div>
          <div className="col-span-2">
            <label className={LABEL_CLS}>Digital Gold / Sovereign Bonds</label>
            <NI prefix="₹" value={owned.gold?.digital} onChange={v => upO('gold', { ...owned.gold, digital: v })} placeholder="25,000" />
          </div>
        </div>
      </div>
    );

    case 'realEstate': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🏘️ Real Estate</p>
        <p className="text-xs text-slate-400">Enter approximate current market value of each property</p>
        <ListBuilder items={owned.realEstate || []} onChange={v => upO('realEstate', v)}
          blank={{ name: '', value: '' }} addLabel="Add property"
          renderRow={(item, i, u) => (
            <div className="grid grid-cols-2 gap-2">
              <TI value={item.name} onChange={v => u('name', v)} placeholder="e.g. Flat in Whitefield" />
              <NI prefix="₹" value={item.value} onChange={v => u('value', v)} placeholder="Market value" />
            </div>
          )} />
      </div>
    );

    case 'foreign': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🌍 Foreign Investments & Crypto</p>
        <ListBuilder items={owned.foreignInvestments || []} onChange={v => upO('foreignInvestments', v)}
          blank={{ type: '', amountInr: '' }} addLabel="Add investment"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <ChipPicker value={item.type} onChange={v => u('type', v)} options={['US Stocks / ETFs', 'Crypto', 'NRI Account', 'Other']} placeholder="Type of investment" />
              <NI prefix="₹" value={item.amountInr} onChange={v => u('amountInr', v)} placeholder="Value in ₹ (INR equivalent)" />
            </div>
          )} />
      </div>
    );

    case 'moneyLent': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🤝 Money Lent Out</p>
        <p className="text-xs text-slate-400">Track loans you've given — we'll forecast interest income for you</p>
        <ListBuilder items={owned.moneyLent || []} onChange={v => upO('moneyLent', v)}
          blank={{ person: '', amount: '', lentDate: '', interestRate: '' }} addLabel="Add another loan given"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Borrower</p>
                  <TI value={item.person} onChange={v => u('person', v)} placeholder="e.g. Rahul" />
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Amount lent</p>
                  <NI prefix="₹" value={item.amount} onChange={v => u('amount', v)} placeholder="50,000" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Date lent</p>
                  <input type="date" value={item.lentDate || ''} onChange={e => u('lentDate', e.target.value)}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400" />
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Interest rate</p>
                  <NI value={item.interestRate} onChange={v => u('interestRate', v)} placeholder="12" suffix="% p.a." />
                </div>
              </div>
            </div>
          )} />
      </div>
    );

    case 'otherAssets': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">➕ Other Assets</p>
        <p className="text-xs text-slate-400">Vehicle, art, collectibles, or anything else of value</p>
        <ListBuilder items={owned.otherAssets || []} onChange={v => upO('otherAssets', v)}
          blank={{ description: '', value: '' }} addLabel="Add asset"
          renderRow={(item, i, u) => (
            <div className="grid grid-cols-2 gap-2">
              <TI value={item.description} onChange={v => u('description', v)} placeholder="e.g. My Car, Laptop" />
              <NI prefix="₹" value={item.value} onChange={v => u('value', v)} placeholder="Current value" />
            </div>
          )} />
      </div>
    );

    // ── Liabilities ──

    case 'creditCards': return (
      <div className="grid grid-cols-2 gap-4">
        <div className={cardCls}>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">💳 Credit Card Balances</p>
          <p className="text-xs text-slate-400">How much do you owe <strong>right now</strong> — not the credit limit</p>
          <ListBuilder items={owed.creditCards || []} onChange={v => upOw('creditCards', v)}
            blank={{ name: '', bank: '', outstanding: '' }} addLabel="Add a card"
            renderRow={(item, i, u) => (
              <div className="grid grid-cols-2 gap-2">
                <TI value={item.name} onChange={v => u('name', v)} placeholder="e.g. HDFC Regalia" />
                <NI prefix="₹" value={item.outstanding} onChange={v => u('outstanding', v)} placeholder="Amount owed" />
              </div>
            )} />
        </div>
        <div className="bg-rose-50 border border-rose-100 rounded-2xl p-5 flex flex-col justify-center gap-3">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center shrink-0"><Zap size={16} /></div>
            <div>
              <p className="font-bold text-sm text-rose-800">Pay high-interest first</p>
              <p className="text-xs text-rose-600 mt-0.5">Paying off a card at 36% is a guaranteed 36% return on investment.</p>
            </div>
          </div>
          <p className="text-xs text-rose-400">If you have no outstanding balance, leave this empty and move on.</p>
        </div>
      </div>
    );

    case 'homeLoans': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🏠 Home Loan</p>
        <p className="text-xs text-slate-400">Outstanding principal — track for Section 24b/80C tax benefits</p>
        <ListBuilder items={owed.homeLoans || []} onChange={v => upOw('homeLoans', v)}
          blank={{ lender: '', outstanding: '', emi: '' }} addLabel="Add home loan"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <SI value={item.lender} onChange={v => u('lender', v)} options={BANKS} placeholder="Lending bank" />
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase mb-1 block">Outstanding</label>
                  <NI prefix="₹" value={item.outstanding} onChange={v => u('outstanding', v)} placeholder="45,00,000" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase mb-1 block">Monthly EMI</label>
                  <NI prefix="₹" value={item.emi} onChange={v => u('emi', v)} placeholder="42,500" />
                </div>
              </div>
            </div>
          )} />
      </div>
    );

    case 'vehicleLoans': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🚗 Vehicle Loan</p>
        <ListBuilder items={owed.vehicleLoans || []} onChange={v => upOw('vehicleLoans', v)}
          blank={{ type: '', lender: '', outstanding: '', emi: '' }} addLabel="Add vehicle loan"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <Toggle value={item.type} onChange={v => u('type', v)} opts={[{ v: 'Car', l: '🚗 Car' }, { v: 'Bike', l: '🏍️ Bike' }]} />
                <SI value={item.lender} onChange={v => u('lender', v)} options={BANKS} placeholder="Bank" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <NI prefix="₹" value={item.outstanding} onChange={v => u('outstanding', v)} placeholder="Outstanding" />
                <NI prefix="₹" value={item.emi} onChange={v => u('emi', v)} placeholder="Monthly EMI" />
              </div>
            </div>
          )} />
      </div>
    );

    case 'educationLoans': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🎓 Education Loan</p>
        <ListBuilder items={owed.educationLoans || []} onChange={v => upOw('educationLoans', v)}
          blank={{ lender: '', purpose: '', outstanding: '', emi: '' }} addLabel="Add education loan"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <TI value={item.lender} onChange={v => u('lender', v)} placeholder="Bank / institution" />
                <TI value={item.purpose} onChange={v => u('purpose', v)} placeholder="e.g. MBA, MBBS" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <NI prefix="₹" value={item.outstanding} onChange={v => u('outstanding', v)} placeholder="Outstanding" />
                <NI prefix="₹" value={item.emi} onChange={v => u('emi', v)} placeholder="Monthly EMI" />
              </div>
            </div>
          )} />
      </div>
    );

    case 'personalLoans': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">💸 Personal Loan</p>
        <ListBuilder items={owed.personalLoans || []} onChange={v => upOw('personalLoans', v)}
          blank={{ lender: '', outstanding: '', emi: '' }} addLabel="Add personal loan"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <TI value={item.lender} onChange={v => u('lender', v)} placeholder="Lender (e.g. Bajaj Finserv, SBI)" />
              <div className="grid grid-cols-2 gap-2">
                <NI prefix="₹" value={item.outstanding} onChange={v => u('outstanding', v)} placeholder="Outstanding" />
                <NI prefix="₹" value={item.emi} onChange={v => u('emi', v)} placeholder="Monthly EMI" />
              </div>
            </div>
          )} />
      </div>
    );

    case 'otherLoans': return (
      <div className={cardCls}>
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🤲 Other Debts</p>
        <p className="text-xs text-slate-400">Money borrowed from friends, relatives, or chit funds</p>
        <ListBuilder items={owed.otherLoans || []} onChange={v => upOw('otherLoans', v)}
          blank={{ description: '', amount: '' }} addLabel="Add"
          renderRow={(item, i, u) => (
            <div className="grid grid-cols-2 gap-2">
              <TI value={item.description} onChange={v => u('description', v)} placeholder="e.g. Borrowed from Dad" />
              <NI prefix="₹" value={item.amount} onChange={v => u('amount', v)} placeholder="Amount owed" />
            </div>
          )} />
      </div>
    );

    default: return <p className="text-slate-400 text-sm">Unknown category: {catId}</p>;
  }
}

// Renders all selected categories within a group on one scrollable screen
function GroupFormContent({ groupId, selAssets, selLiabilities, owned, setOwned, owed, setOwed }) {
  const group = CATEGORY_GROUPS.find(g => g.id === groupId);
  if (!group) return null;
  const activeCats = group.cats.filter(catId => selAssets.has(catId) || selLiabilities.has(catId));
  return (
    <div className="space-y-5">
      {activeCats.map(catId => (
        <CategoryFormContent key={catId} catId={catId}
          owned={owned} setOwned={setOwned}
          owed={owed} setOwed={setOwed}
        />
      ))}
    </div>
  );
}

// Phase 2 wrapper (was Phase 3) — manages grouped form navigation with persistent scale header
function Phase3_BalanceForms({ catQueue, catIndex, setCatIndex, selAssets, selLiabilities, owned, setOwned, owed, setOwed, assetTotal, liabilityTotal, onBack, onNext }) {
  const cat = catQueue[catIndex]; // now a group object {id, label, emoji, cats}

  const goNext = () => {
    if (catIndex < catQueue.length - 1) setCatIndex(i => i + 1);
    else onNext();
  };
  const goPrev = () => {
    if (catIndex > 0) setCatIndex(i => i - 1);
    else onBack();
  };

  if (!cat) return null;

  return (
    <div className="h-full flex flex-col">
      <ScaleHeader
        assets={assetTotal} liabilities={liabilityTotal}
        stepIdx={catIndex} totalSteps={catQueue.length}
        catLabel={cat.label} catEmoji={cat.emoji}
      />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <AnimatePresence mode="wait">
            <motion.div key={cat.id}
              initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}
              transition={{ duration: 0.18 }}>
              <GroupFormContent
                groupId={cat.id}
                selAssets={selAssets} selLiabilities={selLiabilities}
                owned={owned} setOwned={setOwned}
                owed={owed} setOwed={setOwed}
              />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-6 py-4 shrink-0">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
          <button onClick={goPrev}
            className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700 px-4 py-2 rounded-xl hover:bg-slate-100 transition">
            <ArrowLeft size={15} /> Back
          </button>
          <button onClick={goNext}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-sm transition text-sm">
            {catIndex < catQueue.length - 1
              ? `Next: ${catQueue[catIndex + 1]?.label || 'Continue'}`
              : 'Set my goals'
            }
            <ArrowRight size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── PHASE 4: GOALS ───────────────────────────────────────────────────────────

function Phase4_Goals({ data, setData, profile, owned, onNext, onBack }) {
  const up  = (k, v) => setData(p => ({ ...p, [k]: v }));
  const upP = (k, v) => setData(p => ({ ...p, [k]: { ...p[k], ...v } }));
  const [activeGoal, setActiveGoal] = useState(null);

  const userAge   = parseInt(profile?.age) || 30;
  const retire    = data.retire    || {};
  const emergency = data.emergency || {};
  const home      = data.home      || {};

  const epfBal   = parseInt(owned?.epf?.balance) || 0;
  const npsBal   = parseInt(owned?.nps?.balance) || 0;
  const retSaved = epfBal + npsBal;
  const retireYears  = Math.max(0, (parseInt(retire.retireAge) || 60) - userAge);
  const emergTarget  = (parseInt(emergency.monthlyExpenses) || 0) * (emergency.months || 6);

  const isOn = idx =>
    idx === 0 ? !!retire.on
    : idx === 1 ? !!emergency.on
    : idx === 2 ? (data.education?.length > 0)
    : idx === 3 ? !!home.on
    : idx === 4 ? (data.vacation?.length > 0)
    : (data.custom?.length > 0);

  const handleCard = idx => {
    const id = GOAL_CATS[idx].id;
    if (activeGoal === id) { setActiveGoal(null); return; }
    if (!isOn(idx)) {
      if (idx === 0) upP('retire', { on: true });
      else if (idx === 1) upP('emergency', { on: true });
      else if (idx === 2) {
        const n = Math.max(1, parseInt(profile.numChildren) || 1);
        up('education', Array.from({ length: n }, (_, i) => ({ _id: Date.now() + i, childName: '', childAge: '', yearsNeeded: '', amountNeeded: '', alreadySaved: '' })));
      }
      else if (idx === 3) upP('home', { on: true });
      else if (idx === 4) up('vacation', [{ _id: Date.now(), destination: '', budget: '', inYears: '', alreadySaved: '' }]);
      else                up('custom',   [{ _id: Date.now(), description: '', amountNeeded: '', inYears: '', alreadySaved: '' }]);
    }
    setActiveGoal(id);
  };

  const removeGoal = (idx, e) => {
    e.stopPropagation();
    if (idx === 0) upP('retire', { on: false });
    else if (idx === 1) upP('emergency', { on: false });
    else if (idx === 2) up('education', []);
    else if (idx === 3) upP('home', { on: false });
    else if (idx === 4) up('vacation', []);
    else                up('custom', []);
    if (activeGoal === GOAL_CATS[idx].id) setActiveGoal(null);
  };

  const planCount = [
    data.retire?.on, data.emergency?.on, data.education?.length > 0,
    data.home?.on, data.vacation?.length > 0, data.custom?.length > 0,
  ].filter(Boolean).length;

  const DoneBtn = () => (
    <button onClick={() => setActiveGoal(null)}
      className="w-full mt-3 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold py-2.5 rounded-xl transition flex items-center justify-center gap-2">
      <Check size={14} /> Done — save this goal
    </button>
  );

  const renderDetail = id => {
    if (id === 'retire') return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLS}>Retire at age</label>
            <div className="flex items-center gap-2">
              <NI value={retire.retireAge} onChange={v => upP('retire', { retireAge: v })} placeholder="60" />
              <span className="text-xs text-slate-400 shrink-0">yrs</span>
            </div>
            {retireYears > 0 && <p className="text-[10px] text-indigo-500 font-bold mt-1">In {retireYears} years</p>}
          </div>
          <div>
            <label className={LABEL_CLS}>Monthly expenses after retiring</label>
            <NI prefix="₹" value={retire.monthly} onChange={v => upP('retire', { monthly: v })} placeholder="80,000" />
            <p className="text-[10px] text-slate-400 mt-0.5">In today's money</p>
          </div>
        </div>
        <div>
          <label className={LABEL_CLS}>Already saved for retirement?</label>
          <NI prefix="₹" value={retire.alreadySaved ?? (retSaved > 0 ? String(retSaved) : '')} onChange={v => upP('retire', { alreadySaved: v })} placeholder="8,50,000" />
          {retSaved > 0 && !retire.alreadySaved && <p className="text-[10px] text-emerald-600 font-bold mt-0.5">Pre-filled from your EPF / NPS ✅</p>}
        </div>
        <DoneBtn />
      </div>
    );

    if (id === 'emergency') return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLS}>Monthly household expenses</label>
            <NI prefix="₹" value={emergency.monthlyExpenses} onChange={v => upP('emergency', { monthlyExpenses: v })} placeholder="60,000" />
          </div>
          <div>
            <label className={LABEL_CLS}>Months to keep safe</label>
            <Toggle value={String(emergency.months || 6)} onChange={v => upP('emergency', { months: parseInt(v) })}
              opts={[{ v: '3', l: '3 mo' }, { v: '6', l: '6 mo' }, { v: '12', l: '12 mo' }]} />
          </div>
        </div>
        <div>
          <label className={LABEL_CLS}>Already set aside?</label>
          <NI prefix="₹" value={emergency.alreadySaved} onChange={v => upP('emergency', { alreadySaved: v })} placeholder="1,00,000" />
        </div>
        {emergTarget > 0 && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-3 flex items-center justify-between">
            <div><p className="text-[10px] font-bold text-emerald-600 uppercase mb-0.5">Target</p><p className="text-lg font-black text-emerald-800">{inr(emergTarget)}</p></div>
            {emergency.alreadySaved && <div className="text-right"><p className="text-[10px] font-bold text-slate-400 uppercase mb-0.5">Gap</p><p className="text-base font-bold text-rose-500">{inr(Math.max(0, emergTarget - parseInt(emergency.alreadySaved)))}</p></div>}
          </div>
        )}
        <DoneBtn />
      </div>
    );

    if (id === 'education') return (
      <div className="space-y-3">
        <ListBuilder items={data.education || []} onChange={v => up('education', v)}
          blank={{ childName: '', childAge: '', yearsNeeded: '', amountNeeded: '', alreadySaved: '' }}
          addLabel="Add for another child"
          renderRow={(item, i, u) => (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <TI value={item.childName} onChange={v => u('childName', v)} placeholder="Child's name" />
                <div className="flex items-center gap-2"><NI value={item.childAge} onChange={v => u('childAge', v)} placeholder="Age" /><span className="text-[10px] text-slate-400 font-bold shrink-0">yrs</span></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className={LABEL_CLS}>Need in (yrs)</label><NI value={item.yearsNeeded} onChange={v => u('yearsNeeded', v)} placeholder="12" /></div>
                <div><label className={LABEL_CLS}>Target amount</label><NI prefix="₹" value={item.amountNeeded} onChange={v => u('amountNeeded', v)} placeholder="20,00,000" /></div>
              </div>
              <div><label className={LABEL_CLS}>Already saved?</label><NI prefix="₹" value={item.alreadySaved} onChange={v => u('alreadySaved', v)} placeholder="0" /></div>
            </div>
          )} />
        <DoneBtn />
      </div>
    );

    if (id === 'home') return (
      <div className="space-y-4">
        <div>
          <label className={LABEL_CLS}>What are you buying?</label>
          <Toggle value={home.purchaseType || 'home'} onChange={v => upP('home', { purchaseType: v })}
            opts={[{ v: 'home', l: '🏠 Home' }, { v: 'car', l: '🚗 Car' }, { v: 'wedding', l: '💍 Wedding' }, { v: 'other', l: 'Other' }]} />
        </div>
        <div>
          <label className={LABEL_CLS}>Budget</label>
          <NI prefix="₹" value={home.budget} onChange={v => upP('home', { budget: v })} placeholder="80,00,000" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className={LABEL_CLS}>Buying in (years)</label><NI value={home.inYears} onChange={v => upP('home', { inYears: v })} placeholder="3" /></div>
          <div><label className={LABEL_CLS}>Already saved?</label><NI prefix="₹" value={home.alreadySaved} onChange={v => upP('home', { alreadySaved: v })} placeholder="5,00,000" /></div>
        </div>
        <DoneBtn />
      </div>
    );

    if (id === 'vacation') return (
      <div className="space-y-3">
        <ListBuilder items={data.vacation || []} onChange={v => up('vacation', v)}
          blank={{ destination: '', budget: '', inYears: '', alreadySaved: '' }} addLabel="Add another trip"
          renderRow={(item, i, u) => (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div><label className={LABEL_CLS}>In how many years?</label><NI value={item.inYears} onChange={v => u('inYears', v)} placeholder="1" /></div>
                <div><label className={LABEL_CLS}>Destination</label><TI value={item.destination} onChange={v => u('destination', v)} placeholder="Maldives…" /></div>
                <div><label className={LABEL_CLS}>Estimated cost</label><NI prefix="₹" value={item.budget} onChange={v => u('budget', v)} placeholder="3,00,000" /></div>
              </div>
            </div>
          )} />
        <DoneBtn />
      </div>
    );

    if (id === 'custom') return (
      <div className="space-y-3">
        <ListBuilder items={data.custom || []} onChange={v => up('custom', v)}
          blank={{ description: '', amountNeeded: '', inYears: '', alreadySaved: '' }} addLabel="Add another goal"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <TI value={item.description} onChange={v => u('description', v)} placeholder="e.g. Starting my own business…" />
              <div className="grid grid-cols-2 gap-3">
                <NI prefix="₹" value={item.amountNeeded} onChange={v => u('amountNeeded', v)} placeholder="How much?" />
                <div className="flex items-center gap-2"><NI value={item.inYears} onChange={v => u('inYears', v)} placeholder="5" /><span className="text-xs text-slate-400 shrink-0">yrs</span></div>
              </div>
              <div><label className={LABEL_CLS}>Already saved?</label><NI prefix="₹" value={item.alreadySaved} onChange={v => u('alreadySaved', v)} placeholder="0" /></div>
            </div>
          )} />
        <DoneBtn />
      </div>
    );
    return null;
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 pb-10 space-y-5">
      <div>
        <p className="text-2xl font-extrabold text-slate-900 leading-tight">
          {profile.name ? `${firstName(profile.name)}, what are you building towards?` : 'What are you building towards?'}
        </p>
        <p className="text-slate-500 text-sm mt-1">Tap a goal to select it and fill in the details. Skip any that don't apply.</p>
      </div>

      {/* Goal grid */}
      <div className="grid grid-cols-3 gap-2.5">
        {GOAL_CATS.map((cat, idx) => {
          const on = isOn(idx);
          const active = activeGoal === cat.id;
          return (
            <button key={cat.id} onClick={() => handleCard(idx)}
              className={`flex items-start gap-3 p-4 rounded-xl border-2 transition-all text-left relative ${
                active ? 'border-indigo-600 bg-indigo-50/80 shadow-lg ring-2 ring-indigo-200'
                : on   ? 'border-emerald-400 bg-emerald-50/60 shadow-sm'
                       : 'border-slate-100 bg-white hover:border-indigo-200 hover:bg-slate-50 hover:shadow-sm'
              }`}>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0 ${cat.iconBg}`}>{cat.emoji}</div>
              <div className="min-w-0 flex-1">
                <p className={`text-[10px] font-black tracking-[0.12em] uppercase mb-0.5 ${active ? 'text-indigo-600' : on ? 'text-emerald-600' : 'text-slate-500'}`}>{cat.label}</p>
                <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">{cat.desc}</p>
              </div>
              {!active && on && (
                <button onClick={e => removeGoal(idx, e)} title="Remove"
                  className="absolute top-2 right-2 w-5 h-5 rounded-full bg-emerald-500 hover:bg-red-400 flex items-center justify-center transition-colors group/rm">
                  <Check size={9} className="text-white group-hover/rm:hidden" />
                  <X size={9} className="text-white hidden group-hover/rm:block" />
                </button>
              )}
            </button>
          );
        })}
      </div>

      {/* Detail panel */}
      <AnimatePresence mode="wait">
        {activeGoal && (() => {
          const idx = GOAL_CATS.findIndex(c => c.id === activeGoal);
          const cat = GOAL_CATS[idx];
          return (
            <motion.div key={activeGoal} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} transition={{ duration: 0.18 }}
              className="bg-white rounded-2xl border-2 border-indigo-200 shadow-sm overflow-hidden">
              <div className={`flex items-center justify-between px-5 py-3 ${cat.iconBg}`}>
                <div className="flex items-center gap-3">
                  <span className="text-lg">{cat.emoji}</span>
                  <p className="text-xs font-black text-slate-700 uppercase tracking-widest">{cat.label}</p>
                </div>
                <button onClick={() => setActiveGoal(null)} className="text-slate-400 hover:text-slate-600 p-1"><X size={15} /></button>
              </div>
              <div className="p-5">{renderDetail(activeGoal)}</div>
            </motion.div>
          );
        })()}
      </AnimatePresence>

      {/* Nav */}
      <div className="sticky bottom-0 bg-slate-50 pt-4 pb-6 border-t border-slate-200/60 z-10 flex gap-3">
        <button onClick={onBack}
          className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700 px-4 py-2.5 rounded-xl hover:bg-white border border-slate-200 transition">
          <ArrowLeft size={15} /> Back
        </button>
        <button onClick={onNext}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-indigo-100 transition flex items-center justify-center gap-2">
          {planCount > 0 ? `See my financial picture →` : 'Build my Ledger →'}
        </button>
      </div>
    </div>
  );
}

// ─── PAYLOAD BUILDER ──────────────────────────────────────────────────────────

function buildDashboardPayload(profile, owned, owed, savings) {
  const int = v => parseInt(v) || 0;
  const flt = v => parseFloat(v) || 0;
  return {
    name: profile.name || '',
    age: int(profile.age),
    monthly_income: 0,
    monthly_expenses: int(savings.emergency?.monthlyExpenses || 0),
    assets: {
      banks: [
        ...(owned.bankAccounts || []).map(a => ({ id: a._id, name: a.nickname || a.bank || 'Bank Account', balance: flt(a.balance) })),
        ...(owned.cashInHand ? [{ id: 'cash', name: 'Cash in Hand', balance: flt(owned.cashInHand) }] : []),
      ],
      equity: [
        ...(owned.stocks || []).map(s => ({ id: s._id, name: s.broker || 'Stocks', balance: flt(s.value) })),
        ...(owned.mutualFunds || []).map(m => ({ id: m._id, name: m.platform || 'Mutual Funds', balance: flt(m.value) })),
      ],
      providentFund: [
        ...(owned.epf?.balance  ? [{ id: 'epf', name: 'EPF', balance: flt(owned.epf.balance) }]  : []),
        ...(owned.nps?.balance  ? [{ id: 'nps', name: 'NPS', balance: flt(owned.nps.balance) }]  : []),
      ],
      fixedDeposits: (owned.fixedDeposits || []).map(fd => ({
        id: fd._id, name: (fd.bank || 'FD') + (fd.type ? ` (${fd.type})` : ''), balance: flt(fd.amount),
      })),
      bullion: [
        ...(owned.gold?.jewellery ? [{ id: 'gold-j', name: 'Gold Jewellery', balance: flt(owned.gold.jewellery) }] : []),
        ...(owned.gold?.coins     ? [{ id: 'gold-c', name: 'Gold Coins',     balance: flt(owned.gold.coins) }]     : []),
        ...(owned.gold?.digital   ? [{ id: 'gold-d', name: 'Digital Gold',   balance: flt(owned.gold.digital) }]   : []),
      ],
      realEstate: (owned.realEstate || []).map(r => ({ id: r._id, name: r.name || 'Property', balance: flt(r.value) })),
      others: (owned.otherAssets || []).map(o => ({ id: o._id, name: o.description || 'Other Asset', balance: flt(o.value) })),
      foreignEquity: (owned.foreignInvestments || []).map(f => ({ id: f._id, name: f.type || 'Foreign / Crypto', balance: flt(f.amountInr) })),
      moneyLent: (owned.moneyLent || []).map(l => ({
        id: l._id, name: l.person || 'Unknown', balance: flt(l.amount),
        lent_date: l.lentDate || null, interest_rate: flt(l.interestRate) || null,
      })),
    },
    liabilities: {
      creditCards:      (owed.creditCards    || []).map(c => ({ id: c._id, name: c.name || 'Credit Card',   balance: flt(c.outstanding) })),
      homeLoans:        (owed.homeLoans      || []).map(l => ({ id: l._id, name: l.lender || 'Home Loan',   balance: flt(l.outstanding) })),
      vehicleLoans:     (owed.vehicleLoans   || []).map(l => ({ id: l._id, name: l.lender || 'Vehicle Loan', balance: flt(l.outstanding) })),
      educationalLoans: (owed.educationLoans || []).map(l => ({ id: l._id, name: l.lender || 'Education Loan', balance: flt(l.outstanding) })),
      personalLoans: [
        ...(owed.personalLoans || []).map(l => ({ id: l._id, name: l.lender || 'Personal Loan', balance: flt(l.outstanding) })),
        ...(owed.otherLoans    || []).map(l => ({ id: l._id, name: l.description || 'Other Loan', balance: flt(l.amount) })),
      ],
    },
    goals: [
      ...(savings.retire?.on ? [{ id: 'retire', name: 'Retirement',
        target: int(savings.retire.monthly || 0) * 12 * 25,
        years: Math.max(1, int(savings.retire.retireAge || 60) - int(profile.age || 30)),
        current: int(savings.retire.alreadySaved || 0) }] : []),
      ...(savings.emergency?.on ? [{ id: 'emergency', name: 'Emergency Fund',
        target: int(savings.emergency.monthlyExpenses || 0) * int(savings.emergency.months || 6),
        years: 1, current: int(savings.emergency.alreadySaved || 0) }] : []),
      ...(savings.education || []).map((e, i) => ({
        id: `edu-${i}`, name: `${e.childName || 'Child'}'s Education`,
        target: int(e.amountNeeded || 0), years: int(e.yearsNeeded || 10), current: int(e.alreadySaved || 0) })),
      ...(savings.home?.on ? [{ id: 'home', name: savings.home.purchaseType === 'car' ? 'Car / Vehicle' : 'Home Purchase',
        target: int(savings.home.budget || 0), years: int(savings.home.inYears || 5), current: int(savings.home.alreadySaved || 0) }] : []),
      ...(savings.vacation || []).map((v, i) => ({
        id: `vac-${i}`, name: v.destination || 'Vacation',
        target: int(v.budget || 0), years: int(v.inYears || 2), current: int(v.alreadySaved || 0) })),
      ...(savings.custom || []).map((c, i) => ({
        id: `cust-${i}`, name: c.description || 'Goal',
        target: int(c.amountNeeded || 0), years: int(c.inYears || 5), current: int(c.alreadySaved || 0) })),
    ],
  };
}

// ─── PHASE 5: FINAL SUMMARY ───────────────────────────────────────────────────

function Phase5_Summary({ profile, owned, owed, savings, onComplete }) {
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState('');
  const name = firstName(profile.name);

  const assetTotal = computeAssetTotal(owned);
  const liabilityTotal = computeLiabilityTotal(owed);
  const netWorth = assetTotal - liabilityTotal;

  const planCount = [
    savings.retire?.on, savings.emergency?.on, savings.education?.length > 0,
    savings.home?.on, savings.vacation?.length > 0, savings.custom?.length > 0,
  ].filter(Boolean).length;

  // Compute rough monthly SIP for all goals
  const GV_RETURN = 0.12;
  function computeSip(target, current, years) {
    if (years <= 0) return 0;
    const r = GV_RETURN / 12, n = years * 12;
    const fvCurrent = current * Math.pow(1 + GV_RETURN, years);
    const remaining = Math.max(0, target - fvCurrent);
    if (remaining <= 0) return 0;
    return Math.ceil(remaining * r / (Math.pow(1 + r, n) - 1));
  }
  const userAge = parseInt(profile.age) || 30;
  let monthlySip = 0;
  if (savings.retire?.on) monthlySip += computeSip(int(savings.retire.monthly || 0) * 12 * 25, int(savings.retire.alreadySaved || 0), Math.max(1, int(savings.retire.retireAge || 60) - userAge));
  if (savings.emergency?.on) monthlySip += computeSip(int(savings.emergency.monthlyExpenses || 0) * int(savings.emergency.months || 6), int(savings.emergency.alreadySaved || 0), 2);
  (savings.education || []).forEach(e => monthlySip += computeSip(int(e.amountNeeded || 0), int(e.alreadySaved || 0), int(e.yearsNeeded || 10)));
  if (savings.home?.on) monthlySip += computeSip(int(savings.home.budget || 0), int(savings.home.alreadySaved || 0), int(savings.home.inYears || 5));

  function int(v) { return parseInt(v) || 0; }

  const assetRows = [
    { label: 'Bank & Cash',      emoji: '🏦', amount: (sum(owned.bankAccounts,'balance') + (parseInt(owned.cashInHand)||0)) },
    { label: 'Stocks',           emoji: '📈', amount: sum(owned.stocks,'value') },
    { label: 'Mutual Funds',     emoji: '📦', amount: sum(owned.mutualFunds,'value') },
    { label: 'EPF / NPS',        emoji: '🛡️', amount: (parseInt(owned.epf?.balance)||0) + (parseInt(owned.nps?.balance)||0) },
    { label: 'Fixed Deposits',   emoji: '🔒', amount: sum(owned.fixedDeposits,'amount') },
    { label: 'Gold',             emoji: '🥇', amount: (parseInt(owned.gold?.jewellery)||0)+(parseInt(owned.gold?.coins)||0)+(parseInt(owned.gold?.digital)||0) },
    { label: 'Real Estate',      emoji: '🏘️', amount: sum(owned.realEstate,'value') },
    { label: 'Foreign / Crypto', emoji: '🌍', amount: sum(owned.foreignInvestments,'amountInr') },
    { label: 'Money Lent',       emoji: '🤝', amount: sum(owned.moneyLent,'amount') },
    { label: 'Other Assets',     emoji: '➕', amount: sum(owned.otherAssets,'value') },
  ].filter(r => r.amount > 0);

  const liabilityRows = [
    { label: 'Credit Cards',   emoji: '💳', amount: sum(owed.creditCards,'outstanding') },
    { label: 'Home Loan',      emoji: '🏠', amount: sum(owed.homeLoans,'outstanding') },
    { label: 'Vehicle Loan',   emoji: '🚗', amount: sum(owed.vehicleLoans,'outstanding') },
    { label: 'Education Loan', emoji: '🎓', amount: sum(owed.educationLoans,'outstanding') },
    { label: 'Personal Loan',  emoji: '💸', amount: sum(owed.personalLoans,'outstanding') },
    { label: 'Other Debts',    emoji: '🤲', amount: sum(owed.otherLoans,'amount') },
  ].filter(r => r.amount > 0);

  const handleEnter = async () => {
    setSaving(true); setSaveErr('');
    try {
      const payload = buildDashboardPayload(profile, owned, owed, savings);
      await API.dashboard.save(payload);
      onComplete({ profile, owned, owed, savings });
    } catch (e) {
      const msg = e?.response?.data?.message || e?.message || 'Unknown error';
      setSaveErr(`Could not save — please try again. (${msg})`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      {/* Hero heading */}
      <div className="text-center space-y-1">
        <p className="text-3xl font-extrabold text-slate-900">
          {name ? `Your picture is ready, ${name}!` : 'Your financial picture is ready!'}
        </p>
        <p className="text-slate-500 text-sm">Here's the complete view. Save it to enter your Ledger.</p>
      </div>

      {/* Big animated scale */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm px-6 py-5">
        <BalanceScale assets={assetTotal} liabilities={liabilityTotal} />

        {/* Tilt label */}
        <p className={`text-center text-sm font-bold mt-2 ${netWorth >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
          {netWorth > 0 ? '⬆ Positive net worth — great foundation!' : netWorth < 0 ? '⬇ Negative net worth — common while paying off loans.' : 'Scale is balanced'}
        </p>
      </div>

      {/* Breakdown grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
            <span className="text-sm">💼</span>
            <p className="font-bold text-sm text-slate-700">Assets</p>
            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full ml-auto">{inr(assetTotal)}</span>
          </div>
          <div className="px-4 py-3 space-y-1.5">
            {assetRows.length === 0
              ? <p className="text-xs text-slate-400 italic">No assets entered.</p>
              : assetRows.map(r => (
                <div key={r.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5"><span className="text-sm">{r.emoji}</span><span className="text-xs text-slate-600">{r.label}</span></div>
                  <span className="text-xs font-bold text-slate-800">{inr(r.amount)}</span>
                </div>
              ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
            <span className="text-sm">📋</span>
            <p className="font-bold text-sm text-slate-700">Liabilities</p>
            <span className="text-xs font-bold text-red-500 bg-red-50 px-2 py-0.5 rounded-full ml-auto">{inr(liabilityTotal)}</span>
          </div>
          <div className="px-4 py-3 space-y-1.5">
            {liabilityRows.length === 0
              ? <p className="text-xs text-slate-400 italic">No liabilities — impressive!</p>
              : liabilityRows.map(r => (
                <div key={r.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5"><span className="text-sm">{r.emoji}</span><span className="text-xs text-slate-600">{r.label}</span></div>
                  <span className="text-xs font-bold text-slate-800">{inr(r.amount)}</span>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Goals summary */}
      {planCount > 0 && (
        <div className="bg-indigo-600 rounded-2xl p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-indigo-200 uppercase tracking-widest mb-0.5">Goals planned</p>
              <p className="text-2xl font-black">{planCount} goal{planCount !== 1 ? 's' : ''}</p>
            </div>
            {monthlySip > 0 && (
              <div className="text-right">
                <p className="text-xs font-bold text-indigo-200 uppercase tracking-widest mb-0.5">Monthly SIP needed</p>
                <p className="text-2xl font-black">{inr(monthlySip)}<span className="text-sm font-medium text-indigo-200">/mo</span></p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {saveErr && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-3">
          <X size={16} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{saveErr}</p>
        </div>
      )}

      {/* Save CTA */}
      <button onClick={handleEnter} disabled={saving}
        className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70 text-white font-black py-4 rounded-xl shadow-lg shadow-indigo-100 transition text-lg flex items-center justify-center gap-3 group">
        {saving
          ? <span className="animate-pulse">Saving your ledger…</span>
          : saveErr
            ? <>Retry <ArrowRight className="group-hover:translate-x-1 transition-transform" /></>
            : <>Enter Your Ledger <ArrowRight className="group-hover:translate-x-1 transition-transform" /></>
        }
      </button>
      <p className="text-center text-xs text-slate-400">You can refine any of this from your dashboard at any time.</p>
    </div>
  );
}

// ─── ROOT ─────────────────────────────────────────────────────────────────────

const PHASES_LABEL = ['You & Your Money', 'Add Numbers', 'Goals', 'Your Ledger'];

export default function OnboardingV3({ onComplete, userEmail = '' }) {
  const [phase, setPhase] = useState(1);
  const [catIndex, setCatIndex] = useState(0);

  const [profile, setProfile] = useState({ ...D_PROFILE });
  const [selAssets, setSelAssets] = useState(new Set());
  const [selLiabilities, setSelLiabilities] = useState(new Set());
  const [owned, setOwned] = useState({ ...D_OWNED });
  const [owed, setOwed] = useState({ ...D_OWED });
  const [savings, setSavings] = useState({ ...D_GOALS });

  // Group-based queue for Phase 2 (balance forms) — max 4 grouped screens
  const catQueue = CATEGORY_GROUPS.filter(g =>
    g.cats.some(catId => selAssets.has(catId) || selLiabilities.has(catId))
  );

  const assetTotal      = computeAssetTotal(owned);
  const liabilityTotal  = computeLiabilityTotal(owed);

  // Phase 1 → 2: seed persona defaults + goal presets, then go to balance forms
  const afterPhase1 = () => {
    // Pre-select education goal if they have kids
    if (profile.numChildren > 0) {
      setSavings(prev => ({
        ...prev,
        education: Array.from({ length: profile.numChildren }, (_, i) => ({
          _id: Date.now() + i, childName: '', childAge: '', yearsNeeded: '', amountNeeded: '', alreadySaved: '',
        })),
      }));
    }
    setOwned(prev => {
      if (prev.bankAccounts.length > 0) return prev;
      const defs = PERSONA_DEFAULTS[profile.profileType] || PERSONA_DEFAULTS.other;
      return { ...prev, ...defs };
    });
    const goalPreset = GOAL_PRESETS[profile.profileType] || [];
    setSavings(prev => ({
      ...prev,
      retire:    goalPreset.includes('retire')    ? { ...prev.retire,    on: true } : prev.retire,
      emergency: goalPreset.includes('emergency') ? { ...prev.emergency, on: true } : prev.emergency,
    }));
    setCatIndex(0);
    setPhase(2);
  };

  const sv = { initial: { opacity: 0, x: 28 }, animate: { opacity: 1, x: 0 }, exit: { opacity: 0, x: -28 } };

  // AI apply handler — dispatches fills to the right state based on current phase
  // phase 1 = profile+pick, phase 2 = balance forms, phase 3 = goals, phase 4 = summary
  const handleAiApply = useCallback((fills) => {
    if (phase === 1) {
      setProfile(p => {
        const n = { ...p };
        if (fills.name) n.name = fills.name;
        if (fills.age) n.age = fills.age;
        if (fills.profileType) {
          n.profileType = fills.profileType;
          const preset = PROFILE_PRESETS[fills.profileType] || PROFILE_PRESETS.other;
          setSelAssets(new Set(preset.assets));
          setSelLiabilities(new Set(preset.liabilities));
        }
        if (fills.city) n.city = fills.city;
        if (fills.maritalStatus) n.maritalStatus = fills.maritalStatus;
        if (fills.numChildren !== undefined) n.numChildren = fills.numChildren;
        return n;
      });
    }
    if (phase === 2) {
      const cat = catQueue[catIndex]?.id; // group id e.g. 'banking', 'investments', 'liabilities'
      setOwned(p => {
        const n = { ...p };
        if (fills.bankBalance && cat === 'banking') {
          const arr = [...(p.bankAccounts || [])];
          if (arr.length > 0) arr[arr.length - 1] = { ...arr[arr.length - 1], balance: fills.bankBalance };
          n.bankAccounts = arr;
        }
        if (fills.epfBalance && cat === 'investments') n.epf = { ...p.epf, hasEpf: true, balance: fills.epfBalance };
        if (fills.amount) {
          if (cat === 'investments' && p.mutualFunds?.length > 0) {
            const arr = [...p.mutualFunds]; arr[arr.length - 1] = { ...arr[arr.length - 1], value: fills.amount }; n.mutualFunds = arr;
          } else if (cat === 'investments' && p.stocks?.length > 0) {
            const arr = [...p.stocks]; arr[arr.length - 1] = { ...arr[arr.length - 1], value: fills.amount }; n.stocks = arr;
          } else if (cat === 'other-assets' && p.fixedDeposits?.length > 0) {
            const arr = [...p.fixedDeposits]; arr[arr.length - 1] = { ...arr[arr.length - 1], amount: fills.amount }; n.fixedDeposits = arr;
          }
        }
        return n;
      });
      setOwed(p => {
        const n = { ...p };
        if (fills.outstanding && cat === 'liabilities') {
          if (p.homeLoans?.length > 0) {
            const arr = [...p.homeLoans]; arr[arr.length - 1] = { ...arr[arr.length - 1], outstanding: fills.outstanding, ...(fills.emi ? { emi: fills.emi } : {}) }; n.homeLoans = arr;
          } else if (p.creditCards?.length > 0) {
            const arr = [...p.creditCards]; arr[arr.length - 1] = { ...arr[arr.length - 1], outstanding: fills.outstanding }; n.creditCards = arr;
          } else if (p.personalLoans?.length > 0) {
            const arr = [...p.personalLoans]; arr[arr.length - 1] = { ...arr[arr.length - 1], outstanding: fills.outstanding }; n.personalLoans = arr;
          }
        }
        return n;
      });
    }
    if (phase === 3) {
      setSavings(p => {
        const n = { ...p };
        if (fills.retireAge || fills.retireMonthly) n.retire = { ...p.retire, on: true, ...(fills.retireAge ? { retireAge: fills.retireAge } : {}), ...(fills.retireMonthly ? { monthly: fills.retireMonthly } : {}) };
        if (fills.emergencyMonths || fills.monthlyExpense) n.emergency = { ...p.emergency, on: true, ...(fills.emergencyMonths ? { months: parseInt(fills.emergencyMonths) } : {}), ...(fills.monthlyExpense ? { monthlyExpenses: fills.monthlyExpense } : {}) };
        return n;
      });
    }
  }, [phase, catQueue, catIndex, setSelAssets, setSelLiabilities]);

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shrink-0 z-40 shadow-sm">
        <div className="max-w-[1200px] mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <span className="text-base font-bold text-indigo-700 shrink-0">Ledger</span>

          {/* Phase stepper */}
          <div className="flex items-center gap-0">
            {PHASES_LABEL.map((label, idx) => {
              const p = idx + 1;
              const done   = phase > p;
              const active = phase === p;
              return (
                <React.Fragment key={p}>
                  <button
                    onClick={() => done && setPhase(p)}
                    disabled={!done}
                    className="flex flex-col items-center gap-0.5 px-1 min-w-0">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition ${done ? 'bg-emerald-500 border-emerald-500 text-white cursor-pointer' : active ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-100' : 'bg-white border-slate-300 text-slate-400'}`}>
                      {done ? <Check size={10} /> : p}
                    </div>
                    <span className={`text-[9px] font-bold whitespace-nowrap hidden md:block ${active ? 'text-indigo-700' : done ? 'text-emerald-600' : 'text-slate-400'}`}>{label}</span>
                  </button>
                  {idx < PHASES_LABEL.length - 1 && (
                    <div className={`h-0.5 w-6 md:w-10 mx-0.5 mb-3 transition ${phase > p ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          <div className="shrink-0">
            {userEmail && (
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-full px-3 py-1">
                <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-indigo-600">{userEmail[0].toUpperCase()}</span>
                </div>
                <span className="text-xs font-medium text-slate-600 max-w-[140px] truncate hidden sm:block">{userEmail}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Content — main area + AI sidebar */}
      <div className="flex-1 overflow-hidden flex">
        {/* Main content */}
        <div className="flex-1 min-w-0 overflow-hidden">
          <AnimatePresence mode="wait">
            {phase === 1 && (
              <motion.div key="p1" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.2 }} className="h-full overflow-y-auto">
                <Phase1_ProfileAndPick
                  data={profile} setData={setProfile}
                  selAssets={selAssets} setSelAssets={setSelAssets}
                  selLiabilities={selLiabilities} setSelLiabilities={setSelLiabilities}
                  onNext={afterPhase1}
                />
              </motion.div>
            )}
            {phase === 2 && catQueue.length > 0 && (
              <motion.div key="p2" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.2 }} className="h-full flex flex-col">
                <Phase3_BalanceForms
                  catQueue={catQueue} catIndex={catIndex} setCatIndex={setCatIndex}
                  selAssets={selAssets} selLiabilities={selLiabilities}
                  owned={owned} setOwned={setOwned}
                  owed={owed} setOwed={setOwed}
                  assetTotal={assetTotal} liabilityTotal={liabilityTotal}
                  onBack={() => setPhase(1)}
                  onNext={() => setPhase(3)}
                />
              </motion.div>
            )}
            {phase === 2 && catQueue.length === 0 && (
              <motion.div key="p2-empty" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.2 }} className="h-full overflow-y-auto flex items-center justify-center">
                <div className="text-center space-y-4 p-8">
                  <p className="text-slate-500">No categories selected. Go back and choose what you have.</p>
                  <button onClick={() => setPhase(1)} className="flex items-center gap-2 mx-auto text-indigo-600 font-bold hover:text-indigo-800"><ArrowLeft size={15} /> Back to selection</button>
                </div>
              </motion.div>
            )}
            {phase === 3 && (
              <motion.div key="p3" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.2 }} className="h-full overflow-y-auto">
                <Phase4_Goals
                  data={savings} setData={setSavings}
                  profile={profile} owned={owned}
                  onNext={() => setPhase(4)}
                  onBack={() => { setCatIndex(catQueue.length - 1); setPhase(2); }}
                />
              </motion.div>
            )}
            {phase === 4 && (
              <motion.div key="p4" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.2 }} className="h-full overflow-y-auto">
                <Phase5_Summary
                  profile={profile} owned={owned} owed={owed} savings={savings}
                  onComplete={onComplete}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* AI sidebar */}
        <div className="w-72 xl:w-80 shrink-0 border-l border-slate-200 bg-slate-50 p-4 flex flex-col">
          <AiPanel
            phase={phase}
            currentCatId={catQueue[catIndex]?.id}
            onApply={handleAiApply}
          />
        </div>
      </div>
    </div>
  );
}
