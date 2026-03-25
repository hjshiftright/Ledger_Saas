import React, { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import {
  TrendingUp, TrendingDown, Wallet, PieChart as PieIcon, Target,
  BarChart2, Zap, ShieldCheck, Leaf, ArrowUpRight, ArrowDownRight,
  RefreshCw, AlertTriangle, CheckCircle, IndianRupee, Sparkles,
  ChevronRight, Activity, CreditCard, Flame, Clock,
} from 'lucide-react'
import { API } from './api'
import ReportsPage from './ReportsPage'

// ─── Formatters ───────────────────────────────────────────────────────────────

const fmt = (v) => {
  const n = parseFloat(v) || 0
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)}Cr`
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(2)}L`
  if (n >= 1_000) return `₹${(n / 1_000).toFixed(1)}K`
  return '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

const deltaBadge = (v) => `${v > 0 ? '+' : ''}${v}%`

// ─── Color constants ──────────────────────────────────────────────────────────

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16']
const DOMAIN_COLORS = {
  'Cash & Bank': '#22c55e', 'Equities': '#6366f1', 'Mutual Funds': '#8b5cf6',
  'Fixed Deposits': '#06b6d4', 'Provident Funds': '#f59e0b', 'Real Estate': '#ef4444',
  'Gold & Commodities': '#f97316', 'Foreign Assets': '#14b8a6', 'Other Assets': '#94a3b8',
}
const IDEAL_ALLOC = {
  'Cash & Bank': 10, 'Equities': 30, 'Mutual Funds': 25,
  'Fixed Deposits': 15, 'Provident Funds': 10, 'Gold & Commodities': 5, 'Real Estate': 5,
}

// ─── Shared UI atoms ──────────────────────────────────────────────────────────

function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <RefreshCw size={24} className="animate-spin text-indigo-400" />
    </div>
  )
}

function Empty({ msg = 'No transactions imported yet.' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-slate-400">
      <BarChart2 size={44} className="mb-3 opacity-20" />
      <p className="text-sm font-medium">{msg}</p>
      <p className="text-xs mt-1 text-slate-300">Import transactions to see your dashboards come alive.</p>
    </div>
  )
}

function InsightCard({ icon, color, text }) {
  const map = {
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    rose: 'bg-rose-50 border-rose-200 text-rose-800',
    amber: 'bg-amber-50 border-amber-200 text-amber-800',
    sky: 'bg-sky-50 border-sky-200 text-sky-800',
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-800',
    violet: 'bg-violet-50 border-violet-200 text-violet-800',
  }
  return (
    <div className={`rounded-xl border px-3 py-2.5 flex items-start gap-2.5 ${map[color] ?? map.indigo}`}>
      <span className="text-base shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1 text-xs leading-relaxed">{text}</div>
    </div>
  )
}

function StatCard({ label, value, sub, delta, deltaLabel, icon: Icon, accent = 'indigo', big }) {
  const am = {
    indigo: { bg: 'bg-indigo-50', icon: 'text-indigo-600', val: 'text-indigo-700' },
    emerald: { bg: 'bg-emerald-50', icon: 'text-emerald-600', val: 'text-emerald-700' },
    rose: { bg: 'bg-rose-50', icon: 'text-rose-600', val: 'text-rose-700' },
    amber: { bg: 'bg-amber-50', icon: 'text-amber-600', val: 'text-amber-700' },
    sky: { bg: 'bg-sky-50', icon: 'text-sky-600', val: 'text-sky-700' },
    violet: { bg: 'bg-violet-50', icon: 'text-violet-600', val: 'text-violet-700' },
  }
  const ac = am[accent] ?? am.indigo
  const pos = delta >= 0
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <span className="text-slate-500 text-sm font-medium leading-snug">{label}</span>
        {Icon && <span className={`${ac.bg} ${ac.icon} p-2 rounded-xl`}><Icon size={16} /></span>}
      </div>
      <div className={`font-bold ${big ? 'text-3xl' : 'text-2xl'} ${ac.val} mb-1`}>{value}</div>
      {sub && <div className="text-slate-400 text-xs">{sub}</div>}
      {delta !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs font-semibold ${pos ? 'text-emerald-600' : 'text-rose-500'}`}>
          {pos ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
          {deltaBadge(delta)} {deltaLabel}
        </div>
      )}
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-md px-3 py-2 text-xs">
      <div className="font-medium text-slate-500 mb-1 tracking-wide">{label}</div>
      {payload.map((e, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: e.color }} />
          <span className="text-slate-500">{e.name}:</span>
          <span className="font-medium text-slate-800">{fmt(e.value)}</span>
        </div>
      ))}
    </div>
  )
}

function DashletShell({ emoji, title, badge, badgeColor = 'indigo', children }) {
  const bc = {
    emerald: 'bg-emerald-100 text-emerald-700',
    rose: 'bg-rose-100 text-rose-700',
    amber: 'bg-amber-100 text-amber-700',
    indigo: 'bg-indigo-100 text-indigo-700',
    sky: 'bg-sky-100 text-sky-700',
  }
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{emoji}</span>
        <h3 className="font-bold text-slate-800 flex-1">{title}</h3>
        {badge && <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${bc[badgeColor]}`}>{badge}</span>}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  )
}

