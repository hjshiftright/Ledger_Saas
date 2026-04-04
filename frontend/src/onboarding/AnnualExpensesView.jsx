import React, { useState, useEffect } from 'react';
import {
  Shield, Briefcase, Bell, GraduationCap, CreditCard,
  ChevronRight, User, Plus, Edit2, Trash2, ArrowRight,
} from 'lucide-react';
import { API } from '../api.js';
import { FadeIn, Btn } from './shared.jsx';
import { inr, saveJson } from './utils.js';
import { MONTHS_SHORT, SK } from './constants.js';

const ANNUAL_ITEM_ICONS = {
  insurance: Shield,
  vacation:  Briefcase,
  festival:  Bell,
  school:    GraduationCap,
  custom:    CreditCard,
};

const DUMMY_ANNUAL_ITEMS = [
  { id: 'dummy_1', label: 'Health Insurance Premium',   desc: 'Annual family floater policy renewal',     amount: '25000',  months: ['APR'],        iconKey: 'insurance' },
  { id: 'dummy_2', label: 'Vehicle Insurance',          desc: 'Car / two-wheeler insurance renewal',      amount: '12000',  months: ['JAN'],        iconKey: 'insurance' },
  { id: 'dummy_3', label: 'Family Vacation',            desc: 'Summer holiday travel & stay',             amount: '60000',  months: ['MAY'],        iconKey: 'vacation'  },
  { id: 'dummy_4', label: 'Diwali & Festive Spending',  desc: 'Gifts, sweets, home décor, new clothes',   amount: '30000',  months: ['OCT','NOV'],  iconKey: 'festival'  },
  { id: 'dummy_5', label: 'School / Tuition Fees',      desc: 'Annual school admission & tuition',        amount: '80000',  months: ['APR','JUN'],  iconKey: 'school'    },
  { id: 'dummy_6', label: 'Annual Subscriptions',       desc: 'OTT, cloud storage, software renewals',    amount: '8000',   months: ['JAN'],        iconKey: 'custom'    },
];

