import React, { useState, useEffect } from 'react'
import { Target, Plus, Trash2, Edit2, X, TrendingUp } from 'lucide-react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

const BASE = 'http://127.0.0.1:8000/api/v1'

const GOAL_ICONS = {
  RETIREMENT: '🏝️',
  HOME: '🏠',
  EDUCATION: '🎓',
  VEHICLE: '🚗',
  VACATION: '🏖️',
  EMERGENCY: '🛡️',
  WEDDING: '💍',
  OTHERS: '🎯',
}

const PRIORITY_COLOR = {
  HIGH: 'text-red-600 bg-red-50 border-red-100',
  MEDIUM: 'text-amber-600 bg-amber-50 border-amber-100',
  LOW: 'text-green-600 bg-green-50 border-green-100',
}

function barColor(pct) {
  if (pct >= 75) return 'bg-green-500'
  if (pct >= 40) return 'bg-[#2C4A70]'
  return 'bg-amber-400'
}

function fmtCurrency(val) {
  const n = parseFloat(val) || 0
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`
  return `₹${n.toLocaleString('en-IN')}`
}

function today() {
  return new Date().toISOString().slice(0, 10)
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
  const maxAge = goal.targetAge + 1
  const data = []
  let portfolio = goal.current || 0
  const r = GV_RETURN / 12

  for (let yr = 0; yr <= maxAge - age; yr++) {
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

function goalToVizShape(g, userAge) {
  const meta = GOAL_VIZ_META[g.goal_type] || GOAL_VIZ_META.OTHERS
  let years = 5
  if (g.target_date) {
    const diff = new Date(g.target_date) - new Date()
    years = Math.max(1, Math.round(diff / (365.25 * 24 * 3600 * 1000)))
  }
  const target  = parseFloat(g.target_amount) || 0
  const current = parseFloat(g.current_amount) || 0
  return {
    id:        String(g.id),
    name:      g.name,
    emoji:     meta.emoji,
    color:     meta.color,
    years,
    target,
    current,
    targetAge: userAge + years,
    sip:       computeSip(target, current, years),
  }
}

function GoalVizModal({ apiGoal, userAge, onClose }) {
  const [vizGoal, setVizGoal] = useState(() => goalToVizShape(apiGoal, userAge))
  const [sip, setSip]         = useState(() => computeSip(
    parseFloat(apiGoal.target_amount) || 0,
    parseFloat(apiGoal.current_amount) || 0,
    (() => {
      if (apiGoal.target_date) {
        const diff = new Date(apiGoal.target_date) - new Date()
        return Math.max(1, Math.round(diff / (365.25 * 24 * 3600 * 1000)))
      }
      return 5
    })(),
  ))

  const goal = { ...vizGoal, sip }
  const chartData = buildChartData(goal, userAge)
  const projected = computeSip(vizGoal.target, vizGoal.current, vizGoal.years)
  const pct = projected > 0 ? Math.round((sip / projected) * 100) : 100

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{vizGoal.emoji}</span>
            <div>
              <h2 className="text-lg font-bold text-slate-800">{vizGoal.name}</h2>
              <p className="text-sm text-slate-500">
                {vizGoal.years}y to go · Target {fmtCr(vizGoal.target)} · Age {vizGoal.targetAge}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-700 rounded-full hover:bg-slate-100 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* SIP input */}
          <div className="flex items-center gap-4 bg-slate-50 rounded-xl p-4">
            <div className="flex-1">
              <p className="text-xs text-slate-500 font-medium mb-1">Monthly SIP</p>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-sm">₹</span>
                <input
                  type="number"
                  value={sip}
                  onChange={e => setSip(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-36 text-lg font-bold text-slate-800 bg-white border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#2C4A70]/40"
                />
                <span className="text-slate-400 text-sm">/mo</span>
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 font-medium mb-1">Funding</div>
              <div
                className="text-2xl font-bold"
                style={{ color: pct >= 100 ? '#10b981' : pct >= 75 ? '#818cf8' : '#f59e0b' }}
              >
                {pct}%
              </div>
              <div className="text-xs text-slate-400">of required</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 font-medium mb-1">Recommended</div>
              <div className="text-sm font-semibold text-[#2C4A70]">₹{projected.toLocaleString('en-IN')}/mo</div>
            </div>
          </div>

          {/* Summary chips */}
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#2C4A70]/5 border border-[#2C4A70]/25 text-[#2C4A70] text-xs font-semibold">
              💰 ₹{sip.toLocaleString('en-IN')}/mo SIP
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border"
                 style={{ borderColor: vizGoal.color + '55', backgroundColor: vizGoal.color + '11', color: vizGoal.color }}>
              {vizGoal.emoji} {pct}% funded
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
                <YAxis yAxisId="left" orientation="left" stroke="#94a3b8"
                       tickFormatter={v => fmtCr(v)} tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis yAxisId="right" orientation="right" stroke="#94a3b8"
                       tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, color: '#1e293b' }}
                  formatter={(value, name) =>
                    name === 'Portfolio Value'
                      ? [fmtCr(value), name]
                      : [`₹${Number(value).toLocaleString('en-IN')}`, name]
                  }
                  labelFormatter={v => `Age ${v}`}
                />
                <Legend wrapperStyle={{ color: '#64748b', fontSize: 11 }} />
                <Area yAxisId="left" type="monotone" dataKey="portfolio" name="Portfolio Value"
                      stroke="#818cf8" fill="#818cf8" fillOpacity={0.18} strokeWidth={2} />
                <Line yAxisId="right" type="monotone" dataKey="monthly" name="Monthly SIP"
                      stroke="#10b981" strokeWidth={2} dot={false} strokeDasharray="5 3" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-slate-800">{fmtCr(vizGoal.target)}</div>
              <div className="text-xs text-slate-400 mt-0.5">Target corpus</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-emerald-600">{fmtCr(vizGoal.current)}</div>
              <div className="text-xs text-slate-400 mt-0.5">Already saved</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <div className="text-lg font-bold text-[#2C4A70]">{vizGoal.years}y</div>
              <div className="text-xs text-slate-400 mt-0.5">Time horizon</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const EMPTY_FORM = {
  name: '',
  goal_type: 'OTHERS',
  target_amount: '',
  current_amount: '0',
  start_date: today(),
  target_date: '',
  priority: 'MEDIUM',
  notes: '',
}

export default function GoalsPage({ userAge: userAgeProp = 30 }) {
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [editId, setEditId] = useState(null)
  const [selectedGoal, setSelectedGoal] = useState(null)

  const userAge = userAgeProp

  useEffect(() => { fetchGoals() }, [])

  async function fetchGoals() {
    setLoading(true)
    try {
      const r = await fetch(`${BASE}/goals`)
      if (r.ok) setGoals(await r.json())
    } finally {
      setLoading(false)
    }
  }

  function setField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  async function submitGoal(e) {
    e.preventDefault()
    setError('')
    if (!form.name || !form.target_amount || !form.start_date) {
      setError('Name, target amount and start date are required.')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        ...form,
        target_amount: parseFloat(form.target_amount),
        current_amount: parseFloat(form.current_amount) || 0,
        target_date: form.target_date || null,
        notes: form.notes || null,
      }
      const method = editId ? 'PATCH' : 'POST'
      const url = editId ? `${BASE}/goals/${editId}` : `${BASE}/goals`
      const r = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        setError(err.detail || 'Failed to save goal.')
        return
      }
      setShowForm(false)
      setEditId(null)
      setForm(EMPTY_FORM)
      await fetchGoals()
    } finally {
      setSubmitting(false)
    }
  }

  async function deleteGoal(id) {
    if (!confirm('Delete this goal?')) return
    await fetch(`${BASE}/goals/${id}`, { method: 'DELETE' })
    await fetchGoals()
  }

  function startEdit(g) {
    setForm({
      name: g.name,
      goal_type: g.goal_type,
      target_amount: g.target_amount,
      current_amount: g.current_amount,
      start_date: g.start_date,
      target_date: g.target_date || '',
      priority: g.priority,
      notes: g.notes || '',
    })
    setEditId(g.id)
    setShowForm(true)
  }

  const totalTarget = goals.reduce((s, g) => s + (parseFloat(g.target_amount) || 0), 0)
  const totalCurrent = goals.reduce((s, g) => s + (parseFloat(g.current_amount) || 0), 0)

  return (
    <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-10 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-800">🎯 Things you're working towards</h1>
          <p className="text-slate-400 mt-0.5 text-xs">How much you've saved and how far to go for each goal</p>
        </div>
        <button
          onClick={() => { setForm(EMPTY_FORM); setEditId(null); setShowForm(true) }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#2C4A70] text-white text-sm font-semibold rounded-lg hover:bg-[#1F344F] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" /> Add a goal
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
          <div className="text-slate-500 mt-1 mb-6 text-sm">Add your first goal — a home, a holiday, retirement — and we'll help you figure out how much to set aside each month.</div>
          <button
            onClick={() => { setForm(EMPTY_FORM); setEditId(null); setShowForm(true) }}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#2C4A70] text-white font-semibold rounded-xl hover:bg-[#1F344F] transition-colors"
          >
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
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${PRIORITY_COLOR[g.priority] || 'text-slate-600 bg-slate-50 border-slate-100'}`}>
                      {g.priority}
                    </span>
                  </div>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => startEdit(g)}
                    className="p-1.5 text-slate-400 hover:text-[#2C4A70] rounded-lg hover:bg-[#2C4A70]/5"
                    title="Edit goal"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteGoal(g.id)}
                    className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                    title="Delete goal"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>{fmtCurrency(g.current_amount)} saved so far</span>
                  <span className="font-semibold text-[#2C4A70]">{g.progress_pct}% there</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all ${barColor(g.progress_pct)}`}
                    style={{ width: `${g.progress_pct}%` }}
                  />
                </div>
                <div className="text-right text-xs text-slate-400 mt-0.5">
                  Goal: {fmtCurrency(g.target_amount)}
                </div>
              </div>

              <div className="flex justify-between text-xs text-slate-500">
                <span>Started {g.start_date}</span>
                {g.target_date && <span>Due {g.target_date}</span>}
              </div>
              {g.notes && <p className="text-xs text-slate-400 mt-2 italic">{g.notes}</p>}

              {/* Visualize button */}
              <button
                onClick={() => setSelectedGoal(g)}
                className="mt-3 w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#2C4A70]/5 text-[#2C4A70] text-xs font-semibold hover:bg-[#2C4A70]/10 transition-colors border border-[#2C4A70]/15"
              >
                <TrendingUp size={13} /> View Projection
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Goal Viz Modal */}
      {selectedGoal && (
        <GoalVizModal
          apiGoal={selectedGoal}
          userAge={userAge}
          onClose={() => setSelectedGoal(null)}
        />
      )}

      {/* Create / Edit modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 my-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-slate-800">{editId ? 'Update this goal' : 'Add a new goal'}</h3>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{error}</div>}

            <form onSubmit={submitGoal} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Goal Name *</label>
                <input
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                  value={form.name}
                  onChange={e => setField('name', e.target.value)}
                  placeholder="e.g. House Down Payment"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
                  <select
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                    value={form.goal_type}
                    onChange={e => setField('goal_type', e.target.value)}
                  >
                    {Object.keys(GOAL_ICONS).map(k => <option key={k} value={k}>{GOAL_ICONS[k]} {k}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Priority</label>
                  <select
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                    value={form.priority}
                    onChange={e => setField('priority', e.target.value)}
                  >
                    <option>HIGH</option><option>MEDIUM</option><option>LOW</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Target Amount (₹) *</label>
                  <input
                    type="number"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                    value={form.target_amount}
                    onChange={e => setField('target_amount', e.target.value)}
                    placeholder="5000000"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Current Amount (₹)</label>
                  <input
                    type="number"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                    value={form.current_amount}
                    onChange={e => setField('current_amount', e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Start Date *</label>
                  <input
                    type="date"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                    value={form.start_date}
                    onChange={e => setField('start_date', e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Target Date</label>
                  <input
                    type="date"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none"
                    value={form.target_date}
                    onChange={e => setField('target_date', e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
                <textarea
                  rows={2}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#2C4A70]/30 focus:outline-none resize-none"
                  value={form.notes}
                  onChange={e => setField('notes', e.target.value)}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 px-4 py-2 border border-slate-200 rounded-xl text-slate-700 text-sm font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-[#2C4A70] text-white rounded-xl text-sm font-semibold hover:bg-[#1F344F] disabled:opacity-50"
                >
                  {submitting ? 'Saving…' : editId ? 'Update Goal' : 'Create Goal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
