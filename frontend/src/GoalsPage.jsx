import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Target, Plus, Trash2, Edit2, X, TrendingUp, Check,
  AlertCircle, Home, GraduationCap, CreditCard, Car, Briefcase, Heart,
} from 'lucide-react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { API } from './api.js'

// ── Goal type options — mirrors onboarding GOAL_OPTS ─────────────────────────
const GOAL_OPTS = [
  { id: 'emergency', icon: AlertCircle,   goalType: 'EMERGENCY',  label: 'Emergency Fund',   desc: 'Prepare for the unexpected' },
  { id: 'home',      icon: Home,          goalType: 'HOME',       label: 'Buy a Home',       desc: 'Down payment planning' },
  { id: 'retire',    icon: TrendingUp,    goalType: 'RETIREMENT', label: 'Retire Early',     desc: 'Secure your future' },
  { id: 'education', icon: GraduationCap, goalType: 'EDUCATION',  label: 'Education',        desc: 'College or upskilling' },
  { id: 'vehicle',   icon: Car,           goalType: 'VEHICLE',    label: 'Buy a Vehicle',    desc: 'Next set of wheels' },
  { id: 'vacation',  icon: Briefcase,     goalType: 'VACATION',   label: 'Travel / Vacation',desc: 'Make memories' },
  { id: 'wedding',   icon: Heart,         goalType: 'WEDDING',    label: 'Wedding',          desc: 'The big day' },
  { id: 'debt',      icon: CreditCard,    goalType: 'OTHERS',     label: 'Pay off Debt',     desc: 'Clear loans faster' },
  { id: 'custom',    icon: Plus,          goalType: 'OTHERS',     label: 'Custom Goal',      desc: 'Anything else' },
]

const GOAL_TYPE_TO_OPT = {
  EMERGENCY: 'emergency', HOME: 'home', RETIREMENT: 'retire',
  EDUCATION: 'education', VEHICLE: 'vehicle', VACATION: 'vacation',
  WEDDING: 'wedding', OTHERS: 'custom',
}

const TIMELINE_OPTS = [
  { label: '6 months',  months: 6   },
  { label: '1 year',    months: 12  },
  { label: '2 years',   months: 24  },
  { label: '3 years',   months: 36  },
  { label: '5 years',   months: 60  },
  { label: '10 years',  months: 120 },
  { label: '15 years',  months: 180 },
  { label: '20+ years', months: 240 },
]

// ── Formatters ────────────────────────────────────────────────────────────────
function fmtCurrency(val) {
  const n = parseFloat(val) || 0
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`
  if (n >= 100000)   return `₹${(n / 100000).toFixed(1)}L`
  return `₹${n.toLocaleString('en-IN')}`
}

function num(v) {
  return parseFloat(String(v).replace(/[^0-9.]/g, '')) || 0
}

function monthsFromTargetDate(target_date) {
  if (!target_date) return 12
  const diff = new Date(target_date) - new Date()
  return Math.max(1, Math.round(diff / (30.5 * 24 * 3600 * 1000)))
}

function targetDateFromMonths(months) {
  const d = new Date()
  d.setMonth(d.getMonth() + months)
  return d.toISOString().slice(0, 10)
}

function barColor(pct) {
  if (pct >= 75) return 'bg-green-500'
  if (pct >= 40) return 'bg-[#2C4A70]'
  return 'bg-amber-400'
}

// ── Goal visualization helpers ────────────────────────────────────────────────
const GV_RETURN = 0.12
const GV_STEPUP = 0.0512

function computeSip(target, current, years) {
  if (years <= 0) return 0
  const r = GV_RETURN / 12
  const n = years * 12
  const fvCurrent = current * Math.pow(1 + GV_RETURN, years)
  const remaining = Math.max(0, target - fvCurrent)
  if (remaining <= 0) return 0
  return Math.ceil(remaining * r / (Math.pow(1 + r, n) - 1))
}

function buildChartData(goal, age) {
  const data = []
  let portfolio = goal.current || 0
  const r = GV_RETURN / 12
  for (let yr = 0; yr <= goal.years; yr++) {
    const curAge = age + yr
    let monthlyInvest = 0
    if (yr < goal.years) {
      monthlyInvest = Math.round((goal.sip || 0) * Math.pow(1 + GV_STEPUP, yr))
    }
    for (let m = 0; m < 12; m++) {
      portfolio = portfolio * (1 + r) + monthlyInvest
    }
    if (curAge === goal.targetAge) portfolio = Math.max(0, portfolio - goal.target)
    data.push({ age: curAge, monthly: monthlyInvest, portfolio: Math.round(portfolio) })
  }
  return data
}

const fmtCr = v => {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`
  return `₹${Math.round(v / 1000)}K`
}

