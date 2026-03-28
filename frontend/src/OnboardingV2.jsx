import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import {
  ArrowRight, ArrowLeft, Check,
  Send, X, PlusCircle, CheckCircle2, Sparkles, Target, Zap, Home, Pencil
} from 'lucide-react';
import { API } from './api.js';

// ─── CONSTANTS ────────────────────────────────────────────────────────────────

const PHASES = [
  { id: 1, label: 'Profile' },
  { id: 2, label: 'Current Health' },
  { id: 3, label: 'Future Health' },
  { id: 4, label: 'Your Ledger' },
];

const PROFILE_TYPES = [
  { id: 'salaried',   emoji: '💼', label: 'Riya (Salaried)',        desc: 'Managing monthly cycles, tax planning (80C), and building an emergency fund.' },
  { id: 'business',   emoji: '🏪', label: 'Suresh (Small Business)', desc: 'Optimizing cash flow, GST tracking, and separating personal from business wealth.' },
  { id: 'investor',   emoji: '📊', label: 'Ananya (Early Investor)',  desc: 'Aggressive compounding, crypto exposure, and diversifying across global markets.' },
  { id: 'retired',    emoji: '🌅', label: 'Vijay (Retired)',          desc: 'Fixed income, managing corpus drawdown, pension planning, and estate goals.' },
  { id: 'homemaker',  emoji: '🏠', label: 'Meena (Homemaker)',        desc: 'Tracking household budgets, managing shared finances, and planning for family goals.' },
  { id: 'other',      emoji: '🌟', label: 'Just Exploring',           desc: "Not sure yet? Let's get a complete picture and figure it out together." },
];

const CITIES = [
  'Bengaluru','Mumbai','Delhi','Hyderabad','Chennai','Pune','Kolkata',
  'Ahmedabad','Jaipur','Kochi','Surat','Lucknow','Indore','Bhopal',
  'Chandigarh','Visakhapatnam','Coimbatore','Vadodara','Nagpur','Other',
];

const BANKS = [
  'HDFC Bank','SBI','ICICI Bank','Axis Bank','Kotak Mahindra Bank',
  'Yes Bank','Bank of Baroda','PNB','Canara Bank','IndusInd Bank',
  'Federal Bank','IDFC First Bank','Bajaj Finance','Other',
];
const BROKERS = ['Zerodha','Groww','Angel One','Upstox','HDFC Securities','ICICI Direct','Other'];
const MF_PLATFORMS = ['Groww','Kuvera','Paytm Money','SBI MF','HDFC MF','Zerodha Coin','MF Central','Other'];

// Pre-seeded accounts shown on S2 based on persona chosen in S1
const PERSONA_DEFAULTS = {
  salaried: {
    bankAccounts: [
      { _id: 1, nickname: 'Salary A/c',   bank: 'HDFC Bank', balance: '' },
      { _id: 2, nickname: 'Savings A/c',  bank: 'SBI',       balance: '' },
    ],
    epf: { hasEpf: true, balance: '' },
  },
  business: {
    bankAccounts: [
      { _id: 1, nickname: 'Current A/c',  bank: 'HDFC Bank', balance: '' },
      { _id: 2, nickname: 'Personal Savings', bank: 'ICICI Bank', balance: '' },
    ],
  },
  investor: {
    bankAccounts: [
      { _id: 1, nickname: 'Savings A/c',  bank: 'HDFC Bank', balance: '' },
    ],
    stocks:       [{ _id: 1, broker: 'Zerodha', value: '' }],
    mutualFunds:  [{ _id: 1, platform: 'Groww',  value: '' }],
  },
  retired: {
    bankAccounts: [
      { _id: 1, nickname: 'Pension A/c',  bank: 'SBI',       balance: '' },
      { _id: 2, nickname: 'Savings A/c',  bank: 'HDFC Bank', balance: '' },
    ],
    epf: { hasEpf: false, balance: '' },
    nps: { hasNps: true,  balance: '' },
  },
  homemaker: {
    bankAccounts: [
      { _id: 1, nickname: 'Family Savings', bank: 'SBI',     balance: '' },
    ],
  },
  other: {
    bankAccounts: [
      { _id: 1, nickname: 'Savings A/c',  bank: 'HDFC Bank', balance: '' },
    ],
  },
};

const ASSET_CATS = [
  { id: 'bankAccounts',       emoji: '🏦', label: 'Bank Accounts',       sub: 'Savings & salary accounts' },
  { id: 'stocks',             emoji: '📈', label: 'Stocks',              sub: 'NSE / BSE / US' },
  { id: 'mutualFunds',        emoji: '📦', label: 'SIPs & Funds',        sub: 'Groww, Kuvera, etc.' },
  { id: 'retirementSavings',  emoji: '🛡️', label: 'EPF / NPS',          sub: 'Retirement savings' },
  { id: 'gold',               emoji: '🥇', label: 'Gold',               sub: 'Jewellery, coins, digital' },
  { id: 'fixedDeposits',      emoji: '🔒', label: 'Fixed Deposits',      sub: 'FDs & recurring deposits' },
  { id: 'foreignInvestments', emoji: '🌍', label: 'Foreign / Crypto',    sub: 'US ETFs, NRI, crypto' },
  { id: 'otherAssets',        emoji: '➕', label: 'Other',              sub: 'Land, vehicle, insurance' },
];

const LIABILITY_CATS = [
  { id: 'creditCards',    emoji: '💳', label: 'Credit Cards',  sub: 'Card balance outstanding' },
  { id: 'homeLoans',      emoji: '🏠', label: 'Home Loan',     sub: 'Outstanding + monthly EMI' },
  { id: 'vehicleLoans',   emoji: '🚗', label: 'Vehicle Loan',  sub: 'Car, bike, commercial' },
  { id: 'educationLoans', emoji: '🎓', label: 'Education Loan',sub: 'Self or child' },
  { id: 'personalLoans',  emoji: '💸', label: 'Personal Loan', sub: 'Bank or fintech app' },
  { id: 'otherLoans',     emoji: '➕', label: 'Other Loans',   sub: 'Friend, relative, chit fund' },
];

const GOAL_CATS = [
  { id: 'retire',    iconBg: 'bg-orange-100',  emoji: '🌅', label: 'RETIREMENT',     desc: "What's your number? When can you stop relying on a salary to meet your expenses — and for how long?" },
  { id: 'emergency', iconBg: 'bg-red-100',     emoji: '🛡️', label: 'EMERGENCY',      desc: 'Build a safety net — job loss, medical bills, urgent repairs — 3 to 12 months of living expenses, always liquid.' },
  { id: 'education', iconBg: 'bg-purple-100',  emoji: '🎓', label: 'EDUCATION',      desc: 'Prepare for the high costs of education — plan for a 4-year US college, IIT, Medical school, or an MBA.' },
  { id: 'home',      iconBg: 'bg-blue-100',    emoji: '🏠', label: 'PURCHASE',       desc: 'Save towards a house downpayment, your wedding / honeymoon, a celebratory trip, or a luxury car.' },
  { id: 'vacation',  iconBg: 'bg-sky-100',     emoji: '✈️', label: 'HOLIDAYS',       desc: 'Put vacations on autopilot — India or Abroad | Luxury, Comfortable, Budget | Any year, any destination.' },
  { id: 'custom',    iconBg: 'bg-amber-100',   emoji: '✨', label: 'SOMETHING ELSE', desc: 'A business launch, a big celebration, an inheritance goal — name it and we\'ll build a plan around it.' },
];

