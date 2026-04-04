import React, { useState, useRef } from 'react';
import {
  Plus, AlertCircle, ArrowRight, Edit2, Trash2,
  Landmark, Home, TrendingUp, TrendingDown, Wallet, Building2, CreditCard, Layers,
} from 'lucide-react';
import { ProtonInline } from '../ProtonAssistant.jsx';
import AddLedgerItemDialog from '../AddLedgerItemDialog';
import { Btn } from './shared.jsx';
import { inr, saveJson } from './utils.js';
import { DUMMY_DATA, SUGGESTED_PROMPTS, SK } from './constants.js';

function parseMessage(text) {
  const t = text.toLowerCase();
  const assets = [];
  const liabilities = [];

  const liabilityKeywords = ['loan', 'emi', 'credit card', 'dues', 'debt', 'owe', 'owing', 'outstanding', 'mortgage'];
  const isLiability = liabilityKeywords.some(k => t.includes(k));

  const amountMatch = text.match(/[₹]?\s*(\d[\d,.]*)\s*(l|lakh|lac|k|cr|crore)?/i);
  let value = 0;
  if (amountMatch) {
    const raw = parseFloat(amountMatch[1].replace(/,/g, ''));
    const unit = (amountMatch[2] || '').toLowerCase();
    if (unit === 'l' || unit === 'lakh' || unit === 'lac') value = raw * 100000;
    else if (unit === 'cr' || unit === 'crore') value = raw * 10000000;
    else if (unit === 'k') value = raw * 1000;
    else value = raw;
  }

  const bankMatch = text.match(/(hdfc|sbi|icici|axis|kotak|idfc|yes bank|bob|pnb|canara|federal|indusind|amex|citi|hsbc|zerodha|groww|upstox|kite|paytm|nps|epf|ppf|lic|bajaj|tata|reliance|idbi)/i);
  const nameHint = bankMatch ? bankMatch[1].toUpperCase() : '';

  let name = '';
  let type = 'other';

  if (t.includes('saving') || t.includes('current') || t.includes('account') || t.includes('fd') || t.includes('fixed deposit')) {
    name = nameHint ? `${nameHint} Savings Account` : 'Bank Account';
    type = 'bank';
  } else if (t.includes('flat') || t.includes('house') || t.includes('apartment') || t.includes('property') || t.includes('plot') || t.includes('land')) {
    name = 'Property'; type = 'property';
  } else if (t.includes('stock') || t.includes('mf') || t.includes('mutual fund') || t.includes('portfolio') || t.includes('equity') || t.includes('shares') || t.includes('demat')) {
    name = nameHint ? `${nameHint} Portfolio` : 'Equity Portfolio'; type = 'stocks';
  } else if (t.includes('gold') || t.includes('jewel')) {
    name = 'Gold / Jewellery'; type = 'other';
  } else if (isLiability && (t.includes('home loan') || t.includes('mortgage'))) {
    name = nameHint ? `Home Loan (${nameHint})` : 'Home Loan'; type = 'loan';
  } else if (isLiability && (t.includes('car loan') || t.includes('vehicle'))) {
    name = 'Car Loan'; type = 'loan';
  } else if (isLiability && t.includes('personal loan')) {
    name = 'Personal Loan'; type = 'loan';
  } else if (isLiability && t.includes('credit card')) {
    name = nameHint ? `Credit Card (${nameHint})` : 'Credit Card'; type = 'credit';
  } else if (isLiability) {
    name = 'Loan / Debt'; type = 'other';
  } else {
    name = nameHint || 'Asset'; type = 'other';
  }

  if (value === 0) return null;

  if (isLiability) {
    return { kind: 'liability', item: { id: Date.now(), name, value, type, detail: text } };
  } else {
    return { kind: 'asset', item: { id: Date.now(), name, value, type, detail: text } };
  }
}