export default function AnnualExpensesView({ data, setData, onBack, onComplete }) {
  const [isDummy, setIsDummy] = useState(() => {
    if (!data.items?.length) return true;
    return data.items.every(i => String(i.id).startsWith('dummy_'));
  });
  const [items,    setItems]    = useState(() => !data.items?.length ? DUMMY_ANNUAL_ITEMS : data.items);
  const [showAdd,  setShowAdd]  = useState(false);
  const [newItem,  setNewItem]  = useState({ label: '', desc: '', amount: '', months: [] });
  const [editId,   setEditId]   = useState(null);
  const [editItem, setEditItem] = useState(null);
  const [saving,   setSaving]   = useState(false);

  const clearDummy = () => { setItems([]); setIsDummy(false); };

  useEffect(() => {
    API.dashboard.load()
      .then(d => {
        if (d?.annualExpenses?.length) {
          setItems(d.annualExpenses);
          setData(prev => ({ ...prev, items: d.annualExpenses }));
          saveJson(SK.annualexpenses, { ...data, items: d.annualExpenses });
        }
      })
      .catch(() => {});
  }, []);

  const totalOutlay       = items.reduce((acc, item) => acc + (parseFloat(item.amount) || 0), 0);
  const monthlyReserve    = Math.round(totalOutlay / 12);
  const monthsWithExpenses = new Set(items.flatMap(item => item.months));

  const toggleMonth = (m) =>
    setNewItem(prev => ({
      ...prev,
      months: prev.months.includes(m) ? prev.months.filter(x => x !== m) : [...prev.months, m],
    }));

  const addItem = () => {
    if (!newItem.label.trim() || !newItem.amount) return;
    setIsDummy(false);
    setItems(prev => [...prev, { ...newItem, id: `custom_${Date.now()}`, iconKey: 'custom' }]);
    setNewItem({ label: '', desc: '', amount: '', months: [] });
    setShowAdd(false);
  };

  const removeItem = (id) => { setIsDummy(false); setItems(prev => prev.filter(i => i.id !== id)); };

  const startEdit  = (item) => { setEditId(item.id); setEditItem({ label: item.label, desc: item.desc || '', amount: String(item.amount), months: [...item.months] }); setShowAdd(false); };
  const cancelEdit = () => { setEditId(null); setEditItem(null); };
  const saveEdit   = () => {
    if (!editItem.label.trim() || !editItem.amount) return;
    setIsDummy(false);
    const newId = String(editId).startsWith('dummy_') ? `custom_${Date.now()}` : editId;
    setItems(prev => prev.map(i => i.id === editId ? { ...i, ...editItem, id: newId } : i));
    cancelEdit();
  };
  const toggleEditMonth = (m) =>
    setEditItem(prev => ({
      ...prev,
      months: prev.months.includes(m) ? prev.months.filter(x => x !== m) : [...prev.months, m],
    }));

  const persist = async (extra = {}) => {
    const updated = { ...data, items, ...extra };
    setData(updated);
    saveJson(SK.annualexpenses, updated);
    setSaving(true);
    try { await API.dashboard.save({ annualExpenses: updated.items }); } catch (_) { /* silent */ } finally { setSaving(false); }
    return updated;
  };

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-base italic font-serif font-bold text-[#2C4A70]">The Private Ledger</span>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-sm font-semibold text-slate-600">Annual Irregular Expense Mapping</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-[#2C4A70] flex items-center justify-center">
          <User size={14} className="text-white" />
        </div>
      </div>

      {/* Scroll area */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <FadeIn>
          <h1 className="text-4xl font-serif font-black text-[#2C4A70] leading-tight mb-2">
            Some expenses don't happen every month.
          </h1>
          <p className="text-slate-500 mb-4 max-w-2xl text-[15px]">
            Think about insurance premiums, annual subscriptions, festival spending, vacations, and school admissions. These "lumpy" costs often derail monthly budgets.
          </p>

          {isDummy && (
            <div className="mb-6 flex items-center justify-between bg-amber-50 border border-amber-200 rounded-2xl px-5 py-3.5">
              <div className="flex items-center gap-2.5 text-amber-700">
                <span className="text-base">⚠️</span>
                <p className="text-sm font-medium">
                  These are <strong>sample expenses</strong> to help you get started — not your real data. Edit any entry, remove what doesn't apply, or clear all and start fresh.
                </p>
              </div>
              <button onClick={clearDummy}
                className="ml-4 shrink-0 text-xs font-bold text-amber-700 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
                Clear & Start Fresh
              </button>
            </div>
          )}

          <div className="flex gap-6 items-start">
            {/* LEFT: Projected Annual Outlays */}
            <div className="flex-1 flex flex-col gap-4">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                  <h3 className="text-[15px] font-bold text-slate-800">Projected Annual Outlays</h3>
                  <div className="flex items-center gap-2">
                    {items.length > 0 && (
                      <button onClick={clearDummy} className="text-xs font-bold text-slate-400 hover:text-rose-500 hover:bg-rose-50 px-3 py-1.5 rounded-lg transition-colors">
                        Clear all
                      </button>
                    )}
                    <button onClick={() => { setShowAdd(v => !v); setEditId(null); setEditItem(null); }}
                      className="flex items-center gap-1.5 text-xs font-bold text-[#2C4A70] hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors">
                      <Plus size={13} /> Add New
                    </button>
                  </div>
                </div>

                <div className="divide-y divide-slate-100">
                  {items.length === 0 && (
                    <div className="px-6 py-8 text-center">
                      <div className="w-12 h-12 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200 flex items-center justify-center mx-auto mb-3">
                        <Bell size={20} className="text-slate-300" />
                      </div>
                      <p className="text-sm font-semibold text-slate-500 mb-1">No annual expenses added yet</p>
                      <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
                        Add things like insurance premiums, school fees, vacations, or festival budgets — expenses that hit once a year and catch you off guard.
                      </p>
                    </div>
                  )}

                  {items.map(item => {
                    const Icon = ANNUAL_ITEM_ICONS[item.iconKey] || CreditCard;
                    const amt  = parseFloat(item.amount) || 0;
                    const isEditing = editId === item.id;
                    return (
                      <div key={item.id}>
                        {/* Normal row */}
                        {!isEditing && (
                          <div className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/60 transition-colors group">
                            <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center shrink-0 text-slate-500">
                              <Icon size={16} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <p className="text-sm font-bold text-slate-800 truncate">{item.label}</p>
                                {String(item.id).startsWith('dummy_') && (
                                  <span className="text-[9px] font-bold bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded tracking-wider shrink-0">SAMPLE</span>
                                )}
                              </div>
                              <p className="text-xs text-slate-400 truncate">{item.desc}</p>
                            </div>
                            <div className="text-right shrink-0">
                              <p className="text-sm font-black text-[#2C4A70]">₹{amt.toLocaleString('en-IN')}</p>
                              <div className="flex gap-1 justify-end mt-1">
                                {item.months.map(m => (
                                  <span key={m} className="text-[9px] font-bold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded tracking-widest">{m}</span>
                                ))}
                              </div>
                            </div>
                            <div className="opacity-0 group-hover:opacity-100 transition-opacity ml-2 flex items-center gap-1">
                              <button onClick={() => startEdit(item)} className="text-slate-300 hover:text-[#2C4A70] p-1"><Edit2 size={14} /></button>
                              <button onClick={() => removeItem(item.id)} className="text-slate-300 hover:text-rose-500 p-1"><Trash2 size={14} /></button>
                            </div>
                          </div>
                        )}

                        {/* Inline edit form */}
                        {isEditing && (
                          <div className="px-6 py-4 bg-indigo-50/40 border-t border-indigo-100">
                            <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3">Edit Item</p>
                            <div className="flex gap-3 mb-3">
                              <input type="text" placeholder="Expense name" value={editItem.label}
                                onChange={e => setEditItem(p => ({ ...p, label: e.target.value }))}
                                className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10" />
                              <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">₹</span>
                                <input type="number" placeholder="0" value={editItem.amount}
                                  onChange={e => setEditItem(p => ({ ...p, amount: e.target.value }))}
                                  className="w-32 text-sm border border-slate-200 rounded-lg pl-7 pr-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                              </div>
                            </div>
                            <input type="text" placeholder="Short description (optional)" value={editItem.desc}
                              onChange={e => setEditItem(p => ({ ...p, desc: e.target.value }))}
                              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 mb-3" />
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {MONTHS_SHORT.map(m => (
                                <button key={m} onClick={() => toggleEditMonth(m)}
                                  className={`text-[10px] font-bold px-2.5 py-1 rounded-full transition-colors ${
                                    editItem.months.includes(m) ? 'bg-[#2C4A70] text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                                  }`}>{m}</button>
                              ))}
                            </div>
                            <div className="flex justify-end gap-2">
                              <button onClick={cancelEdit} className="text-xs font-semibold text-slate-400 hover:text-slate-600 px-3 py-1.5 transition-colors">Cancel</button>
                              <button onClick={saveEdit} disabled={!editItem.label.trim() || !editItem.amount}
                                className="text-xs font-bold bg-[#2C4A70] text-white px-4 py-1.5 rounded-lg hover:bg-[#1e3557] disabled:opacity-40 transition-colors">
                                Save Changes
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Add new item form */}
                {showAdd && (
                  <div className="px-6 py-4 bg-indigo-50/40 border-t border-indigo-100">
                    <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3">New Annual Outlay</p>
                    <div className="flex gap-3 mb-3">
                      <input type="text" placeholder="Expense name" value={newItem.label}
                        onChange={e => setNewItem(p => ({ ...p, label: e.target.value }))}
                        className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10" />
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">₹</span>
                        <input type="number" placeholder="0" value={newItem.amount}
                          onChange={e => setNewItem(p => ({ ...p, amount: e.target.value }))}
                          className="w-32 text-sm border border-slate-200 rounded-lg pl-7 pr-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                      </div>
                    </div>
                    <input type="text" placeholder="Short description (optional)" value={newItem.desc}
                      onChange={e => setNewItem(p => ({ ...p, desc: e.target.value }))}
                      className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 mb-3" />
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {MONTHS_SHORT.map(m => (
                        <button key={m} onClick={() => toggleMonth(m)}
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-full transition-colors ${
                            newItem.months.includes(m) ? 'bg-[#2C4A70] text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}>{m}</button>
                      ))}
                    </div>
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setShowAdd(false)} className="text-xs font-semibold text-slate-400 hover:text-slate-600 px-3 py-1.5 transition-colors">Cancel</button>
                      <button onClick={addItem} disabled={!newItem.label.trim() || !newItem.amount}
                        className="text-xs font-bold bg-[#2C4A70] text-white px-4 py-1.5 rounded-lg hover:bg-[#1e3557] disabled:opacity-40 transition-colors">
                        Add Outlay
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* RIGHT: Intensity grid + cards */}
            <div className="w-[340px] shrink-0 flex flex-col gap-4">
              {/* Cash Outflow Intensity */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <h3 className="text-[15px] font-bold text-slate-800 mb-4">Cash Outflow Intensity</h3>
                <div className="grid grid-cols-4 gap-2 mb-6">
                  {MONTHS_SHORT.map(m => {
                    const active = monthsWithExpenses.has(m);
                    return (
                      <div key={m} className={`rounded-xl py-3 flex flex-col items-center gap-1.5 border transition-colors ${
                        active ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-100'
                      }`}>
                        <span className={`text-[10px] font-bold tracking-widest ${active ? 'text-green-700' : 'text-slate-400'}`}>{m}</span>
                        {active && <div className="w-1.5 h-1.5 rounded-full bg-green-500" />}
                      </div>
                    );
                  })}
                </div>
                <div className="border-t border-slate-100 pt-4">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Total Non-Monthly Outlay</p>
                  <p className="text-3xl font-black text-[#2C4A70]">₹{totalOutlay.toLocaleString('en-IN')}</p>
                  <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                    Requires a monthly reserve of ~₹{monthlyReserve.toLocaleString('en-IN')} to remain liquid.
                  </p>
                </div>
              </div>

              {/* Sinking Fund Strategy */}
              <div className="bg-[#2C4A70] rounded-2xl p-6 text-white relative overflow-hidden">
                <div className="absolute top-4 right-4 w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-sm">💡</div>
                <h3 className="text-[15px] font-bold mb-2">A Sinking Fund Strategy</h3>
                <p className="text-sm text-white/70 mb-5 leading-relaxed">
                  By identifying ₹{totalOutlay.toLocaleString('en-IN')} in annual costs now, we can structure your monthly cash flow to automatically set aside funds. This prevents high-interest debt when the bills arrive.
                </p>
                <button className="w-full bg-white text-[#2C4A70] font-bold text-sm py-3 rounded-xl hover:bg-slate-100 transition-colors">
                  Enable Automatic Reserves
                </button>
              </div>

              {/* Data Sovereignty */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-[#526B5C]/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Shield size={13} className="text-[#526B5C]" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-800 mb-1">Data Sovereignty</p>
                  <p className="text-xs text-slate-500 leading-relaxed">Calculations for your irregular expenses are processed entirely on this device. No financial data ever leaves your local environment.</p>
                </div>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>

      {/* Footer nav */}
      <div className="bg-white border-t border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <button onClick={onBack} className="flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-[#2C4A70] transition-colors uppercase tracking-wide">
          <ArrowRight size={14} className="rotate-180" /> Back to Cash Flow
        </button>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full border-2 border-[#2C4A70] flex items-center justify-center text-[11px] font-black text-[#2C4A70]">2/2</div>
            <div>
              <p className="text-[10px] font-bold text-[#2C4A70] uppercase tracking-widest leading-none">Step 2 of 2</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Annual Irregular Expense Mapping</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => persist()} className="px-5 py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors uppercase tracking-wide">
              Save Draft
            </button>
            <Btn disabled={saving} onClick={async () => { await persist({ completed: true }); onComplete(); }}>
              {saving ? 'Saving…' : 'Proceed to Accounts'}
            </Btn>
          </div>
        </div>
      </div>
    </div>
  );
}