const GOAL_VIZ_META = {
  RETIREMENT: { emoji: '🌅', color: '#818cf8' },
  EMERGENCY:  { emoji: '🛡️', color: '#34d399' },
  HOME:       { emoji: '🏠', color: '#fb923c' },
  VEHICLE:    { emoji: '🚗', color: '#60a5fa' },
  EDUCATION:  { emoji: '🎓', color: '#f472b6' },
  VACATION:   { emoji: '✈️', color: '#a78bfa' },
  WEDDING:    { emoji: '💍', color: '#f43f5e' },
  OTHERS:     { emoji: '🎯', color: '#facc15' },
}

function GoalVizModal({ apiGoal, userAge, onClose }) {
  const meta  = GOAL_VIZ_META[apiGoal.goal_type] || GOAL_VIZ_META.OTHERS
  const years = apiGoal.target_date
    ? Math.max(1, Math.round((new Date(apiGoal.target_date) - new Date()) / (365.25 * 24 * 3600 * 1000)))
    : 5
  const target  = parseFloat(apiGoal.target_amount) || 0
  const current = parseFloat(apiGoal.current_amount) || 0
  const [sip, setSip] = useState(() => computeSip(target, current, years))

  const projected = computeSip(target, current, years)
  const pct = projected > 0 ? Math.round((sip / projected) * 100) : 100
  const vizGoal = { target, current, years, targetAge: userAge + years, sip }
  const chartData = buildChartData(vizGoal, userAge)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{meta.emoji}</span>
            <div>
              <h2 className="text-lg font-bold text-slate-800">{apiGoal.name}</h2>
              <p className="text-sm text-slate-500">{years}y to go · Target {fmtCr(target)}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-700 rounded-full hover:bg-slate-100 transition-colors"><X size={20} /></button>
        </div>

        <div className="px-6 py-5 space-y-5">
          <div className="flex items-center gap-4 bg-slate-50 rounded-xl p-4">
            <div className="flex-1">
              <p className="text-xs text-slate-500 font-medium mb-1">Monthly SIP</p>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-sm">₹</span>
                <input type="number" value={sip} onChange={e => setSip(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-36 text-lg font-bold text-slate-800 bg-white border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#2C4A70]/40" />
                <span className="text-slate-400 text-sm">/mo</span>
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 font-medium mb-1">Funding</div>
              <div className="text-2xl font-bold" style={{ color: pct >= 100 ? '#10b981' : pct >= 75 ? meta.color : '#f59e0b' }}>{pct}%</div>
              <div className="text-xs text-slate-400">of required</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 font-medium mb-1">Recommended</div>
              <div className="text-sm font-semibold text-[#2C4A70]">₹{projected.toLocaleString('en-IN')}/mo</div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-slate-600 font-semibold text-xs mb-3 uppercase tracking-wider">Goal Projection</p>
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="age" stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 11 }} label={{ value: 'Age', position: 'insideBottomRight', offset: -5, fill: '#94a3b8', fontSize: 11 }} />
                <YAxis yAxisId="left" tickFormatter={v => fmtCr(v)} stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis yAxisId="right" orientation="right" tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 10 }}
                  formatter={(value, name) => name === 'Portfolio Value' ? [fmtCr(value), name] : [`₹${Number(value).toLocaleString('en-IN')}`, name]}
                  labelFormatter={v => `Age ${v}`} />
                <Legend wrapperStyle={{ color: '#64748b', fontSize: 11 }} />
                <Area yAxisId="left" type="monotone" dataKey="portfolio" name="Portfolio Value" stroke={meta.color} fill={meta.color} fillOpacity={0.15} strokeWidth={2} />
                <Line yAxisId="right" type="monotone" dataKey="monthly" name="Monthly SIP" stroke="#10b981" strokeWidth={2} dot={false} strokeDasharray="5 3" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-slate-800">{fmtCr(target)}</div>
              <div className="text-xs text-slate-400 mt-0.5">Target corpus</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-emerald-600">{fmtCr(current)}</div>
              <div className="text-xs text-slate-400 mt-0.5">Already saved</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-[#2C4A70]">{years}y</div>
              <div className="text-xs text-slate-400 mt-0.5">Time horizon</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Goal type picker (step 1 of add) ─────────────────────────────────────────
function GoalTypePicker({ onPick, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2 }}
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden z-10"
      >
        <div className="h-1.5 bg-gradient-to-r from-[#2C4A70] to-[#526B5C]" />
        <div className="p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-serif font-black text-[#2C4A70]">What are you working towards?</h3>
              <p className="text-xs text-slate-400 mt-1">Pick a goal type to get started</p>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors text-lg leading-none">×</button>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {GOAL_OPTS.map(opt => {
              const Icon = opt.icon
              return (
                <button key={opt.id} onClick={() => onPick(opt)}
                  className="flex flex-col items-center gap-2 p-4 rounded-2xl border-2 border-slate-200 hover:border-[#2C4A70] hover:bg-indigo-50 text-center transition-all group">
                  <div className="w-10 h-10 rounded-xl bg-slate-100 group-hover:bg-[#2C4A70]/10 flex items-center justify-center transition-colors">
                    <Icon size={18} className="text-slate-500 group-hover:text-[#2C4A70] transition-colors" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-700 group-hover:text-[#2C4A70] leading-tight">{opt.label}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">{opt.desc}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ── Goal config dialog (step 2 of add / edit) ─────────────────────────────────
function GoalConfigDialog({ opt, existing, onSave, onClose }) {
  const Icon = opt.icon
  const [targetAmount, setTargetAmount] = useState(existing?.target_amount ? String(existing.target_amount) : '')
  const [currentAmount, setCurrentAmount] = useState(existing?.current_amount ? String(existing.current_amount) : '0')
  const [timelineMonths, setTimelineMonths] = useState(() =>
    existing?.target_date ? monthsFromTargetDate(existing.target_date) : 12
  )
  const [priority, setPriority] = useState(existing?.priority?.toLowerCase() || 'medium')
  const [note, setNote]         = useState(existing?.notes || '')
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState('')

  const canSave = num(targetAmount) > 0
  const monthlySaving = timelineMonths > 0 ? Math.ceil(num(targetAmount) / timelineMonths) : 0

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')
    try {
      await onSave({
        name:           opt.label,
        goal_type:      opt.goalType,
        target_amount:  num(targetAmount),
        current_amount: num(currentAmount),
        target_date:    targetDateFromMonths(timelineMonths),
        notes:          note || null,
      })
      onClose()
    } catch (e) {
      setError('Failed to save goal. Please try again.')
    } finally {
      setSaving(false)
    }
  }

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
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-[#2C4A70]/10 flex items-center justify-center">
                <Icon size={22} className="text-[#2C4A70]" />
              </div>
              <div>
                <h3 className="text-xl font-serif font-black text-[#2C4A70]">{opt.label}</h3>
                <p className="text-xs text-slate-400">{opt.desc}</p>
              </div>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors text-lg leading-none">×</button>
          </div>

          {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{error}</div>}

          <div className="space-y-5">
            {/* Target amount */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Target Amount</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
                <input value={targetAmount} onChange={e => setTargetAmount(e.target.value)} placeholder="0" inputMode="numeric"
                  className="w-full border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
              </div>
              {num(targetAmount) > 0 && <p className="text-xs text-slate-400 mt-1 pl-1">{fmtCurrency(num(targetAmount))}</p>}
            </div>

            {/* Already saved */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
                Already Saved <span className="text-slate-300 font-normal normal-case">(optional)</span>
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
                <input value={currentAmount} onChange={e => setCurrentAmount(e.target.value)} placeholder="0" inputMode="numeric"
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
                <p className="text-lg font-black text-[#2C4A70]">{fmtCurrency(monthlySaving)}</p>
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

          <div className="flex gap-3 mt-7">
            <button onClick={onClose} className="flex-1 py-3 rounded-full border-2 border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-colors">
              Cancel
            </button>
            <button onClick={handleSave} disabled={!canSave || saving}
              className="flex-1 py-3 rounded-full bg-[#2C4A70] text-white font-semibold text-sm hover:bg-[#1F344F] disabled:opacity-40 disabled:cursor-not-allowed shadow-md transition-all">
              {saving ? 'Saving…' : existing ? 'Update Goal' : 'Add Goal'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function GoalsPage({ userAge = 30 }) {
  const [goals, setGoals]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [selectedGoal, setSelectedGoal] = useState(null)

  // Modal state: null | 'pick' | 'config'
  const [modalStep, setModalStep] = useState(null)
  const [pickedOpt, setPickedOpt] = useState(null)
  const [editGoal, setEditGoal]   = useState(null)   // existing API goal being edited

  useEffect(() => { fetchGoals() }, [])

  async function fetchGoals() {
    setLoading(true)
    try {
      const data = await API.goals.list()
      setGoals(data || [])
    } catch (_) {
      setGoals([])
    } finally {
      setLoading(false)
    }
  }

  function openAdd() {
    setEditGoal(null)
    setPickedOpt(null)
    setModalStep('pick')
  }

  function openEdit(g) {
    const optId = GOAL_TYPE_TO_OPT[g.goal_type] || 'custom'
    const opt   = GOAL_OPTS.find(o => o.id === optId) || GOAL_OPTS[GOAL_OPTS.length - 1]
    setEditGoal(g)
    setPickedOpt(opt)
    setModalStep('config')
  }

  function closeModal() {
    setModalStep(null)
    setPickedOpt(null)
    setEditGoal(null)
  }

  async function handleSave(payload) {
    if (editGoal) {
      await API.goals.update(editGoal.id, payload)
    } else {
      await API.goals.create(payload)
    }
    await fetchGoals()
  }

  async function deleteGoal(id) {
    if (!confirm('Delete this goal?')) return
    await API.goals.delete(id)
    await fetchGoals()
  }

  const totalTarget  = goals.reduce((s, g) => s + (parseFloat(g.target_amount)  || 0), 0)
  const totalCurrent = goals.reduce((s, g) => s + (parseFloat(g.current_amount) || 0), 0)

  const GOAL_ICONS = {
    RETIREMENT: '🏝️', HOME: '🏠', EDUCATION: '🎓', VEHICLE: '🚗',
    VACATION: '✈️', EMERGENCY: '🛡️', WEDDING: '💍', OTHERS: '🎯',
  }

  return (
    <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-10 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-800">🎯 Things you're working towards</h1>
          <p className="text-slate-400 mt-0.5 text-xs">How much you've saved and how far to go for each goal</p>
        </div>
        <button onClick={openAdd}
          className="flex items-center gap-1.5 px-4 py-2 bg-[#2C4A70] text-white text-sm font-semibold rounded-xl hover:bg-[#1F344F] transition-colors">
          <Plus className="w-4 h-4" /> Add a goal
        </button>
      </div>

      {/* Summary strip */}
      {goals.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-100 p-3 text-center shadow-sm">
            <div className="text-xl font-bold text-[#2C4A70]">{goals.length}</div>
            <div className="text-xs text-slate-400 mt-0.5">goals on the go</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3 text-center shadow-sm">
            <div className="text-xl font-bold text-slate-800">{fmtCurrency(totalTarget)}</div>
            <div className="text-xs text-slate-400 mt-0.5">total you're aiming for</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3 text-center shadow-sm">
            <div className="text-xl font-bold text-emerald-700">{fmtCurrency(totalCurrent)}</div>
            <div className="text-xs text-slate-400 mt-0.5">already set aside</div>
          </div>
        </div>
      )}

      {/* Goal cards */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading goals…</div>
      ) : goals.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-100 shadow-sm">
          <div className="text-5xl mb-3">🎯</div>
          <div className="text-lg font-bold text-slate-700">Nothing here yet</div>
          <div className="text-slate-500 mt-1 mb-6 text-sm">
            Add your first goal — a home, a holiday, retirement — and we'll help you figure out how much to set aside each month.
          </div>
          <button onClick={openAdd}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#2C4A70] text-white font-semibold rounded-xl hover:bg-[#1F344F] transition-colors">
            <Plus className="w-4 h-4" /> Set your first goal
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {goals.map(g => (
            <div key={g.id} className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{GOAL_ICONS[g.goal_type] || '🎯'}</span>
                  <div>
                    <div className="font-semibold text-slate-800">{g.name}</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {g.target_date ? `Due ${g.target_date}` : 'No target date'}
                    </div>
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(g)} className="p-1.5 text-slate-400 hover:text-[#2C4A70] rounded-lg hover:bg-[#2C4A70]/5" title="Edit goal">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button onClick={() => deleteGoal(g.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50" title="Delete goal">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="mb-3">
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>{fmtCurrency(g.current_amount)} saved</span>
                  <span className="font-semibold text-[#2C4A70]">{Math.round(g.progress_pct || 0)}% there</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div className={`h-2.5 rounded-full transition-all ${barColor(g.progress_pct || 0)}`}
                    style={{ width: `${Math.min(100, g.progress_pct || 0)}%` }} />
                </div>
                <div className="text-right text-xs text-slate-400 mt-0.5">Goal: {fmtCurrency(g.target_amount)}</div>
              </div>

              {g.notes && <p className="text-xs text-slate-400 italic mb-3">{g.notes}</p>}

              <button onClick={() => setSelectedGoal(g)}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#2C4A70]/5 text-[#2C4A70] text-xs font-semibold hover:bg-[#2C4A70]/10 transition-colors border border-[#2C4A70]/15">
                <TrendingUp size={13} /> View Projection
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Goal viz modal */}
      {selectedGoal && (
        <GoalVizModal apiGoal={selectedGoal} userAge={userAge} onClose={() => setSelectedGoal(null)} />
      )}

      {/* Step 1: Goal type picker */}
      <AnimatePresence>
        {modalStep === 'pick' && (
          <GoalTypePicker
            onPick={opt => { setPickedOpt(opt); setModalStep('config') }}
            onClose={closeModal}
          />
        )}
      </AnimatePresence>

      {/* Step 2: Goal config dialog */}
      <AnimatePresence>
        {modalStep === 'config' && pickedOpt && (
          <GoalConfigDialog
            opt={pickedOpt}
            existing={editGoal}
            onSave={handleSave}
            onClose={closeModal}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
