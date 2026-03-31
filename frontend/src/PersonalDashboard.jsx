import React, { useState, useEffect } from 'react';
import { API } from './api.js';
import {
  Wallet, CreditCard, PiggyBank, Target, Upload, FileText,
  ChevronRight, ArrowUpRight, ArrowDownRight, Briefcase, Store,
  Home, TrendingUp, RefreshCw, Check, AlertCircle, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

// ── theme constants ──────────────────────────────────────────────────────────
const NAVY   = '#2C4A70';
const SAGE   = '#526B5C';
const BG     = '#F7F8F9';

// ── goal type display ────────────────────────────────────────────────────────
const GOAL_TYPE_INFO = {
  RETIREMENT:  { emoji: '🏝️',  label: 'Retirement'         },
  EMERGENCY:   { emoji: '🛡️',  label: 'Emergency Fund'     },
  HOME:        { emoji: '🏠',  label: 'Dream Home'         },
  EDUCATION:   { emoji: '🎓',  label: 'Education'          },
  VEHICLE:     { emoji: '🚗',  label: 'Vehicle'            },
  VACATION:    { emoji: '✈️',  label: 'Vacation'           },
  WEDDING:     { emoji: '💍',  label: 'Wedding'            },
  OTHERS:      { emoji: '🎯',  label: 'Other Goal'         },
};

// Map our onboarding GOAL_OPTS ids → display info
const ONBOARDING_GOAL_MAP = {
  retirement: { type: 'RETIREMENT', label: 'Retire Early'    },
  emergency:  { type: 'EMERGENCY',  label: 'Emergency Fund'  },
  home:       { type: 'HOME',       label: 'Buy a Home'      },
  education:  { type: 'EDUCATION',  label: 'Education'       },
  vehicle:    { type: 'VEHICLE',    label: 'Vehicle'         },
  vacation:   { type: 'VACATION',   label: 'Vacation'        },
  wedding:    { type: 'WEDDING',    label: 'Wedding'         },
  debt:       { type: 'OTHERS',     label: 'Pay off Debt'    },
  custom:     { type: 'OTHERS',     label: 'Custom Goal'     },
};

// Mirrors DUMMY_GOALS in OnboardingV4 — used as last-resort fallback when the
// user reaches Dashboards without having visited the Goals section at all.
const PERSPECTIVE_DUMMY_GOALS = {
  salaried: [
    { id: 'emergency', targetAmount: 300000,   timelineMonths: 12,  note: '3× monthly salary as safety net' },
    { id: 'retire',    targetAmount: 10000000, timelineMonths: 240, note: 'FIRE target at 50' },
    { id: 'home',      targetAmount: 2000000,  timelineMonths: 48,  note: 'Down payment for home purchase' },
  ],
  business: [
    { id: 'emergency', targetAmount: 1000000,  timelineMonths: 6,   note: 'Business continuity reserve' },
    { id: 'debt',      targetAmount: 2500000,  timelineMonths: 36,  note: 'Clear working capital loan' },
    { id: 'retire',    targetAmount: 20000000, timelineMonths: 180, note: 'Exit corpus target' },
  ],
  homemaker: [
    { id: 'emergency', targetAmount: 200000,  timelineMonths: 12, note: 'Household emergency buffer' },
    { id: 'education', targetAmount: 1500000, timelineMonths: 96, note: "Children's higher education fund" },
    { id: 'home',      targetAmount: 500000,  timelineMonths: 24, note: 'Home renovation fund' },
  ],
  investor: [
    { id: 'retire',  targetAmount: 50000000, timelineMonths: 120, note: 'FIRE corpus — 25× annual expenses' },
    { id: 'custom',  targetAmount: 5000000,  timelineMonths: 60,  note: 'Passive income portfolio target' },
    { id: 'debt',    targetAmount: 5500000,  timelineMonths: 48,  note: 'Prepay home loan early' },
  ],
};

// ── goal projection helpers ──────────────────────────────────────────────────
const GV_RETURN = 0.12;
const GV_STEPUP = 0.0512;

function computeSip(target, current, years) {
  if (years <= 0) return 0;
  const r = GV_RETURN / 12;
  const n = years * 12;
  const fvCurrent = current * Math.pow(1 + GV_RETURN, years);
  const remaining = Math.max(0, target - fvCurrent);
  if (remaining <= 0) return 0;
  return Math.ceil(remaining * r / (Math.pow(1 + r, n) - 1));
}

function buildChartData(goal, startAge) {
  const data = [];
  let portfolio = goal.current || 0;
  const r = GV_RETURN / 12;
  for (let yr = 0; yr <= goal.years; yr++) {
    const age = startAge + yr;
    let monthlyInvest = 0;
    if (yr < goal.years) {
      monthlyInvest = Math.round((goal.sip || 0) * Math.pow(1 + GV_STEPUP, yr));
    }
    for (let m = 0; m < 12; m++) {
      portfolio = portfolio * (1 + r) + monthlyInvest;
    }
    data.push({ age, monthly: monthlyInvest, portfolio: Math.round(portfolio) });
  }
  return data;
}

function fmtCr(v) {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  return `₹${Math.round(v / 1000)}K`;
}

// ── goal projection modal ────────────────────────────────────────────────────
function GoalProjectionModal({ goal, onClose, userAge = 30 }) {
  const [sip, setSip] = useState(goal.monthlySavingNeeded || 0);
  const years = Math.max(1, Math.round((goal.timelineMonths || 12) / 12));

  const recommended = computeSip(goal.targetAmount, 0, years);
  const pct = recommended > 0 ? Math.round((sip / recommended) * 100) : 100;
  const chartGoal = { target: goal.targetAmount, current: 0, sip, years };
  const chartData = buildChartData(chartGoal, userAge);

  const info = GOAL_TYPE_INFO[goal.goalType] || GOAL_TYPE_INFO.OTHERS;
  const accentColor = {
    RETIREMENT: '#2C4A70', EMERGENCY: '#526B5C', HOME: '#fb923c',
    EDUCATION: '#f472b6', VEHICLE: '#60a5fa', VACATION: '#a78bfa',
    WEDDING: '#f43f5e', OTHERS: '#facc15',
  }[goal.goalType] || NAVY;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{info.emoji}</span>
            <div>
              <h2 className="text-lg font-bold text-slate-800">{goal.name}</h2>
              <p className="text-sm text-slate-500">
                {years}y horizon · Target {fmtCr(goal.targetAmount)}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-700 rounded-full hover:bg-slate-100 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* SIP input row */}
          <div className="flex items-center gap-4 bg-slate-50 rounded-xl p-4">
            <div className="flex-1">
              <p className="text-xs text-slate-500 font-medium mb-1">Monthly SIP</p>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-sm">₹</span>
                <input type="number" value={sip}
                  onChange={e => setSip(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-36 text-lg font-bold text-slate-800 bg-white border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#2C4A70]/30"
                />
                <span className="text-slate-400 text-sm">/mo</span>
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 font-medium mb-1">Funding</div>
              <div className="text-2xl font-bold" style={{ color: pct >= 100 ? '#10b981' : pct >= 75 ? accentColor : '#f59e0b' }}>
                {pct}%
              </div>
              <div className="text-xs text-slate-400">of required</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 font-medium mb-1">Recommended</div>
              <div className="text-sm font-semibold" style={{ color: NAVY }}>₹{recommended.toLocaleString('en-IN')}/mo</div>
            </div>
          </div>

          {/* Chips */}
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#2C4A70]/5 border border-[#2C4A70]/20 text-[#2C4A70] text-xs font-semibold">
              💰 ₹{sip.toLocaleString('en-IN')}/mo SIP
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border"
              style={{ borderColor: accentColor + '55', backgroundColor: accentColor + '11', color: accentColor }}>
              {info.emoji} {pct}% funded
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-slate-600 text-xs font-semibold">
              📈 5.12% step-up · 12% returns
            </div>
          </div>

          {/* Chart */}
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-slate-600 font-semibold text-xs mb-3 uppercase tracking-wider">Goal Projection</p>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="age" stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 11 }}
                  label={{ value: 'Age', position: 'insideBottomRight', offset: -5, fill: '#94a3b8', fontSize: 11 }} />
                <YAxis yAxisId="left" tickFormatter={v => fmtCr(v)} stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis yAxisId="right" orientation="right" tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 10 }}
                  formatter={(value, name) => name === 'Portfolio Value' ? [fmtCr(value), name] : [`₹${Number(value).toLocaleString('en-IN')}`, name]}
                  labelFormatter={v => `Age ${v}`}
                />
                <Legend wrapperStyle={{ color: '#64748b', fontSize: 11 }} />
                <Area yAxisId="left" type="monotone" dataKey="portfolio" name="Portfolio Value"
                  stroke={accentColor} fill={accentColor} fillOpacity={0.15} strokeWidth={2} />
                <Line yAxisId="right" type="monotone" dataKey="monthly" name="Monthly SIP"
                  stroke="#526B5C" strokeWidth={2} dot={false} strokeDasharray="5 3" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-slate-800">{fmtCr(goal.targetAmount)}</div>
              <div className="text-xs text-slate-400 mt-0.5">Target corpus</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold" style={{ color: SAGE }}>{fmtCr(sip * years * 12)}</div>
              <div className="text-xs text-slate-400 mt-0.5">Total invested</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold" style={{ color: NAVY }}>{years}y</div>
              <div className="text-xs text-slate-400 mt-0.5">Time horizon</div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

const PERSPECTIVE_INFO = {
  salaried:  { icon: Briefcase,  label: 'Salaried Professional' },
  business:  { icon: Store,      label: 'Business Owner'         },
  homemaker: { icon: Home,       label: 'Homemaker'              },
  investor:  { icon: TrendingUp, label: 'Investor'               },
};

// ── formatters ───────────────────────────────────────────────────────────────
function fmt(amount) {
  const n = typeof amount === 'number' ? amount : (parseFloat(amount) || 0);
  const abs = Math.abs(n);
  let s;
  if (abs >= 10000000) s = `₹${(abs / 10000000).toFixed(1)}Cr`;
  else if (abs >= 100000) s = `₹${(abs / 100000).toFixed(1)}L`;
  else s = `₹${abs.toLocaleString('en-IN')}`;
  return n < 0 ? `-${s}` : s;
}

// ── stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, accent, delay = 0, negative = false }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm"
    >
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[2px] mb-2">{label}</p>
      <p className="text-3xl font-black" style={{ color: negative ? '#E53E3E' : accent || NAVY }}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-2">{sub}</p>}
    </motion.div>
  );
}

