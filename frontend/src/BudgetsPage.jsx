import React, { useState, useEffect } from 'react'
import { Plus, Trash2, X, PiggyBank } from 'lucide-react'

const BASE = 'http://127.0.0.1:8000/api/v1'

// Default expense categories from the seeded Chart of Accounts
const COMMON_CATEGORIES = [
  { code: '4101', name: 'Rent / Housing' },
  { code: '4201', name: 'Dining & Food' },
  { code: '4301', name: 'Transport' },
  { code: '4401', name: 'Shopping' },
  { code: '4501', name: 'Healthcare' },
  { code: '4601', name: 'Utilities' },
  { code: '4701', name: 'EMI / Debt Payments' },
  { code: '4801', name: 'Insurance' },
  { code: '4901', name: 'Entertainment' },
  { code: '4999', name: 'Miscellaneous' },
]

function spendPct(spent, budgeted) {
  const s = parseFloat(spent) || 0
  const b = parseFloat(budgeted) || 0
  return b > 0 ? Math.min((s / b) * 100, 100) : 0
}

function barColor(pct) {
  if (pct >= 90) return 'bg-red-500'
  if (pct >= 70) return 'bg-amber-500'
  return 'bg-green-500'
}

function fmtAmount(val) {
  const n = parseFloat(val) || 0
  return `₹${n.toLocaleString('en-IN')}`
}

function thisMonthRange() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
  return { start, end }
}

