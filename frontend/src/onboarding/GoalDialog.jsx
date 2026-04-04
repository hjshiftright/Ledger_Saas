import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { inr, num } from './utils.js';

export default function GoalDialog({ goal, existing, assets = [], onSave, onRemove, onClose }) {
  const Icon = goal.icon;
  const seed = existing || {};
  const [targetAmount,   setTargetAmount]   = useState(seed.targetAmount ? String(seed.targetAmount) : '');
  const [timelineMonths, setTimelineMonths] = useState(seed.timelineMonths || 12);
  const [priority,       setPriority]       = useState(seed.priority       || 'medium');
  const [note,           setNote]           = useState(seed.note           || '');

  const computePrefill = () => {
    if (existing?.alreadySaved) return String(existing.alreadySaved);
    const match = {
      emergency: (a) => a.filter(x => /saving|bank|liquid|fd|fixed.deposit/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      retire:    (a) => a.filter(x => /epf|ppf|nps|pension|provident|pf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      home:      (a) => a.filter(x => /home|property|real.estate|flat|house/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      vehicle:   (a) => a.filter(x => /car|vehicle|bike|auto/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      education: (a) => a.filter(x => /education|college|sukanya|ppf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
    };
    const fn = match[goal.id];
    const prefilled = fn ? fn(assets) : 0;
    return prefilled > 0 ? String(prefilled) : '';
  };
  const [alreadySaved, setAlreadySaved] = useState(computePrefill);

  const prefillAmt = (() => {
    const match = {
      emergency: (a) => a.filter(x => /saving|bank|liquid|fd|fixed.deposit/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      retire:    (a) => a.filter(x => /epf|ppf|nps|pension|provident|pf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      home:      (a) => a.filter(x => /home|property|real.estate|flat|house/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      vehicle:   (a) => a.filter(x => /car|vehicle|bike|auto/i.test(x.name)).reduce((s,x)=>s+x.value,0),
      education: (a) => a.filter(x => /education|college|sukanya|ppf/i.test(x.name)).reduce((s,x)=>s+x.value,0),
    };
    const fn = match[goal.id];
    return fn ? fn(assets) : 0;
  })();

  const canSave = num(targetAmount) > 0;
  const remaining = Math.max(0, num(targetAmount) - num(alreadySaved));
  const monthlySaving = timelineMonths > 0 ? Math.ceil(remaining / timelineMonths) : 0;

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
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-[#2C4A70]/10 flex items-center justify-center">
                <Icon size={22} className="text-[#2C4A70]" />
              </div>
              <div>
                <h3 className="text-xl font-serif font-black text-[#2C4A70]">{goal.label}</h3>
                <p className="text-xs text-slate-400">{goal.desc}</p>
              </div>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors text-lg leading-none">×</button>
          </div>

          <div className="space-y-5">
            {/* Target amount */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Target Amount</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
                <input value={targetAmount} onChange={e => setTargetAmount(e.target.value)} placeholder="0" inputMode="numeric"
                  className="w-full border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
              </div>
              {num(targetAmount) > 0 && <p className="text-xs text-slate-400 mt-1 pl-1">{inr(num(targetAmount))}</p>}
            </div>

            {/* Already saved */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
                Already Saved <span className="text-slate-300 font-normal normal-case">(optional)</span>
              </label>
              {prefillAmt > 0 && !existing && (
                <div className="mb-2 flex items-center gap-2 bg-indigo-50 border border-indigo-100 rounded-xl px-3 py-2">
                  <span className="text-indigo-500 text-xs">💡</span>
                  <p className="text-xs text-indigo-700 flex-1">
                    We found <strong>{inr(prefillAmt)}</strong> from your assets that may count towards this goal.
                  </p>
                  <button onClick={() => setAlreadySaved(String(prefillAmt))} className="text-xs font-bold text-indigo-600 hover:underline shrink-0">Use this</button>
                </div>
              )}
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">₹</span>
                <input value={alreadySaved} onChange={e => setAlreadySaved(e.target.value)} placeholder="0" inputMode="numeric"
                  className="w-full border-2 border-slate-200 rounded-xl pl-8 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all" />
              </div>
            </div>

            {/* Timeline */}
            <div>
              <div className="flex justify-between items-end mb-2">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block">Timeline</label>
                <div className="text-sm font-bold text-[#2C4A70]">
                  {timelineMonths < 12
                    ? `${timelineMonths} months`
                    : `${Math.floor(timelineMonths / 12)} year${Math.floor(timelineMonths / 12) > 1 ? 's' : ''}${timelineMonths % 12 ? ` ${timelineMonths % 12} mo` : ''}`}
                </div>
              </div>
              <input type="range" min="3" max="240" step="3" value={timelineMonths} onChange={e => setTimelineMonths(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#2C4A70]" />
              <div className="flex justify-between text-[10px] font-semibold text-slate-400 mt-2 px-1">
                <span>3 mo</span><span>5 yrs</span><span>10 yrs</span><span>20 yrs</span>
              </div>
            </div>

            {/* Monthly savings preview */}
            {canSave && (
              <div className="bg-slate-50 rounded-2xl px-5 py-4 border border-slate-100 flex items-center justify-between">
                <p className="text-sm text-slate-500 font-medium">Monthly saving needed</p>
                <p className="text-lg font-black text-[#2C4A70]">{inr(monthlySaving)}</p>
              </div>
            )}

            {/* Priority */}
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-2">Priority</label>
              <div className="flex gap-2">
                {[
                  { id: 'high',   label: 'High',   color: 'border-rose-400 bg-rose-50 text-rose-600'     },
                  { id: 'medium', label: 'Medium', color: 'border-amber-400 bg-amber-50 text-amber-600'  },
                  { id: 'low',    label: 'Low',    color: 'border-slate-300 bg-slate-50 text-slate-500'  },
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

          {/* Actions */}
          <div className="flex gap-3 mt-7">
            {existing && (
              <button onClick={() => { onRemove(goal.id); onClose(); }}
                className="px-4 py-3 rounded-full border-2 border-rose-200 text-rose-500 hover:bg-rose-50 text-sm font-semibold transition-colors">
                Remove
              </button>
            )}
            <button onClick={onClose} className="flex-1 py-3 rounded-full border-2 border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => {
                try {
                  onSave({ id: goal.id, targetAmount: num(targetAmount), alreadySaved: num(alreadySaved), timelineMonths, priority, note });
                } catch (e) { console.error('Save crash:', e); }
                finally { onClose(); }
              }}
              disabled={!canSave}
              className="flex-1 py-3 rounded-full bg-[#2C4A70] text-white font-semibold text-sm hover:bg-[#1F344F] disabled:opacity-40 disabled:cursor-not-allowed shadow-md transition-all">
              {existing ? 'Update Goal' : 'Add Goal'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