function MiniBar({ value, max, color = 'bg-indigo-500' }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// DASHLET COMPONENTS — each receives just its data slice
// ═══════════════════════════════════════════════════════════════════════════════

// ── Survival Runway ──────────────────────────────────────────────────────────

function SurvivalRunwayCard({ d }) {
  const { months, liquid_assets, avg_monthly_expenses, status } = d
  const TARGET = 12
  const pct = Math.min(100, (months / TARGET) * 100)
  const styles = {
    safe: { bar: 'bg-emerald-500', text: 'text-emerald-600', label: '✈️ You\'re cleared for a long flight', badge: 'Safe', bc: 'emerald' },
    warning: { bar: 'bg-amber-500', text: 'text-amber-600', label: '⚠️ Runway is getting short', badge: 'Build up', bc: 'amber' },
    critical: { bar: 'bg-rose-500', text: 'text-rose-600', label: '🚨 Need to grow this urgently', badge: 'Critical', bc: 'rose' },
  }
  const s = styles[status] ?? styles.safe
  return (
    <DashletShell emoji="✈️" title="Survival Runway" badge={s.badge} badgeColor={s.bc}>
      <div className={`text-4xl font-bold ${s.text} mb-1`}>{months}</div>
      <div className="text-slate-500 text-sm mb-1">months you can live without any income</div>
      <div className="text-slate-400 text-xs mb-4">
        {fmt(liquid_assets)} liquid ÷ {fmt(avg_monthly_expenses)}/mo expenses
      </div>
      {/* Runway visual */}
      <div className="relative mb-1">
        <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${s.bar} transition-all duration-700`} style={{ width: `${pct}%` }}>
            <span className="sr-only">{months} months</span>
          </div>
        </div>
        {/* 6-month marker */}
        <div className="absolute top-0 h-full w-0.5 bg-slate-400 opacity-60" style={{ left: `${(6 / TARGET) * 100}%` }} />
      </div>
      <div className="flex justify-between text-xs text-slate-400 mb-4">
        <span>0</span><span className="text-slate-500 font-medium">6mo min</span><span>12 months</span>
      </div>
      <InsightCard icon={status === 'safe' ? '🛡️' : '💡'} color={status === 'safe' ? 'emerald' : 'amber'}
        text={s.label + `. Target: 6 months. To add 1 more month of runway, save ${fmt(avg_monthly_expenses)} extra.`} />
    </DashletShell>
  )
}

// ── Wealth Velocity ───────────────────────────────────────────────────────────

function WealthVelocityCard({ d }) {
  const { paise_per_rupee, nw_growth_12m, income_12m } = d
  const val = paise_per_rupee
  const status = val >= 20 ? 'great' : val >= 10 ? 'good' : val >= 0 ? 'low' : 'negative'
  const styles = {
    great: { color: '#22c55e', text: 'text-emerald-600', msg: 'Excellent velocity! You\'re building real wealth.' },
    good: { color: '#f59e0b', text: 'text-amber-600', msg: 'Decent! Aim for ₹20 per ₹100 to fast-track your goals.' },
    low: { color: '#ef4444', text: 'text-rose-600', msg: 'Low velocity. A small cut in lifestyle spend can 2× this.' },
    negative: { color: '#ef4444', text: 'text-rose-600', msg: 'Your wealth shrank this year. Time to course-correct.' },
  }
  const s = styles[status]
  const pct = Math.min(100, Math.max(0, val * 2))
  const gaugeData = [{ value: pct }, { value: 100 - pct }]
  return (
    <DashletShell emoji="🚀" title="Wealth Velocity">
      <div className="flex flex-col items-center">
        <div className="relative w-48 h-24 mb-2">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={gaugeData} cx="50%" cy="100%" startAngle={180} endAngle={0}
                innerRadius={52} outerRadius={80} dataKey="value" paddingAngle={1}>
                <Cell fill={s.color} />
                <Cell fill="#f1f5f9" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute bottom-0 inset-x-0 flex flex-col items-center">
            <span className={`text-2xl font-bold ${s.text}`}>₹{val}</span>
            <span className="text-xs text-slate-400">per ₹100 earned</span>
          </div>
        </div>
        <p className="text-sm text-slate-600 text-center mb-3">{s.msg}</p>
        <div className="w-full grid grid-cols-2 gap-2 text-center">
          <div className="bg-indigo-50 rounded-xl p-3">
            <div className="text-indigo-700 font-bold text-sm">{fmt(income_12m)}</div>
            <div className="text-indigo-400 text-xs">Earned (12m)</div>
          </div>
          <div className={`rounded-xl p-3 ${nw_growth_12m >= 0 ? 'bg-emerald-50' : 'bg-rose-50'}`}>
            <div className={`font-bold text-sm ${nw_growth_12m >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
              {nw_growth_12m >= 0 ? '+' : ''}{fmt(nw_growth_12m)}
            </div>
            <div className={`text-xs ${nw_growth_12m >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>Wealth gained</div>
          </div>
        </div>
      </div>
    </DashletShell>
  )
}

// ── Lazy Money Auditor ────────────────────────────────────────────────────────

function LazyMoneyCard({ d }) {
  const { lazy_amount, safety_buffer, liquid_assets, annual_inflation_loss } = d
  const hasLazy = lazy_amount > 0
  return (
    <DashletShell emoji="😴" title="Lazy Money Auditor"
      badge={hasLazy ? `Losing ${fmt(annual_inflation_loss)}/yr` : 'Optimised!'}
      badgeColor={hasLazy ? 'rose' : 'emerald'}>
      {hasLazy ? (
        <>
          <div className="text-3xl font-semibold text-amber-600 mb-1">{fmt(lazy_amount)}</div>
          <div className="text-slate-500 text-sm mb-1">sitting idle — doing nothing for you</div>
          <div className="text-slate-400 text-xs mb-4">
            Your liquid cash: {fmt(liquid_assets)} · Safety buffer needed: {fmt(safety_buffer)}
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-1">
            <div className="h-full bg-amber-400 rounded-full" style={{ width: `${Math.min(100, lazy_amount / liquid_assets * 100)}%` }} />
          </div>
          <p className="text-xs text-slate-400 mb-4">{Math.round(lazy_amount / liquid_assets * 100)}% of your liquid cash is idle</p>
          <InsightCard icon="💡" color="sky"
            text={`Moving ${fmt(lazy_amount)} to a mutual fund at 10% p.a. could earn you ${fmt(lazy_amount * 0.10)} extra per year instead of losing ${fmt(annual_inflation_loss)} to inflation.`} />
        </>
      ) : (
        <InsightCard icon="🏆" color="emerald"
          text="No lazy money detected! You've put your savings to work well. Review annually to keep it that way." />
      )}
    </DashletShell>
  )
}

// ── Passive Orchard ───────────────────────────────────────────────────────────

function PassiveOrchardCard({ d }) {
  const { monthly_investment_income, avg_monthly_expenses, coverage_pct } = d
  const BILLS = [
    { name: 'Internet', cost: 700 },
    { name: 'Electricity', cost: 1500 },
    { name: 'Groceries', cost: 5000 },
    { name: 'Fuel', cost: 3000 },
    { name: 'Rent/EMI', cost: avg_monthly_expenses * 0.30 },
  ]
  let rem = monthly_investment_income
  const covered = BILLS.filter(b => { if (rem >= b.cost) { rem -= b.cost; return true } return false })
  return (
    <DashletShell emoji="🌳" title="Passive Orchard"
      badge={coverage_pct > 0 ? `${coverage_pct}% covered` : 'Plant seeds!'}
      badgeColor={coverage_pct >= 50 ? 'emerald' : coverage_pct > 0 ? 'amber' : 'indigo'}>
      {monthly_investment_income > 0 ? (
        <>
          <div className="text-3xl font-semibold text-emerald-600 mb-1">{fmt(monthly_investment_income)}</div>
          <div className="text-slate-500 text-sm mb-3">your investments earn for you each month</div>
          <div className="mb-1">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Monthly expense coverage</span>
              <span className="font-bold text-emerald-600">{coverage_pct}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-700"
                style={{ width: `${Math.min(100, coverage_pct)}%` }} />
            </div>
          </div>
          {covered.length > 0 && (
            <p className="text-xs text-emerald-600 font-medium mt-2 mb-3">
              🍎 Pays for: {covered.map(b => b.name).join(' · ')}
            </p>
          )}
          <InsightCard icon="🎯" color="emerald"
            text={covered.length > 0
              ? `Your investments cover ${covered.map(b => b.name).join(', ')} every month. Next target: cover one more bill!`
              : `You're on your way! At current growth, your passive income will cover your internet bill soon.`} />
        </>
      ) : (
        <>
          <div className="text-3xl font-semibold text-slate-300 mb-3">₹0</div>
          <InsightCard icon="🌱" color="sky"
            text="Plant your first seeds! Invest in dividend funds to start earning passive income that pays your bills for free." />
        </>
      )}
    </DashletShell>
  )
}

// ── Debt Snowball ─────────────────────────────────────────────────────────────

function DebtSnowballCard({ d }) {
  const { debts, total_debt, monthly_int_total } = d
  if (!debts.length) {
    return (
      <DashletShell emoji="🏆" title="Debt Snowball" badge="Debt Free!" badgeColor="emerald">
        <InsightCard icon="🎉" color="emerald"
          text="Zero liabilities! You owe nothing to anyone. That's a rare achievement — protect it." />
      </DashletShell>
    )
  }
  const rateColor = (r) => r >= 24 ? 'rose' : r >= 12 ? 'amber' : 'sky'
  const rateStyle = { rose: 'border-rose-200 bg-rose-50', amber: 'border-amber-200 bg-amber-50', sky: 'border-sky-200 bg-sky-50' }
  const rateText = { rose: 'text-rose-700', amber: 'text-amber-700', sky: 'text-sky-700' }
  return (
    <DashletShell emoji="❄️" title="Debt Snowball" badge={`₹${Math.round(monthly_int_total).toLocaleString()}/mo interest`} badgeColor="rose">
      <p className="text-slate-500 text-sm mb-4">Pay the costliest debt first. Then roll the freed-up cash onto the next one — like a snowball.</p>
      <div className="space-y-2 mb-4">
        {debts.slice(0, 4).map((debt, i) => {
          const rc = rateColor(debt.annual_rate)
          return (
            <div key={i} className={`rounded-xl border p-3 ${rateStyle[rc]}`}>
              <div className="flex justify-between items-start">
                <div>
                  <div className={`font-semibold text-sm ${rateText[rc]}`}>{debt.name}</div>
                  <div className="text-xs text-slate-400">{debt.annual_rate}% p.a. · {fmt(debt.monthly_int)}/mo interest</div>
                </div>
                <div className="text-right">
                  <div className={`font-bold ${rateText[rc]}`}>{fmt(debt.balance)}</div>
                  {i === 0 && <div className="text-xs text-rose-600 font-semibold">Kill first ☠️</div>}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <InsightCard icon="💸" color="rose"
        text={`You're paying ${fmt(monthly_int_total)}/month just in interest on ${fmt(total_debt)} total debt. Every extra rupee toward your highest-rate debt saves money instantly.`} />
    </DashletShell>
  )
}

// ── Freedom Clock ─────────────────────────────────────────────────────────────

function FreedomClockCard({ d, hero = false }) {
  const { fire_number, current_net_worth, monthly_savings, fire_date, progress_pct } = d
  const achieved = progress_pct >= 100
  const fireFormatted = fire_date
    ? (() => { try { return new Date(fire_date + '-01').toLocaleDateString('en-IN', { year: 'numeric', month: 'long' }) } catch { return fire_date } })()
    : null

  return (
    <div className={`bg-white rounded-2xl border border-slate-100 p-6 ${hero ? 'shadow-md' : 'shadow-sm'}`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">🕊️</span>
        <div>
          <h3 className={`font-bold text-slate-800 ${hero ? 'text-xl' : 'text-base'}`}>Freedom Clock</h3>
          <p className="text-slate-400 text-xs">work becomes optional when…</p>
        </div>
        {!achieved && progress_pct > 0 && (
          <span className="ml-auto bg-indigo-50 text-indigo-600 text-xs font-bold px-2.5 py-1 rounded-full">{progress_pct}% there</span>
        )}
      </div>
      {achieved ? (
        <div className="text-center py-4">
          <div className="text-5xl mb-3">🎉</div>
          <div className="text-xl font-bold text-emerald-700">You're already free!</div>
          <div className="text-slate-500 text-sm mt-1">Net worth covers 25× annual expenses. Work is now a choice.</div>
        </div>
      ) : (
        <>
          <div className={`${hero ? 'text-4xl' : 'text-2xl'} font-bold text-slate-900 mb-1`}>
            {fireFormatted ?? '—'}
          </div>
          <div className="text-slate-500 text-sm mb-5">
            {monthly_savings > 0 ? `Saving ${fmt(monthly_savings)}/mo · ${fmt(fire_number)} is the finish line` : 'Start saving consistently to unlock your date'}
          </div>
          <div className="mb-4">
            <div className="flex justify-between text-xs text-slate-400 mb-1.5">
              <span>{fmt(current_net_worth)} today</span>
              <span>Goal: {fmt(fire_number)}</span>
            </div>
            <div className="h-3 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700"
                style={{ width: `${Math.min(100, progress_pct)}%` }} />
            </div>
          </div>
          {monthly_savings > 5000 && (
            <div className="bg-indigo-50 rounded-xl px-4 py-3 text-sm text-indigo-700">
              💡 Saving ₹5,000 more/month moves your freedom date forward by ~{Math.max(1, Math.round((fire_number - current_net_worth) / (monthly_savings + 5000) / 12 * 0.15))} months
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Lifestyle Creep ───────────────────────────────────────────────────────────

function LifestyleCreepCard({ d, monthly }) {
  const { income_growth_pct: incG, expense_growth_pct: expG, creep_detected } = d
  const diff = (expG - incG).toFixed(1)
  return (
    <DashletShell emoji="🕵️" title="Lifestyle Creep Detector"
      badge={creep_detected ? '⚠️ Detected' : '✅ In Check'}
      badgeColor={creep_detected ? 'rose' : 'emerald'}>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="text-center p-4 rounded-xl bg-emerald-50">
          <div className="text-xs text-emerald-600 font-medium mb-1">Income growing</div>
          <div className="text-2xl font-bold text-emerald-700">{incG >= 0 ? '+' : ''}{incG}%</div>
        </div>
        <div className="text-center p-4 rounded-xl bg-rose-50">
          <div className="text-xs text-rose-600 font-medium mb-1">Expenses growing</div>
          <div className="text-2xl font-bold text-rose-700">{expG >= 0 ? '+' : ''}{expG}%</div>
        </div>
      </div>
      {monthly && monthly.length > 3 && (
        <div className="mb-4">
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={monthly} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
              <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <YAxis hide />
              <Tooltip content={<ChartTooltip />} />
              <Line type="monotone" dataKey="income" name="Income" stroke="#22c55e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="expenses" name="Expenses" stroke="#f43f5e" strokeWidth={2} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      <InsightCard icon={creep_detected ? '🚨' : '🧘'} color={creep_detected ? 'rose' : 'emerald'}
        text={creep_detected
          ? `Expenses are growing ${diff}pts faster than income. Lifestyle creep is silently shrinking what you keep.`
          : `Great discipline! Your income is growing at ${incG}% while expenses at ${expG}%. The gap is healthy.`} />
    </DashletShell>
  )
}

// ── Guilt-Free Spend Zone ─────────────────────────────────────────────────────

function GuiltFreeSpendCard({ d }) {
  const { fun_budget, avg_monthly_income, current_month_spent, current_month_income, estimated_fixed } = d
  const spentFrac = avg_monthly_income > 0 ? current_month_spent / avg_monthly_income * 100 : 0
  const light = spentFrac < 70 ? 'green' : spentFrac < 90 ? 'amber' : 'red'
  return (
    <DashletShell emoji="🟢" title="Guilt-Free Spend Zone"
      badge={light === 'green' ? 'Spend freely!' : light === 'amber' ? 'Slow down' : 'Stop!'}
      badgeColor={light === 'green' ? 'emerald' : light === 'amber' ? 'amber' : 'rose'}>
      <div className={`text-3xl font-semibold mb-1 ${light === 'green' ? 'text-emerald-600' : light === 'amber' ? 'text-amber-600' : 'text-rose-600'}`}>
        {fmt(fun_budget)}
      </div>
      <div className="text-slate-500 text-sm mb-4">is 100% guilt-free to spend this month</div>

      {/* Traffic light */}
      <div className="flex items-center gap-3 mb-4 p-3 bg-slate-50 rounded-xl">
        <div className={`w-5 h-5 rounded-full shrink-0 ${light === 'green' ? 'bg-emerald-500 shadow-lg shadow-emerald-300' : 'bg-slate-200'}`} />
        <div className={`w-5 h-5 rounded-full shrink-0 ${light === 'amber' ? 'bg-amber-500 shadow-lg shadow-amber-300' : 'bg-slate-200'}`} />
        <div className={`w-5 h-5 rounded-full shrink-0 ${light === 'red' ? 'bg-rose-500 shadow-lg shadow-rose-300' : 'bg-slate-200'}`} />
        <span className="text-sm text-slate-600 font-medium ml-1">
          {light === 'green' ? 'You\'re in the green zone' : light === 'amber' ? 'Approaching limit' : 'Budget exceeded'}
        </span>
      </div>

      <div className="text-xs text-slate-400 mb-3">
        This month: earned {fmt(current_month_income)} · spent {fmt(current_month_spent)}
        · fixed costs ~{fmt(estimated_fixed)}/mo
      </div>
      <InsightCard icon={light === 'green' ? '🎉' : '⚠️'} color={light === 'green' ? 'emerald' : 'amber'}
        text={light === 'green'
          ? `Spending ${fmt(fun_budget)} won't hurt any of your savings goals. Enjoy it!`
          : `You've spent ${fmt(current_month_spent)} this month. Consider pausing discretionary purchases.`} />
    </DashletShell>
  )
}

// ── Inflation Ghost ───────────────────────────────────────────────────────────

function InflationGhostCard({ d }) {
  let { current_monthly, in_5_years, in_10_years, in_20_years, inflation_rate_pct } = d

  const isHypothetical = !current_monthly || current_monthly === 0
  if (isHypothetical) {
    current_monthly = 100
    const r = (inflation_rate_pct || 6) / 100
    in_5_years = current_monthly * Math.pow(1 + r, 5)
    in_10_years = current_monthly * Math.pow(1 + r, 10)
    in_20_years = current_monthly * Math.pow(1 + r, 20)
  }

  const bars = [
    { year: 'Today', amount: current_monthly, color: '#6366f1' },
    { year: '5 yrs', amount: in_5_years, color: '#8b5cf6' },
    { year: '10 yrs', amount: in_10_years, color: '#a855f7' },
    { year: '20 yrs', amount: in_20_years, color: '#d946ef' },
  ]
  const max = in_20_years
  return (
    <DashletShell emoji="👻" title="Inflation Ghost" badge={`${inflation_rate_pct}% p.a.`} badgeColor="violet">
      <p className="text-slate-500 text-sm mb-5">
        The silent thief. Your ₹1 today buys less every year — here's what your current lifestyle costs in the future.
      </p>
      <div className="space-y-3 mb-4">
        {bars.map((b, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-14 text-xs text-slate-500 font-medium shrink-0">{b.year}</div>
            <div className="flex-1 h-8 bg-slate-100 rounded-lg overflow-hidden relative">
              <div className="h-full rounded-lg transition-all duration-700 flex items-center px-3"
                style={{ width: `${Math.min(100, (b.amount / max) * 100)}%`, background: b.color, opacity: 1 - i * 0.12 }}>
                <span className="text-xs font-medium text-white whitespace-nowrap">{fmt(b.amount)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      <InsightCard icon="🧮" color="violet"
        text={isHypothetical
          ? `Because no expense data is found, here's how inflation eats ₹100. In 10 years, you'll need ${fmt(in_10_years)} to equal ₹100 today.`
          : `To maintain today's ${fmt(current_monthly)}/month lifestyle in 10 years, you'll need ${fmt(in_10_years)}/month. Increase SIPs by ${inflation_rate_pct}% annually to stay ahead.`} />
    </DashletShell>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 1 — NET ASSET VALUE
// ═══════════════════════════════════════════════════════════════════════════════

function NavTab({ liData, liLoading, showAdvanced, onToggleAdvanced }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [months, setMonths] = useState(12)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await API.reports.navDashboard({ months })) }
    catch { setData(null) }
    finally { setLoading(false) }
  }, [months])

  useEffect(() => { load() }, [load])

  if (loading) return <Spinner />
  if (!data) return <Empty />

  const nw = data.net_worth
  const assets = data.total_assets
  const liabs = data.total_liabilities
  const liquid = data.liquidity.liquid
  const liqPct = assets > 0 ? Math.round(liquid / assets * 100) : 0
  const debtR = assets > 0 ? Math.round(liabs / assets * 100) : 0

  const insights = []
  if (nw > 0 && data.nw_change_pct > 0)
    insights.push({ icon: '🚀', color: 'emerald', text: `Your wealth grew by ${fmt(data.nw_change)} (${deltaBadge(data.nw_change_pct)}) in the last period. Keep the momentum!` })
  if (debtR > 40)
    insights.push({ icon: '⚠️', color: 'rose', text: `${debtR}% of your assets are financed by debt. Bringing this below 30% will meaningfully improve your financial health.` })
  if (liqPct < 10)
    insights.push({ icon: '💧', color: 'amber', text: `Only ${liqPct}% of your wealth is quickly accessible. Keep at least 6 months of expenses in liquid form.` })
  if (insights.length === 0)
    insights.push({ icon: '✅', color: 'emerald', text: 'Your net asset position looks solid. Keep monitoring monthly and stay consistent.' })

  return (
    <div className="space-y-8">
      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Your Net Worth" value={fmt(nw)} sub="Assets minus what you owe"
          delta={data.nw_change_pct} deltaLabel="last month" icon={TrendingUp}
          accent={nw >= 0 ? 'emerald' : 'rose'} big />
        <StatCard label="Total Assets" value={fmt(assets)} sub="Everything you own" icon={Wallet} accent="indigo" />
        <StatCard label="Total Liabilities" value={fmt(liabs)} sub="Everything you owe" icon={CreditCard} accent="rose" />
        <StatCard label="Liquid Cash" value={fmt(liquid)} sub={`${liqPct}% of assets instantly accessible`} icon={ShieldCheck} accent="emerald" />
      </div>

      {/* Wealth trend */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-slate-800">Your wealth over time 📈</h3>
            <p className="text-slate-500 text-sm">Watching this line go up is the whole point</p>
          </div>
          <select value={months} onChange={e => setMonths(Number(e.target.value))}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-600">
            {[6, 12, 24, 36].map(m => <option key={m} value={m}>{m} months</option>)}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data.history} margin={{ top: 5, right: 10, bottom: 0, left: 10 }}>
            <defs>
              <linearGradient id="nwGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="assetGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} width={70} />
            <Tooltip content={<ChartTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="total_assets" name="Assets" stroke="#22c55e" fill="url(#assetGrad)" strokeWidth={2} dot={false} />
            <Area type="monotone" dataKey="net_worth" name="Net Worth" stroke="#6366f1" fill="url(#nwGrad)" strokeWidth={2.5} dot={false} />
            <Area type="monotone" dataKey="total_liabilities" name="Liabilities" stroke="#f43f5e" fill="none" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Dashlets row 1: Survival Runway + Wealth Velocity */}
      {!liLoading && liData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SurvivalRunwayCard d={liData.survival_runway} />
          <WealthVelocityCard d={liData.wealth_velocity} />
        </div>
      )}

      {/* Asset distribution + liquid vs locked */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Asset donut */}
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">What you own 🏦</h3>
          <p className="text-slate-500 text-sm mb-4">Every asset you have, broken down</p>
          {data.asset_distribution.length === 0 ? <Empty msg="No asset accounts found." /> : (
            <div className="flex gap-6 items-center">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie data={data.asset_distribution} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}>
                    {data.asset_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={fmt} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2 min-w-0">
                {data.asset_distribution.slice(0, 6).map((item, i) => (
                  <div key={i} className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-xs text-slate-600 truncate">{item.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-xs font-mono font-semibold text-slate-800">{fmt(item.value)}</span>
                      <span className="text-xs text-slate-400">{item.percent}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Liquid vs locked */}
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm space-y-5">
          <div>
            <h3 className="text-base font-bold text-slate-800 mb-1">Liquid vs locked-in 💧</h3>
            <p className="text-slate-500 text-sm mb-4">How quickly can you access your money in an emergency?</p>
            <div className="flex gap-4 mb-3">
              <div className="flex-1 bg-emerald-50 rounded-xl p-3 text-center">
                <div className="text-emerald-600 text-xs font-semibold">Ready to use 💧</div>
                <div className="text-emerald-700 font-bold text-xl mt-1">{fmt(liquid)}</div>
                <div className="text-emerald-500 text-xs">{liqPct}% of assets</div>
              </div>
              <div className="flex-1 bg-slate-50 rounded-xl p-3 text-center">
                <div className="text-slate-600 text-xs font-semibold">Locked away 🔒</div>
                <div className="text-slate-700 font-bold text-xl mt-1">{fmt(data.liquidity.illiquid)}</div>
                <div className="text-slate-400 text-xs">{100 - liqPct}% of assets</div>
              </div>
            </div>
            <MiniBar value={liqPct} max={100} color="bg-emerald-400" />
          </div>
          {data.liability_distribution.length > 0 && (
            <div>
              <h4 className="text-sm font-bold text-slate-700 mb-3">What you owe</h4>
              <div className="space-y-2">
                {data.liability_distribution.slice(0, 4).map((item, i) => (
                  <div key={i} className="flex items-center justify-between gap-2">
                    <span className="text-xs text-slate-600 truncate">{item.name}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-rose-400 rounded-full" style={{ width: `${item.percent}%` }} />
                      </div>
                      <span className="text-xs font-mono font-semibold text-rose-700">{fmt(item.value)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Dashlets row 2: Lazy Money + Passive Orchard */}
      {!liLoading && liData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LazyMoneyCard d={liData.lazy_money} />
          <PassiveOrchardCard d={liData.passive_orchard} />
        </div>
      )}

      {/* Debt Snowball — full width */}
      {!liLoading && liData && (
        <DebtSnowballCard d={liData.debt_snowball} />
      )}

      {/* Insights */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={16} className="text-indigo-500" />
          <h3 className="text-base font-bold text-slate-800">What this means for you</h3>
        </div>
        <div className="space-y-3">
          {insights.map((ins, i) => <InsightCard key={i} {...ins} />)}
        </div>
      </div>

      {/* Advanced toggle */}
      <button onClick={onToggleAdvanced}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-dashed border-slate-300 text-slate-500 text-sm hover:border-indigo-400 hover:text-indigo-600 transition-colors">
        <BarChart2 size={15} />
        {showAdvanced ? 'Hide' : 'Show'} advanced reports — balance sheet, trial balance &amp; more
        <ChevronRight size={14} className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
      </button>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 2 — CASH FLOW
// ═══════════════════════════════════════════════════════════════════════════════

function CashFlowTab({ liData, liLoading, showAdvanced, onToggleAdvanced }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [months, setMonths] = useState(12)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await API.reports.cashFlowDashboard({ months })) }
    catch { setData(null) }
    finally { setLoading(false) }
  }, [months])

  useEffect(() => { load() }, [load])

  if (loading) return <Spinner />
  if (!data) return <Empty />

  const cur = data.current_month
  const surplus = cur.income - cur.expenses
  const savR = cur.income > 0 ? Math.round(surplus / cur.income * 100) : 0
  const nzInc = data.monthly.filter(m => m.income > 0)
  const avgSavR = nzInc.length > 0
    ? Math.round(nzInc.reduce((a, m) => a + m.savings_rate, 0) / nzInc.length) : 0

  const insights = []
  if (savR >= 30) insights.push({ icon: '🌟', color: 'emerald', text: `You're saving ${savR}% this month — that's gold-standard territory. The 30% benchmark is what separates those who build wealth from those who just earn it.` })
  else if (savR >= 15) insights.push({ icon: '👍', color: 'sky', text: `You're saving ${savR}% of your income. Solid! Push for 30% to accelerate your freedom date.` })
  else if (cur.income > 0) insights.push({ icon: '⚡', color: 'amber', text: `Only ${savR}% saved this month. Even cutting one subscription or dining-out trip per week can push this above 20%.` })
  if (surplus < 0) insights.push({ icon: '🚨', color: 'rose', text: `Spent ${fmt(Math.abs(surplus))} more than earned this month. Look at your top 3 expense categories for quick wins.` })
  if (cur.expense_categories.length > 0) {
    const top = cur.expense_categories[0]
    insights.push({ icon: '🔍', color: 'indigo', text: `"${top.name}" is your biggest spend at ${fmt(top.amount)} this month. Is that aligned with what matters most to you?` })
  }

  return (
    <div className="space-y-8">
      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Money In" value={fmt(cur.income)} sub="Income this month" icon={TrendingUp} accent="emerald" />
        <StatCard label="Money Out" value={fmt(cur.expenses)} sub="Spending this month" icon={TrendingDown} accent="rose" />
        <StatCard label="Left Over" value={fmt(surplus)} sub="Your monthly surplus" icon={Wallet} accent={surplus >= 0 ? 'indigo' : 'rose'} big />
        <StatCard label="Savings Rate" value={`${savR}%`} sub={`Avg: ${avgSavR}% over ${months}m`} icon={Activity}
          accent={savR >= 20 ? 'emerald' : savR >= 10 ? 'amber' : 'rose'} />
      </div>

      {/* Monthly bar chart */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-slate-800">Money in vs money out 📊</h3>
            <p className="text-slate-500 text-sm">When green is taller than red, you're winning</p>
          </div>
          <select value={months} onChange={e => setMonths(Number(e.target.value))}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-600">
            {[6, 12, 24].map(m => <option key={m} value={m}>{m} months</option>)}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.monthly} margin={{ top: 5, right: 10, bottom: 0, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} width={65} />
            <Tooltip content={<ChartTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="income" name="Income" fill="#22c55e" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expenses" name="Expenses" fill="#f43f5e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Freedom Clock — hero dashlet */}
      {!liLoading && liData && (
        <FreedomClockCard d={liData.fire_clock} hero />
      )}

      {/* Savings rate + expense breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">Your savings habit 💪</h3>
          <p className="text-slate-500 text-sm mb-4">Aim to keep this above 20% every month</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.monthly.filter(m => m.income > 0)} margin={{ top: 5, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip formatter={v => `${v}%`} content={({ active, payload, label: l }) => {
                if (!active || !payload?.length) return null
                return (
                  <div className="bg-white border border-slate-200 rounded-xl shadow px-3 py-2 text-xs">
                    <div className="font-semibold mb-1">{l}</div>
                    <div>Savings rate: <span className="font-mono font-bold text-indigo-700">{payload[0]?.value}%</span></div>
                  </div>
                )
              }} />
              <Line type="monotone" dataKey="savings_rate" name="Savings Rate" stroke="#6366f1" strokeWidth={2.5}
                dot={{ fill: '#6366f1', r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">Where your money goes 🛍️</h3>
          <p className="text-slate-500 text-sm mb-4">Top expense categories this month</p>
          {cur.expense_categories.length === 0 ? <Empty msg="No expenses this month yet." /> : (
            <div className="space-y-3">
              {cur.expense_categories.slice(0, 6).map((cat, i) => {
                const p = cur.expenses > 0 ? Math.round(cat.amount / cur.expenses * 100) : 0
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-700 truncate">{cat.name}</span>
                        <span className="font-mono font-semibold text-slate-800 shrink-0 ml-2">{fmt(cat.amount)}</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${p}%`, background: COLORS[i % COLORS.length] }} />
                      </div>
                    </div>
                    <span className="text-xs text-slate-400 w-8 text-right shrink-0">{p}%</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Dashlets row: Lifestyle Creep + Guilt-Free Spend */}
      {!liLoading && liData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LifestyleCreepCard d={liData.lifestyle_creep} monthly={liData.monthly} />
          <GuiltFreeSpendCard d={liData.guilt_free_spend} />
        </div>
      )}

      {/* Insights */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={16} className="text-indigo-500" />
          <h3 className="text-base font-bold text-slate-800">The honest picture</h3>
        </div>
        <div className="space-y-3">
          {insights.map((ins, i) => <InsightCard key={i} {...ins} />)}
        </div>
      </div>

      <button onClick={onToggleAdvanced}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-dashed border-slate-300 text-slate-500 text-sm hover:border-indigo-400 hover:text-indigo-600 transition-colors">
        <BarChart2 size={15} />
        {showAdvanced ? 'Hide' : 'Show'} advanced reports — income statement, journal &amp; more
        <ChevronRight size={14} className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
      </button>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 3 — LIFE GOALS (aspirational dashlets from Phase 3–4 docs)
// ═══════════════════════════════════════════════════════════════════════════════

function LifeGoalsTab({ liData, liLoading }) {
  if (liLoading) return <Spinner />
  if (!liData) return <Empty />

  const { fire_clock, survival_runway, inflation_ghost, debt_snowball, lifestyle_creep, guilt_free_spend, monthly } = liData

  // Subscription bin — estimate recurring spends using 10yr projection from guilt_free_spend data
  const monthlyFixed = guilt_free_spend.estimated_fixed
  const subBin10yr = Math.round(monthlyFixed * 120)

  // Overall life score (0-100) based on key metrics
  const scores = [
    survival_runway.months >= 6 ? 25 : survival_runway.months >= 3 ? 15 : 5,
    fire_clock.progress_pct * 0.25,
    !lifestyle_creep.creep_detected ? 25 : 10,
    debt_snowball.total_debt === 0 ? 25 : Math.max(0, 25 - (debt_snowball.total_debt / 500000) * 5),
  ]
  const lifeScore = Math.min(100, Math.round(scores.reduce((a, b) => a + b, 0)))
  const scoreEmoji = lifeScore >= 70 ? '🌟' : lifeScore >= 40 ? '📈' : '🚧'

  return (
    <div className="space-y-8">

      {/* Life Score hero — clean white card with score ring */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-start gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">{scoreEmoji}</span>
              <h2 className="text-xl font-black text-slate-800">Financial Life Score</h2>
            </div>
            <p className="text-slate-500 text-sm mb-5">Based on runway, FIRE progress, debt &amp; spending discipline</p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="w-28 text-xs text-slate-500 shrink-0">Emergency Runway</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ${survival_runway.months >= 6 ? 'bg-emerald-500' : survival_runway.months >= 3 ? 'bg-amber-500' : 'bg-rose-500'}`}
                    style={{ width: `${Math.min(100, survival_runway.months / 12 * 100)}%` }} />
                </div>
                <span className="text-xs font-semibold text-slate-700 w-16 text-right shrink-0">{survival_runway.months}mo runway</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-28 text-xs text-slate-500 shrink-0">FIRE Progress</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-indigo-500 transition-all duration-700" style={{ width: `${Math.min(100, fire_clock.progress_pct)}%` }} />
                </div>
                <span className="text-xs font-semibold text-slate-700 w-16 text-right shrink-0">{fire_clock.progress_pct}%</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-28 text-xs text-slate-500 shrink-0">Lifestyle Check</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ${!lifestyle_creep.creep_detected ? 'bg-emerald-500' : 'bg-rose-500'}`}
                    style={{ width: `${!lifestyle_creep.creep_detected ? 100 : 35}%` }} />
                </div>
                <span className={`text-xs font-semibold w-16 text-right shrink-0 ${!lifestyle_creep.creep_detected ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {!lifestyle_creep.creep_detected ? '✓ Good' : '⚠ Creep'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-28 text-xs text-slate-500 shrink-0">Debt Load</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ${debt_snowball.total_debt === 0 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                    style={{ width: `${debt_snowball.total_debt === 0 ? 100 : 50}%` }} />
                </div>
                <span className={`text-xs font-semibold w-16 text-right shrink-0 ${debt_snowball.total_debt === 0 ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {debt_snowball.total_debt === 0 ? '✓ Clear' : fmt(debt_snowball.total_debt)}
                </span>
              </div>
            </div>
          </div>

          {/* Score ring — half gauge */}
          <div className="flex flex-col items-center shrink-0">
            <div className="relative w-32 h-20">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={[{ value: lifeScore }, { value: 100 - lifeScore }]}
                    dataKey="value" cx="50%" cy="100%" startAngle={180} endAngle={0} innerRadius={46} outerRadius={60}>
                    <Cell fill={lifeScore >= 70 ? '#22c55e' : lifeScore >= 40 ? '#f59e0b' : '#ef4444'} />
                    <Cell fill="#f1f5f9" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
                <span className="text-2xl font-black text-slate-800">{lifeScore}</span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
            </div>
            <div className={`text-xs font-bold mt-1 ${lifeScore >= 70 ? 'text-emerald-600' : lifeScore >= 40 ? 'text-amber-600' : 'text-rose-600'}`}>
              {lifeScore >= 70 ? 'Excellent' : lifeScore >= 40 ? 'On Track' : 'Needs Work'}
            </div>
          </div>
        </div>

        <div className={`mt-5 text-sm rounded-xl px-4 py-3 ${lifeScore >= 70 ? 'bg-emerald-50 text-emerald-700' : lifeScore >= 40 ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'}`}>
          {lifeScore >= 70 ? '🎉 You\'re on a great financial track. Stay consistent and keep growing.'
            : lifeScore >= 40 ? '📋 Good foundations, but a few key areas need attention to reach financial freedom.'
              : '🔧 Your financial health needs work. Focus on the areas above to improve your score.'}
        </div>
      </div>

      {/* Inflation Ghost — unique to Life Goals */}
      <InflationGhostCard d={inflation_ghost} />

      {/* Subscription Bin */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-2xl">🗑️</span>
          <h3 className="text-base font-bold text-slate-800">Subscription &amp; Fixed Cost Bin</h3>
          <span className="ml-auto text-xs bg-rose-100 text-rose-700 font-bold px-2.5 py-1 rounded-full">
            {fmt(subBin10yr)} over 10 years
          </span>
        </div>
        <p className="text-slate-500 text-sm mb-5">
          Your fixed &amp; recurring monthly costs of {fmt(monthlyFixed)}/month — that's <strong>{fmt(subBin10yr)}</strong> you'll spend on them over the next 10 years. Cancel anything you don't actively love.
        </p>
        <div className="grid grid-cols-3 gap-4 mb-5">
          <div className="bg-rose-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-rose-700">{fmt(monthlyFixed)}</div>
            <div className="text-rose-500 text-xs mt-1">per month in fixed costs</div>
          </div>
          <div className="bg-amber-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-amber-700">{fmt(monthlyFixed * 12)}</div>
            <div className="text-amber-500 text-xs mt-1">per year</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-slate-700">{fmt(subBin10yr)}</div>
            <div className="text-slate-400 text-xs mt-1">over 10 years</div>
          </div>
        </div>
        <InsightCard icon="💡" color="amber"
          text={`Cutting just ₹2,000/month of unused subscriptions saves ${fmt(2000 * 120)} over 10 years — and invested at 12%, it grows to ${fmt(Math.round(2000 * ((Math.pow(1 + 0.01, 120) - 1) / 0.01)))}.`} />
      </div>

      {/* Income vs expense divergence chart — full width */}
      {monthly && monthly.length > 3 && (
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">Your income &amp; spending story 📖</h3>
          <p className="text-slate-500 text-sm mb-5">The gap between these two lines is your wealth-building engine</p>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={monthly} margin={{ top: 5, right: 10, bottom: 0, left: 10 }}>
              <defs>
                <linearGradient id="incGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} width={65} />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="income" name="Income" stroke="#22c55e" fill="url(#incGrad)" strokeWidth={2.5} dot={false} />
              <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#f43f5e" fill="url(#expGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 4 — DIVERSIFICATION (unchanged)
// ═══════════════════════════════════════════════════════════════════════════════

function DiversificationTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.reports.diversificationDashboard().then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />
  if (!data || !data.distribution.length) return <Empty />

  const top = data.distribution[0]
  const count = data.distribution.length
  const insights = []
  if (data.concentration_warning) insights.push({ icon: '⚠️', color: 'amber', text: data.concentration_warning })
  if (count < 3) insights.push({ icon: '📦', color: 'rose', text: `Wealth in only ${count} asset type${count > 1 ? 's' : ''}. Diversify into equities, gold, and fixed deposits to lower risk.` })
  else if (count >= 5) insights.push({ icon: '🌈', color: 'emerald', text: `Across ${count} asset classes — excellent diversification foundation.` })
  if (top.asset_class === 'Cash & Bank' && top.percent > 50)
    insights.push({ icon: '😴', color: 'amber', text: `Over half your wealth is in bank accounts. Inflation erodes idle cash at ~6%/year. Move some into equity mutual funds.` })

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Total Assets" value={fmt(data.total_assets)} sub="Everything you own, combined" icon={Wallet} accent="indigo" big />
        <StatCard label="Asset Classes" value={count} sub="Buckets you've spread across" icon={PieIcon}
          accent={count >= 5 ? 'emerald' : count >= 3 ? 'amber' : 'rose'} />
        <StatCard label="Largest Holding" value={top.asset_class} sub={`${top.percent}% of your wealth`}
          icon={top.percent > 60 ? AlertTriangle : CheckCircle} accent={top.percent > 60 ? 'rose' : 'emerald'} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">Your asset mix 🥧</h3>
          <p className="text-slate-500 text-sm mb-5">How your wealth is spread across categories</p>
          <div className="flex gap-6 items-center">
            <ResponsiveContainer width={180} height={180}>
              <PieChart>
                <Pie data={data.distribution} dataKey="value" nameKey="asset_class"
                  cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={2}>
                  {data.distribution.map((d, i) => <Cell key={i} fill={DOMAIN_COLORS[d.asset_class] ?? COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [fmt(v), n]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2">
              {data.distribution.map((d, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: DOMAIN_COLORS[d.asset_class] ?? COLORS[i % COLORS.length] }} />
                    <span className="text-xs text-slate-600 truncate">{d.asset_class}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-mono font-semibold">{fmt(d.value)}</span>
                    <span className="text-xs text-slate-400 w-8 text-right">{d.percent}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">You vs a balanced portfolio ⚖️</h3>
          <p className="text-slate-500 text-sm mb-5">Your actual allocation vs a typical balanced recommendation</p>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart layout="vertical"
              data={data.distribution.map(d => ({ name: d.asset_class.replace(' & ', '/'), actual: d.percent, ideal: IDEAL_ALLOC[d.asset_class] ?? 5 }))}
              margin={{ top: 0, right: 30, bottom: 0, left: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} width={70} />
              <Tooltip formatter={v => `${v}%`} />
              <Bar dataKey="actual" name="Your allocation" fill="#6366f1" radius={[0, 4, 4, 0]} />
              <Bar dataKey="ideal" name="Guideline" fill="#e2e8f0" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4"><Sparkles size={16} className="text-indigo-500" /><h3 className="font-bold text-slate-800">What this means for you</h3></div>
        <div className="space-y-3">{insights.map((ins, i) => <InsightCard key={i} {...ins} />)}</div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 5 — SPENDING (unchanged)
// ═══════════════════════════════════════════════════════════════════════════════

function SpendingTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [months, setMonths] = useState(6)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await API.reports.spendingDashboard({ months })) }
    catch { setData(null) }
    finally { setLoading(false) }
  }, [months])

  useEffect(() => { load() }, [load])

  if (loading) return <Spinner />
  if (!data || !data.category_trends.length) return <Empty />

  const cur = data.total_current_month
  const prev = data.total_previous_month
  const delta = prev > 0 ? Math.round((cur - prev) / prev * 100) : 0
  const stackedData = data.labels.map((lbl, li) => {
    const pt = { label: lbl }
    data.category_trends.forEach(ct => { pt[ct.category] = ct.monthly_amounts[li] ?? 0 })
    return pt
  })

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Spent This Month" value={fmt(cur)} sub="All categories added up" icon={TrendingDown} accent={delta > 15 ? 'rose' : 'emerald'} big />
        <StatCard label="Spent Last Month" value={fmt(prev)} sub="Same time last month" icon={BarChart2} accent="indigo" />
        <StatCard label="Month-on-Month" value={delta >= 0 ? `+${delta}%` : `${delta}%`}
          sub={delta > 0 ? '↑ Spending increased' : '↓ Spending decreased'}
          icon={delta > 0 ? TrendingUp : TrendingDown} accent={delta > 15 ? 'rose' : delta <= 0 ? 'emerald' : 'amber'} />
      </div>
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-slate-800">Spending patterns over time 📊</h3>
            <p className="text-slate-500 text-sm">Thicker layer = more spend in that category</p>
          </div>
          <select value={months} onChange={e => setMonths(Number(e.target.value))}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-600">
            {[3, 6, 12].map(m => <option key={m} value={m}>{m} months</option>)}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={stackedData} margin={{ top: 5, right: 10, bottom: 0, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} width={65} />
            <Tooltip content={<ChartTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {data.category_trends.map((ct, i) => (
              <Area key={ct.category} type="monotone" dataKey={ct.category} stackId="1"
                stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} strokeWidth={1.5} fillOpacity={0.7} dot={false} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-800 mb-1">This month vs last month 🔍</h3>
        <p className="text-slate-500 text-sm mb-4">Green = spent less, Red = spent more</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs text-slate-500 font-semibold uppercase tracking-wide">
                <th className="text-left py-2 pr-4">Category</th>
                <th className="text-right py-2 px-4">Last Month</th>
                <th className="text-right py-2 px-4">This Month</th>
                <th className="text-right py-2 pl-4">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.month_delta.map((d, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="py-2.5 pr-4 text-slate-700">{d.category}</td>
                  <td className="py-2.5 px-4 text-right font-mono text-slate-500">{fmt(d.previous)}</td>
                  <td className="py-2.5 px-4 text-right font-mono font-semibold text-slate-800">{fmt(d.current)}</td>
                  <td className={`py-2.5 pl-4 text-right font-semibold text-xs ${d.change_pct > 0 ? 'text-rose-600' : d.change_pct < 0 ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {d.change_pct > 0 ? '+' : ''}{d.change_pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 6 — TAX (unchanged)
// ═══════════════════════════════════════════════════════════════════════════════

function TaxTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.reports.taxDashboard().then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />
  if (!data) return <Empty />

  const leftOnTable = data.total_limit - data.total_used
  const fyEnd = new Date(data.fy_end)
  const fyEndDate = new Date(fyEnd.getFullYear() + (fyEnd.getMonth() < 3 ? 0 : 1), 2, 31)
  const daysLeft = Math.max(0, Math.ceil((fyEndDate - fyEnd) / 86400000))

  const insights = []
  if (data.overall_pct < 50)
    insights.push({ icon: '⏰', color: 'rose', text: `Used only ${Math.round(data.overall_pct)}% of deductions. ${daysLeft} days left to save up to ${fmt(data.potential_tax_saving)} in taxes.` })
  else if (data.overall_pct < 80)
    insights.push({ icon: '📋', color: 'amber', text: `${Math.round(data.overall_pct)}% utilised. Review remaining 80C and 80D limits before March 31.` })
  else
    insights.push({ icon: '🏆', color: 'emerald', text: `${Math.round(data.overall_pct)}% utilised — excellent tax planning this year!` })
  const s80c = data.sections.find(s => s.section === '80C')
  if (s80c?.remaining > 0)
    insights.push({ icon: '💡', color: 'sky', text: `${fmt(s80c.remaining)} left in Section 80C. ELSS mutual funds have the shortest 3-year lock-in and give market-linked returns.` })

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Earned this year" value={fmt(data.annual_income_so_far)} sub="April to today" icon={IndianRupee} accent="indigo" big />
        <StatCard label="Tax breaks used" value={fmt(data.total_used)} sub={`of ${fmt(data.total_limit)} limit`} icon={CheckCircle} accent="emerald" />
        <StatCard label="Still left to claim" value={fmt(leftOnTable)} sub="Room left before March 31" icon={Leaf} accent={leftOnTable > 50000 ? 'amber' : 'emerald'} />
        <StatCard label="Taxes you can save" value={fmt(data.potential_tax_saving)} sub="At 30% slab" icon={Zap} accent="rose" />
      </div>
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-800 mb-1">Section-wise deduction progress 🧾</h3>
        <p className="text-slate-500 text-sm mb-6">Which limits you've used — and what's still left to claim before March 31</p>
        <div className="space-y-6">
          {data.sections.map((sec, i) => {
            const color = sec.percent >= 90 ? 'bg-emerald-500' : sec.percent >= 50 ? 'bg-amber-500' : 'bg-rose-500'
            const badge = sec.percent >= 90 ? 'emerald' : sec.percent >= 50 ? 'amber' : 'rose'
            const bmap = { emerald: 'bg-emerald-100 text-emerald-700', amber: 'bg-amber-100 text-amber-700', rose: 'bg-rose-100 text-rose-700' }
            return (
              <div key={i}>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-sm font-bold text-slate-800">Section {sec.section}</span>
                    <span className="text-slate-400 text-xs ml-2">Limit: {fmt(sec.limit)}</span>
                  </div>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${bmap[badge]}`}>{sec.percent}%</span>
                </div>
                <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden mb-1">
                  <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${Math.min(100, sec.percent)}%` }} />
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Invested: {fmt(sec.used)}</span>
                  {sec.remaining > 0 && <span className="text-amber-600 font-medium">{fmt(sec.remaining)} remaining</span>}
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-1">Overall tax score 🎯</h3>
          <p className="text-slate-500 text-sm mb-4">How well you've planned your taxes this year</p>
          <div className="flex justify-center mb-2">
            <div className="relative w-52 h-28">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={[{ value: data.overall_pct }, { value: 100 - data.overall_pct }]}
                    dataKey="value" cx="50%" cy="100%" startAngle={180} endAngle={0} innerRadius={60} outerRadius={90}>
                    <Cell fill={data.overall_pct >= 80 ? '#22c55e' : data.overall_pct >= 50 ? '#f59e0b' : '#ef4444'} />
                    <Cell fill="#f1f5f9" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center mt-8">
                <span className="text-3xl font-black text-slate-800">{Math.round(data.overall_pct)}%</span>
                <span className="text-xs text-slate-400">utilised</span>
              </div>
            </div>
          </div>
          <div className="text-center text-sm text-slate-500">{daysLeft} days left in this financial year</div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-800 mb-4">Smart tax moves for you 💡</h3>
          <div className="space-y-3">
            {insights.map((ins, i) => <InsightCard key={i} {...ins} />)}
            <InsightCard icon="📌" color="indigo" text="These are estimates based on a 30% slab. Consult your CA for personalized tax planning." />
          </div>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ADVANCED REPORTS SECTION
// ═══════════════════════════════════════════════════════════════════════════════

function AdvancedSection() {
  return (
    <div className="mt-8 border-t-2 border-dashed border-indigo-200 pt-8">
      <div className="flex items-center gap-2 mb-6">
        <div className="bg-slate-700 text-white p-2 rounded-xl"><BarChart2 size={16} /></div>
        <div>
          <h2 className="text-lg font-bold text-slate-800">Advanced Accounting Reports</h2>
          <p className="text-slate-500 text-sm">Balance sheet, trial balance, ledger, journal &amp; more</p>
        </div>
      </div>
      <ReportsPage />
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN CONTAINER
// ═══════════════════════════════════════════════════════════════════════════════

const TABS = [
  { id: 'nav', label: 'Net Worth', emoji: '📊', subtitle: 'Your wealth at a glance', icon: TrendingUp },
  { id: 'flow', label: 'Cash Flow', emoji: '💸', subtitle: 'Money in and money out', icon: Activity },
  { id: 'goals', label: 'Life Goals', emoji: '🎯', subtitle: 'Your financial life story', icon: Target },
  { id: 'divers', label: 'Diversification', emoji: '🌈', subtitle: 'How spread is your wealth', icon: PieIcon },
  { id: 'spend', label: 'Spending', emoji: '🛒', subtitle: 'Where your money really goes', icon: BarChart2 },
  { id: 'tax', label: 'Tax Savings', emoji: '🏦', subtitle: 'Saving what you can?', icon: ShieldCheck },
]

export default function WealthDashboard() {
  const [activeTab, setActiveTab] = useState('nav')
  const [showAdv, setShowAdv] = useState(false)

  // Life-insights data loaded once, shared across Nav / CashFlow / LifeGoals tabs
  const [liData, setLiData] = useState(null)
  const [liLoading, setLiLoading] = useState(true)

  useEffect(() => {
    API.reports.lifeInsights()
      .then(setLiData)
      .catch(() => setLiData(null))
      .finally(() => setLiLoading(false))
  }, [])

  const current = TABS.find(t => t.id === activeTab)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-3xl font-black text-slate-900">Your Wealth Dashboard</h1>
          <p className="text-slate-500 mt-1">Plain numbers, honest stories. No accountant needed.</p>
        </div>

        {/* Tab nav — card style */}
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
          {TABS.map(tab => {
            const active = activeTab === tab.id
            return (
              <button key={tab.id}
                onClick={() => { setActiveTab(tab.id); setShowAdv(false) }}
                className={`flex flex-col items-start p-4 rounded-2xl border-2 text-left transition-all duration-200
                  ${active
                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-200 scale-[1.02]'
                    : 'bg-white border-slate-200 text-slate-700 hover:border-indigo-300 hover:shadow-md'
                  }`}>
                <span className="text-xl mb-1.5">{tab.emoji}</span>
                <span className={`font-bold text-xs leading-tight ${active ? 'text-white' : 'text-slate-800'}`}>{tab.label}</span>
                <span className={`text-xs mt-0.5 leading-tight hidden lg:block ${active ? 'text-indigo-200' : 'text-slate-400'}`}>{tab.subtitle}</span>
              </button>
            )
          })}
        </div>

        {/* Section heading */}
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-indigo-600 text-white p-2.5 rounded-xl">
            <current.icon size={18} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">{current.emoji} {current.label}</h2>
            <p className="text-slate-500 text-sm">{current.subtitle}</p>
          </div>
        </div>

        {/* Tab content */}
        {activeTab === 'nav' && <NavTab liData={liData} liLoading={liLoading} showAdvanced={showAdv} onToggleAdvanced={() => setShowAdv(v => !v)} />}
        {activeTab === 'flow' && <CashFlowTab liData={liData} liLoading={liLoading} showAdvanced={showAdv} onToggleAdvanced={() => setShowAdv(v => !v)} />}
        {activeTab === 'goals' && <LifeGoalsTab liData={liData} liLoading={liLoading} />}
        {activeTab === 'divers' && <DiversificationTab />}
        {activeTab === 'spend' && <SpendingTab />}
        {activeTab === 'tax' && <TaxTab />}

        {/* Advanced reports — only for Nav + CashFlow tabs */}
        {showAdv && (activeTab === 'nav' || activeTab === 'flow') && <AdvancedSection />}
      </div>
    </div>
  )
}
