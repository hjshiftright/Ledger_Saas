import React, { useState, useRef } from 'react';
import { ChevronRight, User, PiggyBank, Check, ArrowRight } from 'lucide-react';
import { ProtonInline } from '../ProtonAssistant.jsx';
import { FadeIn, Btn } from './shared.jsx';
import { inr, saveJson } from './utils.js';
import { BUDGET_CATS, SK } from './constants.js';

export default function BudgetsSection({ data, setData, onBack, onComplete }) {
  const [incomeStr, setIncomeStr] = useState(data.income     || '');
  const [cats,      setCats]      = useState(data.categories || {});

  const protonRef = useRef(null);
  const handleProtonSend = async () => "I've noted that for your budget. You can adjust the suggested numbers manually.";

  const income = parseFloat(String(incomeStr).replace(/[^0-9.]/g, '')) || 0;

  const toggleCat = (id, pct) => {
    setCats(prev => {
      const next    = { ...prev };
      const current = next[id] || { enabled: false, amount: '' };
      if (!current.enabled) {
        const suggested = income > 0 ? Math.round(income * pct) : 0;
        next[id] = { enabled: true, amount: suggested || '' };
      } else {
        next[id] = { ...current, enabled: false };
      }
      return next;
    });
  };

  const updateAmt = (id, val) => {
    setCats(prev => ({ ...prev, [id]: { enabled: true, amount: val } }));
  };

  const persist = () => {
    const updated = { income: incomeStr, categories: cats };
    setData(updated);
    saveJson(SK.budgets || 'onboarding_v4_budgets', updated);
  };

  const totalBudgeted = Object.values(cats).reduce((acc, c) => acc + (c.enabled ? (parseFloat(c.amount) || 0) : 0), 0);

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-base italic font-serif font-bold text-[#2C4A70]">The Private Ledger</span>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-sm font-semibold text-slate-600">Budgeting Setup</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-[#2C4A70] flex items-center justify-center">
          <User size={14} className="text-white" />
        </div>
      </div>

      {/* Scroll area */}
      <div className="flex-1 overflow-y-auto px-8 py-8 w-full mx-auto">
        <FadeIn>
          <div className="flex gap-6 items-start">
            {/* LEFT column */}
            <div className="w-[65%] flex flex-col gap-5 shrink-0">
              <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <h1 className="text-[22px] font-black text-slate-800 leading-tight">Set up your monthly budget</h1>
                  <span className="text-slate-400"><PiggyBank size={20} /></span>
                </div>
                <p className="text-[13px] font-medium text-slate-500 mb-6">
                  Enter your monthly take-home income and we'll suggest category budgets based on common guidelines.
                </p>

                <div className="mb-8">
                  <p className="text-[12px] font-bold text-slate-500 mb-2">Monthly income (₹)</p>
                  <input type="text" value={incomeStr} onChange={e => setIncomeStr(e.target.value)} placeholder="e.g. 100000"
                    className="w-48 bg-white border-2 border-slate-100 rounded-xl px-4 py-2.5 text-slate-800 font-bold focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 outline-none transition-all shadow-sm" />
                </div>

                <p className="text-[12px] font-bold text-slate-500 mb-3">Suggested category budgets</p>
                <div className="grid grid-cols-2 gap-3 mb-6">
                  {BUDGET_CATS.map(cat => {
                    const st = cats[cat.id] || { enabled: false, amount: '' };
                    return (
                      <div key={cat.id} className={`flex items-center gap-3 border transition-colors rounded-xl p-3 ${st.enabled ? 'border-[#2C4A70]/30 bg-[#2C4A70]/5' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                        <button onClick={() => toggleCat(cat.id, cat.pct)}
                          className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-all ${st.enabled ? 'bg-[#2C4A70] border-[#2C4A70] text-white' : 'border-slate-300 bg-white'}`}>
                          {st.enabled && <Check size={12} strokeWidth={3} />}
                        </button>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-bold text-slate-800 leading-tight">{cat.label}</p>
                          <p className="text-[10px] text-slate-400 font-medium">{cat.pct * 100}% of income</p>
                        </div>
                        <input type="number" value={st.amount} onChange={e => updateAmt(cat.id, e.target.value)} placeholder="0" disabled={!st.enabled}
                          className="w-20 bg-white border border-slate-200 rounded-lg text-right text-sm font-semibold text-slate-700 px-3 py-1.5 focus:border-[#2C4A70] outline-none disabled:opacity-50" />
                      </div>
                    );
                  })}
                </div>

                <div className="flex justify-end">
                  <button onClick={() => { persist(); onComplete(); }} className="text-sm font-bold text-[#2C4A70] hover:text-[#1F344F] transition-colors">
                    Skip for now
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-3 mt-2">
                <h3 className="font-bold text-sm text-slate-800">This Month's Budget</h3>
                <span className="text-slate-400 font-medium text-xs">Total: {inr(totalBudgeted)}</span>
              </div>
            </div>

            {/* RIGHT column */}
            <div className="flex-1 sticky top-0 h-[600px] border border-slate-200 rounded-2xl overflow-hidden shadow-sm bg-white">
              <ProtonInline
                ref={protonRef}
                initialMessage="I'm Proton! I can help you structure your budget based on your spending habits."
                onSend={handleProtonSend}
              />
            </div>
          </div>
        </FadeIn>
      </div>

      {/* Footer nav */}
      <div className="bg-white border-t border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <button onClick={onBack} className="flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-[#2C4A70] transition-colors uppercase tracking-wide">
          <ArrowRight size={14} className="rotate-180" /> Back to Accounts
        </button>
        <div className="flex items-center gap-3">
          <button onClick={() => persist()} className="px-5 py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors uppercase tracking-wide">
            Save Draft
          </button>
          <Btn onClick={() => { persist(); onComplete(); }}>Next: Set Goals</Btn>
        </div>
      </div>
    </div>
  );
}
