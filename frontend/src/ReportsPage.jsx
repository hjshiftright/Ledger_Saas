import React, { useState, useEffect, useCallback } from 'react'
import {
  BarChart2, TrendingUp, TrendingDown, Wallet, CreditCard,
  FileText, PieChart, BookOpen, ChevronDown, ChevronRight,
  RefreshCw, Sparkles, AlertCircle, Scale, Library, ScrollText,
} from 'lucide-react'
import { API } from './api'

// ─── Formatters ─────────────────────────────────────────────────────────────

const fmt = (val, decimals = 0) => {
  const n = parseFloat(val ?? 0)
  if (isNaN(n)) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: decimals,
  }).format(n)
}

const pct = (val) => `${parseFloat(val ?? 0).toFixed(1)}%`

// ─── Period helpers ──────────────────────────────────────────────────────────

const isoDate = (d) => d.toISOString().slice(0, 10)
const today = () => isoDate(new Date())

function getPeriodDates(preset) {
  const now = new Date()
  const T = isoDate(now)
  if (preset === 'this_month') {
    return { fromDate: isoDate(new Date(now.getFullYear(), now.getMonth(), 1)), toDate: T }
  }
  if (preset === 'last_month') {
    const f = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const t = new Date(now.getFullYear(), now.getMonth(), 0)
    return { fromDate: isoDate(f), toDate: isoDate(t) }
  }
  if (preset === 'this_quarter') {
    const q = Math.floor(now.getMonth() / 3)
    return { fromDate: isoDate(new Date(now.getFullYear(), q * 3, 1)), toDate: T }
  }
  if (preset === 'this_fy') {
    const fyYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1
    return { fromDate: `${fyYear}-04-01`, toDate: T }
  }
  if (preset === 'last_12m') {
    const f = new Date(now)
    f.setFullYear(f.getFullYear() - 1)
    return { fromDate: isoDate(f), toDate: T }
  }
  return { fromDate: T, toDate: T }
}

// ─── Shared UI pieces ────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color = 'slate', icon: Icon }) {
  const colors = {
    slate: 'bg-white border-slate-100',
    emerald: 'bg-emerald-50 border-emerald-100',
    rose: 'bg-rose-50 border-rose-100',
    indigo: 'bg-[#2C4A70]/5 border-[#2C4A70]/15',
  }
  return (
    <div className={`rounded-xl border p-4 shadow-sm ${colors[color]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        {Icon && <Icon size={15} className="text-slate-400" />}
      </div>
      <div className="text-2xl font-bold text-slate-800">{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-16 text-slate-400">
      <RefreshCw size={20} className="animate-spin mr-2" />
      <span className="text-sm">Loading…</span>
    </div>
  )
}

function Empty({ msg = 'No data for this period.' }) {
  return (
    <div className="flex flex-col items-center py-12 text-slate-400">
      <BarChart2 size={36} className="mb-2 opacity-40" />
      <p className="text-sm">{msg}</p>
    </div>
  )
}

// Period selector ─────────────────────────────────────────────────────────────

const PRESETS = [
  { id: 'this_month', label: 'This Month' },
  { id: 'last_month', label: 'Last Month' },
  { id: 'this_quarter', label: 'This Quarter' },
  { id: 'this_fy', label: 'This FY' },
  { id: 'last_12m', label: 'Last 12M' },
  { id: 'custom', label: 'Custom' },
]

function PeriodSelector({ preset, fromDate, toDate, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {PRESETS.map(p => (
        <button
          key={p.id}
          onClick={() => onChange(p.id)}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors
            ${preset === p.id
              ? 'bg-[#2C4A70] text-white'
              : 'bg-white border border-slate-200 text-slate-600 hover:border-[#2C4A70]/35 hover:text-[#2C4A70]'
            }`}
        >
          {p.label}
        </button>
      ))}
      {preset === 'custom' && (
        <div className="flex items-center gap-1.5 ml-1">
          <input
            type="date" value={fromDate}
            onChange={e => onChange('custom', e.target.value, toDate)}
            className="border border-slate-200 rounded-lg px-2 py-1 text-xs text-slate-700"
          />
          <span className="text-slate-400 text-xs">–</span>
          <input
            type="date" value={toDate}
            onChange={e => onChange('custom', fromDate, e.target.value)}
            className="border border-slate-200 rounded-lg px-2 py-1 text-xs text-slate-700"
          />
        </div>
      )}
    </div>
  )
}

// ─── Monthly bar chart (CSS only) ────────────────────────────────────────────