export default function MappingSection({ data, setData, perspective = 'salaried', onComplete }) {
  const [isDummy, setIsDummy] = useState(() => {
    const hasUserData = (data.assets?.length || data.liabilities?.length);
    if (!hasUserData) {
      const seed = DUMMY_DATA[perspective] || DUMMY_DATA.salaried;
      setData(d => ({ ...d, assets: seed.assets, liabilities: seed.liabilities }));
      return true;
    }
    const allNeg = [...(data.assets || []), ...(data.liabilities || [])].every(i => i.id < 0);
    return allNeg && (data.assets?.length > 0 || data.liabilities?.length > 0);
  });

  const protonRef = useRef(null);

  const clearDummy = () => {
    setData(d => ({ ...d, assets: [], liabilities: [] }));
    setIsDummy(false);
    protonRef.current?.addMessage({ role: 'proton', content: "Cleared! Start fresh — tell me about your accounts, investments, and any debts." });
  };

  const [dialog, setDialog] = useState(false);
  const [editItem, setEditItem] = useState(null);

  const assets      = data.assets      || [];
  const liabilities = data.liabilities || [];

  const addAsset = (item) => { setIsDummy(false); setData(d => ({ ...d, assets: [...(d.assets || []), { ...item, id: Date.now() + Math.random() }] })); };
  const addLib   = (item) => { setIsDummy(false); setData(d => ({ ...d, liabilities: [...(d.liabilities || []), { ...item, id: Date.now() + Math.random() }] })); };

  const categoryToItemType = (category) => {
    if (category === 'creditCards') return 'credit';
    if (['homeLoans', 'vehicleLoans', 'personalLoans', 'educationalLoans'].includes(category)) return 'loan';
    if (['banks', 'fixedDeposits', 'providentFund'].includes(category)) return 'bank';
    if (category === 'realEstate') return 'property';
    if (category === 'equity' || category === 'foreignEquity') return 'stocks';
    return 'other';
  };

  const handleDialogEdit = (category, type, entryData) => {
    const kind = type === 'liab' ? 'liability' : 'asset';
    const id = editItem.id;
    const itemType = categoryToItemType(category);
    const item = { name: entryData.name, value: entryData.balance, type: itemType, detail: entryData.description || '' };
    if (kind === 'asset') {
      setData(d => ({ ...d, assets: d.assets.map(a => a.id === id ? { ...item, id, _kind: 'asset' } : a) }));
    } else {
      setData(d => ({ ...d, liabilities: d.liabilities.map(l => l.id === id ? { ...item, id, _kind: 'liability' } : l) }));
    }
    setIsDummy(false);
    setEditItem(null);
  };

  const handleDialogAdd = (category, type, entryData) => {
    const kind = type === 'liab' ? 'liability' : 'asset';
    const itemType = categoryToItemType(category);
    const item = { name: entryData.name, value: entryData.balance, type: itemType, detail: entryData.description || '' };
    if (kind === 'asset') addAsset(item);
    else addLib(item);
    setDialog(false);
  };

  const simulateAIResponse = (text) => {
    const lowercaseText = text.toLowerCase();
    let message = "I've analyzed your message and mapped the details to your ledger below. ";
    let count = 0;

    const parseValue = (valStr, unitStr) => {
      let val = parseInt(valStr.replace(/,/g, ''));
      if (unitStr) {
        const u = unitStr.toLowerCase();
        if (u.includes('k')) val *= 1000;
        if (u.includes('l') || u.includes('lakh')) val *= 100000;
        if (u.includes('cr') || u.includes('crore')) val *= 10000000;
      }
      return val;
    };

    const bankRegex = /(?:i have|savings in|account with|at)\s+([\w\s]+?)\s*(?:(?:savings|bank|account|fd))\s*(?:with|of)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    let match;
    while ((match = bankRegex.exec(lowercaseText)) !== null) {
      addAsset({ type: 'bank', name: match[1].trim().toUpperCase() + " Bank Account", value: parseValue(match[2], match[3]) });
      count++;
    }

    const propertyRegex = /(?:own|plot|flat|property|home|worth)\s*(?:of|in|at)?\s+([\w\s]+?)\s*(?:worth)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = propertyRegex.exec(lowercaseText)) !== null) {
      addAsset({ type: 'property', name: match[1].trim().toUpperCase() + " Property", value: parseValue(match[2], match[3]) });
      count++;
    }

    const stockRegex = /(?:stocks?|shares?|portfolio|invested in)\s+([\w\s]+?)\s*(?:of|at)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = stockRegex.exec(lowercaseText)) !== null) {
      addAsset({ type: 'stocks', name: match[1].trim().toUpperCase() + " Portfolio", value: parseValue(match[2], match[3]) });
      count++;
    }

    const loanRegex = /([\w\s]+?)\s*(?:home|personal|auto|student)?\s*(?:loan|mortgage)\s*(?:of|with|at)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = loanRegex.exec(lowercaseText)) !== null) {
      addLib({ type: 'loan', name: match[1].trim().toUpperCase() + " Loan", detail: 'Fixed rate mortgage', value: parseValue(match[2], match[3]) });
      count++;
    }

    const cardRegex = /([\w\s]+?)\s*(?:credit card|card|debt|dues)\s*(?:of|with|at)?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+)\s*(l|k|cr|lakh|crore)?/gi;
    while ((match = cardRegex.exec(lowercaseText)) !== null) {
      addLib({ type: 'card', name: match[1].trim().toUpperCase() + " Due", detail: 'Statement balance', value: parseValue(match[2], match[3]) });
      count++;
    }

    if (count === 0) {
      message = "I couldn't quite catch the specific amounts or institutions. Try saying something like 'I have a savings account with 5L in HDFC' or 'HDFC home loan of 30L'.";
    }

    return message;
  };

  const totalA   = assets.reduce((s, a) => s + a.value, 0);
  const totalL   = liabilities.reduce((s, a) => s + a.value, 0);
  const netWorth = totalA - totalL;

  const handleProtonSend = async (text) => {
    await new Promise(r => setTimeout(r, 800));
    return simulateAIResponse(text);
  };

  const removeAsset = (id) => { setIsDummy(false); setData(d => ({ ...d, assets: d.assets.filter(a => a.id !== id) })); };
  const removeLib   = (id) => { setIsDummy(false); setData(d => ({ ...d, liabilities: d.liabilities.filter(a => a.id !== id) })); };
  const handleComplete = () => { saveJson(SK.mapping, data); onComplete(); };
  const hasAny = assets.length > 0 || liabilities.length > 0;

  const PERSPECTIVE_TIPS = {
    salaried: [
      { id: 'epf',        check: (a) => !a.some(x => /epf|pf|provident/i.test(x.name)),             emoji: '🏦', text: 'As a salaried employee, your EPF corpus is likely your largest retirement asset. Add it under investments.' },
      { id: 'fd',         check: (a) => !a.some(x => /fd|fixed.deposit/i.test(x.name)),              emoji: '💰', text: "Most salaried professionals keep a Fixed Deposit as an emergency buffer. Don't forget to add it." },
      { id: 'creditcard', check: (_, l) => !l.some(x => x.type === 'credit' || /credit.card/i.test(x.name)), emoji: '💳', text: 'Credit card outstanding is often overlooked. Add your current card balance under what you owe.' },
    ],
    business: [
      { id: 'currentacc', check: (a) => !a.some(x => /current.account|business.account/i.test(x.name)), emoji: '🏦', text: 'Add your business current account separately from personal savings for accurate net worth tracking.' },
      { id: 'gst',        check: (_, l) => !l.some(x => /gst|tax/i.test(x.name)),                       emoji: '📋', text: 'Business owners often have GST payables. Add any tax liabilities under what you owe.' },
    ],
    homemaker: [
      { id: 'gold', check: (a) => !a.some(x => /gold|jewel/i.test(x.name)), emoji: '🪙', text: 'Gold and jewellery are significant assets for most Indian households. Add their estimated current value.' },
      { id: 'rd',   check: (a) => !a.some(x => /rd|recurring/i.test(x.name)), emoji: '📅', text: 'If you have an RD (Recurring Deposit), add it — it counts as a liquid savings asset.' },
    ],
    investor: [
      { id: 'nps',   check: (a) => !a.some(x => /nps|pension/i.test(x.name)),                          emoji: '🎯', text: 'NPS corpus is often missed. Add it under investments for accurate retirement projection.' },
      { id: 'demat', check: (a) => !a.some(x => /demat|portfolio|zerodha|groww/i.test(x.name)),         emoji: '📊', text: 'Your demat/equity portfolio is likely your largest asset. Add its current market value.' },
    ],
  };

  const activeTips = (PERSPECTIVE_TIPS[perspective] || []).filter(t => t.check(assets, liabilities));

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-5 flex items-start justify-between shrink-0">
        <div>
          <h2 className="text-3xl font-serif font-black text-[#2C4A70] leading-tight">Here's what we understood.</h2>
          <p className="text-slate-400 text-sm mt-1">We have synthesized your digital footprint into a private architectural view of your wealth.</p>
        </div>
      </div>

      {/* Dummy data disclaimer */}
      {isDummy && (
        <div className="bg-amber-50 border-b border-amber-200 px-8 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 text-amber-700">
            <span className="text-base">⚠️</span>
            <p className="text-sm font-medium">These are <strong>sample figures</strong> based on your profile — not your real data. Edit each entry or clear all and start fresh.</p>
          </div>
          <button onClick={clearDummy} className="text-xs font-bold text-amber-700 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ml-4">
            Clear & Start Fresh
          </button>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-6 px-8 py-6 bg-white border-b border-slate-100 shrink-0">
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[2px] mb-2">What I own</p>
          <p className="text-4xl font-black text-[#2C4A70]">{inr(totalA)}</p>
        </div>
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[2px] mb-2">What I owe</p>
          <p className="text-4xl font-black text-[#2C4A70]">{inr(totalL)}</p>
        </div>
        <div className={`rounded-2xl p-6 shadow-xl ${netWorth >= 0 ? 'bg-[#2C4A70] shadow-[#2C4A70]/20' : 'bg-rose-600 shadow-rose-600/20'}`}>
          <p className={`text-[10px] font-bold uppercase tracking-[2px] mb-2 ${netWorth >= 0 ? 'text-indigo-200' : 'text-rose-200'}`}>My Net Worth</p>
          <p className="text-4xl font-black text-white">{inr(netWorth)}</p>
          {netWorth < 0 && <p className="text-[10px] text-rose-200 mt-1">Debts exceed savings</p>}
        </div>
      </div>

      {/* Perspective-aware tips */}
      {activeTips.length > 0 && (
        <div className="shrink-0 bg-amber-50 border-b border-amber-100 px-8 py-3 flex flex-wrap gap-2">
          {activeTips.map(tip => (
            <div key={tip.id} className="flex items-start gap-2 text-amber-800 text-xs bg-white border border-amber-200 rounded-xl px-3 py-2 max-w-sm">
              <span className="shrink-0">{tip.emoji}</span>
              <span>{tip.text}</span>
            </div>
          ))}
        </div>
      )}

      {/* Insights strip */}
      {(() => {
        const hints = [];
        const hasProperty    = assets.some(a => a.type === 'property');
        const hasHomeLoan    = liabilities.some(l => /home|housing|mortgage/i.test(l.name));
        const hasVehicle     = assets.some(a => a.type === 'vehicle' || /\bcar\b|\bbike\b|\bvehicle\b/i.test(a.name));
        const hasVehicleLoan = liabilities.some(l => /\bcar\s*loan\b|\bvehicle\s*loan\b|\bauto\s*loan\b|\bbike\s*loan\b/i.test(l.name));

        if (hasHomeLoan && !hasProperty)   hints.push({ emoji: '🏠', text: "You've added a home loan — don't forget to add the property under What I own." });
        if (hasProperty && !hasHomeLoan)   hints.push({ emoji: '💡', text: "You own a property. If there's a home loan against it, add it under What I owe." });
        if (hasVehicleLoan && !hasVehicle) hints.push({ emoji: '🚗', text: "You have a vehicle loan — consider adding the vehicle itself under What I own." });
        if (hasVehicle && !hasVehicleLoan) hints.push({ emoji: '💡', text: "You've listed a vehicle. If there's an auto loan on it, add it under What I owe." });

        return hints.length > 0 ? (
          <div className="shrink-0 bg-indigo-50 border-b border-indigo-100 px-8 py-3 space-y-1.5">
            {hints.map((h, i) => (
              <div key={i} className="flex items-start gap-2.5 text-indigo-700 text-xs font-medium">
                <span className="text-sm shrink-0">{h.emoji}</span>
                <span>{h.text}</span>
              </div>
            ))}
          </div>
        ) : null;
      })()}

      {/* Main split */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left — financial map */}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {!hasAny ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-16">
              <div className="w-16 h-16 bg-white rounded-2xl border-2 border-dashed border-slate-200 flex items-center justify-center mb-4">
                <Layers size={28} className="text-slate-300" />
              </div>
              <p className="font-serif italic text-lg text-slate-400">Your financial map will appear here.</p>
              <p className="text-slate-300 text-sm mt-2">Start chatting on the right, or click Add to enter manually.</p>
              <button onClick={() => setDialog(true)} className="mt-8 px-6 py-2.5 bg-indigo-50 text-[#2C4A70] font-bold text-sm rounded-xl border border-indigo-100 hover:bg-indigo-100 transition-colors">
                <Plus size={14} className="inline mr-1" /> Add
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-500">{assets.length + liabilities.length} item{assets.length + liabilities.length !== 1 ? 's' : ''}</p>
                <button onClick={() => setDialog(true)} className="text-xs font-bold text-[#2C4A70] flex items-center gap-1 px-3 py-1.5 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors">
                  <Plus size={13} /> Add
                </button>
              </div>

              <div className="grid grid-cols-2 gap-5">
                {/* Assets column */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full bg-[#2C4A70]" />
                    <p className="text-xs font-bold text-[#2C4A70] uppercase tracking-widest">What I own</p>
                    <span className="ml-auto text-xs font-bold text-slate-400">{assets.length} item{assets.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
                    {assets.length === 0 ? (
                      <div className="px-5 py-8 text-center text-slate-300 text-xs italic">No assets added yet</div>
                    ) : assets.map(item => {
                      const iconMap = { bank: Landmark, property: Home, stocks: TrendingUp, loan: Building2, credit: CreditCard };
                      const Icon = iconMap[item.type] || Wallet;
                      return (
                        <div key={item.id} className="group flex items-center gap-3 px-4 py-3.5 hover:bg-slate-50 transition-colors">
                          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-[#2C4A70]/8 border border-[#2C4A70]/10">
                            <Icon size={15} className="text-[#2C4A70]" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-bold text-sm text-slate-800 truncate">{item.name}</p>
                            {item.detail && <p className="text-xs text-slate-400 truncate">{item.detail}</p>}
                          </div>
                          <p className="font-black text-sm shrink-0 text-[#2C4A70]">{inr(item.value)}</p>
                          <button onClick={() => setEditItem({ ...item, _kind: 'asset' })}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-[#2C4A70] p-1 shrink-0">
                            <Edit2 size={14} />
                          </button>
                          <button onClick={() => removeAsset(item.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-rose-400 p-1 shrink-0">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      );
                    })}
                    <div className="px-4 py-2.5 bg-[#2C4A70]/4 border-t border-[#2C4A70]/10">
                      <p className="text-xs font-black text-[#2C4A70] text-right">{inr(totalA)} total</p>
                    </div>
                  </div>
                </div>

                {/* Liabilities column */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full bg-rose-400" />
                    <p className="text-xs font-bold text-rose-500 uppercase tracking-widest">What I owe</p>
                    <span className="ml-auto text-xs font-bold text-slate-400">{liabilities.length} item{liabilities.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
                    {liabilities.length === 0 ? (
                      <div className="px-5 py-8 text-center text-slate-300 text-xs italic">No liabilities added yet</div>
                    ) : liabilities.map(item => {
                      const iconMap = { loan: Building2, card: CreditCard, credit: CreditCard };
                      const Icon = iconMap[item.type] || TrendingDown;
                      return (
                        <div key={item.id} className="group flex items-center gap-3 px-4 py-3.5 hover:bg-rose-50/40 transition-colors">
                          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-rose-50 border border-rose-100">
                            <Icon size={15} className="text-rose-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-bold text-sm text-slate-800 truncate">{item.name}</p>
                            {item.detail && <p className="text-xs text-slate-400 truncate">{item.detail}</p>}
                          </div>
                          <p className="font-black text-sm shrink-0 text-rose-500">−{inr(item.value)}</p>
                          <button onClick={() => setEditItem({ ...item, _kind: 'liability' })}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-[#2C4A70] p-1 shrink-0">
                            <Edit2 size={14} />
                          </button>
                          <button onClick={() => removeLib(item.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-300 hover:text-rose-400 p-1 shrink-0">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      );
                    })}
                    <div className="px-4 py-2.5 bg-rose-50/60 border-t border-rose-100">
                      <p className="text-xs font-black text-rose-500 text-right">−{inr(totalL)} total</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-px bg-slate-200 shrink-0" />

        {/* Right — Proton assistant */}
        <div className="w-[380px] shrink-0 flex flex-col border-l border-slate-100">
          <ProtonInline
            ref={protonRef}
            subtitle="Your financial companion"
            placeholder="E.g. HDFC savings ₹3L, home loan ₹28L…"
            prompts={!hasAny ? SUGGESTED_PROMPTS.slice(0, 3) : []}
            initialMessage="I've pre-filled a starting map based on your profile. You can edit any entry, remove what doesn't apply, or just tell me what you own and owe in plain language."
            onSend={handleProtonSend}
          />
        </div>
      </div>

      {/* Sticky Footer */}
      <div className="bg-white border-t border-slate-200 px-8 py-5 flex items-center justify-between shrink-0 shadow-[0_-4px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center gap-2 text-slate-400">
          <AlertCircle size={14} className="text-slate-300" />
          <p className="text-[11px] font-medium">All data is kept on your device. We do not store any ledger details on our servers.</p>
        </div>
        <Btn onClick={handleComplete} disabled={!hasAny} className="px-10 py-4 shadow-xl shadow-[#2C4A70]/20 min-w-[240px]">
          Looks good, continue <ArrowRight size={20} />
        </Btn>
      </div>

      <AddLedgerItemDialog isOpen={dialog} onAdd={handleDialogAdd} onClose={() => setDialog(false)} />
      <AddLedgerItemDialog isOpen={!!editItem} initialEntry={editItem} onAdd={handleDialogEdit} onClose={() => setEditItem(null)} />
    </div>
  );
}