// ── main component ───────────────────────────────────────────────────────────
export default function PersonalDashboard({ onboardingData, onStartImport, onNavigate }) {
  const [dbGoals, setDbGoals] = useState(null);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [dbData,  setDbData]  = useState(null);

  // Try to load richer data from backend (non-blocking)
  useEffect(() => {
    API.dashboard.load()
      .then(d => setDbData(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    API.reports.summary()
      .then(d => setDbGoals(d?.goals || null))
      .catch(() => {});
  }, []);

  // ── Resolve onboarding data from props only (never localStorage) ──────────
  // Reading localStorage here would leak one user's data to the next logged-in user.
  const profile   = onboardingData?.profile  || {};
  const mapping   = onboardingData?.mapping  || {};
  const goalsData = onboardingData?.goals    || {};

  // Always use onboarding mapping data as the primary source for totals —
  // these are the values the user explicitly entered during the Mapping step.
  const totalAssets      = (mapping.assets      || []).reduce((s, a) => s + (a.value || 0), 0);
  const totalLiabilities = (mapping.liabilities || []).reduce((s, l) => s + (l.value || 0), 0);
  const netWorth = totalAssets - totalLiabilities;

  // ── Build goals list from onboarding (fallback to backend) ────────────────
  const today = new Date();

  // Onboarding-configured goals → display shape
  const goalDetails = goalsData.goalDetails || {};
  const dummyDetails = goalsData.dummyGoalDetails || [];
  const isDummyGoals = dummyDetails.length > 0 && Object.keys(goalDetails).length === 0;

  const localGoals = Object.entries(goalDetails).map(([id, d]) => {
    const meta = ONBOARDING_GOAL_MAP[id] || { type: 'OTHERS', label: id };
    return {
      id,
      name: meta.label,
      goalType: meta.type,
      targetAmount: d.targetAmount || 0,
      timelineMonths: d.timelineMonths || 12,
      monthlySavingNeeded: d.targetAmount && d.timelineMonths ? Math.ceil(d.targetAmount / d.timelineMonths) : 0,
      priority: d.priority || 'medium',
      progress: 0,
      note: d.note || '',
    };
  });

  const dummyGoals = dummyDetails.map(d => {
    const meta = ONBOARDING_GOAL_MAP[d.id] || { type: 'OTHERS', label: String(d.id) };
    return {
      id: String(d.id),
      name: meta.label,
      goalType: meta.type,
      targetAmount: d.targetAmount || 0,
      timelineMonths: d.timelineMonths || 12,
      monthlySavingNeeded: d.targetAmount && d.timelineMonths ? Math.ceil(d.targetAmount / d.timelineMonths) : 0,
      priority: 'medium',
      progress: 0,
      note: d.note || '',
    };
  });

  // Always prefer onboarding-saved goals; backend goals are supplementary only
  // when no onboarding goals exist at all.
  // Last-resort fallback: perspective-based dummy goals so the section is never empty
  const perspectiveDummies = (() => {
    const key = profile.perspective || 'salaried';
    const raw = PERSPECTIVE_DUMMY_GOALS[key] || PERSPECTIVE_DUMMY_GOALS.salaried;
    return raw.map(d => {
      const meta = ONBOARDING_GOAL_MAP[d.id] || { type: 'OTHERS', label: String(d.id) };
      return {
        id: String(d.id),
        name: meta.label,
        goalType: meta.type,
        targetAmount: d.targetAmount || 0,
        timelineMonths: d.timelineMonths || 12,
        monthlySavingNeeded: d.targetAmount && d.timelineMonths
          ? Math.ceil(d.targetAmount / d.timelineMonths) : 0,
        priority: 'medium',
        progress: 0,
        note: d.note || '',
        isDummy: true,
      };
    });
  })();

  const goals = localGoals.length
    ? localGoals
    : (isDummyGoals ? dummyGoals : (dbGoals?.length
        ? dbGoals.map(g => {
            const targetDate = g.target_date ? new Date(g.target_date) : null;
            const months = targetDate
              ? Math.max(1, Math.round((targetDate - today) / (30.5 * 24 * 3600 * 1000)))
              : 12;
            const target  = parseFloat(g.target_amount)  || 0;
            const current = parseFloat(g.current_amount) || 0;
            return {
              id: String(g.id),
              name: g.name,
              goalType: g.goal_type || 'OTHERS',
              targetAmount: target,
              timelineMonths: months,
              monthlySavingNeeded: months > 0 ? Math.ceil(Math.max(0, target - current) / months) : 0,
              priority: 'medium',
              progress: Math.min(100, Math.round((current / target) * 100) || 0),
              note: g.notes || '',
            };
          })
        : perspectiveDummies));

  const totalMonthlyTarget = goals.reduce((s, g) => s + (g.monthlySavingNeeded || 0), 0);
  const inc = parseInt(String(goalsData.incomeString || '').replace(/\D/g, '')) || 0;

  const firstName = profile.legalName?.split(' ')[0] || 'there';
  const perspInfo = PERSPECTIVE_INFO[profile.perspective] || PERSPECTIVE_INFO.salaried;
  const PerspIcon = perspInfo.icon;

  // Money lent section (from DB only)
  const lentItems = (dbData?.assets?.moneyLent || []).filter(l => l.balance > 0 && l.interest_rate > 0);
  const totalAnnualInterest = lentItems.reduce((s, l) => s + l.balance * (l.interest_rate / 100), 0);

  return (
    <div className="w-full px-6 md:px-10 py-8 space-y-8" style={{ background: BG }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-serif font-black" style={{ color: NAVY }}>
            Hey, {firstName} 👋
          </h1>
          <div className="flex items-center gap-2 mt-1.5 text-slate-500 text-sm font-medium">
            <PerspIcon size={14} className="shrink-0" />
            <span>{perspInfo.label}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[2px] mb-1">Net Worth</p>
          <p className={`text-4xl font-black ${netWorth >= 0 ? '' : 'text-rose-600'}`}
            style={netWorth >= 0 ? { color: NAVY } : {}}>
            {netWorth >= 0 ? '' : '-'}{fmt(Math.abs(netWorth))}
          </p>
        </div>
      </div>

      {/* ── Key stats ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-5">
        <StatCard label="What I own" value={fmt(totalAssets)} sub="Total assets" accent={NAVY} delay={0} />
        <StatCard label="What I owe" value={fmt(totalLiabilities)} sub="Total liabilities" accent="#E53E3E" delay={0.08} />
        <StatCard
          label="Monthly target"
          value={totalMonthlyTarget > 0 ? fmt(totalMonthlyTarget) : '—'}
          sub="To hit all goals on time"
          accent={SAGE}
          delay={0.16}
        />
      </div>

      <div className="lg:grid lg:grid-cols-12 lg:gap-8 lg:items-start space-y-8 lg:space-y-0">

        {/* ── Left: Goals ────────────────────────────────────────────────── */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">

          {goals.length > 0 ? (
            <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                    🎯 Financial milestones
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">Monthly savings needed to reach each goal</p>
                </div>
                {(isDummyGoals || goals.some(g => g.isDummy)) && (
                  <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
                    ⚠️ Suggested — configure in Goals tab
                  </span>
                )}
              </div>

              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                {goals.map((g, i) => {
                  const info = GOAL_TYPE_INFO[g.goalType] || GOAL_TYPE_INFO.OTHERS;
                  const pct  = g.progress || 0;
                  return (
                    <motion.button key={g.id} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.07 }}
                      onClick={() => setSelectedGoal(g)}
                      className="bg-slate-50 rounded-2xl p-4 border border-slate-100 flex flex-col gap-3 text-left hover:shadow-md hover:border-[#2C4A70]/20 transition-all w-full">
                      <div className="flex items-center gap-3">
                        <span className="w-10 h-10 bg-white rounded-xl border border-slate-100 shadow-sm flex items-center justify-center text-xl shrink-0">
                          {info.emoji}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm text-slate-800 truncate">{g.name || info.label}</p>
                          <p className="text-[10px] text-slate-400 font-semibold">
                            {g.timelineMonths >= 12 ? `${(g.timelineMonths / 12).toFixed(1)}yr` : `${g.timelineMonths}mo`} timeline · click to project
                          </p>
                        </div>
                      </div>

                      {pct > 0 && (
                        <div>
                          <div className="flex justify-between text-[10px] font-medium text-slate-400 mb-1">
                            <span>Progress</span><span>{pct}%</span>
                          </div>
                          <div className="w-full bg-slate-200 rounded-full h-1.5">
                            <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: SAGE }} />
                          </div>
                        </div>
                      )}

                      <div className="flex items-end justify-between pt-2 border-t border-slate-100">
                        <div>
                          <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide">Monthly SIP</p>
                          <p className="text-lg font-black" style={{ color: NAVY }}>{fmt(g.monthlySavingNeeded)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide">Target</p>
                          <p className="text-sm font-bold text-slate-600">{fmt(g.targetAmount)}</p>
                        </div>
                      </div>
                    </motion.button>
                  );
                })}
              </div>

              {totalMonthlyTarget > 0 && (
                <div className="mt-5 pt-4 border-t border-slate-100 flex justify-between items-center bg-slate-50 rounded-xl px-5 py-3">
                  <span className="text-sm font-semibold text-slate-600">Total monthly target across all goals</span>
                  <span className="text-2xl font-black" style={{ color: NAVY }}>
                    {fmt(totalMonthlyTarget)}<span className="text-xs font-medium text-slate-400">/mo</span>
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-2xl p-8 border border-dashed border-slate-200 text-center">
              <Target size={32} className="mx-auto mb-3 text-slate-300" />
              <p className="text-slate-400 font-medium">No goals configured yet</p>
              <p className="text-xs text-slate-300 mt-1">Head over to the Goals tab to set up your milestones</p>
              <button onClick={() => onNavigate?.('goals')}
                className="mt-4 text-xs font-bold px-4 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors">
                Set up Goals →
              </button>
            </div>
          )}

          {/* Asset breakdown from onboarding mapping */}
          {(mapping.assets?.length > 0 || mapping.liabilities?.length > 0) && (
            <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
              <h2 className="text-base font-bold text-slate-800 mb-4">📊 Your wealth map</h2>
              <div className="grid md:grid-cols-2 gap-6">
                {mapping.assets?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[2px] text-slate-400 mb-3">Assets</p>
                    <div className="space-y-2">
                      {mapping.assets.map((a, i) => (
                        <div key={i} className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-2.5 border border-slate-100">
                          <p className="text-sm font-semibold text-slate-700 truncate">{a.name}</p>
                          <p className="text-sm font-black shrink-0 ml-2" style={{ color: NAVY }}>{fmt(a.value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {mapping.liabilities?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[2px] text-slate-400 mb-3">Liabilities</p>
                    <div className="space-y-2">
                      {mapping.liabilities.map((l, i) => (
                        <div key={i} className="flex items-center justify-between bg-rose-50 rounded-xl px-4 py-2.5 border border-rose-100">
                          <p className="text-sm font-semibold text-slate-700 truncate">{l.name}</p>
                          <p className="text-sm font-black text-rose-600 shrink-0 ml-2">{fmt(l.value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Actions + next steps ──────────────────────────────────── */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-5">

          {/* Import CTA */}
          <div className="rounded-2xl p-5 border shadow-sm" style={{ background: `${NAVY}08`, borderColor: `${NAVY}22` }}>
            <div className="flex items-start gap-4 mb-4">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${NAVY}15` }}>
                <Upload size={20} style={{ color: NAVY }} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800">Import Bank Statement</h3>
                <p className="text-xs text-slate-500 mt-0.5 leading-snug">Drop a PDF or CSV — AI reads, categorises, you approve</p>
              </div>
            </div>
            <button onClick={onStartImport}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 text-white text-sm font-bold rounded-xl transition-colors shadow-sm"
              style={{ background: NAVY }}
              onMouseEnter={e => e.target.style.background = '#1F344F'}
              onMouseLeave={e => e.target.style.background = NAVY}>
              <FileText size={15} /> Start New Import
            </button>
          </div>

          {/* Next steps */}
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800 mb-4">🗺️ Your path forward</h2>
            <div className="space-y-2.5">
              {[
                { step: 1, title: 'Categorise & Approve', desc: 'AI categorises each row — you approve before saving', nav: 'import', color: NAVY },
                { step: 2, title: 'Set Budget Limits',    desc: 'Monthly limits per category — Ledger flags overages', nav: 'budgets', color: SAGE },
                { step: 3, title: 'Review Insights',      desc: 'Track net worth growth and deep analytics', nav: 'wealth', color: '#7C6A8A' },
              ].map(({ step, title, desc, nav, color }) => (
                <div key={step} className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 bg-slate-50 hover:bg-slate-100 transition-colors group cursor-pointer"
                  onClick={() => onNavigate?.(nav)}>
                  <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-white text-[10px] font-black"
                    style={{ background: color }}>
                    {step}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-slate-800">{title}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
                  </div>
                  <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-500 shrink-0 mt-0.5 transition-colors" />
                </div>
              ))}
            </div>
          </div>

          {/* Income vs goals snapshot (if income data available) */}
          {inc > 0 && totalMonthlyTarget > 0 && (
            <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
              <h2 className="text-sm font-bold text-slate-800 mb-4">💰 Monthly allocation</h2>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Monthly income</span>
                  <span className="font-bold text-slate-800">{fmt(inc)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Towards goals</span>
                  <span className="font-bold" style={{ color: SAGE }}>{fmt(totalMonthlyTarget)}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div className="h-2.5 rounded-full transition-all" style={{ width: `${Math.min(100, Math.round((totalMonthlyTarget / inc) * 100))}%`, background: SAGE }} />
                </div>
                <p className="text-[10px] text-slate-400">
                  {Math.round((totalMonthlyTarget / inc) * 100)}% of income allocated to goals
                </p>
              </div>
            </div>
          )}

          {/* Money lent — only when DB data present */}
          {lentItems.length > 0 && (
            <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
              <h2 className="text-sm font-bold text-slate-800 mb-4">🤝 Interest Forecast</h2>
              <div className="space-y-3">
                {lentItems.map((l, i) => {
                  const lentDate = l.lent_date ? new Date(l.lent_date) : null;
                  const daysElapsed = lentDate ? Math.max(0, Math.floor((today - lentDate) / 86400000)) : null;
                  const accrued = lentDate ? (l.balance * (l.interest_rate / 100) * daysElapsed / 365) : null;
                  return (
                    <div key={i} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-bold text-slate-800">{l.name}</span>
                        <span className="text-xs font-bold px-2 py-0.5 rounded-lg" style={{ color: NAVY, background: `${NAVY}10` }}>
                          {l.interest_rate}% p.a.
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <p className="text-slate-400 mb-0.5">Principal</p>
                          <p className="font-bold text-slate-700">{fmt(l.balance)}</p>
                        </div>
                        {accrued !== null && (
                          <div>
                            <p className="text-slate-400 mb-0.5">Accrued ({daysElapsed}d)</p>
                            <p className="font-bold" style={{ color: SAGE }}>{fmt(accrued)}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div className="flex justify-between items-center pt-2 border-t border-slate-100">
                  <span className="text-xs text-slate-500 font-medium">Total annual interest</span>
                  <span className="font-bold text-sm" style={{ color: SAGE }}>{fmt(totalAnnualInterest)}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Goal projection modal */}
      <AnimatePresence>
        {selectedGoal && (
          <GoalProjectionModal goal={selectedGoal} onClose={() => setSelectedGoal(null)} userAge={parseInt(profile.age) || 30} />
        )}
      </AnimatePresence>
    </div>
  );
}