const SUGGESTED = {
  1: ["I'm Priya, 28, software engineer in Bangalore, married", "I run a small business in Pune, 2 kids", "I'm 45, retired, support my parents"],
  2: ["HDFC savings ₹2 lakhs, SBI ₹50k, EPF ₹8 lakhs", "₹3 lakhs in Zerodha stocks, ₹5 lakhs Groww MFs", "FD with SBI ₹3 lakhs, gold worth ₹2 lakhs"],
  3: ["Home loan ₹35 lakhs remaining, EMI ₹32,000", "ICICI credit card ₹15,000 outstanding", "Personal loan Bajaj ₹1.2 lakhs"],
  4: ["Retire at 58 with ₹70k/month expenses", "Emergency 6 months, spend ₹55k/month", "Save ₹20 lakhs for daughter's college in 12 years"],
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

function parseAmt(numStr, ctx = '') {
  const n = parseInt((numStr || '').replace(/,/g, '')) || 0;
  const c = ctx.toLowerCase();
  if (/cr(ore)?/.test(c)) return n * 10000000;
  if (/lakh|lac/.test(c)) return n * 100000;
  if (/\bk\b|thousand/.test(c)) return n * 1000;
  return n;
}

function firstName(name) {
  return (name || '').trim().split(' ')[0] || '';
}

// ─── AI NLP PARSER ────────────────────────────────────────────────────────────

function parseAI(text, step) {
  const t = text, lo = text.toLowerCase();
  const fills = {};

  if (step === 1) {
    const nm = t.match(/(?:i(?:'m| am)|my name is|call me|i am)\s+([A-Z][a-z]{1,20})/i) || t.match(/^([A-Z][a-z]{1,20})[,\s]/);
    if (nm) fills.name = nm[1];
    const ag = t.match(/(\d{2})\s*(?:years? old|yr)/i) || t.match(/age[:\s]+(\d{2})/i);
    if (ag) { const a = parseInt(ag[1]); if (a >= 18 && a <= 80) fills.age = String(a); }
    if (/software|engineer|developer|it |employee|salaried|analyst|manager|works? (?:at|for)/i.test(lo)) fills.profileType = 'salaried';
    else if (/business|entrepreneur|owner|shop|store|proprietor/i.test(lo)) fills.profileType = 'business';
    else if (/investor|invest|stock.*trad/i.test(lo)) fills.profileType = 'investor';
    else if (/freelanc|consultant|self.employ/i.test(lo)) fills.profileType = 'freelancer';
    else if (/homemaker|housewife|stay.at.home/i.test(lo)) fills.profileType = 'homemaker';
    else if (/retire[d]/i.test(lo)) fills.profileType = 'retired';
    else if (/explore|not sure|just looking|no idea/i.test(lo)) fills.profileType = 'other';
    const city = CITIES.find(c => c !== 'Other' && new RegExp('\\b' + c + '\\b', 'i').test(t));
    if (city) fills.city = city;
    if (/\bmarried\b/i.test(lo)) fills.maritalStatus = 'yes';
    else if (/\bsingle\b|\bnot married\b/i.test(lo)) fills.maritalStatus = 'no';
    const kd = t.match(/(\d)\s*(?:kid|child|son|daughter)/i);
    if (kd) fills.numChildren = parseInt(kd[1]);
    else if (/no kids|no children/i.test(lo)) fills.numChildren = 0;
    if (/support.*parent|parent.*depend/i.test(lo)) fills.parentsSupport = true;
  }

  if (step === 2) {
    const bms = [...t.matchAll(/(hdfc|sbi|icici|axis|kotak|yes bank|canara|pnb)\b[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?\b/gi)];
    if (bms.length) fills.bankAccounts = bms.map(m => ({ nickname: m[1].toUpperCase() + ' A/c', bank: BANKS.find(b => b.toLowerCase().startsWith(m[1].toLowerCase())) || m[1].toUpperCase(), balance: String(parseAmt(m[2], m[0])) }));
    const epf = t.match(/epf[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (epf) fills.epfBalance = String(parseAmt(epf[1], epf[0]));
    const mf = t.match(/(?:sip|mutual fund|mf|groww|kuvera)[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (mf) fills.mfTotal = String(parseAmt(mf[1], mf[0]));
    const stk = t.match(/(?:zerodha|stock|share|demat)[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (stk) fills.stockTotal = String(parseAmt(stk[1], stk[0]));
    const fd = t.match(/(?:fd|fixed deposit|rd)[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (fd) fills.fdTotal = String(parseAmt(fd[1], fd[0]));
    const gold = t.match(/gold[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (gold) fills.goldTotal = String(parseAmt(gold[1], gold[0]));
  }

  if (step === 3) {
    const hl = t.match(/home loan[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (hl) fills.homeOutstanding = String(parseAmt(hl[1], hl[0]));
    const emi = t.match(/emi[^₹\d]*?₹?\s*([\d,]+)/i);
    if (emi) fills.homeEmi = String(parseAmt(emi[1], emi[0]));
    const cc = t.match(/credit card[^₹\d]*?₹?\s*([\d,]+)\s*(k|thousand)?/i);
    if (cc) fills.ccOutstanding = String(parseAmt(cc[1], cc[0]));
    const pl = t.match(/personal loan[^₹\d]*?₹?\s*([\d,]+)\s*(lakh|lac|k|cr)?/i);
    if (pl) fills.plOutstanding = String(parseAmt(pl[1], pl[0]));
  }

  if (step === 4) {
    const ra = t.match(/retire[^at]*?at\s*(\d{2})/i) || t.match(/retire.*?(\d{2})\s*(?:years? old)?/i);
    if (ra) fills.retireAge = ra[1];
    const rm = t.match(/(?:₹|rs?\.?)\s*([\d,]+)\s*(?:per month|\/month|monthly).*?retir/i) || t.match(/retir.*?(?:₹|rs?\.?)\s*([\d,]+)\s*(?:per month|\/month)/i);
    if (rm) fills.retireMonthly = String(parseAmt(rm[1], rm[0]));
    const em = t.match(/emergency.*?(\d+)\s*months?/i) || t.match(/(\d+)\s*months?.*?emergency/i);
    if (em) fills.emergencyMonths = em[1];
    const me = t.match(/(?:spend|expenses?)[^₹\d]*?(?:₹|rs?\.?)\s*([\d,]+)\s*(?:per month|\/month|monthly|\/mo)/i);
    if (me) fills.monthlyExpense = String(parseAmt(me[1], me[0]));
  }

  return fills;
}

function aiReply(fills, step) {
  if (!Object.keys(fills).length) {
    return { text: {
      1: "Tell me about yourself in plain English! For example: \"I'm Arjun, 32, software engineer in Bangalore, married with 2 kids.\"",
      2: "What money do you have saved or invested? Example: \"HDFC savings ₹2 lakhs, EPF about ₹8 lakhs, and ₹3 lakhs in Zerodha.\"",
      3: "Tell me about any loans or credit cards. Example: \"Home loan ₹35 lakhs remaining, EMI ₹32,000, ICICI card ₹15k outstanding.\"",
      4: "What are you saving towards? Example: \"Retire at 58 with ₹70k/month, emergency fund 6 months, daughter's college in 12 years.\"",
    }[step] || "Tell me more and I'll fill the form for you!", fills: {} };
  }

  const lines = [];
  if (step === 1) {
    if (fills.name) lines.push(`✅ Name: **${fills.name}**`);
    if (fills.age) lines.push(`✅ Age: **${fills.age}**`);
    if (fills.profileType) lines.push(`✅ Profile: **${PROFILE_TYPES.find(p => p.id === fills.profileType)?.label}**`);
    if (fills.city) lines.push(`✅ City: **${fills.city}**`);
    if (fills.maritalStatus) lines.push(`✅ Married: **${fills.maritalStatus === 'yes' ? 'Yes' : 'No'}**`);
    if (fills.numChildren !== undefined) lines.push(`✅ Children: **${fills.numChildren}**`);
  }
  if (step === 2) {
    if (fills.bankAccounts?.length) fills.bankAccounts.forEach(b => lines.push(`✅ ${b.bank}: **${inr(b.balance)}**`));
    if (fills.epfBalance) lines.push(`✅ EPF: **${inr(fills.epfBalance)}**`);
    if (fills.mfTotal) lines.push(`✅ Mutual Funds: **${inr(fills.mfTotal)}**`);
    if (fills.stockTotal) lines.push(`✅ Stocks: **${inr(fills.stockTotal)}**`);
    if (fills.fdTotal) lines.push(`✅ Fixed Deposits: **${inr(fills.fdTotal)}**`);
    if (fills.goldTotal) lines.push(`✅ Gold: **${inr(fills.goldTotal)}**`);
  }
  if (step === 3) {
    if (fills.homeOutstanding) lines.push(`✅ Home loan outstanding: **${inr(fills.homeOutstanding)}**`);
    if (fills.homeEmi) lines.push(`✅ Home EMI: **${inr(fills.homeEmi)}/month**`);
    if (fills.ccOutstanding) lines.push(`✅ Credit card balance: **${inr(fills.ccOutstanding)}**`);
    if (fills.plOutstanding) lines.push(`✅ Personal loan: **${inr(fills.plOutstanding)}**`);
  }
  if (step === 4) {
    if (fills.retireAge) lines.push(`✅ Retire at: **${fills.retireAge} years old**`);
    if (fills.retireMonthly) lines.push(`✅ Monthly retirement expense: **${inr(fills.retireMonthly)}**`);
    if (fills.emergencyMonths) lines.push(`✅ Emergency fund: **${fills.emergencyMonths} months**`);
    if (fills.monthlyExpense) lines.push(`✅ Monthly expenses: **${inr(fills.monthlyExpense)}**`);
  }

  return { text: `Got it! Here's what I filled in:\n\n${lines.join('\n')}\n\nDoes this look right?`, fills };
}

// ─── PRIMITIVES ───────────────────────────────────────────────────────────────

const INPUT_CLS = 'w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent bg-white transition';
const LABEL_CLS = 'block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wide';

function TI({ value, onChange, placeholder, autoFocus }) {
  return <input type="text" value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder} autoFocus={autoFocus} className={INPUT_CLS} />;
}

// Format a raw digit string in INR grouping: 1234567 → "12,34,567"
function fmtINR(raw) {
  const digits = String(raw ?? '').replace(/\D/g, '');
  if (!digits) return '';
  return parseInt(digits, 10).toLocaleString('en-IN');
}

function NI({ value, onChange, placeholder, min, max, prefix }) {
  const display = fmtINR(value);
  const handleChange = (e) => {
    // Strip formatting, pass raw digits back so parseInt/parseFloat still work
    const raw = e.target.value.replace(/\D/g, '');
    onChange(raw);
  };
  return (
    <div className="relative">
      {prefix && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400 pointer-events-none">{prefix}</span>}
      <input type="text" inputMode="numeric" value={display} onChange={handleChange}
        placeholder={placeholder}
        className={INPUT_CLS + (prefix ? ' pl-7' : '')} />
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

// Compact toggle — smaller padding for tight card spaces
function SmToggle({ value, onChange, opts }) {
  return (
    <div className="flex flex-wrap gap-1">
      {opts.map(o => (
        <button key={o.v} onClick={() => onChange(o.v)}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition ${value === o.v ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-600'}`}>
          {o.l}
        </button>
      ))}
    </div>
  );
}

function Hint({ children, emoji = '\ud83d\udca1' }) {
  return (
    <div className="flex gap-2.5 items-start bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3 text-sm text-indigo-800">
      <span className="shrink-0 mt-px">{emoji}</span><span className="leading-relaxed">{children}</span>
    </div>
  );
}

function ChipPicker({ value, onChange, options, placeholder = 'Type here...' }) {
  // Strip trailing 'Other' from options — we always render our own
  const chips = options[options.length - 1] === 'Other' ? options.slice(0, -1) : options;
  const isCustomVal = value && !chips.includes(value);
  const [otherMode, setOtherMode] = useState(isCustomVal);

  const pick = (opt) => { setOtherMode(false); onChange(opt); };
  const openOther = () => { setOtherMode(true); onChange(''); };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {chips.map(opt => (
          <button key={opt} type="button" onClick={() => pick(opt)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
              !otherMode && value === opt
                ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-700'
            }`}>
            {opt}
          </button>
        ))}
        <button type="button" onClick={openOther}
          className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
            otherMode
              ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
              : 'bg-white text-slate-500 border-dashed border-slate-300 hover:border-indigo-300 hover:text-indigo-700'
          }`}>
          + Other
        </button>
      </div>
      {otherMode && (
        <input type="text" value={value || ''} onChange={e => onChange(e.target.value)}
          placeholder={placeholder} autoFocus className={INPUT_CLS} />
      )}
    </div>
  );
}

function Nav({ onBack, onNext, nextLabel = 'Continue', backLabel, isFirst }) {
  return (
    <div className="flex items-center justify-between pt-4 mt-2">
      {!isFirst
        ? <button onClick={onBack} className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700 px-4 py-2 rounded-xl hover:bg-slate-100 transition">
            <ArrowLeft size={15} />{backLabel || 'Back'}
          </button>
        : <div />}
      <button onClick={onNext} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold px-6 py-2.5 rounded-xl transition shadow-sm">
        {nextLabel}<ArrowRight size={15} />
      </button>
    </div>
  );
}

// ─── LIST BUILDER ─────────────────────────────────────────────────────────────

function ListBuilder({ items, onChange, blank, addLabel, renderRow }) {
  const add = () => onChange([...items, { ...blank, _id: Date.now() }]);
  const rm = i => onChange(items.filter((_, idx) => idx !== i));
  const up = (i, k, v) => onChange(items.map((item, idx) => idx === i ? { ...item, [k]: v } : item));
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

// ─── TILE (category card in grid) ─────────────────────────────────────────────

function Tile({ emoji, label, sub, active, filled, onClick }) {
  return (
    <button onClick={onClick}
      className={`w-full flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition text-center ${
        active   ? 'border-indigo-500 bg-indigo-50 shadow-md' :
        filled   ? 'border-emerald-300 bg-emerald-50' :
                   'border-slate-200 bg-white hover:border-indigo-200 hover:bg-slate-50'
      }`}>
      <span className="text-2xl leading-none">{emoji}</span>
      <div>
        <p className={`text-xs font-bold leading-tight ${active ? 'text-indigo-700' : filled ? 'text-emerald-700' : 'text-slate-700'}`}>{label}</p>
        <p className="text-[10px] text-slate-400 leading-tight mt-0.5">{sub}</p>
      </div>
      {filled && !active && <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-semibold"><CheckCircle2 size={10} /> Added</span>}
      {active && <span className="text-[10px] text-indigo-600 font-semibold">▲ editing</span>}
    </button>
  );
}

// ─── TILE DETAIL PANEL ────────────────────────────────────────────────────────

function TileDetail({ children, onClose }) {
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.15 }}
      className="bg-white border-2 border-indigo-200 rounded-2xl p-5 shadow-lg relative">
      <button onClick={onClose} className="absolute top-3 right-3 text-slate-300 hover:text-slate-500 transition p-1">
        <X size={15} />
      </button>
      {children}
    </motion.div>
  );
}

// ─── GOAL CARD ────────────────────────────────────────────────────────────────

function GoalCard({ cat, on, onToggle, children }) {
  return (
    <div className={`border rounded-2xl overflow-hidden transition-all duration-200 ${
      on ? 'border-indigo-300 shadow-sm' : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'
    }`}>
      <button onClick={onToggle} className="w-full flex items-center gap-4 px-5 py-4 bg-white text-left">
        <div className={`w-12 h-12 rounded-2xl ${cat.iconBg} flex items-center justify-center text-2xl shrink-0`}>
          {cat.emoji}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-black text-slate-500 tracking-[0.14em] uppercase mb-1">{cat.label}</p>
          <p className="text-sm text-slate-600 leading-relaxed">{cat.desc}</p>
        </div>
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ml-3 transition-all ${
          on ? 'bg-indigo-600 border-indigo-600' : 'border-slate-300 bg-white'
        }`}>
          {on && <Check size={10} className="text-white" />}
        </div>
      </button>
      <AnimatePresence>
        {on && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
            <div className="border-t border-slate-100 px-5 py-5 bg-slate-50/40 space-y-5">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── AI PANEL ─────────────────────────────────────────────────────────────────

function AiPanel({ step, onApply }) {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [showSugg, setShowSugg] = useState(true);
  const endRef = useRef(null);

  const welcome = {
    1: "👋 Hi! Tell me about yourself — I'll fill everything in for you.",
    2: "Tell me what you've saved or invested and I'll fill it all in!",
    3: "Tell me about your loans or cards — I'll handle the details.",
    4: "What are you saving for? Tell me your plans and I'll set them up!",
  };

  useEffect(() => {
    setMsgs([{ role: 'ai', text: welcome[step] || '' }]);
    setShowSugg(true);
    setInput('');
  }, [step]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, typing]);

  const send = () => {
    const txt = input.trim();
    if (!txt) return;
    setInput('');
    setShowSugg(false);
    setMsgs(p => [...p, { role: 'user', text: txt }]);
    setTyping(true);
    setTimeout(() => {
      const fills = parseAI(txt, step);
      const r = aiReply(fills, step);
      setTyping(false);
      setMsgs(p => [...p, { role: 'ai', text: r.text, fills: r.fills }]);
    }, 700 + Math.random() * 400);
  };

  const apply = fills => {
    onApply(fills);
    setMsgs(p => [...p, { role: 'ai', text: '✅ Done! Check the form on the left and edit anything if needed.' }]);
  };

  const renderLine = (line, j) => {
    if (!line) return <br key={j} />;
    const html = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    const cls = line.startsWith('✅') ? 'text-[11px] text-emerald-700 font-medium' : 'text-[11px] leading-relaxed';
    return <p key={j} className={cls} dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-violet-50 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-xl bg-indigo-600 flex items-center justify-center text-sm shrink-0">🤖</div>
          <div>
            <p className="text-xs font-bold text-slate-800">Your Financial Guide</p>
            <p className="text-[10px] text-slate-400">Just talk — I'll fill the form</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {msgs.map((m, i) => {
          const isAi = m.role === 'ai';
          const hasFills = m.fills && Object.keys(m.fills).length > 0;
          return (
            <div key={i} className={`flex ${isAi ? 'justify-start' : 'justify-end'}`}>
              <div className="max-w-[88%] space-y-1.5">
                {isAi && <div className="flex items-center gap-1 mb-0.5"><div className="w-4 h-4 rounded-full bg-indigo-100 flex items-center justify-center text-[9px]">🤖</div><span className="text-[9px] text-slate-400">Guide</span></div>}
                <div className={`rounded-2xl px-3 py-2.5 space-y-0.5 ${isAi ? 'bg-white border border-slate-200 text-slate-700 rounded-tl-sm' : 'bg-indigo-600 text-white rounded-tr-sm'}`}>
                  {isAi ? m.text.split('\n').map(renderLine) : <p className="text-[11px]">{m.text}</p>}
                </div>
                {hasFills && (
                  <div className="flex gap-1.5 flex-wrap">
                    <button onClick={() => apply(m.fills)} className="flex items-center gap-1 text-[10px] font-bold bg-emerald-600 text-white px-2.5 py-1.5 rounded-lg hover:bg-emerald-700 transition"><Check size={9} />Fill this in</button>
                    <button onClick={() => setMsgs(p => [...p, { role: 'ai', text: "No problem! Fill it in manually, or tell me again." }])} className="text-[10px] font-medium text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 transition">✏️ Tweak</button>
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
                {[0,150,300].map(d => <span key={d} className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: d + 'ms' }} />)}
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {showSugg && msgs.length <= 1 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5 shrink-0">
          {(SUGGESTED[step] || []).map((p, i) => (
            <button key={i} onClick={() => setInput(p)}
              className="text-[10px] bg-slate-50 border border-slate-200 text-slate-600 px-2.5 py-1 rounded-full hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition leading-tight text-left">{p}</button>
          ))}
        </div>
      )}

      <div className="p-3 border-t border-slate-100 shrink-0">
        <div className="flex gap-2">
          <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Type anything here..."
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

// ─── STEPPER ──────────────────────────────────────────────────────────────────

function Stepper({ step, onGoTo }) {
  const currentPhase = step <= 2 ? 1 : step <= 5 ? 2 : step <= 7 ? 3 : 4;

  return (
    <div className="flex items-center justify-center gap-0">
      {PHASES.map((p, idx) => {
        const done = currentPhase > p.id;
        const active = currentPhase === p.id;

        // Mapping phase back to first step of that phase for navigation
        const stepToJump = p.id === 1 ? 1 : p.id === 2 ? 3 : p.id === 3 ? 6 : 8;

        return (
          <React.Fragment key={p.id}>
            <button onClick={() => done && onGoTo(stepToJump)} disabled={!done}
              className="flex flex-col items-center gap-1 min-w-0 px-1">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold border-2 transition ${done ? 'bg-emerald-500 border-emerald-500 text-white cursor-pointer' : active ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-100' : 'bg-white border-slate-300 text-slate-400'}`}>
                {done ? <Check size={12} /> : p.id}
              </div>
              <span className={`text-[10px] font-bold whitespace-nowrap hidden sm:block ${active ? 'text-indigo-700' : done ? 'text-emerald-600' : 'text-slate-400'}`}>
                {p.label}
              </span>
            </button>
            {idx < PHASES.length - 1 && (
              <div className={`h-0.5 w-8 sm:w-16 mx-1 mb-4 transition ${currentPhase > p.id ? 'bg-emerald-400' : 'bg-slate-200'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── LAYOUT WRAPPER ───────────────────────────────────────────────────────────

function Layout({ step, children, onApplyAI }) {
  return (
    <div className="flex gap-6 h-[calc(100vh-60px)]">
      <div className="flex-1 min-w-0 overflow-y-auto py-4 px-2 flex flex-col">
        {children}
      </div>
      <div className="w-72 xl:w-80 shrink-0 py-6">
        <div className="h-full">
          <AiPanel step={step} onApply={onApplyAI} />
        </div>
      </div>
    </div>
  );
}

// ─── SCREEN 1: ABOUT YOU ──────────────────────────────────────────────────────

const D1 = { name:'', age:'', profileType:null, city:'Bengaluru', maritalStatus:null, numChildren:0, parentsSupport:null, otherDependents:'' };

const greetings = ['', 'Great name!', 'Love it!', 'Nice!', 'Awesome!'];

function S1({ data, setData, onNext }) {
  const [errs, setErrs] = useState({});
  const up = (k, v) => setData(p => ({ ...p, [k]: v }));
  const name = firstName(data.name);

  const applyAI = useCallback(f => {
    setData(p => {
      const n = { ...p };
      if (f.name) n.name = f.name;
      if (f.age) n.age = f.age;
      if (f.profileType) n.profileType = f.profileType;
      if (f.city) n.city = f.city;
      if (f.maritalStatus) n.maritalStatus = f.maritalStatus;
      if (f.numChildren !== undefined) n.numChildren = f.numChildren;
      if (f.parentsSupport !== undefined) n.parentsSupport = f.parentsSupport;
      return n;
    });
  }, [setData]);

  const go = () => {
    const e = {};
    if (!data.name?.trim() || data.name.length < 2) e.name = 'Please enter your name';
    if (!data.age || parseInt(data.age) < 18 || parseInt(data.age) > 80) e.age = 'Please enter your age (18–80)';
    if (!data.profileType) e.profileType = 'Please pick one that fits you';
    setErrs(e);
    if (!Object.keys(e).length) onNext();
  };

  return (
    <Layout step={1} onApplyAI={applyAI}>
      <div className="space-y-4 h-full flex flex-col">

        {/* Hero greeting */}
        <AnimatePresence mode="wait">
          {name
            ? <motion.div key={name} initial={{ opacity:0, y:-6 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }} className="space-y-0.5 shrink-0">
                <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 1 of 4 ———</p>
                <p className="text-2xl font-extrabold text-slate-900 leading-tight">Great to meet you, {name}!</p>
                <p className="text-slate-500">Let's set up the right foundation for your journey.</p>
              </motion.div>
            : <motion.div key="default" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} className="space-y-0.5 shrink-0">
                <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 1 of 4 ———</p>
                <p className="text-2xl font-extrabold text-slate-900 leading-tight">Let's personalize your ledger.</p>
                <p className="text-slate-500">Tell us a bit about yourself so we can set up the right foundation.</p>
              </motion.div>
          }
        </AnimatePresence>

        {/* Side-by-side: personal card (left) + persona picker (right) */}
        <div className="flex gap-5 flex-1 min-h-0">

          {/* LEFT — personal + family card */}
          <div className="w-[380px] shrink-0 bg-white rounded-2xl border border-slate-200 shadow-sm px-5 py-6 flex flex-col gap-0">

            {/* Personal */}
            <div className="space-y-3 flex-1 flex flex-col justify-center">
              <div>
                <label className={LABEL_CLS}>You are</label>
                <TI value={data.name} onChange={v => up('name', v)} placeholder="e.g. Advait Sharma" autoFocus />
                {errs.name && <p className="text-xs text-red-500 mt-0.5">{errs.name}</p>}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL_CLS}>You're … years old</label>
                  <NI value={data.age} onChange={v => up('age', v)} placeholder="28" min={18} max={80} />
                  {errs.age && <p className="text-xs text-red-500 mt-0.5">{errs.age}</p>}
                </div>
                <div>
                  <label className={LABEL_CLS}>You live in</label>
                  <SI value={data.city} onChange={v => up('city', v)} options={CITIES} placeholder="Bengaluru" />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-100 my-3" />

            {/* Family */}
            <div className="flex-1 flex flex-col justify-center">
              <p className="text-xs font-semibold text-slate-600 mb-3">Your family <span className="font-normal text-slate-400">(optional)</span></p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-4">
                <div>
                  <label className={LABEL_CLS}>Married?</label>
                  <SmToggle value={data.maritalStatus} onChange={v => up('maritalStatus', v)} opts={[{v:'yes',l:'Yes'},{v:'no',l:'Not yet'}]} />
                </div>
                <div>
                  <label className={LABEL_CLS}>Children?</label>
                  <SmToggle value={String(data.numChildren)} onChange={v => up('numChildren', parseInt(v))} opts={[{v:'0',l:'None'},{v:'1',l:'1'},{v:'2',l:'2'},{v:'3',l:'3+'}]} />
                </div>
                <div>
                  <label className={LABEL_CLS}>Supporting parents?</label>
                  <SmToggle value={data.parentsSupport === null ? null : String(data.parentsSupport)} onChange={v => up('parentsSupport', v === 'true')} opts={[{v:'true',l:'Yes'},{v:'false',l:'No'}]} />
                </div>
                <div>
                  <label className={LABEL_CLS}>Other dependents?</label>
                  <TI value={data.otherDependents} onChange={v => up('otherDependents', v)} placeholder="e.g. siblings" />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-100 my-3" />

            <div className="flex items-center gap-2 bg-indigo-50/60 rounded-xl px-3 py-2.5 border border-indigo-100/50">
              <CheckCircle2 size={13} className="text-indigo-500 shrink-0" />
              <p className="text-[11px] text-slate-500 italic">Bank-grade encryption. Your data stays private.</p>
            </div>
          </div>

          {/* RIGHT — persona picker fills remaining space */}
          <div className="flex-1 flex flex-col gap-3 min-w-0">
            <div className="shrink-0">
              <p className={LABEL_CLS}>Who does this sound like?</p>
              <p className="text-xs text-slate-400 mt-0.5">Pick the profile that best describes how you manage money today</p>
              {errs.profileType && <p className="text-xs text-red-500 mt-1">{errs.profileType}</p>}
            </div>

            <div className="grid grid-cols-2 gap-3 flex-1">
              {PROFILE_TYPES.map(p => (
                <button key={p.id} onClick={() => up('profileType', p.id)}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border-2 transition-all text-left group h-full ${
                    data.profileType === p.id
                      ? 'border-indigo-500 bg-indigo-50/70 shadow-md ring-2 ring-indigo-100'
                      : 'border-slate-100 bg-white hover:border-indigo-200 hover:bg-slate-50/60 hover:shadow-sm'
                  }`}>
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-lg shrink-0 transition-colors ${
                    data.profileType === p.id ? 'bg-indigo-100' : 'bg-slate-50 group-hover:bg-indigo-50'
                  }`}>
                    {p.emoji}
                  </div>
                  <div className="min-w-0">
                    <p className={`text-sm font-bold leading-tight mb-1 ${
                      data.profileType === p.id ? 'text-indigo-700' : 'text-slate-800'
                    }`}>{p.label}</p>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{p.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

        </div>{/* end side-by-side */}

        <div className="shrink-0">
          <Nav isFirst onNext={go} nextLabel={name ? `That's me, let's go →` : "That's me — keep going"} />
        </div>
      </div>
    </Layout>
  );
}

// ─── SCREEN 2: WHAT YOU OWN ───────────────────────────────────────────────────

const D2 = {
  bankAccounts:[], cashInHand:'10000', stocks:[], mutualFunds:[],
  epf:{ hasEpf:null, balance:'' }, nps:{ hasNps:null, balance:'' },
  gold:{ jewellery:'', coins:'', digital:'' },
  fixedDeposits:[], foreignInvestments:[], otherAssets:[], moneyLent:[],
};

function S2({ data, setData, onNext, onBack, name }) {
  const [subStep, setSubStep] = useState(0); // 0: intro, 1: banks+cash, 2: market, 3: retirement, 4: safety (FD/Gold), 5: others
  const up = (k, v) => setData(p => ({ ...p, [k]: v }));

  const applyAI = useCallback(f => {
    setData(p => {
      const n = { ...p };
      if (f.bankAccounts?.length) n.bankAccounts = [...(p.bankAccounts || []), ...f.bankAccounts];
      if (f.epfBalance) n.epf = { hasEpf: true, balance: f.epfBalance };
      if (f.mfTotal) n.mutualFunds = [{ _id: Date.now(), platform: 'Various', value: f.mfTotal }];
      if (f.stockTotal) n.stocks = [{ _id: Date.now(), broker: 'Zerodha', value: f.stockTotal }];
      if (f.fdTotal) n.fixedDeposits = [{ _id: Date.now(), bank: 'SBI', type: 'FD', amount: f.fdTotal, maturity: '' }];
      if (f.goldTotal) n.gold = { ...p.gold, jewellery: f.goldTotal };
      return n;
    });
  }, [setData]);

  const total = [
    sum(data.bankAccounts, 'balance'), parseInt(data.cashInHand) || 0,
    sum(data.stocks, 'value'), sum(data.mutualFunds, 'value'),
    parseInt(data.epf?.balance) || 0, parseInt(data.nps?.balance) || 0,
    (parseInt(data.gold?.jewellery)||0)+(parseInt(data.gold?.coins)||0)+(parseInt(data.gold?.digital)||0),
    sum(data.fixedDeposits, 'amount'), sum(data.foreignInvestments, 'amountInr'),
    sum(data.otherAssets, 'value'), sum(data.moneyLent, 'amount'),
  ].reduce((a,b) => a+b, 0);

  const steps = [
    { id: 'banks', label: 'Bank Accounts & Cash', icon: '🏦' },
    { id: 'market', label: 'Stocks & Funds', icon: '📈' },
    { id: 'retirement', label: 'EPF / NPS', icon: '🛡️' },
    { id: 'safety', label: 'FDs & Gold', icon: '🔒' },
    { id: 'others', label: 'Property & Others', icon: '➕' },
  ];

  return (
    <Layout step={2} onApplyAI={applyAI}>
      <div className="w-full max-w-3xl space-y-3 pb-4">
        
        {/* Story Header */}
        <div className="space-y-0.5">
          <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 2 of 4 ———</p>
          <p className="text-2xl font-extrabold text-slate-900 leading-tight">
            {subStep === 0 ? "What do you currently own?" : steps[subStep-1]?.label}
          </p>
          <p className="text-slate-500 text-sm">
            {subStep === 0 
              ? "Where is your money working? Estimates are fine!" 
              : "Tell us about your " + steps[subStep-1]?.label?.toLowerCase() + "."}
          </p>
        </div>

        <AnimatePresence mode="wait">
          {subStep === 0 && (
            <motion.div key="intro" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}>
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <div className="grid grid-cols-3 gap-4 mb-4">
                  {[['1','🏦','Bank accounts & cash'],['2','📈','Stocks, mutual funds & SIPs'],['3','🛡️','Retirement, FDs & other assets']].map(([n,e,l]) => (
                    <div key={n} className="flex items-center gap-3 bg-slate-50 rounded-xl p-3">
                      <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0 text-xs font-bold">{n}</div>
                      <div><span className="text-lg leading-none">{e}</span><p className="text-xs text-slate-600 font-medium mt-0.5">{l}</p></div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-3">
                  <button onClick={onBack} className="flex items-center gap-1 px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition">
                    <ArrowLeft size={16} /> Back
                  </button>
                  <button onClick={() => setSubStep(1)} className="flex-1 bg-indigo-600 text-white font-bold py-3 rounded-xl shadow-lg shadow-indigo-200 hover:bg-indigo-700 transition flex items-center justify-center gap-2 group">
                    Start the tour <ArrowRight className="group-hover:translate-x-1 transition-transform" size={18} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {subStep === 1 && (
            <motion.div key="banks" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              {/* main 2-col layout */}
              <div className="grid grid-cols-2 gap-4">

                {/* LEFT — bank account cards */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-4 pt-4 pb-2 border-b border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center text-sm">🏦</div>
                      <p className="text-sm font-bold text-slate-700">Bank Accounts</p>
                    </div>
                    {data.bankAccounts?.length > 0 && (
                      <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                        {data.bankAccounts.length} account{data.bankAccounts.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <div className="p-3 space-y-1.5">
                    {(data.bankAccounts || []).map((item, i) => {
                      const accentColors = [
                        'border-l-indigo-400',
                        'border-l-emerald-400',
                        'border-l-amber-400',
                        'border-l-rose-400',
                        'border-l-sky-400',
                      ];
                      const accent = accentColors[i % accentColors.length];
                      const u = (k, v) => {
                        const updated = [...(data.bankAccounts || [])];
                        updated[i] = { ...updated[i], [k]: v };
                        up('bankAccounts', updated);
                      };
                      const remove = () => up('bankAccounts', (data.bankAccounts || []).filter((_, j) => j !== i));
                      return (
                        <div key={item._id || i} className={`border-l-4 ${accent} rounded-xl bg-slate-50/60 px-3 py-2 space-y-1.5`}>
                          {/* Row 1: Account name — full width, prominent */}
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={item.nickname || ''}
                              onChange={e => u('nickname', e.target.value)}
                              placeholder="Account name (e.g. Salary A/c)"
                              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm font-medium text-slate-800 placeholder-slate-400 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition"
                            />
                            <button onClick={remove} className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-200 hover:bg-red-100 hover:text-red-500 flex items-center justify-center transition-colors">
                              <X size={10} />
                            </button>
                          </div>
                          {/* Row 2: Bank dropdown + Balance side by side */}
                          <div className="flex items-center gap-2">
                            <select
                              value={item.bank}
                              onChange={e => u('bank', e.target.value)}
                              className="flex-1 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                            >
                              <option value="">Select bank</option>
                              {BANKS.map(b => <option key={b} value={b}>{b}</option>)}
                            </select>
                            <div className="flex-shrink-0 w-28">
                              <NI prefix="₹" value={item.balance} onChange={v=>u('balance',v)} placeholder="Balance" />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    <button
                      onClick={() => up('bankAccounts', [...(data.bankAccounts||[]), {_id: Date.now(), nickname:'', bank:'', balance:''}])}
                      className="w-full flex items-center justify-center gap-2 py-2 rounded-xl border-2 border-dashed border-indigo-200 text-indigo-500 hover:border-indigo-400 hover:bg-indigo-50/50 transition text-sm font-semibold">
                      <PlusCircle size={15} /> Add bank account
                    </button>
                  </div>
                </div>

                {/* RIGHT — cash + summary */}
                <div className="flex flex-col gap-3">
                  {/* Cash in hand */}
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                    <div className="px-4 pt-4 pb-2 border-b border-slate-100 flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center text-sm">💵</div>
                      <div>
                        <p className="text-sm font-bold text-slate-700">Cash in hand</p>
                        <p className="text-xs text-slate-400">Wallet, purse, or cash at home</p>
                      </div>
                    </div>
                    <div className="p-3">
                      <NI prefix="₹" value={data.cashInHand} onChange={v => up('cashInHand', v)} placeholder="e.g. 10,000" />
                    </div>
                  </div>

                  {/* Live liquid total */}
                  {(() => {
                    const bankTotal = sum(data.bankAccounts || [], 'balance');
                    const cashTotal = parseInt(data.cashInHand) || 0;
                    const liquidTotal = bankTotal + cashTotal;
                    return liquidTotal > 0 ? (
                      <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-2xl p-4 text-white shadow-lg shadow-indigo-200">
                        <p className="text-xs font-bold text-indigo-200 uppercase tracking-widest mb-1">Liquid Assets</p>
                        <p className="text-2xl font-black">{inr(liquidTotal)}</p>
                        {data.bankAccounts?.length > 0 && cashTotal > 0 && (
                          <div className="mt-2 pt-2 border-t border-indigo-500 flex justify-between text-xs text-indigo-200">
                            <span>Banks: {inr(bankTotal)}</span>
                            <span>Cash: {inr(cashTotal)}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-4">
                        <p className="text-xs text-indigo-700 leading-relaxed"><strong>Why we ask:</strong> Your liquid balance helps us calculate the exact emergency fund target you need to stay protected from surprises.</p>
                      </div>
                    );
                  })()}
                </div>
              </div>

              <div className="flex justify-between">
                <button onClick={() => setSubStep(0)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Back</button>
                <button onClick={() => setSubStep(2)} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition">Next: Investments →</button>
              </div>
            </motion.div>
          )}

          {subStep === 2 && (
            <motion.div key="market" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest">📦 Mutual Funds & SIPs</label>
                  <ListBuilder items={data.mutualFunds||[]} onChange={v=>up('mutualFunds',v)} blank={{platform:'',value:''}} addLabel="Add MF platform"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2">
                        <ChipPicker value={item.platform} onChange={v=>u('platform',v)} options={MF_PLATFORMS} placeholder="Enter platform name" />
                        <NI prefix="₹" value={item.value} onChange={v=>u('value',v)} placeholder="Current Value" />
                      </div>
                    )} />
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest">📈 Direct Stocks / Shares</label>
                  <ListBuilder items={data.stocks||[]} onChange={v=>up('stocks',v)} blank={{broker:'',value:''}} addLabel="Add broker"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2">
                        <ChipPicker value={item.broker} onChange={v=>u('broker',v)} options={BROKERS} placeholder="Enter broker name" />
                        <NI prefix="₹" value={item.value} onChange={v=>u('value',v)} placeholder="Current Value" />
                      </div>
                    )} />
                </div>
              </div>
              <div className="flex justify-between">
                <button onClick={() => setSubStep(1)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Back</button>
                <button onClick={() => setSubStep(3)} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition">Next: Retirement →</button>
              </div>
            </motion.div>
          )}

          {subStep === 3 && (
            <motion.div key="retirement" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🛡️ Provident Fund (EPF)</p>
                  <div className="flex items-center gap-3">
                    <p className="text-sm text-slate-600 flex-1">PF deducted from salary?</p>
                    <Toggle value={data.epf?.hasEpf===null?null:String(data.epf?.hasEpf)} onChange={v=>up('epf',{...data.epf,hasEpf:v==='true'})} opts={[{v:'true',l:'Yes'},{v:'false',l:'No'}]} />
                  </div>
                  {data.epf?.hasEpf && (
                    <motion.div initial={{ height:0, opacity:0 }} animate={{ height:'auto', opacity:1 }} className="space-y-2 overflow-hidden">
                      <label className={LABEL_CLS}>EPF balance today</label>
                      <NI prefix="₹" value={data.epf?.balance} onChange={v=>up('epf',{...data.epf,balance:v})} placeholder="e.g. 8,50,000" />
                      <p className="text-[10px] text-slate-400">Check EPFO portal or salary statement.</p>
                    </motion.div>
                  )}
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">🏛️ National Pension (NPS)</p>
                  <div className="flex items-center gap-3">
                    <p className="text-sm text-slate-600 flex-1">Have an NPS account?</p>
                    <Toggle value={data.nps?.hasNps===null?null:String(data.nps?.hasNps)} onChange={v=>up('nps',{...data.nps,hasNps:v==='true'})} opts={[{v:'true',l:'Yes'},{v:'false',l:'No'}]} />
                  </div>
                  {data.nps?.hasNps && (
                    <motion.div initial={{ height:0, opacity:0 }} animate={{ height:'auto', opacity:1 }} className="overflow-hidden">
                      <NI prefix="₹" value={data.nps?.balance} onChange={v=>up('nps',{...data.nps,balance:v})} placeholder="e.g. 1,50,000" />
                    </motion.div>
                  )}
                </div>
              </div>
              <div className="flex justify-between">
                <button onClick={() => setSubStep(2)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Previous</button>
                <button onClick={() => setSubStep(4)} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition">Next: Safety Net →</button>
              </div>
            </motion.div>
          )}

          {subStep === 4 && (
            <motion.div key="safety" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🔒</span>
                    <div>
                      <p className="font-bold text-slate-800 text-sm">Fixed Deposits & RDs</p>
                      <p className="text-xs text-slate-500">Secure savings with guaranteed returns.</p>
                    </div>
                  </div>
                  <ListBuilder items={data.fixedDeposits||[]} onChange={v=>up('fixedDeposits',v)} blank={{bank:'',type:'FD',amount:'',maturity:''}} addLabel="Add FD / RD"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2">
                        <ChipPicker value={item.bank} onChange={v=>u('bank',v)} options={BANKS} placeholder="Enter bank name" />
                        <NI prefix="₹" value={item.amount} onChange={v=>u('amount',v)} placeholder="Amount" />
                      </div>
                    )} />
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">💍</span>
                    <div>
                      <p className="font-bold text-slate-800 text-sm">Gold & Precious Metals</p>
                      <p className="text-xs text-slate-500">Jewellery, coins, or digital gold.</p>
                    </div>
                  </div>
                  <div>
                    <label className={LABEL_CLS}>Jewellery (approx value)</label>
                    <NI prefix="₹" value={data.gold?.jewellery} onChange={v=>up('gold',{...data.gold,jewellery:v})} placeholder="2,00,000" />
                  </div>
                  <div>
                    <label className={LABEL_CLS}>Coins / Digital Gold</label>
                    <NI prefix="₹" value={data.gold?.digital} onChange={v=>up('gold',{...data.gold,digital:v})} placeholder="50,000" />
                  </div>
                </div>
              </div>
              <div className="flex justify-between">
                <button onClick={() => setSubStep(3)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Previous</button>
                <button onClick={() => setSubStep(5)} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition">Almost done! →</button>
              </div>
            </motion.div>
          )}

          {subStep === 5 && (
            <motion.div key="others" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest">➕ Property & Other Assets</label>
                  <ListBuilder items={data.otherAssets||[]} onChange={v=>up('otherAssets',v)} blank={{description:'',value:''}} addLabel="Add an asset"
                    renderRow={(item,i,u)=>(
                      <div className="grid grid-cols-2 gap-2">
                        <TI value={item.description} onChange={v=>u('description',v)} placeholder="e.g. My Car, Apartment" />
                        <NI prefix="₹" value={item.value} onChange={v=>u('value',v)} placeholder="Current Value" />
                      </div>
                    )} />
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest">🌍 Foreign / Crypto</label>
                  <ListBuilder items={data.foreignInvestments||[]} onChange={v=>up('foreignInvestments',v)} blank={{currency:'',type:'',amountInr:''}} addLabel="Add foreign asset"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2">
                        <ChipPicker value={item.type} onChange={v=>u('type',v)} options={['US Stocks / ETFs','Crypto']} placeholder="Type of investment" />
                        <NI prefix="₹" value={item.amountInr} onChange={v=>u('amountInr',v)} placeholder="Value in ₹" />
                      </div>
                    )} />
                </div>
              </div>

              {/* Money Lent — full width card */}
              <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🤝</span>
                  <div>
                    <p className="font-bold text-slate-800 text-sm">Money Lent to Friends / Family</p>
                    <p className="text-xs text-slate-500">Track amounts you've lent out — principal, date & interest rate.</p>
                  </div>
                </div>
                <ListBuilder
                  items={data.moneyLent||[]}
                  onChange={v=>up('moneyLent',v)}
                  blank={{person:'', amount:'', lentDate:'', interestRate:''}}
                  addLabel="Add another loan"
                  renderRow={(item,i,u)=>(
                    <div className="space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Borrower name</p>
                          <TI value={item.person} onChange={v=>u('person',v)} placeholder="e.g. Rahul" />
                        </div>
                        <div>
                          <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Amount lent</p>
                          <NI prefix="₹" value={item.amount} onChange={v=>u('amount',v)} placeholder="50,000" />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Date lent</p>
                          <input
                            type="date"
                            value={item.lentDate||''}
                            onChange={e=>u('lentDate', e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                          />
                        </div>
                        <div>
                          <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Interest rate (% p.a.)</p>
                          <div className="flex items-center gap-1.5">
                            <NI value={item.interestRate} onChange={v=>u('interestRate',v)} placeholder="12" />
                            <span className="text-xs text-slate-400 font-medium shrink-0">% p.a.</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                />
              </div>

              <div className="flex justify-between">
                <button onClick={() => setSubStep(4)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Previous</button>
                <button onClick={onNext} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition">See what you own total →</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Running total overlay - visible from investments step onwards */}
        <AnimatePresence>
          {total > 0 && subStep >= 2 && (
            <motion.div initial={{ y:20, opacity:0 }} animate={{ y:0, opacity:1 }} className="sticky bottom-4 left-0 right-0 z-10">
              <div className="flex items-center justify-between bg-white border border-slate-200 text-slate-900 rounded-2xl px-6 py-4 shadow-xl">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Total Wealth So Far</span>
                  <div className="text-2xl font-black text-indigo-600">{inr(total)}</div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-slate-400">Step {subStep} of 5</p>
                  <div className="flex gap-1 mt-1 justify-end">
                    {[1,2,3,4,5].map(i => (
                      <div key={i} className={`w-3 h-1 rounded-full transition-colors ${i <= subStep ? 'bg-indigo-500' : 'bg-slate-200'}`} />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </Layout>
  );
}

// ─── SCREEN 3: WHAT YOU OWE ───────────────────────────────────────────────────

const D3 = { creditCards:[], homeLoans:[], vehicleLoans:[], educationLoans:[], personalLoans:[], otherLoans:[] };

function S3({ data, setData, onNext, onBack, name }) {
  const [subStep, setSubStep] = useState(0); // 0: intro, 1: cc, 2: major (home/vehicle), 3: others
  const up = (k, v) => setData(p => ({ ...p, [k]: v }));

  const applyAI = useCallback(f => {
    setData(p => {
      const n = { ...p };
      if (f.homeOutstanding) n.homeLoans = [{ _id: Date.now(), lender:'HDFC Bank', outstanding:f.homeOutstanding, emi:f.homeEmi||'', rate:'' }];
      if (f.ccOutstanding) n.creditCards = [{ _id: Date.now(), name:'Credit Card', bank:'', outstanding:f.ccOutstanding }];
      if (f.plOutstanding) n.personalLoans = [{ _id: Date.now(), lender:'', outstanding:f.plOutstanding, emi:'' }];
      return n;
    });
  }, [setData]);

  const totalOwed = [
    sum(data.creditCards,'outstanding'), sum(data.homeLoans,'outstanding'),
    sum(data.vehicleLoans,'outstanding'), sum(data.educationLoans,'outstanding'),
    sum(data.personalLoans,'outstanding'), sum(data.otherLoans,'amount'),
  ].reduce((a,b)=>a+b,0);

  const steps = [
    { id: 'cc', label: 'Credit Cards', icon: '💳' },
    { id: 'major', label: 'Home & Auto Loans', icon: '🏠' },
    { id: 'others', label: 'Other Obligations', icon: '📝' },
  ];

  return (
    <Layout step={3} onApplyAI={applyAI}>
      <div className="w-full max-w-3xl space-y-3 pb-4">
        
        {/* Story Header */}
        <div className="space-y-0.5">
          <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 3 of 4 ———</p>
          <p className="text-2xl font-extrabold text-slate-900 leading-tight">
            {subStep === 0 ? "Mapping your obligations" : steps[subStep-1]?.label}
          </p>
          <p className="text-slate-500 text-sm">
            {subStep === 0 
              ? "Knowing your commitments helps us build the clearest path forward." 
              : "Let's list your " + steps[subStep-1]?.label?.toLowerCase() + "."}
          </p>
        </div>

        <AnimatePresence mode="wait">
          {subStep === 0 && (
            <motion.div key="intro" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}>
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <div className="grid grid-cols-3 gap-4 mb-4">
                  {[['💳','Credit Cards','High-interest balances to prioritize'],['🏠','Major Loans','Home & vehicle EMIs for tax optimization'],['📝','Other Loans','Personal, education & informal borrowings']].map(([e,l,d]) => (
                    <div key={l} className="bg-slate-50 rounded-xl p-3">
                      <span className="text-2xl">{e}</span>
                      <p className="font-bold text-sm text-slate-800 mt-1">{l}</p>
                      <p className="text-xs text-slate-500">{d}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-3">
                  <button onClick={onBack} className="flex items-center gap-1 px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition">
                    <ArrowLeft size={16} /> Back
                  </button>
                  <button onClick={() => setSubStep(1)} className="flex-1 bg-indigo-600 text-white font-bold py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition flex items-center justify-center gap-2 group">
                    Continue the audit <ArrowRight className="group-hover:translate-x-1 transition-transform" size={18} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {subStep === 1 && (
            <motion.div key="cc" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">💳 Credit Card Balances</p>
                  <ListBuilder items={data.creditCards||[]} onChange={v=>up('creditCards',v)} blank={{name:'',bank:'',outstanding:''}} addLabel="Add a card"
                    renderRow={(item,i,u)=>(
                      <div className="grid grid-cols-2 gap-2">
                        <TI value={item.name} onChange={v=>u('name',v)} placeholder="e.g. HDFC Regalia" />
                        <NI prefix="₹" value={item.outstanding} onChange={v=>u('outstanding',v)} placeholder="Principal Owed" />
                      </div>
                    )} />
                </div>
                <div className="bg-rose-50 border border-rose-100 rounded-2xl p-4 flex flex-col justify-center">
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center shrink-0"><Zap size={16} /></div>
                    <div>
                      <p className="font-bold text-sm text-rose-800">Pay high-interest first</p>
                      <p className="text-xs text-rose-600 mt-0.5">Paying off a card at 36% interest = guaranteed 36% investment return.</p>
                    </div>
                  </div>
                  <p className="text-xs text-rose-500">If you have no credit card debt, just skip this and move on.</p>
                </div>
              </div>
              <div className="flex justify-between">
                <button onClick={() => setSubStep(0)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Back</button>
                <button onClick={() => setSubStep(2)} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition text-sm">Next: Major Loans →</button>
              </div>
            </motion.div>
          )}

          {subStep === 2 && (
            <motion.div key="major" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🏠</span>
                    <div>
                      <p className="font-bold text-slate-800 text-sm">Home Loan</p>
                      <p className="text-[11px] text-slate-500">Track for tax benefits (Sec 24b/80C).</p>
                    </div>
                  </div>
                  <ListBuilder items={data.homeLoans||[]} onChange={v=>up('homeLoans',v)} blank={{lender:'',outstanding:'',emi:'',rate:''}} addLabel="Add home loan"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2 p-3 bg-slate-50/50 rounded-xl border border-slate-100">
                        <SI value={item.lender} onChange={v=>u('lender',v)} options={BANKS} placeholder="Lending Bank" />
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Outstanding</label>
                            <NI prefix="₹" value={item.outstanding} onChange={v=>u('outstanding',v)} placeholder="45,00,000" />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Monthly EMI</label>
                            <NI prefix="₹" value={item.emi} onChange={v=>u('emi',v)} placeholder="42,500" />
                          </div>
                        </div>
                      </div>
                    )} />
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🚗</span>
                    <div>
                      <p className="font-bold text-slate-800 text-sm">Vehicle Loan</p>
                      <p className="text-[11px] text-slate-500">Cars, bikes, or commercial vehicles.</p>
                    </div>
                  </div>
                  <ListBuilder items={data.vehicleLoans||[]} onChange={v=>up('vehicleLoans',v)} blank={{type:'',lender:'',outstanding:'',emi:''}} addLabel="Add vehicle loan"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2 p-3 bg-slate-50/50 rounded-xl border border-slate-100">
                        <div className="grid grid-cols-2 gap-2">
                          <Toggle value={item.type} onChange={v=>u('type',v)} opts={[{v:'Car',l:'Car'},{v:'Bike',l:'Bike'}]} />
                          <SI value={item.lender} onChange={v=>u('lender',v)} options={BANKS} placeholder="Which bank?" />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <NI prefix="₹" value={item.outstanding} onChange={v=>u('outstanding',v)} placeholder="Outstanding" />
                          <NI prefix="₹" value={item.emi} onChange={v=>u('emi',v)} placeholder="EMI" />
                        </div>
                      </div>
                    )} />
                </div>
              </div>

              <div className="flex justify-between pt-2">
                <button onClick={() => setSubStep(1)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Back</button>
                <button onClick={() => setSubStep(3)} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition text-sm">One last step →</button>
              </div>
            </motion.div>
          )}

          {subStep === 3 && (
            <motion.div key="others" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest">📝 Personal / Education Loans</label>
                  <ListBuilder items={data.personalLoans||[]} onChange={v=>up('personalLoans',v)} blank={{lender:'',outstanding:'',emi:''}} addLabel="Add loan"
                    renderRow={(item,i,u)=>(
                      <div className="space-y-2 p-3 bg-slate-50/50 rounded-xl">
                        <TI value={item.lender} onChange={v=>u('lender',v)} placeholder="Purpose or lender (e.g. MBA Loan)" />
                        <div className="grid grid-cols-2 gap-2">
                          <NI prefix="₹" value={item.outstanding} onChange={v=>u('outstanding',v)} placeholder="Amount Owed" />
                          <NI prefix="₹" value={item.emi} onChange={v=>u('emi',v)} placeholder="Monthly EMI" />
                        </div>
                      </div>
                    )} />
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest">🤝 Other Loans (hand-loans etc.)</label>
                  <ListBuilder items={data.otherLoans||[]} onChange={v=>up('otherLoans',v)} blank={{description:'',amount:''}} addLabel="Add other commitment"
                    renderRow={(item,i,u)=>(
                      <div className="grid grid-cols-2 gap-2">
                        <TI value={item.description} onChange={v=>u('description',v)} placeholder="e.g. Borrowed from Friend" />
                        <NI prefix="₹" value={item.amount} onChange={v=>u('amount',v)} placeholder="Balance" />
                      </div>
                    )} />
                </div>
              </div>
              <div className="flex justify-between">
                <button onClick={() => setSubStep(2)} className="text-slate-400 hover:text-slate-600 font-medium text-sm">← Previous</button>
                <button onClick={onNext} className="bg-indigo-600 text-white font-extrabold px-10 py-4 rounded-2xl shadow-xl shadow-indigo-100 hover:bg-indigo-700 transition transform hover:-translate-y-0.5 text-sm md:text-base">
                  Finish Health Audit →
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Running total overlay */}
        <AnimatePresence>
          {totalOwed > 0 && (
            <motion.div initial={{ y:20, opacity:0 }} animate={{ y:0, opacity:1 }} className="sticky bottom-4 left-0 right-0 z-10">
              <div className="flex items-center justify-between bg-rose-600 text-white rounded-2xl px-6 py-4 shadow-xl">
                <div>
                  <span className="text-[10px] font-bold text-rose-200 uppercase tracking-widest">Total Liabilities Listed</span>
                  <div className="text-2xl font-black">{inr(totalOwed)}</div>
                </div>
                <div className="text-right">
                   <p className="text-[10px] text-rose-200">The clear path is forming...</p>
                   <div className="flex gap-1 mt-1 justify-end">
                    {[1,2,3].map(i => (
                      <div key={i} className={`w-3 h-1 rounded-full transition-colors ${i <= subStep ? 'bg-white' : 'bg-rose-400/50'}`} />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Layout>
  );
}

// ─── SCREEN 4: WHAT I'M SAVING FOR ───────────────────────────────────────────

const D4 = {
  retire:{ on:false }, emergency:{ on:false, months:6 },
  education:[], home:{ on:false }, car:{ on:false }, vacation:[], custom:[],
};

function S4({ data, setData, onNext, onBack, profile, owned, name }) {
  const up  = (k, v) => setData(p => ({ ...p, [k]: v }));
  const upP = (k, v) => setData(p => ({ ...p, [k]: { ...p[k], ...v } }));
  const [activeGoal, setActiveGoal] = useState(null); // which detail panel is open

  const applyAI = useCallback(f => {
    setData(p => {
      const n = { ...p };
      if (f.retireAge)       n.retire    = { ...p.retire,    on: true, retireAge: f.retireAge };
      if (f.retireMonthly)   n.retire    = { ...n.retire,    on: true, monthly: f.retireMonthly };
      if (f.emergencyMonths) n.emergency = { ...p.emergency, on: true, months: parseInt(f.emergencyMonths) };
      if (f.monthlyExpense)  n.emergency = { ...n.emergency, on: true, monthlyExpenses: f.monthlyExpense };
      return n;
    });
  }, [setData]);

  const userAge  = parseInt(profile?.age) || 30;
  const retire   = data.retire    || {};
  const emergency = data.emergency || {};
  const home     = data.home      || {};

  const epfBal   = parseInt(owned?.epf?.balance) || 0;
  const npsBal   = parseInt(owned?.nps?.balance) || 0;
  const retSaved = epfBal + npsBal;

  const retireYears  = Math.max(0, (parseInt(retire.retireAge) || 60) - userAge);
  const retireCorpus = retire.monthly ? retire.monthly * 12 * 25 * Math.pow(1.06, retireYears) : 0;
  const emergTarget  = (parseInt(emergency.monthlyExpenses) || 0) * (emergency.months || 6);

  const planCount = [
    data.retire?.on, data.emergency?.on, data.education?.length > 0,
    data.home?.on, data.vacation?.length > 0, data.custom?.length > 0,
  ].filter(Boolean).length;

  // isOn: has the goal been added/saved
  const isOn = (idx) => idx === 0 ? !!retire.on
    : idx === 1 ? !!emergency.on
    : idx === 2 ? data.education?.length > 0
    : idx === 3 ? !!home.on
    : idx === 4 ? data.vacation?.length > 0
    : data.custom?.length > 0;

  // handleCardClick: toggle add + open detail, or just open if already added
  const handleCardClick = (idx) => {
    const id = GOAL_CATS[idx].id;
    if (activeGoal === id) { setActiveGoal(null); return; } // collapse if already open
    // Add the goal if not already added
    if (!isOn(idx)) {
      if (idx === 0) upP('retire',    { on: true });
      else if (idx === 1) upP('emergency', { on: true });
      else if (idx === 2) {
        const numKids = Math.max(1, parseInt(profile.numChildren) || 1);
        up('education', Array.from({ length: numKids }, (_, i) => ({ _id: Date.now() + i, childName:'', childAge:'', yearsNeeded:'', amountNeeded:'', alreadySaved:'' })));
      }
      else if (idx === 3) upP('home',      { on: true });
      else if (idx === 4) up('vacation',   [{ _id: Date.now(), destination:'', budget:'', inYears:'', alreadySaved:'' }]);
      else                up('custom',     [{ _id: Date.now(), description:'', amountNeeded:'', inYears:'', alreadySaved:'' }]);
    }
    setActiveGoal(id);
  };

  // removeGoal: deselect a goal that's been added (via × on the card)
  const removeGoal = (idx, e) => {
    e.stopPropagation();
    if (idx === 0) upP('retire',    { on: false });
    else if (idx === 1) upP('emergency', { on: false });
    else if (idx === 2) up('education', []);
    else if (idx === 3) upP('home',      { on: false });
    else if (idx === 4) up('vacation',   []);
    else                up('custom',     []);
    if (activeGoal === GOAL_CATS[idx].id) setActiveGoal(null);
  };

  // Detail panel for each goal
  const renderDetail = (id) => {
    const done = () => setActiveGoal(null);
    const DoneBtn = () => (
      <button onClick={done}
        className="w-full mt-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold py-2.5 rounded-xl transition flex items-center justify-center gap-2">
        <Check size={14} /> Done — save this goal
      </button>
    );

    if (id === 'retire') return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Retire at age</label>
            <div className="flex items-center gap-2">
              <NI value={retire.retireAge} onChange={v => upP('retire', { retireAge: v })} placeholder="60" min={30} max={75} />
              <span className="text-xs text-slate-400 font-medium shrink-0">yrs</span>
            </div>
            {retireYears > 0 && <p className="text-[10px] text-indigo-500 font-bold mt-1.5 uppercase tracking-wide">In {retireYears} years</p>}
          </div>
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Monthly expenses after retiring</label>
            <NI prefix="₹" value={retire.monthly} onChange={v => upP('retire', { monthly: v })} placeholder="80,000" />
            <p className="text-[10px] text-slate-400 mt-1">In today's money</p>
          </div>
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Already saved for retirement?</label>
          <NI prefix="₹" value={retire.alreadySaved ?? (retSaved > 0 ? String(retSaved) : '')} onChange={v => upP('retire', { alreadySaved: v })} placeholder="8,50,000" />
          {retSaved > 0 && !retire.alreadySaved && <p className="text-[10px] text-emerald-600 font-bold mt-1 uppercase">Pre-filled from your EPF / NPS ✅</p>}
        </div>
        {retireCorpus > 0 && <Hint emoji="📊">To retire at {retire.retireAge || 60} with {inr(retire.monthly)}/month for 30 years, you'll need roughly <strong>{inr(Math.round(retireCorpus))}</strong>.{retSaved > 0 ? ' You already have a head start! 🎉' : " Let's start building that bridge."}</Hint>}
        <DoneBtn />
      </div>
    );

    if (id === 'emergency') return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Monthly household expenses</label>
            <NI prefix="₹" value={emergency.monthlyExpenses} onChange={v => upP('emergency', { monthlyExpenses: v })} placeholder="60,000" />
          </div>
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Months to keep safe</label>
            <Toggle value={String(emergency.months || 6)} onChange={v => upP('emergency', { months: parseInt(v) })} opts={[{v:'3',l:'3 mo'},{v:'6',l:'6 mo'},{v:'12',l:'12 mo'}]} />
          </div>
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Already set aside?</label>
          <NI prefix="₹" value={emergency.alreadySaved} onChange={v => upP('emergency', { alreadySaved: v })} placeholder="1,00,000" />
        </div>
        {emergTarget > 0 && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-3 flex items-center justify-between">
            <div><p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-0.5">Target</p><p className="text-lg font-black text-emerald-800">{inr(emergTarget)}</p></div>
            {emergency.alreadySaved && <div className="text-right"><p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Gap</p><p className="text-base font-bold text-rose-500">{inr(Math.max(0, emergTarget - parseInt(emergency.alreadySaved)))}</p></div>}
          </div>
        )}
        <DoneBtn />
      </div>
    );

    if (id === 'education') return (
      <div className="space-y-3">
        <ListBuilder items={data.education || []} onChange={v => up('education', v)}
          blank={{ childName:'', childAge:'', yearsNeeded:'', amountNeeded:'', alreadySaved:'' }}
          addLabel="Add for another child"
          renderRow={(item, i, u) => (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <TI value={item.childName} onChange={v => u('childName', v)} placeholder="Child's name" />
                <div className="flex items-center gap-2"><NI value={item.childAge} onChange={v => u('childAge', v)} placeholder="Age" min={0} max={25} /><span className="text-[10px] text-slate-400 font-bold uppercase shrink-0">yrs</span></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Needed in (yrs)</p><NI value={item.yearsNeeded} onChange={v => u('yearsNeeded', v)} placeholder="12" /></div>
                <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Target amount</p><NI prefix="₹" value={item.amountNeeded} onChange={v => u('amountNeeded', v)} placeholder="20,00,000" /></div>
              </div>
              <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Already saved for this?</p><NI prefix="₹" value={item.alreadySaved} onChange={v => u('alreadySaved', v)} placeholder="0" /></div>
            </div>
          )} />
        <DoneBtn />
      </div>
    );

    if (id === 'home') return (
      <div className="space-y-4">
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">What are you buying?</label>
          <Toggle value={home.purchaseType || 'home'} onChange={v => upP('home', { purchaseType: v })} opts={[{v:'home',l:'🏠 Home'},{v:'car',l:'🚗 Car'},{v:'wedding',l:'💍 Wedding'},{v:'other',l:'Other'}]} />
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Budget</label>
          <NI prefix="₹" value={home.budget} onChange={v => upP('home', { budget: v })} placeholder="80,00,000" />
          {(!home.purchaseType || home.purchaseType === 'home') && <p className="text-[10px] text-slate-400 mt-1">Include +10% for registration & interiors</p>}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Buying in</label><div className="flex items-center gap-2"><NI value={home.inYears} onChange={v => upP('home', { inYears: v })} placeholder="3" min={1} max={30} /><span className="text-xs text-slate-400 font-medium shrink-0">years</span></div></div>
          <div><label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 block">Already saved?</label><NI prefix="₹" value={home.alreadySaved} onChange={v => upP('home', { alreadySaved: v })} placeholder="5,00,000" /></div>
        </div>
        <DoneBtn />
      </div>
    );

    if (id === 'vacation') return (
      <div className="space-y-3">
        <ListBuilder items={data.vacation || []} onChange={v => up('vacation', v)}
          blank={{ destination:'', budget:'', inYears:'', alreadySaved:'' }} addLabel="Add another trip"
          renderRow={(item, i, u) => (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">In how many years?</p><NI value={item.inYears} onChange={v => u('inYears', v)} placeholder="1" min={0} /></div>
                <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Destination</p><TI value={item.destination} onChange={v => u('destination', v)} placeholder="Maldives…" /></div>
                <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Estimated cost</p><NI prefix="₹" value={item.budget} onChange={v => u('budget', v)} placeholder="3,00,000" /></div>
              </div>
              <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Already saved for this trip?</p><NI prefix="₹" value={item.alreadySaved} onChange={v => u('alreadySaved', v)} placeholder="0" /></div>
            </div>
          )} />
        <DoneBtn />
      </div>
    );

    if (id === 'custom') return (
      <div className="space-y-3">
        <ListBuilder items={data.custom || []} onChange={v => up('custom', v)}
          blank={{ description:'', amountNeeded:'', inYears:'', alreadySaved:'' }} addLabel="Add another goal"
          renderRow={(item, i, u) => (
            <div className="space-y-2">
              <TI value={item.description} onChange={v => u('description', v)} placeholder="e.g. Starting my own business…" />
              <div className="grid grid-cols-2 gap-3">
                <NI prefix="₹" value={item.amountNeeded} onChange={v => u('amountNeeded', v)} placeholder="How much?" />
                <div className="flex items-center gap-2"><NI value={item.inYears} onChange={v => u('inYears', v)} placeholder="3" min={0} /><span className="text-[10px] text-slate-400 font-medium shrink-0">years</span></div>
              </div>
              <div><p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Already saved for this?</p><NI prefix="₹" value={item.alreadySaved} onChange={v => u('alreadySaved', v)} placeholder="0" /></div>
            </div>
          )} />
        <DoneBtn />
      </div>
    );
    return null;
  };

  return (
    <Layout step={4} onApplyAI={applyAI}>
      <div className="max-w-2xl space-y-5 pb-10">

        {/* Header */}
        <div className="space-y-1">
          <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 4 of 4 ———</p>
          <p className="text-2xl font-extrabold text-slate-900 leading-tight">
            {name ? `${name}, what are you saving for?` : 'What are you saving for?'}
          </p>
          <p className="text-slate-500 leading-relaxed">
            Tap a goal to select it and fill in the details.
          </p>
        </div>

        {/* 3-column goal selection grid */}
        <div className="grid grid-cols-3 gap-2.5">
          {GOAL_CATS.map((cat, idx) => {
            const on = isOn(idx);
            const active = activeGoal === cat.id;
            return (
              <button key={cat.id} onClick={() => handleCardClick(idx)}
                className={`flex items-start gap-3 p-4 rounded-xl border-2 transition-all text-left group relative ${
                  active  ? 'border-indigo-600 bg-indigo-50/80 shadow-lg ring-2 ring-indigo-200'
                  : on    ? 'border-emerald-400 bg-emerald-50/60 shadow-sm'
                          : 'border-slate-100 bg-white hover:border-indigo-200 hover:bg-slate-50/60 hover:shadow-sm'
                }`}>
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0 ${cat.iconBg}`}>
                  {cat.emoji}
                </div>
                <div className="min-w-0 flex-1">
                  <p className={`text-[10px] font-black tracking-[0.12em] uppercase mb-0.5 ${active ? 'text-indigo-600' : on ? 'text-emerald-600' : 'text-slate-500'}`}>{cat.label}</p>
                  <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">{cat.desc}</p>
                </div>
                {/* State badge top-right */}
                {active && (
                  <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center">
                    <ArrowRight size={9} className="text-white -rotate-90" />
                  </div>
                )}
                {!active && on && (
                  <button onClick={(e) => removeGoal(idx, e)} title="Remove"
                    className="absolute top-2 right-2 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center hover:bg-red-400 transition-colors group/rm">
                    <Check size={9} className="text-white group-hover/rm:hidden" />
                    <X size={9} className="text-white hidden group-hover/rm:block" />
                  </button>
                )}
              </button>
            );
          })}
        </div>

        {planCount === 0 && !activeGoal && (
          <Hint>Tap any goal above to select it — you can always change these later.</Hint>
        )}

        {/* Single active detail panel */}
        <AnimatePresence mode="wait">
          {activeGoal && (() => {
            const idx = GOAL_CATS.findIndex(c => c.id === activeGoal);
            const cat = GOAL_CATS[idx];
            const borderCols = ['border-orange-200','border-red-200','border-purple-200','border-blue-200','border-sky-200','border-amber-200'];
            return (
              <motion.div key={activeGoal}
                initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:10 }}
                transition={{ duration:0.18 }}
                className={`bg-white rounded-2xl border-2 ${borderCols[idx]} shadow-sm overflow-hidden`}>
                <div className={`flex items-center justify-between px-5 py-3 ${cat.iconBg}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{cat.emoji}</span>
                    <p className="text-xs font-black text-slate-700 uppercase tracking-widest">{cat.label}</p>
                  </div>
                  <button onClick={() => setActiveGoal(null)} className="text-slate-400 hover:text-slate-600 transition p-1">
                    <X size={15} />
                  </button>
                </div>
                <div className="p-5">
                  {renderDetail(activeGoal)}
                </div>
              </motion.div>
            );
          })()}
        </AnimatePresence>

        <div className="sticky bottom-0 bg-slate-50 pt-4 pb-8 border-t border-slate-200/60 z-10 flex items-center justify-between gap-4">
          <button onClick={onBack} className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700 px-4 py-2 rounded-xl hover:bg-slate-100 transition"><ArrowLeft size={15} /> Back</button>
          <button onClick={onNext} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-indigo-100 transition max-w-sm flex items-center justify-center gap-2">
            {planCount > 0 ? `Visualise ${planCount} goal${planCount > 1 ? 's' : ''} →` : 'Build My Ledger →'}
          </button>
        </div>
      </div>
    </Layout>
  );
}
// ─── COMPLETION SCREEN ────────────────────────────────────────────────────────

// ─── Payload builder ────────────────────────────────────────────────────────
const buildDashboardPayload = (profile, owned, owed, savings) => {
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
      others: [
        ...(owned.foreignInvestments || []).map(f => ({ id: f._id, name: f.type || 'Foreign / Crypto', balance: flt(f.amountInr) })),
        ...(owned.otherAssets || []).map(o => ({ id: o._id, name: o.description || 'Other Asset', balance: flt(o.value) })),
      ],
      moneyLent: (owned.moneyLent || []).map(l => ({
        id: l._id, name: l.person || 'Unknown', balance: flt(l.amount),
        lent_date: l.lentDate || null, interest_rate: flt(l.interestRate) || null,
      })),
    },
    liabilities: {
      creditCards:      (owed.creditCards    || []).map(c => ({ id: c._id, name: c.name || c.bank || 'Credit Card',    balance: flt(c.outstanding) })),
      homeLoans:        (owed.homeLoans      || []).map(l => ({ id: l._id, name: l.lender || 'Home Loan',              balance: flt(l.outstanding) })),
      vehicleLoans:     (owed.vehicleLoans   || []).map(l => ({ id: l._id, name: l.lender || 'Vehicle Loan',           balance: flt(l.outstanding) })),
      educationalLoans: (owed.educationLoans || []).map(l => ({ id: l._id, name: l.lender || 'Education Loan',         balance: flt(l.outstanding) })),
      personalLoans: [
        ...(owed.personalLoans || []).map(l => ({ id: l._id, name: l.lender || 'Personal Loan', balance: flt(l.outstanding) })),
        ...(owed.otherLoans    || []).map(l => ({ id: l._id, name: l.source || 'Other Loan',    balance: flt(l.amount) })),
      ],
    },
    goals: [
      ...(savings.retire?.on ? [{ id: 'retire', name: 'Retirement',
        target:  int(savings.retire.monthly || 0) * 12 * 25,
        years:   Math.max(1, int(savings.retire.retireAge || 60) - int(profile.age || 30)),
        current: int(savings.retire.alreadySaved || 0) }] : []),
      ...(savings.emergency?.on ? [{ id: 'emergency', name: 'Emergency Fund',
        target:  int(savings.emergency.monthlyExpenses || 0) * int(savings.emergency.months || 6),
        years: 1, current: int(savings.emergency.alreadySaved || 0) }] : []),
      ...(savings.education || []).map((e, i) => ({
        id: `edu-${i}`, name: `${e.childName || 'Child'}'s Education`,
        target: int(e.amountNeeded || 0), years: int(e.yearsNeeded || 10), current: int(e.alreadySaved || 0) })),
      ...(savings.home?.on ? [{ id: 'home', name: 'Home Purchase',
        target:  int(savings.home.budget || 0),
        years:   int(savings.home.years || 5),
        current: int(savings.home.alreadySaved || 0) }] : []),
      ...(savings.car?.on ? [{ id: 'car', name: 'Car / Vehicle',
        target:  int(savings.car.budget || 0),
        years:   int(savings.car.years || 3),
        current: int(savings.car.alreadySaved || 0) }] : []),
      ...(savings.vacation || []).map((v, i) => ({
        id: `vac-${i}`, name: v.destination || 'Vacation',
        target: int(v.budget || 0), years: int(v.inYears || 2), current: int(v.alreadySaved || 0) })),
      ...(savings.custom || []).map((c, i) => ({
        id: `cust-${i}`, name: c.description || 'Goal',
        target: int(c.amountNeeded || 0), years: int(c.inYears || 5), current: int(c.alreadySaved || 0) })),
    ],
  };
};

// ─── GOAL VISUALISATION ────────────────────────────────────────────────────────

const GV_RETURN  = 0.12;   // 12 % expected annual return
const GV_STEPUP  = 0.0512; // 5.12 % SIP step-up per year
const GV_INF     = 0.06;   // 6 % inflation (for retirement corpus)

function computeSip(target, current, years) {
  if (years <= 0) return 0;
  const r = GV_RETURN / 12;
  const n = years * 12;
  const fvCurrent = current * Math.pow(1 + GV_RETURN, years);
  const remaining = Math.max(0, target - fvCurrent);
  if (remaining <= 0) return 0;
  const sip = remaining * r / (Math.pow(1 + r, n) - 1);
  return Math.ceil(sip);
}

const GOAL_META = {
  retire:    { emoji: '🌅', color: '#818cf8' },
  emergency: { emoji: '🛡️', color: '#34d399' },
  home:      { emoji: '🏠', color: '#fb923c' },
  car:       { emoji: '🚗', color: '#60a5fa' },
};

function buildGoalList(savings, profile) {
  const age = parseInt(profile.age) || 30;
  const goals = [];

  if (savings.retire?.on) {
    const retireAge = parseInt(savings.retire.retireAge) || 60;
    const years = Math.max(1, retireAge - age);
    const monthlyNeed = parseInt(savings.retire.monthly) || 50000;
    const corpus = Math.round(monthlyNeed * 12 * (1 / 0.04) * Math.pow(1 + GV_INF, years));
    goals.push({ id: 'retire', name: 'Retirement', emoji: '🌅', color: '#818cf8',
      years, target: corpus, current: parseInt(savings.retire.alreadySaved) || 0,
      targetAge: retireAge });
  }
  if (savings.emergency?.on) {
    const months = savings.emergency.months3 ? 3 : savings.emergency.months6 ? 6 : 9;
    const monthly = parseInt(savings.emergency.monthlyExpenses) || 30000;
    const years = Math.max(1, parseInt(savings.emergency.inYears) || 2);
    goals.push({ id: 'emergency', name: 'Emergency Fund', emoji: '🛡️', color: '#34d399',
      years, target: monthly * months, current: parseInt(savings.emergency.alreadySaved) || 0,
      targetAge: age + years });
  }
  if (savings.home?.on) {
    const years = Math.max(1, parseInt(savings.home.inYears) || 5);
    goals.push({ id: 'home', name: savings.home.purchaseType === 'upgrade' ? 'Home Upgrade' : 'Buy Home',
      emoji: '🏠', color: '#fb923c',
      years, target: parseInt(savings.home.budget) || 5000000,
      current: parseInt(savings.home.alreadySaved) || 0,
      targetAge: age + years });
  }
  if (savings.car?.on) {
    const years = Math.max(1, parseInt(savings.car.years) || 3);
    goals.push({ id: 'car', name: 'Car / Vehicle', emoji: '🚗', color: '#60a5fa',
      years, target: parseInt(savings.car.budget) || 800000,
      current: parseInt(savings.car.alreadySaved) || 0,
      targetAge: age + years });
  }
  (savings.education || []).forEach((e, i) => {
    const years = Math.max(1, parseInt(e.yearsNeeded) || 10);
    goals.push({ id: `edu-${i}`, name: `${e.childName || 'Child'}'s Education`,
      emoji: '🎓', color: '#f472b6',
      years, target: parseInt(e.amountNeeded) || 2000000,
      current: parseInt(e.alreadySaved) || 0,
      targetAge: age + years });
  });
  (savings.vacation || []).forEach((v, i) => {
    const years = Math.max(1, parseInt(v.inYears) || 2);
    goals.push({ id: `vac-${i}`, name: v.destination || 'Vacation',
      emoji: '✈️', color: '#a78bfa',
      years, target: parseInt(v.budget) || 200000,
      current: parseInt(v.alreadySaved) || 0,
      targetAge: age + years });
  });
  (savings.custom || []).forEach((c, i) => {
    const years = Math.max(1, parseInt(c.inYears) || 5);
    goals.push({ id: `cust-${i}`, name: c.description || 'Custom Goal',
      emoji: '🎯', color: '#facc15',
      years, target: parseInt(c.amountNeeded) || 500000,
      current: parseInt(c.alreadySaved) || 0,
      targetAge: age + years });
  });

  return goals;
}

function buildChartData(goals, age, allocations) {
  const maxAge = Math.max(age + 1, ...goals.map(g => g.targetAge + 1));
  const data = [];
  let portfolio = goals.reduce((s, g) => s + (g.current || 0), 0);

  for (let yr = 0; yr <= maxAge - age; yr++) {
    const curAge = age + yr;
    let monthlyInvest = 0;
    goals.forEach(g => {
      if (yr < g.years) {
        const stepFactor = Math.pow(1 + GV_STEPUP, yr);
        monthlyInvest += Math.round((allocations[g.id] || 0) * stepFactor);
      }
    });

    // portfolio grows at monthly rate and gets monthly injections
    const r = GV_RETURN / 12;
    for (let m = 0; m < 12; m++) {
      portfolio = portfolio * (1 + r) + monthlyInvest;
    }
    // deduct goals that mature this year
    goals.forEach(g => {
      if (curAge === g.targetAge) portfolio = Math.max(0, portfolio - g.target);
    });

    data.push({ age: curAge, monthly: monthlyInvest, portfolio: Math.round(portfolio) });
  }
  return data;
}

const fmtCr = v => {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  return `₹${Math.round(v / 1000)}K`;
};

function GoalViz({ savings, profile, onNext, onBack }) {
  const age = parseInt(profile.age) || 30;
  const goals = buildGoalList(savings, profile);

  const [allocations, setAllocations] = useState(() => {
    const init = {};
    goals.forEach(g => { init[g.id] = computeSip(g.target, g.current, g.years); });
    return init;
  });

  // Ensure any new goals (e.g. 2nd education entry added after first mount) get an allocation
  const allocationsPlusMissing = { ...allocations };
  goals.forEach(g => {
    if (!(g.id in allocationsPlusMissing)) {
      allocationsPlusMissing[g.id] = computeSip(g.target, g.current, g.years);
    }
  });

  const totalMonthly = Object.values(allocationsPlusMissing).reduce((s, v) => s + (parseInt(v) || 0), 0);
  const chartData = buildChartData(goals, age, allocationsPlusMissing);

  if (goals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 gap-6 px-6 text-center">
        <p className="text-slate-400 text-lg">No goals added yet. Go back and add goals to visualize them.</p>
        <button onClick={onBack}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-200 text-slate-700 font-semibold hover:bg-slate-300 transition-colors">
          <ArrowLeft size={18} /> Back to Goals
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 px-4 sm:px-8 max-w-3xl mx-auto w-full pb-10">
      {/* header */}
      <div className="space-y-0.5">
        <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 5 of 6 ———</p>
        <h2 className="text-2xl font-extrabold text-slate-900 leading-tight">
          Invest ₹{totalMonthly.toLocaleString('en-IN')}/mo towards {goals.length} goal{goals.length !== 1 ? 's' : ''} this year
        </h2>
        <p className="text-slate-500 text-sm">
          Step up your SIP by {(GV_STEPUP * 100).toFixed(2)}% every year · 12% assumed returns
        </p>
      </div>

      {/* allocation table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left px-4 py-3 text-slate-400 font-medium w-36">Allocation</th>
              {goals.map(g => (
                <th key={g.id} className="px-4 py-3 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-2xl">{g.emoji}</span>
                    <span className="text-slate-700 font-semibold leading-tight text-xs">{g.name}</span>
                    <span className="text-slate-400 text-xs">{g.years}y · {fmtCr(g.target)}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* editable SIP row */}
            <tr className="border-b border-slate-100">
              <td className="px-4 py-3 text-slate-500 font-medium">Monthly SIP</td>
              {goals.map(g => (
                <td key={g.id} className="px-4 py-3 text-center">
                  <input
                    type="text"
                    inputMode="numeric"
                    value={fmtINR(String(allocationsPlusMissing[g.id] || ''))}
                    onChange={e => {
                      const raw = e.target.value.replace(/[^0-9]/g, '');
                      setAllocations({ ...allocationsPlusMissing, [g.id]: parseInt(raw) || 0 });
                    }}
                    className="w-28 text-center rounded-lg bg-white border border-slate-300 text-slate-800
                               px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-sm"
                  />
                </td>
              ))}
            </tr>
            {/* target age row */}
            <tr>
              <td className="px-4 py-3 text-slate-500 font-medium">Target Age</td>
              {goals.map(g => (
                <td key={g.id} className="px-4 py-3 text-center">
                  <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold"
                        style={{ backgroundColor: g.color + '22', color: g.color }}>
                    Age {g.targetAge}
                  </span>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* summary chips */}
      <div className="flex flex-wrap gap-2">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-sm font-semibold">
          💰 Total: ₹{totalMonthly.toLocaleString('en-IN')}/mo
        </div>
        {goals.map(g => {
          const sip = allocationsPlusMissing[g.id] || 0;
          const projected = computeSip(g.target, g.current, g.years);
          const pct = projected > 0 ? Math.round((sip / projected) * 100) : 100;
          return (
            <div key={g.id} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border"
                 style={{ borderColor: g.color + '55', backgroundColor: g.color + '11', color: g.color }}>
              {g.emoji} {g.name}: {pct}% funded
            </div>
          );
        })}
      </div>

      {/* chart */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-5">
        <p className="text-slate-600 font-semibold text-sm mb-4 uppercase tracking-wider">Planned Goal Path</p>
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="age" stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 12 }}
                   label={{ value: 'Age', position: 'insideBottomRight', offset: -5, fill: '#94a3b8', fontSize: 12 }} />
            <YAxis yAxisId="left" orientation="left" stroke="#94a3b8"
                   tickFormatter={v => fmtCr(v)}
                   tick={{ fill: '#64748b', fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" stroke="#94a3b8"
                   tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`}
                   tick={{ fill: '#64748b', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, color: '#1e293b' }}
              formatter={(value, name) =>
                name === 'Portfolio Value'
                  ? [fmtCr(value), name]
                  : [`₹${Number(value).toLocaleString('en-IN')}`, name]
              }
              labelFormatter={v => `Age ${v}`}
            />
            <Legend wrapperStyle={{ color: '#64748b', fontSize: 12 }} />
            <Area yAxisId="left" type="monotone" dataKey="portfolio" name="Portfolio Value"
                  stroke="#818cf8" fill="#818cf8" fillOpacity={0.18} strokeWidth={2} />
            <Line yAxisId="right" type="monotone" dataKey="monthly" name="Monthly SIP"
                  stroke="#10b981" strokeWidth={2} dot={false} strokeDasharray="5 3" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* nav */}
      <div className="flex justify-between pt-2">
        <button onClick={onBack}
          className="flex items-center gap-2 px-5 py-3 rounded-xl bg-slate-100 text-slate-600 font-semibold hover:bg-slate-200 transition-colors text-sm">
          <ArrowLeft size={16} /> Back
        </button>
        <button onClick={onNext}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-700 transition-colors text-sm shadow-lg shadow-indigo-100">
          See my full picture <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}

// ─── DONE / SUMMARY ────────────────────────────────────────────────────────────

function Done({ profile, owned, owed, savings, onComplete }) {
  const name = firstName(profile.name);
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState('');

  const handleEnter = async () => {
    setSaving(true);
    setSaveErr('');
    try {
      const payload = buildDashboardPayload(profile, owned, owed, savings);
      console.log('[Onboarding] Persisting dashboard payload:', JSON.stringify(payload, null, 2));
      await API.dashboard.save(payload);
      onComplete({ profile, owned, owed, savings });
    } catch (e) {
      console.error('Failed to save onboarding data to backend:', e);
      const msg = e?.response?.data?.message || e?.message || 'Unknown error';
      setSaveErr(`Could not save your data — please try again. (${msg})`);
    } finally {
      setSaving(false);
    }
  };

  const totalOwned = [
    sum(owned.bankAccounts,'balance'), parseInt(owned.cashInHand)||0,
    sum(owned.stocks,'value'), sum(owned.mutualFunds,'value'),
    parseInt(owned.epf?.balance)||0, parseInt(owned.nps?.balance)||0,
    (parseInt(owned.gold?.jewellery)||0)+(parseInt(owned.gold?.coins)||0)+(parseInt(owned.gold?.digital)||0),
    sum(owned.fixedDeposits,'amount'), sum(owned.foreignInvestments,'amountInr'), sum(owned.otherAssets,'value'),
  ].reduce((a,b)=>a+b,0);

  const totalOwed = [
    sum(owed.creditCards,'outstanding'), sum(owed.homeLoans,'outstanding'),
    sum(owed.vehicleLoans,'outstanding'), sum(owed.educationLoans,'outstanding'),
    sum(owed.personalLoans,'outstanding'), sum(owed.otherLoans,'amount'),
  ].reduce((a,b)=>a+b,0);

  const net = totalOwned - totalOwed;

  const plans = [
    savings.retire?.on, savings.emergency?.on, savings.education?.length > 0,
    savings.home?.on, savings.car?.on, savings.vacation?.length > 0, savings.custom?.length > 0,
  ].filter(Boolean).length;

  return (
    <div className="max-w-2xl mx-auto space-y-8 py-8 px-4">
      <div className="text-center space-y-3">
        <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 6 of 6 ———</p>
        <h2 className="text-2xl font-extrabold text-slate-900 leading-tight">
          {name ? `Your picture is ready, ${name}!` : "Your financial picture is ready!"}
        </h2>
        <p className="text-slate-500 max-w-md mx-auto leading-relaxed">
          We've processed your data to build an initial roadmap. Here's a glimpse of what Ledger has calculated for you.
        </p>
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Net Worth Card */}
        <div className="col-span-1 md:col-span-2 bg-white rounded-2xl border border-slate-200 p-8 shadow-sm relative overflow-hidden">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Your Net Worth Today</p>
              <h3 className={`text-5xl font-black leading-none tracking-tighter ${net >= 0 ? 'text-slate-900' : 'text-slate-900'}`}>
                {net < 0 ? '-' : ''}{inr(Math.abs(net))}
              </h3>
              <p className="text-sm text-slate-500 mt-4 leading-relaxed max-w-sm">
                Your net worth is the value of all your assets minus your current liabilities. {net < 0 ? "Having a negative net worth while paying off long-term assets like a home is perfectly normal!" : "You're starting from a position of positive equity — a great foundation."}
              </p>
            </div>
            
            <div className="w-full md:w-64 space-y-3">
              <div className="bg-emerald-50 rounded-2xl p-4 flex items-center justify-between border border-emerald-100/50">
                <span className="text-xs font-bold text-emerald-700">Assets</span>
                <span className="font-bold text-emerald-800">{inr(totalOwned)}</span>
              </div>
              <div className="bg-rose-50 rounded-2xl p-4 flex items-center justify-between border border-rose-100/50">
                <span className="text-xs font-bold text-rose-700">Liabilities</span>
                <span className="font-bold text-rose-800">{inr(totalOwed)}</span>
              </div>
            </div>
          </div>
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full -mr-16 -mt-16 opacity-50 blur-3xl" />
        </div>

        {/* Goal Readiness */}
        <div className="bg-indigo-600 rounded-[32px] p-8 text-white shadow-xl shadow-indigo-100">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
              <Target size={20} />
            </div>
            <h4 className="font-bold text-lg">Goal Readiness</h4>
          </div>
          
          <div className="space-y-6">
            {plans === 0 ? (
               <p className="text-indigo-100 text-sm opacity-80 italic">No specific goals set yet. We'll help you define them in the dashboard.</p>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/10 rounded-2xl p-4">
                  <p className="text-[10px] font-bold text-indigo-200 uppercase tracking-wider mb-1">Set Up</p>
                  <p className="text-2xl font-black">{plans} {plans === 1 ? 'Goal' : 'Goals'}</p>
                </div>
                {savings.emergency?.on && (
                  <div className="bg-white/10 rounded-2xl p-4">
                    <p className="text-[10px] font-bold text-indigo-200 uppercase tracking-wider mb-1">Emergency</p>
                    <p className="text-sm font-bold truncate">{savings.emergency.months} Mo Safe ✅</p>
                  </div>
                )}
              </div>
            )}
            <p className="text-xs text-indigo-100/80 leading-relaxed">
              We've calculated the inflation-adjusted monthly savings needed for your targets.
            </p>
          </div>
        </div>

        {/* Advisor Recommendation */}
        <div className="bg-slate-900 rounded-[32px] p-8 text-white">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center text-slate-900">
              <Zap size={20} />
            </div>
            <h4 className="font-bold text-lg">Advisor Pick</h4>
          </div>
          <div className="space-y-4">
            <p className="text-sm font-medium text-slate-300 leading-relaxed">
              Based on your {totalOwed > 0 ? 'debt-to-asset ratio' : 'profile'}, your first priority should be:
            </p>
            <div className="bg-white/10 rounded-2xl p-4 border border-white/5">
              <p className="text-emerald-400 font-bold mb-1">
                {totalOwed > 1000000 ? "Debt Consolidation Strategy" : savings.emergency?.on ? "Optimizing Tax Benefits" : "Building Emergency Buffer"}
              </p>
              <p className="text-xs text-slate-400">We'll show you exactly how on the next screen.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4 pt-4">
        {saveErr && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-3">
            <X size={18} className="text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-red-700">Failed to save your data</p>
              <p className="text-xs text-red-600 mt-0.5">{saveErr}</p>
            </div>
          </div>
        )}
        <button onClick={handleEnter} disabled={saving}
          className={`w-full ${saveErr ? 'bg-red-600 hover:bg-red-700 shadow-red-200' : 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200'} disabled:opacity-70 text-white font-black py-4 rounded-xl transition transform hover:-translate-y-0.5 shadow-lg text-lg flex items-center justify-center gap-3 group`}>
          {saving
            ? <span className="animate-pulse">Saving your ledger…</span>
            : saveErr
              ? <><span>Retry</span> <ArrowRight className="group-hover:translate-x-1 transition-transform" /></>
              : <><span>Enter Your Ledger</span> <ArrowRight className="group-hover:translate-x-1 transition-transform" /></>}
        </button>
        <p className="text-center text-xs text-slate-400 font-medium tracking-tight">
          You can refine these numbers or add advisors in your workspace at any time.
        </p>
      </div>
    </div>
  );
}

// ─── SUMMARY: PROFILE ─────────────────────────────────────────────────────────

function SummaryProfile({ profile, onNext, onBack, onEdit }) {
  const name = firstName(profile.name);
  const pt = PROFILE_TYPES.find(p => p.id === profile.profileType);

  return (
    <Layout step={2} onApplyAI={() => {}}>
      <div className="w-full max-w-2xl space-y-4 pb-4">
        <div className="space-y-0.5">
          <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 2 of 9 ———</p>
          <p className="text-2xl font-extrabold text-slate-900 leading-tight">Looking good, {name}!</p>
          <p className="text-slate-500 text-sm">Here's what we captured about you. Edit anything that looks off.</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-lg">{pt?.emoji || '🌟'}</span>
              <p className="font-bold text-slate-800">{profile.name}</p>
              {pt && <span className="text-xs bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded-full">{pt.label}</span>}
            </div>
            <button onClick={() => onEdit(1)} className="flex items-center gap-1 text-xs text-indigo-600 font-bold hover:text-indigo-800 transition shrink-0 ml-2">
              <Pencil size={12} /> Edit
            </button>
          </div>

          <div className="px-5 py-4 grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Age</p>
              <p className="text-sm font-semibold text-slate-800">{profile.age} years</p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">City</p>
              <p className="text-sm font-semibold text-slate-800">{profile.city || '—'}</p>
            </div>
            {profile.maritalStatus && (
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Marital Status</p>
                <p className="text-sm font-semibold text-slate-800 capitalize">{profile.maritalStatus}</p>
              </div>
            )}
            {profile.numChildren > 0 && (
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Children</p>
                <p className="text-sm font-semibold text-slate-800">{profile.numChildren}</p>
              </div>
            )}
            {profile.parentsSupport && (
              <div className="col-span-2">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Supporting Parents</p>
                <p className="text-sm font-semibold text-slate-800">Yes</p>
              </div>
            )}
          </div>

          {pt && (
            <div className="px-5 pb-4">
              <div className="bg-indigo-50 rounded-xl p-3">
                <p className="text-xs text-indigo-700 font-medium">{pt.desc}</p>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <button onClick={onBack} className="flex items-center gap-1 px-5 py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition">
            <ArrowLeft size={16} /> Back
          </button>
          <button onClick={onNext} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 rounded-xl transition transform hover:-translate-y-0.5 shadow-lg shadow-indigo-200 text-base flex items-center justify-center gap-3 group">
            <span>Looks good — map my finances</span>
            <ArrowRight className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </Layout>
  );
}

// ─── SUMMARY: FINANCIAL ───────────────────────────────────────────────────────

function SummaryFinancial({ owned, owed, onNext, onBack, onEdit }) {
  const totalAssets = [
    sum(owned.bankAccounts, 'balance'),
    parseInt(owned.cashInHand) || 0,
    sum(owned.stocks, 'value'),
    sum(owned.mutualFunds, 'value'),
    parseInt(owned.epf?.balance) || 0,
    parseInt(owned.nps?.balance) || 0,
    (parseInt(owned.gold?.jewellery) || 0) + (parseInt(owned.gold?.coins) || 0) + (parseInt(owned.gold?.digital) || 0),
    sum(owned.fixedDeposits, 'amount'),
    sum(owned.foreignInvestments, 'amountInr'),
    sum(owned.otherAssets, 'value'),
    sum(owned.moneyLent, 'amount'),
  ].reduce((a, b) => a + b, 0);

  const totalLiabilities = [
    sum(owed.creditCards, 'outstanding'),
    sum(owed.homeLoans, 'outstanding'),
    sum(owed.vehicleLoans, 'outstanding'),
    sum(owed.educationLoans, 'outstanding'),
    sum(owed.personalLoans, 'outstanding'),
    sum(owed.otherLoans, 'amount'),
  ].reduce((a, b) => a + b, 0);

  const netWorth = totalAssets - totalLiabilities;

  const assetRows = [
    { label: 'Bank & Cash',     emoji: '🏦', amount: sum(owned.bankAccounts, 'balance') + (parseInt(owned.cashInHand) || 0) },
    { label: 'Stocks',          emoji: '📈', amount: sum(owned.stocks, 'value') },
    { label: 'Mutual Funds',    emoji: '📦', amount: sum(owned.mutualFunds, 'value') },
    { label: 'EPF / NPS',       emoji: '🛡️', amount: (parseInt(owned.epf?.balance) || 0) + (parseInt(owned.nps?.balance) || 0) },
    { label: 'Gold',            emoji: '🥇', amount: (parseInt(owned.gold?.jewellery) || 0) + (parseInt(owned.gold?.coins) || 0) + (parseInt(owned.gold?.digital) || 0) },
    { label: 'Fixed Deposits',  emoji: '🔒', amount: sum(owned.fixedDeposits, 'amount') },
    { label: 'Foreign / Crypto',emoji: '🌍', amount: sum(owned.foreignInvestments, 'amountInr') },
    { label: 'Other Assets',    emoji: '➕', amount: sum(owned.otherAssets, 'value') },
    { label: 'Money Lent',      emoji: '🤝', amount: sum(owned.moneyLent, 'amount') },
  ].filter(r => r.amount > 0);

  const liabilityRows = [
    { label: 'Credit Cards',    emoji: '💳', amount: sum(owed.creditCards, 'outstanding') },
    { label: 'Home Loan',       emoji: '🏠', amount: sum(owed.homeLoans, 'outstanding') },
    { label: 'Vehicle Loan',    emoji: '🚗', amount: sum(owed.vehicleLoans, 'outstanding') },
    { label: 'Education Loan',  emoji: '🎓', amount: sum(owed.educationLoans, 'outstanding') },
    { label: 'Personal Loan',   emoji: '💸', amount: sum(owed.personalLoans, 'outstanding') },
    { label: 'Other Loans',     emoji: '➕', amount: sum(owed.otherLoans, 'amount') },
  ].filter(r => r.amount > 0);

  return (
    <Layout step={5} onApplyAI={() => {}}>
      <div className="w-full max-w-3xl space-y-4 pb-4">
        <div className="space-y-0.5">
          <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 5 of 9 ———</p>
          <p className="text-2xl font-extrabold text-slate-900 leading-tight">Your financial snapshot</p>
          <p className="text-slate-500 text-sm">Complete picture of assets and liabilities. Edit anything to refine.</p>
        </div>

        {/* Net worth hero */}
        <div className={`rounded-2xl p-5 flex items-center justify-between ${netWorth >= 0 ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
          <div>
            <p className={`text-xs font-bold uppercase tracking-widest mb-0.5 ${netWorth >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>Net Worth</p>
            <p className={`text-3xl font-black ${netWorth >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>{inr(Math.abs(netWorth))}{netWorth < 0 ? ' (negative)' : ''}</p>
            <p className="text-xs text-slate-500 mt-0.5">{inr(totalAssets)} assets − {inr(totalLiabilities)} liabilities</p>
          </div>
          <div className="text-4xl">{netWorth >= 0 ? '📈' : '⚠️'}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Assets */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm">💼</span>
                <p className="font-bold text-sm text-slate-700">Assets</p>
                <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">{inr(totalAssets)}</span>
              </div>
              <button onClick={() => onEdit(3)} className="flex items-center gap-1 text-xs text-indigo-600 font-bold hover:text-indigo-800 transition">
                <Pencil size={11} /> Edit
              </button>
            </div>
            <div className="px-4 py-3 space-y-2">
              {assetRows.length === 0
                ? <p className="text-xs text-slate-400 italic">No assets entered yet.</p>
                : assetRows.map(r => (
                  <div key={r.label} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{r.emoji}</span>
                      <span className="text-xs text-slate-600">{r.label}</span>
                    </div>
                    <span className="text-xs font-bold text-slate-800">{inr(r.amount)}</span>
                  </div>
                ))
              }
            </div>
          </div>

          {/* Liabilities */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm">📋</span>
                <p className="font-bold text-sm text-slate-700">Liabilities</p>
                <span className="text-xs font-bold text-red-500 bg-red-50 px-2 py-0.5 rounded-full">{inr(totalLiabilities)}</span>
              </div>
              <button onClick={() => onEdit(4)} className="flex items-center gap-1 text-xs text-indigo-600 font-bold hover:text-indigo-800 transition">
                <Pencil size={11} /> Edit
              </button>
            </div>
            <div className="px-4 py-3 space-y-2">
              {liabilityRows.length === 0
                ? <p className="text-xs text-slate-400 italic">No liabilities entered yet.</p>
                : liabilityRows.map(r => (
                  <div key={r.label} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{r.emoji}</span>
                      <span className="text-xs text-slate-600">{r.label}</span>
                    </div>
                    <span className="text-xs font-bold text-slate-800">{inr(r.amount)}</span>
                  </div>
                ))
              }
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={onBack} className="flex items-center gap-1 px-5 py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition">
            <ArrowLeft size={16} /> Back
          </button>
          <button onClick={onNext} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 rounded-xl transition transform hover:-translate-y-0.5 shadow-lg shadow-indigo-200 text-base flex items-center justify-center gap-3 group">
            <span>Spot on — now set my goals</span>
            <ArrowRight className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </Layout>
  );
}

// ─── SUMMARY: GOALS ───────────────────────────────────────────────────────────

function SummaryGoals({ savings, profile, owned, onNext, onBack, onEdit }) {
  const name = firstName(profile.name);
  const userAge = parseInt(profile?.age) || 30;

  const activeGoals = [];

  if (savings.retire?.on) {
    const retireAge = parseInt(savings.retire.retireAge) || 60;
    const monthly = parseInt(savings.retire.monthly) || 0;
    const years = Math.max(0, retireAge - userAge);
    const corpus = monthly ? Math.round(monthly * 12 * 25 * Math.pow(1.06, years)) : 0;
    activeGoals.push({
      emoji: '🌅', label: 'Retirement',
      details: [
        savings.retire.retireAge ? `Retire at ${savings.retire.retireAge}` : null,
        monthly ? `${inr(monthly)}/mo expenses` : null,
        corpus ? `Target: ${inr(corpus)} corpus` : null,
      ].filter(Boolean),
    });
  }

  if (savings.emergency?.on) {
    const months = savings.emergency.months || 6;
    const monthly = parseInt(savings.emergency.monthlyExpenses) || 0;
    const target = monthly * months;
    activeGoals.push({
      emoji: '🛡️', label: 'Emergency Fund',
      details: [
        `${months} months coverage`,
        monthly ? `${inr(monthly)}/mo expenses` : null,
        target ? `Target: ${inr(target)}` : null,
      ].filter(Boolean),
    });
  }

  (savings.education || []).forEach(edu => {
    activeGoals.push({
      emoji: '🎓', label: `Education${edu.childName ? ` — ${edu.childName}` : ''}`,
      details: [
        edu.yearsNeeded ? `In ${edu.yearsNeeded} years` : null,
        edu.amountNeeded ? `Target: ${inr(edu.amountNeeded)}` : null,
      ].filter(Boolean),
    });
  });

  if (savings.home?.on) {
    activeGoals.push({
      emoji: '🏠', label: 'Home Purchase',
      details: [
        savings.home.targetAmount ? `Target: ${inr(savings.home.targetAmount)}` : null,
        savings.home.inYears ? `In ${savings.home.inYears} years` : null,
      ].filter(Boolean),
    });
  }

  (savings.vacation || []).forEach(v => {
    activeGoals.push({
      emoji: '✈️', label: `Holiday${v.destination ? ` — ${v.destination}` : ''}`,
      details: [
        v.budget ? `Budget: ${inr(v.budget)}` : null,
        v.inYears ? `In ${v.inYears} years` : null,
      ].filter(Boolean),
    });
  });

  (savings.custom || []).forEach(c => {
    activeGoals.push({
      emoji: '✨', label: c.description || 'Custom Goal',
      details: [
        c.amountNeeded ? `Target: ${inr(c.amountNeeded)}` : null,
        c.inYears ? `In ${c.inYears} years` : null,
      ].filter(Boolean),
    });
  });

  return (
    <Layout step={7} onApplyAI={() => {}}>
      <div className="w-full max-w-2xl space-y-4 pb-4">
        <div className="space-y-0.5">
          <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Step 7 of 9 ———</p>
          <p className="text-2xl font-extrabold text-slate-900 leading-tight">Your goals, {name}</p>
          <p className="text-slate-500 text-sm">
            {activeGoals.length} goal{activeGoals.length !== 1 ? 's' : ''} locked in. Edit anytime to refine the details.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <p className="font-bold text-sm text-slate-700">Planned Goals</p>
            <button onClick={() => onEdit(6)} className="flex items-center gap-1 text-xs text-indigo-600 font-bold hover:text-indigo-800 transition">
              <Pencil size={11} /> Edit Goals
            </button>
          </div>
          <div className="divide-y divide-slate-50">
            {activeGoals.length === 0
              ? (
                <div className="px-5 py-8 text-center">
                  <p className="text-slate-400 text-sm">No goals added yet.</p>
                  <button onClick={() => onEdit(6)} className="mt-2 text-indigo-600 text-sm font-bold hover:underline">
                    Add Goals →
                  </button>
                </div>
              )
              : activeGoals.map((g, i) => (
                <div key={i} className="px-5 py-3 flex items-start gap-3">
                  <span className="text-xl mt-0.5">{g.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm text-slate-800">{g.label}</p>
                    {g.details.length > 0 && (
                      <p className="text-xs text-slate-500 mt-0.5">{g.details.join(' · ')}</p>
                    )}
                  </div>
                  <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />
                </div>
              ))
            }
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={onBack} className="flex items-center gap-1 px-5 py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition">
            <ArrowLeft size={16} /> Back
          </button>
          <button onClick={onNext} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 rounded-xl transition transform hover:-translate-y-0.5 shadow-lg shadow-indigo-200 text-base flex items-center justify-center gap-3 group">
            <span>All set — show my projections</span>
            <ArrowRight className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </Layout>
  );
}

// ─── ROOT EXPORT ──────────────────────────────────────────────────────────────

export default function OnboardingV2({ onComplete, userEmail = '' }) {
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState({ ...D1 });
  const [owned,   setOwned]   = useState({ ...D2 });
  const [owed,    setOwed]    = useState({ ...D3 });
  const [savings, setSavings] = useState({ ...D4 });

  const name = firstName(profile.name);

  const sv = {
    initial: { opacity:0, x:28 },
    animate: { opacity:1, x:0 },
    exit:    { opacity:0, x:-28 },
  };

  // After S1: go to Profile Summary
  const afterS1 = () => setStep(2);

  // After Profile Summary: pre-seed S2 with persona defaults, then go to Assets
  const goToAssets = () => {
    setOwned(prev => {
      if (prev.bankAccounts.length > 0) return prev; // user already edited — don't overwrite
      const defs = PERSONA_DEFAULTS[profile.profileType] || PERSONA_DEFAULTS.other;
      return { ...prev, ...defs };
    });
    setStep(3);
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      <header className="bg-white border-b border-slate-200 shrink-0 z-40 shadow-sm">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <span className="text-base font-bold text-indigo-700 shrink-0">Ledger</span>
          <Stepper step={step} onGoTo={s => s < step && setStep(s)} />
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs text-slate-400 hidden sm:block">
              {step <= 2 ? 'Phase 1 of 4' : step <= 5 ? 'Phase 2 of 4' : step <= 7 ? 'Phase 3 of 4' : step === 8 ? 'Phase 4 of 4' : 'Done!'}
            </span>
            {userEmail && (
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-full px-3 py-1">
                <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-indigo-600">{userEmail[0].toUpperCase()}</span>
                </div>
                <span className="text-xs font-medium text-slate-600 max-w-[140px] truncate">{userEmail}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-hidden max-w-[1400px] w-full mx-auto px-6">
        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div key="s1" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full">
              <S1 data={profile} setData={setProfile} onNext={afterS1} />
            </motion.div>
          )}
          {step === 2 && (
            <motion.div key="sum-profile" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full overflow-y-auto py-4">
              <SummaryProfile profile={profile} onNext={goToAssets} onBack={() => setStep(1)} onEdit={s => setStep(s)} />
            </motion.div>
          )}
          {step === 3 && (
            <motion.div key="s2" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full">
              <S2 data={owned} setData={setOwned} onNext={() => setStep(4)} onBack={() => setStep(2)} name={name} />
            </motion.div>
          )}
          {step === 4 && (
            <motion.div key="s3" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full">
              <S3 data={owed} setData={setOwed} onNext={() => setStep(5)} onBack={() => setStep(3)} name={name} />
            </motion.div>
          )}
          {step === 5 && (
            <motion.div key="sum-financial" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full overflow-y-auto py-4">
              <SummaryFinancial owned={owned} owed={owed} onNext={() => setStep(6)} onBack={() => setStep(4)} onEdit={s => setStep(s)} />
            </motion.div>
          )}
          {step === 6 && (
            <motion.div key="s4" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full">
              <S4 data={savings} setData={setSavings} onNext={() => setStep(7)} onBack={() => setStep(5)} profile={profile} owned={owned} name={name} />
            </motion.div>
          )}
          {step === 7 && (
            <motion.div key="sum-goals" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full overflow-y-auto py-4">
              <SummaryGoals savings={savings} profile={profile} owned={owned} onNext={() => setStep(8)} onBack={() => setStep(6)} onEdit={s => setStep(s)} />
            </motion.div>
          )}
          {step === 8 && (
            <motion.div key="s5" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full overflow-y-auto py-6">
              <GoalViz savings={savings} profile={profile} onNext={() => setStep(9)} onBack={() => setStep(7)} />
            </motion.div>
          )}
          {step === 9 && (
            <motion.div key="s6" variants={sv} initial="initial" animate="animate" exit="exit" transition={{ duration:0.2 }} className="h-full overflow-y-auto py-6">
              <Done profile={profile} owned={owned} owed={owed} savings={savings} onComplete={onComplete} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
