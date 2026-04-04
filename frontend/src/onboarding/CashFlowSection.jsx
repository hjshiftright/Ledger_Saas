import React, { useState } from 'react';
import {
  Home, Utensils, Car, Activity, Zap,
  TrendingUp, AlertCircle, ChevronRight, User, ArrowRight, Plus,
} from 'lucide-react';
import { FadeIn, Btn } from './shared.jsx';
import { saveJson } from './utils.js';
import { SK } from './constants.js';
import AnnualExpensesView from './AnnualExpensesView.jsx';

const DEFAULT_CF_CATS = [
  { id: 'housing',   icon: Home,     label: 'Housing',   sub: 'RENT / MORTGAGE',  color: 'bg-blue-100 text-blue-600',    amount: '' },
  { id: 'lifestyle', icon: Utensils, label: 'Lifestyle', sub: 'FOOD & DINING',    color: 'bg-orange-100 text-orange-600',amount: '' },
  { id: 'transport', icon: Car,      label: 'Transport', sub: 'FUEL & TRANSIT',   color: 'bg-slate-100 text-slate-600',  amount: '' },
  { id: 'wellness',  icon: Activity, label: 'Wellness',  sub: 'HEALTH & INSURE',  color: 'bg-teal-100 text-teal-600',   amount: '' },
  { id: 'utilities', icon: Zap,      label: 'Utilities', sub: 'DIGITAL & HOME',   color: 'bg-purple-100 text-purple-600',amount: '' },
];

export const DEFAULT_CASHFLOW = { primaryIncome: '', secondaryIncome: '', categories: DEFAULT_CF_CATS, completed: false };

export default function CashFlowSection({ data, setData, annualData, setAnnualData, onBack, onComplete }) {
  const [step,            setStep]           = useState(1);
  const [primaryIncome,   setPrimaryIncome]  = useState(data.primaryIncome   || '');
  const [secondaryIncome, setSecondaryIncome]= useState(data.secondaryIncome || '');
  const [categories,      setCategories]     = useState(
    data.categories?.length
      ? data.categories.map(c => ({ ...c, icon: DEFAULT_CF_CATS.find(d => d.id === c.id)?.icon || Plus }))
      : DEFAULT_CF_CATS
  );
  const [showAddCat, setShowAddCat] = useState(false);
  const [newCatName,  setNewCatName] = useState('');

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
        <div className="w-8 h-8 rounded-full bg-[#2C4A70] flex items-center justify-center">
          <User size={14} className="text-white" />
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
            {/* LEFT column */}
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
                  <input type="text" value={primaryIncome} onChange={e => setPrimaryIncome(e.target.value)} placeholder="0.00"
                    className="w-full bg-white border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-slate-800 placeholder-slate-300 text-sm font-semibold focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
                </div>

                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 block">Secondary / Variable Inflows</label>
                <textarea value={secondaryIncome} onChange={e => setSecondaryIncome(e.target.value)}
                  placeholder="e.g. Dividend payouts around ₹400 or freelance side-work" rows={3}
                  className="w-full bg-white border-2 border-slate-200 rounded-xl p-4 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all resize-none" />

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

            {/* RIGHT column */}
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
                          <input type="number" value={cat.amount} onChange={e => updateAmt(cat.id, e.target.value)} placeholder="0"
                            className="w-16 text-right text-sm font-bold text-slate-700 bg-transparent border-0 outline-none placeholder-slate-300 focus:ring-0 [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                        </div>
                      </div>
                    );
                  })}

                  {/* Add Category */}
                  {showAddCat ? (
                    <div className="flex items-center gap-2 border-2 border-dashed border-indigo-200 rounded-xl p-3.5 bg-indigo-50/40">
                      <input autoFocus type="text" value={newCatName} onChange={e => setNewCatName(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') addCategory(); if (e.key === 'Escape') setShowAddCat(false); }}
                        placeholder="Category name"
                        className="flex-1 text-sm bg-transparent outline-none text-slate-700 placeholder-slate-400 min-w-0" />
                      <button onClick={addCategory} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 shrink-0">Add</button>
                      <button onClick={() => setShowAddCat(false)} className="text-xs text-slate-400 hover:text-slate-600 shrink-0">✕</button>
                    </div>
                  ) : (
                    <button onClick={() => setShowAddCat(true)}
                      className="flex items-center justify-center gap-2 border-2 border-dashed border-slate-200 rounded-xl p-3.5 text-sm font-semibold text-slate-400 hover:border-[#2C4A70] hover:text-[#2C4A70] transition-colors bg-white">
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
        <button onClick={onBack} className="flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-[#2C4A70] transition-colors uppercase tracking-wide">
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
            <button onClick={() => persist()} className="px-5 py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors uppercase tracking-wide">
              Save Draft
            </button>
            <Btn onClick={() => { persist(); setStep(2); }}>Next: Annual Expenses</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}