function MonthlyBars({ data, keys, colors, height = 96 }) {
  if (!data?.length) return <Empty msg="No trend data." />
  const vals = data.flatMap(m => keys.map(k => parseFloat(m[k] || 0)))
  const maxV = Math.max(...vals, 1)
  const monthLabel = (label) => label?.slice(5) ?? ''

  return (
    <div className="flex items-end gap-1 overflow-x-auto pb-4" style={{ height: height + 28 }}>
      {data.map((m, i) => (
        <div key={i} className="flex flex-col items-center gap-0.5 min-w-[32px]">
          <div className="flex items-end gap-0.5" style={{ height }}>
            {keys.map((k, ki) => {
              const v = parseFloat(m[k] || 0)
              const pct = Math.max(Math.round((v / maxV) * 100), v > 0 ? 2 : 0)
              return (
                <div
                  key={ki}
                  className={`w-3 rounded-t ${colors[ki]}`}
                  style={{ height: `${pct}%` }}
                  title={`${k}: ${fmt(m[k])}`}
                />
              )
            })}
          </div>
          <span className="text-[9px] text-slate-400">{monthLabel(m.label)}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Expense category bars (horizontal) ──────────────────────────────────────

function CategoryBar({ name, amount, percentage, color = 'bg-rose-400' }) {
  return (
    <div className="mb-2.5">
      <div className="flex justify-between text-sm mb-0.5">
        <span className="text-slate-700">{name}</span>
        <span className="text-slate-600 font-mono">{fmt(amount)} <span className="text-slate-400">({pct(percentage)})</span></span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.min(percentage, 100)}%` }} />
      </div>
    </div>
  )
}

// ─── Balance-sheet tree node ──────────────────────────────────────────────────

function TreeNode({ node, level = 0 }) {
  const [open, setOpen] = useState(level < 2)
  const bal = parseFloat(node.balance ?? 0)
  const hasKids = node.children?.length > 0

  return (
    <div>
      <div
        className={`flex items-center justify-between py-1.5 rounded hover:bg-slate-50
          ${node.is_group ? 'font-semibold' : ''}`}
        style={{ paddingLeft: `${level * 18 + 6}px` }}
      >
        <button
          className="flex items-center gap-1 text-left flex-1 min-w-0"
          onClick={() => hasKids && setOpen(o => !o)}
        >
          {hasKids
            ? open ? <ChevronDown size={13} className="text-slate-400 shrink-0" />
              : <ChevronRight size={13} className="text-slate-400 shrink-0" />
            : <span className="w-3.5 shrink-0" />}
          <span className={`truncate ${node.is_group ? 'text-slate-700' : 'text-slate-600'}`}>{node.name}</span>
          <span className="text-slate-400 text-xs ml-1 shrink-0">{node.code}</span>
        </button>
        <span className={`font-mono text-sm ml-4 shrink-0 ${bal < 0 ? 'text-rose-600' : node.is_group ? 'text-slate-800' : 'text-slate-700'}`}>
          {fmt(node.balance)}
        </span>
      </div>
      {open && hasKids && (
        <div>
          {node.children.map(c => <TreeNode key={c.id} node={c} level={level + 1} />)}
        </div>
      )}
    </div>
  )
}

// ─── Insights panel ──────────────────────────────────────────────────────────

function InsightsPanel({ reportType, data }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const run = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await API.reports.insights({ reportType, data })
      setResult(res)
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-[#2C4A70]/15 bg-[#2C4A70]/5 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#2C4A70] font-semibold text-sm">
          <Sparkles size={15} />
          AI Insights
          <span className="text-slate-400 font-normal text-xs">(requires LLM provider in Settings)</span>
        </div>
        <button
          onClick={() => { setOpen(o => !o); if (!open && !result) run() }}
          className="text-xs px-3 py-1 rounded-full bg-[#2C4A70] text-white hover:bg-[#1F344F] transition-colors"
        >
          {open ? 'Hide' : 'Analyse'}
        </button>
      </div>
      {open && (
        <div className="mt-3">
          {loading && <div className="flex items-center gap-2 text-[#2C4A70] text-sm"><RefreshCw size={14} className="animate-spin" /> Thinking…</div>}
          {result?.error && <div className="flex items-center gap-2 text-slate-500 text-sm"><AlertCircle size={14} />{result.error}</div>}
          {result?.insight && (
            <p className="text-slate-700 text-sm leading-relaxed">{result.insight}</p>
          )}
          {result && !loading && (
            <button onClick={run} className="mt-2 text-xs text-[#2C4A70] hover:text-[#2C4A70]">
              ↺ Regenerate
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Summary Tab ─────────────────────────────────────────────────────────────

function SummaryTab({ fromDate, toDate }) {
  const [data, setData] = useState(null)
  const [trend, setTrend] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoad(true); setError(null)
    try {
      const [s, t] = await Promise.all([
        API.reports.summary({ fromDate, toDate }),
        API.reports.netWorthHistory(12),
      ])
      setData(s); setTrend(t)
    } catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [fromDate, toDate])

  useEffect(() => { load() }, [load])

  if (loading) return <Spinner />
  if (error) return <div className="text-rose-600 text-sm p-4">{error}</div>
  if (!data) return <Empty />

  const netIncome = parseFloat(data.net_income ?? 0)

  return (
    <div className="space-y-6">
      {/* KPIs row 1: balance sheet */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Net Worth" value={fmt(data.net_worth)} color="indigo" icon={Wallet} sub={`as of ${data.as_of}`} />
        <KpiCard label="Total Assets" value={fmt(data.total_assets)} color="emerald" icon={TrendingUp} />
        <KpiCard label="Total Liabilities" value={fmt(data.total_liabilities)} color="rose" icon={CreditCard} />
      </div>

      {/* KPIs row 2: period cash flow */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Period Income" value={fmt(data.period_income)} color="emerald" icon={TrendingUp} sub={`${data.from_date} – ${data.to_date}`} />
        <KpiCard label="Period Expenses" value={fmt(data.period_expenses)} color="rose" icon={TrendingDown} />
        <KpiCard
          label="Net Cash Flow"
          value={fmt(data.net_income)}
          color={netIncome >= 0 ? 'emerald' : 'rose'}
          sub={data.savings_rate > 0 ? `Savings rate ${pct(data.savings_rate)}` : undefined}
        />
      </div>

      {/* Layout: top expenses + NW history */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top expenses */}
        <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-700 mb-4">Where money went this period</h3>
          {data.top_expenses?.length > 0
            ? data.top_expenses.map(e => (
              <CategoryBar key={e.code} name={e.name} amount={e.amount}
                percentage={parseFloat(data.period_expenses) > 0
                  ? (parseFloat(e.amount) / parseFloat(data.period_expenses) * 100) : 0}
              />
            ))
            : <Empty msg="No expenses recorded." />}
        </div>

        {/* Net worth trend */}
        <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-700 mb-2">How your net worth has moved (12 months)</h3>
          <div className="flex gap-3 mb-3 text-xs">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[#2C4A70] inline-block" /> Net Worth</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-400 inline-block" /> Assets</span>
          </div>
          <MonthlyBars
            data={trend}
            keys={['net_worth', 'total_assets']}
            colors={['bg-[#2C4A70]', 'bg-emerald-200']}
          />
        </div>
      </div>

      {/* LLM insights */}
      <InsightsPanel reportType="Financial Summary" data={{
        net_worth: data.net_worth,
        total_assets: data.total_assets,
        total_liabilities: data.total_liabilities,
        period_income: data.period_income,
        period_expenses: data.period_expenses,
        savings_rate: data.savings_rate,
        top_expenses: data.top_expenses,
      }} />
    </div>
  )
}

// ─── Income & Expense Tab ─────────────────────────────────────────────────────

function IncomeExpenseTab({ fromDate, toDate }) {
  const [data, setData] = useState(null)
  const [trend, setTrend] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoad(true); setError(null)
    try {
      const [ie, t] = await Promise.all([
        API.reports.incomeExpense({ fromDate, toDate }),
        API.reports.monthlyTrend(12),
      ])
      setData(ie); setTrend(t)
    } catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [fromDate, toDate])

  useEffect(() => { load() }, [load])

  if (loading) return <Spinner />
  if (error) return <div className="text-rose-600 text-sm p-4">{error}</div>
  if (!data) return <Empty />

  const netIncome = parseFloat(data.net_income ?? 0)

  return (
    <div className="space-y-6">
      {/* Header KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Total Income" value={fmt(data.income?.total)} color="emerald" icon={TrendingUp} />
        <KpiCard label="Total Expenses" value={fmt(data.expenses?.total)} color="rose" icon={TrendingDown} />
        <KpiCard
          label="Net Income"
          value={fmt(data.net_income)}
          color={netIncome >= 0 ? 'emerald' : 'rose'}
          sub={`Savings rate ${pct(data.savings_rate)}`}
        />
      </div>

      {/* Income / Expense tables side-by-side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Income */}
        <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-emerald-700">Money coming in</h3>
            <span className="font-mono text-sm font-bold text-emerald-700">{fmt(data.income?.total)}</span>
          </div>
          {data.income?.items?.length > 0
            ? data.income.items.map(item => (
              <div key={item.code} className="flex justify-between py-1.5 border-b border-slate-50 last:border-0">
                <span className="text-sm text-slate-700">{item.name}</span>
                <span className="text-sm font-mono text-emerald-700">{fmt(item.amount)}</span>
              </div>
            ))
            : <Empty msg="No income recorded." />}
        </div>

        {/* Expenses */}
        <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-rose-700">Money going out</h3>
            <span className="font-mono text-sm font-bold text-rose-700">{fmt(data.expenses?.total)}</span>
          </div>
          {data.expenses?.items?.length > 0
            ? data.expenses.items.map(item => (
              <div key={item.code} className="flex justify-between py-1.5 border-b border-slate-50 last:border-0">
                <span className="text-sm text-slate-700">{item.name}</span>
                <span className="text-sm font-mono text-rose-700">{fmt(item.amount)}</span>
              </div>
            ))
            : <Empty msg="No expenses recorded." />}
        </div>
      </div>

      {/* Monthly trend */}
      <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
        <h3 className="text-sm font-bold text-slate-700 mb-2">Income vs expenses over 12 months</h3>
        <div className="flex gap-4 mb-3 text-xs">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-400 inline-block" /> Income</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-rose-400 inline-block" /> Expenses</span>
        </div>
        <MonthlyBars data={trend} keys={['income', 'expenses']} colors={['bg-emerald-400', 'bg-rose-400']} />
      </div>

      {/* LLM insights */}
      <InsightsPanel reportType="Income & Expense Statement" data={{
        from_date: data.from_date, to_date: data.to_date,
        total_income: data.income?.total, total_expenses: data.expenses?.total,
        net_income: data.net_income, savings_rate: data.savings_rate,
        income_breakdown: data.income?.items, expense_breakdown: data.expenses?.items,
      }} />
    </div>
  )
}

// ─── Balance Sheet Tab ────────────────────────────────────────────────────────

function BalanceSheetTab() {
  const [asOf, setAsOf] = useState(today())
  const [data, setData] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoad(true); setError(null)
    try { setData(await API.reports.balanceSheet({ asOf })) }
    catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [asOf])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <label className="text-sm text-slate-600 font-medium">As of</label>
        <input
          type="date" value={asOf}
          onChange={e => setAsOf(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700"
        />
      </div>

      {loading ? <Spinner /> : error
        ? <div className="text-rose-600 text-sm">{error}</div>
        : !data ? <Empty />
          : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Assets */}
              <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-2">
                  <h3 className="font-bold text-emerald-700">What you own</h3>
                  <span className="font-mono font-bold text-emerald-700">{fmt(data.total_assets)}</span>
                </div>
                {data.assets?.length > 0
                  ? data.assets.map(n => <TreeNode key={n.id} node={n} />)
                  : <Empty msg="No asset accounts." />}
              </div>

              {/* Liabilities */}
              <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-2">
                  <h3 className="font-bold text-rose-700">What you owe</h3>
                  <span className="font-mono font-bold text-rose-700">{fmt(data.total_liabilities)}</span>
                </div>
                {data.liabilities?.length > 0
                  ? data.liabilities.map(n => <TreeNode key={n.id} node={n} />)
                  : <Empty msg="No liability accounts." />}

                {/* Net Worth footer */}
                <div className="mt-4 pt-3 border-t border-slate-200 flex justify-between items-center">
                  <span className="font-semibold text-slate-700">Net Worth</span>
                  <span className={`font-mono font-bold text-lg ${parseFloat(data.net_worth) >= 0 ? 'text-[#2C4A70]' : 'text-rose-600'}`}>
                    {fmt(data.net_worth)}
                  </span>
                </div>
              </div>
            </div>
          )
      }
    </div>
  )
}

// ─── Expense Analytics Tab ────────────────────────────────────────────────────

function ExpenseAnalyticsTab({ fromDate, toDate }) {
  const [data, setData] = useState(null)
  const [trend, setTrend] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoad(true); setError(null)
    try {
      const [cats, t] = await Promise.all([
        API.reports.expenseCategories({ fromDate, toDate }),
        API.reports.monthlyTrend(12),
      ])
      setData(cats); setTrend(t)
    } catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [fromDate, toDate])

  useEffect(() => { load() }, [load])

  if (loading) return <Spinner />
  if (error) return <div className="text-rose-600 text-sm p-4">{error}</div>
  if (!data) return <Empty />

  return (
    <div className="space-y-6">
      {/* Total card */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <KpiCard label="Total Expenses" value={fmt(data.total)} color="rose" icon={TrendingDown}
          sub={`${data.from_date} – ${data.to_date}`}
        />
        <KpiCard label="Categories" value={data.categories?.length ?? 0} color="slate" icon={PieChart} />
      </div>

      {/* Category breakdown */}
      <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
        <h3 className="text-sm font-bold text-slate-700 mb-4">Where your money went, by category</h3>
        {data.categories?.length > 0
          ? data.categories.map(cat => (
            <CategoryBar key={cat.code} name={cat.name} amount={cat.amount} percentage={cat.percentage} />
          ))
          : <Empty msg="No expenses in this period." />}
      </div>

      {/* Monthly spend trend */}
      <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
        <h3 className="text-sm font-bold text-slate-700 mb-2">How much you spent each month (12 months)</h3>
        <MonthlyBars data={trend} keys={['expenses']} colors={['bg-rose-400']} />
      </div>
    </div>
  )
}

// ─── Account Statement Tab ────────────────────────────────────────────────────

function AccountStatementTab({ fromDate, toDate }) {
  const [accounts, setAccounts] = useState([])
  const [selected, setSelected] = useState('')
  const [stmt, setStmt] = useState(null)
  const [loading, setLoad] = useState(false)
  const [accsLoading, setAccsLoad] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    API.reports.accountsList()
      .then(list => { setAccounts(list); if (list.length) setSelected(String(list[0].id)) })
      .catch(e => setError(e.message))
      .finally(() => setAccsLoad(false))
  }, [])

  const load = useCallback(async () => {
    if (!selected) return
    setLoad(true); setError(null)
    try { setStmt(await API.reports.accountStatement(selected, { fromDate, toDate })) }
    catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [selected, fromDate, toDate])

  useEffect(() => { if (selected) load() }, [load, selected])

  return (
    <div className="space-y-5">
      {/* Account selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm text-slate-600 font-medium shrink-0">Account</label>
        {accsLoading
          ? <span className="text-sm text-slate-400">Loading accounts…</span>
          : (
            <select
              value={selected}
              onChange={e => setSelected(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 flex-1 max-w-xs"
            >
              {accounts.map(a => (
                <option key={a.id} value={String(a.id)}>{a.name} ({a.code})</option>
              ))}
            </select>
          )}
      </div>

      {loading ? <Spinner /> : error
        ? <div className="text-rose-600 text-sm">{error}</div>
        : !stmt ? <Empty />
          : (
            <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
              { /* Account header */}
              <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-700">{stmt.account?.name}</span>
                  <span className="text-slate-400 text-xs ml-2">{stmt.account?.code}</span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-500">Opening</div>
                  <div className="font-mono text-sm font-semibold text-slate-700">{fmt(stmt.opening_balance)}</div>
                </div>
              </div>

              {/* Transaction rows */}
              {stmt.entries?.length === 0 ? (
                <div className="px-5 py-8 text-center text-slate-400 text-sm">No transactions in this period.</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
                      <th className="text-left px-4 py-2">Date</th>
                      <th className="text-left px-4 py-2">Description</th>
                      <th className="text-right px-4 py-2">Debit</th>
                      <th className="text-right px-4 py-2">Credit</th>
                      <th className="text-right px-4 py-2">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stmt.entries.map((e, i) => (
                      <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="px-4 py-2 text-slate-500 whitespace-nowrap">{e.date}</td>
                        <td className="px-4 py-2 text-slate-700 max-w-xs truncate">{e.description}</td>
                        <td className="px-4 py-2 font-mono text-right text-rose-700">{e.debit ? fmt(e.debit) : ''}</td>
                        <td className="px-4 py-2 font-mono text-right text-emerald-700">{e.credit ? fmt(e.credit) : ''}</td>
                        <td className="px-4 py-2 font-mono text-right text-slate-800">{fmt(e.balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {/* Closing balance footer */}
              <div className="px-5 py-3 bg-slate-50 border-t border-slate-200 flex justify-end gap-10">
                <span className="text-sm text-slate-500">Closing Balance</span>
                <span className="font-mono font-bold text-slate-800">{fmt(stmt.closing_balance)}</span>
              </div>
            </div>
          )
      }
    </div>
  )
}

// ─── Journal / Day Book Tab ─────────────────────────────────────────────────

const TXN_TYPE_COLOR = {
  INCOME: 'bg-emerald-100 text-emerald-800',
  EXPENSE: 'bg-rose-100 text-rose-800',
  TRANSFER: 'bg-sky-100 text-sky-800',
  JOURNAL: 'bg-slate-100 text-slate-700',
}

// One leg = account code + name + amount in a stacked chip layout
function LegCell({ legs, side }) {
  if (!legs || legs.length === 0) return <td className="px-4 py-3 border-l border-slate-100" />
  const isDebit = side === 'Dr'
  return (
    <td className="px-4 py-3 border-l border-slate-100 align-top min-w-[200px]">
      <div className={`flex gap-2 ${legs.length > 1 ? 'divide-x divide-slate-100' : ''}`}>
        {legs.map((leg, i) => (
          <div key={i} className={`flex flex-col gap-0.5 ${legs.length > 1 ? 'px-2 first:pl-0' : ''}`}>
            <div className="flex items-center gap-1">
              <span className="text-slate-400 font-mono text-xs shrink-0">{leg.account_code}</span>
              <span
                title={leg.account_name}
                className={`text-xs truncate max-w-[140px] ${isDebit ? 'text-slate-600' : 'text-slate-500 italic'}`}
              >
                {leg.account_name}
              </span>
            </div>
            <span className={`font-mono text-sm font-bold ${isDebit ? 'text-rose-700' : 'text-emerald-700'}`}>
              {fmt(leg.amount)}
            </span>
          </div>
        ))}
      </div>
    </td>
  )
}

function JournalTab({ fromDate, toDate }) {
  const [data, setData] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 50

  const load = useCallback(async (p = 1) => {
    setLoad(true); setError(null)
    try {
      const res = await API.reports.journal({ fromDate, toDate, page: p, pageSize: PAGE_SIZE })
      setData(res)
      setPage(p)
    } catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [fromDate, toDate])

  useEffect(() => { load(1) }, [load])

  return (
    <div className="space-y-4">
      {data && !loading && (
        <div className="flex items-center justify-between text-sm text-slate-500">
          <span>
            {data.total} transaction{data.total !== 1 ? 's' : ''}
            {data.total_pages > 1 && ` · Page ${data.page} of ${data.total_pages}`}
          </span>
        </div>
      )}

      {loading ? <Spinner /> : error
        ? <div className="text-rose-600 text-sm">{error}</div>
        : !data || data.entries.length === 0
          ? <Empty msg="No transactions in this period." />
          : (
            <>
              <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-x-auto">
                <table className="w-full min-w-[860px] text-sm">
                  <thead>
                    <tr className="bg-slate-800 text-white text-xs font-semibold uppercase tracking-wide">
                      <th className="text-left px-4 py-3 w-24">Date</th>
                      <th className="text-left px-4 py-3 border-l border-slate-600">Description</th>
                      <th className="text-left px-4 py-3 w-20 border-l border-slate-600">Type</th>
                      <th className="text-left px-4 py-3 border-l border-slate-600">
                        <span className="text-rose-300">Dr</span> — Debit
                      </th>
                      <th className="text-left px-4 py-3 border-l border-slate-600">
                        <span className="text-emerald-300">Cr</span> — Credit
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.entries.map(entry => {
                      const badge = TXN_TYPE_COLOR[entry.transaction_type] ?? TXN_TYPE_COLOR.JOURNAL
                      return (
                        <tr key={entry.id} className="hover:bg-slate-50 align-top">
                          <td className="px-4 py-3 text-slate-400 font-mono text-xs whitespace-nowrap">
                            {entry.date}
                          </td>
                          <td className="px-4 py-3 border-l border-slate-100">
                            <div className="text-slate-800 font-medium">{entry.description}</div>
                            {entry.reference_number && (
                              <div className="text-slate-400 text-xs font-mono mt-0.5">{entry.reference_number}</div>
                            )}
                          </td>
                          <td className="px-4 py-3 border-l border-slate-100">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold whitespace-nowrap ${badge}`}>
                              {entry.transaction_type}
                            </span>
                          </td>
                          <LegCell legs={entry.debits} side="Dr" />
                          <LegCell legs={entry.credits} side="Cr" />
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {data.total_pages > 1 && (
                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => load(page - 1)}
                    className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600
                               disabled:opacity-40 hover:bg-slate-50 transition-colors"
                  >
                    ← Prev
                  </button>
                  <span className="text-sm text-slate-500">{page} / {data.total_pages}</span>
                  <button
                    disabled={page >= data.total_pages}
                    onClick={() => load(page + 1)}
                    className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600
                               disabled:opacity-40 hover:bg-slate-50 transition-colors"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )
      }
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// Main ReportsPage
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Trial Balance Tab ────────────────────────────────────────────────────────

function TrialBalanceTab() {
  const [asOf, setAsOf] = useState(today())
  const [data, setData] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoad(true); setError(null)
    try { setData(await API.reports.trialBalance({ asOf })) }
    catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [asOf])

  useEffect(() => { load() }, [load])

  const TYPE_COLORS = {
    ASSET: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    LIABILITY: 'text-rose-700 bg-rose-50 border-rose-200',
    INCOME: 'text-sky-700 bg-sky-50 border-sky-200',
    EXPENSE: 'text-amber-700 bg-amber-50 border-amber-200',
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <label className="text-sm text-slate-600 font-medium">As of</label>
        <input
          type="date" value={asOf}
          onChange={e => setAsOf(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700"
        />
      </div>

      {loading ? <Spinner /> : error
        ? <div className="text-rose-600 text-sm">{error}</div>
        : !data ? <Empty />
          : (
            <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
              {/* Column headers */}
              <div className="grid grid-cols-[1fr_160px_160px] bg-slate-800 text-white text-xs font-semibold uppercase tracking-wide">
                <div className="px-5 py-3">Account</div>
                <div className="px-5 py-3 text-right border-l border-slate-600">Debit (Dr)</div>
                <div className="px-5 py-3 text-right border-l border-slate-600">Credit (Cr)</div>
              </div>

              {data.sections?.map(section => (
                <div key={section.account_type}>
                  {/* Section heading */}
                  <div className={`grid grid-cols-[1fr_160px_160px] border-b border-slate-100 ${TYPE_COLORS[section.account_type]}`}>
                    <div className="px-5 py-2 text-xs font-bold uppercase tracking-wider col-span-3">
                      {section.label}
                    </div>
                  </div>

                  {/* Account rows */}
                  {section.accounts.length === 0 ? (
                    <div className="px-5 py-3 text-slate-400 text-sm italic">No activity</div>
                  ) : section.accounts.map(acc => (
                    <div
                      key={acc.id}
                      className="grid grid-cols-[1fr_160px_160px] border-b border-slate-50 hover:bg-slate-50"
                    >
                      <div className="px-5 py-2.5 flex items-center gap-2">
                        <span className="text-slate-400 text-xs font-mono">{acc.code}</span>
                        <span className="text-slate-700 text-sm">{acc.name}</span>
                      </div>
                      <div className="px-5 py-2.5 text-right font-mono text-sm border-l border-slate-100
                                    text-slate-800">
                        {acc.debit_balance ? fmt(acc.debit_balance) : ''}
                      </div>
                      <div className="px-5 py-2.5 text-right font-mono text-sm border-l border-slate-100
                                    text-slate-800">
                        {acc.credit_balance ? fmt(acc.credit_balance) : ''}
                      </div>
                    </div>
                  ))}

                  {/* Section subtotal */}
                  <div className={`grid grid-cols-[1fr_160px_160px] border-b border-slate-200 font-semibold
                                 ${TYPE_COLORS[section.account_type]}`}>
                    <div className="px-5 py-2 text-xs">Total {section.label}</div>
                    <div className="px-5 py-2 text-right font-mono text-sm border-l border-slate-200">
                      {parseFloat(section.section_debit) > 0 ? fmt(section.section_debit) : ''}
                    </div>
                    <div className="px-5 py-2 text-right font-mono text-sm border-l border-slate-200">
                      {parseFloat(section.section_credit) > 0 ? fmt(section.section_credit) : ''}
                    </div>
                  </div>
                </div>
              ))}

              {/* Grand totals */}
              <div className="grid grid-cols-[1fr_160px_160px] bg-slate-800 text-white font-bold text-sm">
                <div className="px-5 py-3">Grand Total</div>
                <div className="px-5 py-3 text-right font-mono border-l border-slate-600">
                  {fmt(data.grand_total_debit)}
                </div>
                <div className="px-5 py-3 text-right font-mono border-l border-slate-600">
                  {fmt(data.grand_total_credit)}
                </div>
              </div>

              {/* Balance check */}
              {(() => {
                const dr = parseFloat(data.grand_total_debit ?? 0)
                const cr = parseFloat(data.grand_total_credit ?? 0)
                const diff = Math.abs(dr - cr)
                return diff < 0.01 && (dr > 0 || cr > 0) ? (
                  <div className="px-5 py-2 text-xs text-emerald-600 text-center bg-emerald-50 border-t border-emerald-100">
                    ✓ Books are balanced
                  </div>
                ) : diff > 0.01 ? (
                  <div className="px-5 py-2 text-xs text-rose-600 text-center bg-rose-50 border-t border-rose-100">
                    ⚠ Out of balance by {fmt(diff)} — check for missing entries
                  </div>
                ) : null
              })()}
            </div>
          )
      }
    </div>
  )
}

// ─── Ledger Book Tab ──────────────────────────────────────────────────────────

const LEDGER_CATEGORIES = [
  { id: 'ALL', label: 'All Accounts' },
  { id: 'ASSET', label: 'Assets' },
  { id: 'LIABILITY', label: 'Liabilities' },
  { id: 'INCOME', label: 'Income' },
  { id: 'EXPENSE', label: 'Expenses' },
]

const TYPE_ACCENT = {
  ASSET: { header: 'bg-emerald-700', badge: 'bg-emerald-100 text-emerald-800', dr: 'text-slate-700', cr: 'text-slate-700' },
  LIABILITY: { header: 'bg-rose-700', badge: 'bg-rose-100 text-rose-800', dr: 'text-slate-700', cr: 'text-slate-700' },
  INCOME: { header: 'bg-sky-700', badge: 'bg-sky-100 text-sky-800', dr: 'text-slate-700', cr: 'text-slate-700' },
  EXPENSE: { header: 'bg-amber-700', badge: 'bg-amber-100 text-amber-800', dr: 'text-slate-700', cr: 'text-slate-700' },
}

function LedgerAccountCard({ account }) {
  const [open, setOpen] = useState(true)
  const accent = TYPE_ACCENT[account.account_type] ?? TYPE_ACCENT.ASSET
  const opening = parseFloat(account.opening_balance ?? 0)
  const closing = parseFloat(account.closing_balance ?? 0)
  const hasEntries = account.entries?.length > 0

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden mb-4">
      {/* Account header bar */}
      <div className={`${accent.header} px-5 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <span className="text-white font-mono text-sm font-semibold">{account.code}</span>
          <span className="text-white font-semibold">{account.name}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${accent.badge}`}>
            {account.account_type}
          </span>
        </div>
        <button
          onClick={() => setOpen(o => !o)}
          className="text-white/70 hover:text-white transition-colors"
        >
          {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </button>
      </div>

      {open && (
        <>
          {/* Opening balance row */}
          <div className="bg-slate-50 px-5 py-2 text-sm border-b border-slate-100 flex justify-between">
            <span className="text-slate-500">Opening Balance</span>
            <span className={`font-mono font-semibold ${opening >= 0 ? 'text-slate-700' : 'text-rose-600'}`}>
              {fmt(account.opening_balance)}
            </span>
          </div>

          {/* Ledger table */}
          {!hasEntries ? (
            <div className="px-5 py-6 text-center text-slate-400 text-sm">No transactions in this period.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-500 border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-2 w-24">Date</th>
                  <th className="text-left px-4 py-2">Description</th>
                  <th className="text-right px-4 py-2 w-32 border-l border-slate-200">
                    <span className="text-rose-600 font-semibold">Dr</span>
                    <span className="text-slate-300 mx-1">/</span>
                    <span className="text-emerald-600 font-semibold">Cr</span>
                  </th>
                  <th className="text-right px-4 py-2 w-32 border-l border-slate-200">Balance</th>
                </tr>
              </thead>
              <tbody>
                {account.entries.map((entry, i) => (
                  <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="px-4 py-2 text-slate-400 text-xs whitespace-nowrap">{entry.date}</td>
                    <td className="px-4 py-2 text-slate-700 max-w-xs truncate">{entry.description}</td>
                    <td className="px-4 py-2 font-mono text-right border-l border-slate-100">
                      {entry.debit
                        ? <span className="text-rose-700 font-medium">{fmt(entry.debit)}</span>
                        : <span className="text-emerald-700 font-medium">{fmt(entry.credit)}</span>
                      }
                      <span className="text-slate-300 text-xs ml-1">{entry.debit ? 'Dr' : 'Cr'}</span>
                    </td>
                    <td className={`px-4 py-2 font-mono text-right border-l border-slate-100
                                    ${parseFloat(entry.balance) < 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                      {fmt(Math.abs(parseFloat(entry.balance)))}
                      <span className="text-slate-300 text-xs ml-1">
                        {parseFloat(entry.balance) >= 0
                          ? (account.normal_balance === 'DEBIT' ? 'Dr' : 'Cr')
                          : (account.normal_balance === 'DEBIT' ? 'Cr' : 'Dr')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Totals + closing row */}
          <div className="bg-slate-50 border-t border-slate-200">
            {hasEntries && (
              <div className="grid grid-cols-[1fr_auto_auto] gap-0 text-xs font-semibold text-slate-600">
                <div className="px-5 py-2">Period Totals</div>
                <div className="px-5 py-2 border-l border-slate-200 text-right text-rose-700 font-mono w-32">
                  {fmt(account.period_total_debit)} Dr
                </div>
                <div className="px-5 py-2 border-l border-slate-200 text-right text-emerald-700 font-mono w-32">
                  {fmt(account.period_total_credit)} Cr
                </div>
              </div>
            )}
            <div className="px-5 py-2 flex justify-between border-t border-slate-100 text-sm">
              <span className="text-slate-500">Closing Balance</span>
              <span className={`font-mono font-bold ${closing >= 0 ? 'text-slate-800' : 'text-rose-600'}`}>
                {fmt(account.closing_balance)}
                <span className="text-slate-400 text-xs ml-1">
                  {closing >= 0
                    ? (account.normal_balance === 'DEBIT' ? 'Dr' : 'Cr')
                    : (account.normal_balance === 'DEBIT' ? 'Cr' : 'Dr')}
                </span>
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function LedgerBookTab({ fromDate, toDate }) {
  const [category, setCategory] = useState('ALL')
  const [data, setData] = useState(null)
  const [loading, setLoad] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoad(true); setError(null)
    try {
      setData(await API.reports.generalLedger({
        fromDate, toDate,
        accountType: category === 'ALL' ? undefined : category,
      }))
    } catch (e) { setError(e.message) }
    finally { setLoad(false) }
  }, [fromDate, toDate, category])

  useEffect(() => { load() }, [load])

  const totalAccounts = data?.sections?.reduce((n, s) => n + s.accounts.length, 0) ?? 0

  return (
    <div className="space-y-5">
      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        {LEDGER_CATEGORIES.map(c => (
          <button
            key={c.id}
            onClick={() => setCategory(c.id)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors
              ${category === c.id
                ? 'bg-[#2C4A70] text-white'
                : 'bg-white border border-slate-200 text-slate-600 hover:border-[#2C4A70]/35 hover:text-[#2C4A70]'
              }`}
          >
            {c.label}
          </button>
        ))}
        {data && !loading && (
          <span className="ml-2 self-center text-xs text-slate-400">
            {totalAccounts} account{totalAccounts !== 1 ? 's' : ''} with activity
          </span>
        )}
      </div>

      {loading ? <Spinner /> : error
        ? <div className="text-rose-600 text-sm">{error}</div>
        : !data || data.sections?.length === 0 ? (
          <Empty msg="No accounts with activity in this period." />
        ) : (
          data.sections.map(section => (
            <div key={section.account_type}>
              {/* Section divider */}
              <div className="flex items-center gap-3 mb-3">
                <span className="text-xs font-bold uppercase tracking-widest text-slate-500">
                  {section.label}
                </span>
                <div className="flex-1 h-px bg-slate-200" />
                <span className="text-xs text-slate-400">{section.accounts.length} accounts</span>
              </div>

              {/* Account cards */}
              {section.accounts.map(acc => (
                <LedgerAccountCard key={acc.id} account={acc} />
              ))}
            </div>
          ))
        )
      }
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main ReportsPage
// ═══════════════════════════════════════════════════════════════════════════════

const TABS = [
  { id: 'summary', label: 'Summary', icon: BarChart2, needsPeriod: true },
  { id: 'ie', label: 'Income & Expense', icon: TrendingUp, needsPeriod: true },
  { id: 'balance', label: 'Balance Sheet', icon: FileText, needsPeriod: false },
  { id: 'expenses', label: 'Expense Analytics', icon: PieChart, needsPeriod: true },
  { id: 'journal', label: 'Journal', icon: ScrollText, needsPeriod: true },
  { id: 'ledger', label: 'Ledger Book', icon: Library, needsPeriod: true },
  { id: 'trial', label: 'Trial Balance', icon: Scale, needsPeriod: false },
  { id: 'statement', label: 'Account Statement', icon: BookOpen, needsPeriod: true },
]

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState('summary')
  const [preset, setPreset] = useState('this_month')
  const [{ fromDate, toDate }, setDates] = useState(() => getPeriodDates('this_month'))

  const handlePeriodChange = (newPreset, customFrom, customTo) => {
    setPreset(newPreset)
    if (newPreset === 'custom') {
      setDates({ fromDate: customFrom, toDate: customTo })
    } else {
      setDates(getPeriodDates(newPreset))
    }
  }

  const currentTab = TABS.find(t => t.id === activeTab)

  return (
    <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-10 py-8">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Reports</h1>
          <p className="text-sm text-slate-500 mt-0.5">Financial statements and analytics</p>
        </div>
      </div>

      {/* Tab nav */}
      <div className="flex flex-wrap gap-1 mb-6 bg-slate-100 rounded-xl p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold whitespace-nowrap transition-colors
              ${activeTab === id
                ? 'bg-white text-[#2C4A70] shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Period selector — shown only for tabs that use a period */}
      {currentTab?.needsPeriod && (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-3 mb-6">
          <PeriodSelector preset={preset} fromDate={fromDate} toDate={toDate} onChange={handlePeriodChange} />
        </div>
      )}

      {/* Tab content */}
      {activeTab === 'summary' && <SummaryTab fromDate={fromDate} toDate={toDate} />}
      {activeTab === 'ie' && <IncomeExpenseTab fromDate={fromDate} toDate={toDate} />}
      {activeTab === 'balance' && <BalanceSheetTab />}
      {activeTab === 'expenses' && <ExpenseAnalyticsTab fromDate={fromDate} toDate={toDate} />}
      {activeTab === 'journal' && <JournalTab fromDate={fromDate} toDate={toDate} />}
      {activeTab === 'ledger' && <LedgerBookTab fromDate={fromDate} toDate={toDate} />}
      {activeTab === 'trial' && <TrialBalanceTab />}
      {activeTab === 'statement' && <AccountStatementTab fromDate={fromDate} toDate={toDate} />}
    </div>
  )
}