const EMPTY_ITEM = { account_code: '', budgeted_amount: '' }

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formName, setFormName] = useState('Monthly Budget')
  const [formPeriod, setFormPeriod] = useState('MONTHLY')
  const [formStart, setFormStart] = useState(() => thisMonthRange().start)
  const [formEnd, setFormEnd] = useState(() => thisMonthRange().end)
  const [formRecurring, setFormRecurring] = useState(false)
  const [formItems, setFormItems] = useState([{ ...EMPTY_ITEM }])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { fetchBudgets() }, [])

  async function fetchBudgets() {
    setLoading(true)
    try {
      const r = await fetch(`${BASE}/budgets?active_only=false`)
      if (r.ok) setBudgets(await r.json())
    } finally {
      setLoading(false)
    }
  }

  function addItem() { setFormItems(items => [...items, { ...EMPTY_ITEM }]) }
  function removeItem(i) { setFormItems(items => items.filter((_, idx) => idx !== i)) }
  function updateItem(i, field, val) {
    setFormItems(items => items.map((item, idx) => idx === i ? { ...item, [field]: val } : item))
  }

  async function submitBudget(e) {
    e.preventDefault()
    setError('')
    const validItems = formItems.filter(it => it.account_code && it.budgeted_amount)
    if (!validItems.length) { setError('Add at least one budget category.'); return }
    setSubmitting(true)
    try {
      const payload = {
        name: formName,
        period_type: formPeriod,
        start_date: formStart,
        end_date: formEnd,
        is_recurring: formRecurring,
        items: validItems.map(it => ({
          account_code: it.account_code,
          budgeted_amount: parseFloat(it.budgeted_amount),
        })),
      }
      const r = await fetch(`${BASE}/budgets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        setError(err.detail || 'Failed to create budget.')
        return
      }
      setShowForm(false)
      setFormItems([{ ...EMPTY_ITEM }])
      setFormName('Monthly Budget')
      await fetchBudgets()
    } finally {
      setSubmitting(false)
    }
  }

  async function deactivateBudget(id) {
    if (!confirm('Deactivate this budget?')) return
    await fetch(`${BASE}/budgets/${id}`, { method: 'DELETE' })
    await fetchBudgets()
  }

  const totalBudgetTotal = budgets
    .filter(b => b.is_active)
    .reduce((s, b) => s + (parseFloat(b.total_budgeted) || 0), 0)

  return (
    <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-10 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-800">💰 What you plan to spend</h1>
          <p className="text-slate-400 mt-0.5 text-xs">Monthly limits per category — see how close you're getting</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" /> Create a budget
        </button>
      </div>

      {/* Summary strip */}
      {budgets.filter(b => b.is_active).length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-100 p-3 text-center shadow-sm">
            <div className="text-xl font-bold text-emerald-700">{budgets.filter(b => b.is_active).length}</div>
            <div className="text-xs text-slate-400 mt-0.5">budgets running</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3 text-center shadow-sm">
            <div className="text-xl font-bold text-slate-800">{fmtAmount(totalBudgetTotal)}</div>
            <div className="text-xs text-slate-400 mt-0.5">planned to spend</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3 text-center shadow-sm">
            <div className="text-xl font-bold text-slate-800">
              {fmtAmount(budgets.filter(b => b.is_active).reduce((s, b) => s + (parseFloat(b.total_spent) || 0), 0))}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">spent so far</div>
          </div>
        </div>
      )}

      {/* Budget list */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading budgets…</div>
      ) : budgets.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-100 shadow-sm">
          <div className="text-5xl mb-3">💰</div>
          <div className="text-lg font-bold text-slate-700">No budgets yet</div>
          <div className="text-slate-500 mt-1 mb-6 text-sm">Tell Ledger how much you want to spend on food, rent, entertainment — and it'll keep you honest.</div>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> Set up your first budget
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {budgets.map(b => {
            const totalPct = spendPct(b.total_spent, b.total_budgeted)
            return (
              <div
                key={b.id}
                className={`bg-white rounded-2xl border shadow-sm overflow-hidden hover:shadow-md transition-shadow ${b.is_active ? 'border-slate-100' : 'border-slate-100 opacity-60'}`}
              >
                <div className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-slate-800">{b.name}</h3>
                      <div className="text-xs text-slate-500">
                        {b.period_type} • {b.start_date} → {b.end_date}
                        {b.is_recurring && ' • Recurring'}
                        {!b.is_active && ' • Inactive'}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="text-sm font-bold text-slate-900">
                          {fmtAmount(b.total_spent)}{' '}
                          <span className="text-slate-400 font-normal">/ {fmtAmount(b.total_budgeted)}</span>
                        </div>
                        <div className="text-xs text-slate-500">{totalPct.toFixed(0)}% used</div>
                      </div>
                      {b.is_active && (
                        <button
                          onClick={() => deactivateBudget(b.id)}
                          className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                          title="Deactivate budget"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Overall progress bar */}
                  <div className="w-full bg-slate-100 rounded-full h-2 mb-4">
                    <div
                      className={`h-2 rounded-full transition-all ${barColor(totalPct)}`}
                      style={{ width: `${totalPct}%` }}
                    />
                  </div>

                  {/* Per-category breakdown */}
                  {b.items.length > 0 && (
                    <div className="space-y-2">
                      {b.items.map(item => {
                        const pct = spendPct(item.spent_amount, item.budgeted_amount)
                        return (
                          <div key={item.id} className="flex items-center gap-3">
                            <div className="w-36 text-xs text-slate-600 truncate">{item.account_name}</div>
                            <div className="flex-1">
                              <div className="w-full bg-slate-100 rounded-full h-1.5">
                                <div
                                  className={`h-1.5 rounded-full ${barColor(pct)}`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                            <div className="text-xs text-slate-500 w-36 text-right">
                              {fmtAmount(item.spent_amount)} / {fmtAmount(item.budgeted_amount)}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Create modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 my-8">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-slate-800">Create a budget</h3>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{error}</div>}

            <form onSubmit={submitBudget} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Budget Name</label>
                <input
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-green-300 focus:outline-none"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Period</label>
                  <select
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-green-300 focus:outline-none"
                    value={formPeriod}
                    onChange={e => setFormPeriod(e.target.value)}
                  >
                    <option>MONTHLY</option>
                    <option>QUARTERLY</option>
                    <option>ANNUAL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Start</label>
                  <input
                    type="date"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-green-300 focus:outline-none"
                    value={formStart}
                    onChange={e => setFormStart(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">End</label>
                  <input
                    type="date"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-green-300 focus:outline-none"
                    value={formEnd}
                    onChange={e => setFormEnd(e.target.value)}
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={formRecurring}
                  onChange={e => setFormRecurring(e.target.checked)}
                  className="rounded"
                />
                Recurring budget (auto-renew each period)
              </label>

              {/* Category rows */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700">Categories</label>
                  <button
                    type="button"
                    onClick={addItem}
                    className="text-xs text-green-600 hover:text-green-800 font-medium flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> Add row
                  </button>
                </div>
                <div className="space-y-2">
                  {formItems.map((item, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <select
                        className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-green-300 focus:outline-none"
                        value={item.account_code}
                        onChange={e => updateItem(i, 'account_code', e.target.value)}
                      >
                        <option value="">— Select category —</option>
                        {COMMON_CATEGORIES.map(c => (
                          <option key={c.code} value={c.code}>{c.name} ({c.code})</option>
                        ))}
                      </select>
                      <input
                        type="number"
                        placeholder="Amount ₹"
                        className="w-32 border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-green-300 focus:outline-none"
                        value={item.budgeted_amount}
                        onChange={e => updateItem(i, 'budgeted_amount', e.target.value)}
                      />
                      {formItems.length > 1 && (
                        <button type="button" onClick={() => removeItem(i)} className="text-slate-400 hover:text-red-600">
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-right text-sm font-semibold text-slate-700">
                  Total: ₹{formItems.reduce((s, it) => s + (parseFloat(it.budgeted_amount) || 0), 0).toLocaleString('en-IN')}
                </div>
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
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-xl text-sm font-semibold hover:bg-green-700 disabled:opacity-50"
                >
                  {submitting ? 'Creating…' : 'Create Budget'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
