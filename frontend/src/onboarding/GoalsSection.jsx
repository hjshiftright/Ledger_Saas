import React, { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import {
  AlertCircle, Home, TrendingUp, GraduationCap, CreditCard, Plus,
  ArrowRight, Check, Trash2, Pencil,
} from 'lucide-react';
import { API } from '../api.js';
import { ProtonInline } from '../ProtonAssistant.jsx';
import { GoalVizModal } from '../GoalsPage.jsx';
import GoalDialog from './GoalDialog.jsx';
import { Btn } from './shared.jsx';
import { inr, saveJson } from './utils.js';
import { DUMMY_GOALS, GOALS_AI_PROMPTS, SK } from './constants.js';

export const GOAL_OPTS = [
  { id: 'emergency', icon: AlertCircle,   label: 'Emergency Fund', desc: 'Prepare for the unexpected' },
  { id: 'home',      icon: Home,          label: 'Buy a Home',     desc: 'Down payment planning'      },
  { id: 'retire',    icon: TrendingUp,    label: 'Retire Early',   desc: 'Secure your future'         },
  { id: 'education', icon: GraduationCap, label: 'Education',      desc: 'College or upskilling'      },
  { id: 'debt',      icon: CreditCard,    label: 'Pay off Debt',   desc: 'Clear loans faster'         },
  { id: 'custom',    icon: Plus,          label: 'Custom Goal',    desc: 'Anything else'              },
];

const GOAL_TYPE_MAP = {
  emergency: 'EMERGENCY', home: 'HOME', retire: 'RETIREMENT',
  education: 'EDUCATION', vehicle: 'VEHICLE', vacation: 'VACATION',
  wedding: 'WEDDING', debt: 'OTHERS', custom: 'OTHERS',
};

export default function GoalsSection({ data, setData, perspective = 'salaried', assets = [], onComplete }) {
  const [isDummyGoals, setIsDummyGoals] = useState(() => {
    if (!data.goals?.length && data.dummyGoalDetails === undefined) {
      const seed = DUMMY_GOALS[perspective] || DUMMY_GOALS.salaried;
      setData(d => ({ ...d, dummyGoalDetails: seed }));
      return true;
    }
    return Boolean(data.dummyGoalDetails?.length);
  });

  const [goalDialog,   setGoalDialog]   = useState(null);
  const [selectedViz,  setSelectedViz]  = useState(null);
  const [goalMessages, setGoalMessages] = useState([]);

  const clearDummyGoals = () => {
    setData(d => ({ ...d, goals: [], goalDetails: {}, dummyGoalDetails: [] }));
    setIsDummyGoals(false);
    setGoalMessages(m => [...m, { role: 'ai', text: "Cleared! Now configure the goals that actually matter to you — click any goal card to set your target and timeline." }]);
  };

  const saveGoalDetail = (detail) => {
    setIsDummyGoals(false);
    setData(d => ({
      ...d,
      goals: (d.goals || []).includes(detail.id) ? d.goals : [...(d.goals || []), detail.id],
      goalDetails: { ...(d.goalDetails || {}), [detail.id]: detail },
      dummyGoalDetails: [],
    }));
    const opt = GOAL_OPTS.find(o => o.id === detail.id);
    setGoalMessages(m => [...m, { role: 'ai', text: `Great — **${opt?.label || 'Goal'}** configured: ${inr(detail.targetAmount)} in ${detail.timelineMonths >= 12 ? `${detail.timelineMonths / 12} years` : `${detail.timelineMonths} months`}. Monthly savings needed: ${inr(Math.ceil(detail.targetAmount / detail.timelineMonths))}.` }]);
  };

  const removeGoal = (id) => {
    setData(d => {
      const details = { ...(d.goalDetails || {}) };
      delete details[id];
      return { ...d, goals: (d.goals || []).filter(g => g !== id), goalDetails: details };
    });
  };

  const handleGoalProtonSend = async (text) => {
    await new Promise(r => setTimeout(r, 900));
    const lower = text.toLowerCase();
    let reply = "That's a thoughtful question. Based on your goals, I'd suggest reviewing your emergency fund first — it's the foundation everything else rests on. Once that's set, allocate surplus income toward your highest-priority goal using a SIP or recurring deposit.";
    if (lower.includes('retire')) reply = "For retirement, the rule of thumb is to save 15–20% of monthly income. With a 20-year horizon, even ₹10,000/month compounding at 12% grows to ~₹1 crore. Start early, stay consistent.";
    if (lower.includes('home') || lower.includes('house')) reply = "For a home purchase, target a 20% down payment to avoid PMI and keep EMIs manageable. If your goal is ₹20L down payment in 5 years, you need to save ~₹27,000/month at 8% returns.";
    if (lower.includes('emergency')) reply = "Emergency fund goal: 6 months of expenses in a liquid account. For most households, ₹3–6L is a good target. Prioritise this before any investment-linked goal.";
    if (lower.includes('priorit')) reply = "Priority order: 1) Emergency fund 2) High-interest debt clearance 3) Retirement (start early for compounding) 4) Medium-term goals like education or home down payment.";
    return reply;
  };

  const handleComplete = async () => {
    const u = { ...data, completed: true };
    setData(u);
    saveJson(SK.goals, u);

    const toSave = Object.values(u.goalDetails || {});

    try {
      const existing = await API.goals.list();
      for (const g of existing) {
        await API.goals.delete(g.id);
      }
    } catch (_) { /* non-blocking */ }

    for (const d of toSave) {
      const targetDate = new Date();
      targetDate.setMonth(targetDate.getMonth() + (d.timelineMonths || 12));
      try {
        await API.goals.create({
          name:           GOAL_OPTS.find(o => o.id === d.id)?.label || d.id,
          goal_type:      GOAL_TYPE_MAP[d.id] || 'OTHERS',
          target_amount:  d.targetAmount,
          current_amount: 0,
          target_date:    targetDate.toISOString().slice(0, 10),
          notes:          d.note || null,
        });
      } catch (_) { /* non-blocking */ }
    }

    onComplete();
  };

  const configuredGoals   = Object.keys(data.goalDetails || {});
  const dummyGoalDetails  = data.dummyGoalDetails || [];
  const totalTarget = [
    ...configuredGoals.map(id => (data.goalDetails[id]?.targetAmount || 0)),
    ...dummyGoalDetails.map(g => g.targetAmount || 0),
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-col h-full bg-[#F7F8F9]">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-5 flex items-start justify-between shrink-0">
        <div>
          <h2 className="text-3xl font-serif font-black text-[#2C4A70] leading-tight">Your Financial Milestones</h2>
          <p className="text-slate-400 text-sm mt-1">Configure the goals that matter most — set targets, timelines, and priorities.</p>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-6 text-sm text-slate-500 font-medium">
          <span className="bg-[#2C4A70]/10 text-[#2C4A70] font-bold px-3 py-1.5 rounded-full text-xs">
            {configuredGoals.length + (isDummyGoals ? dummyGoalDetails.length : 0)} goals
          </span>
          {totalTarget > 0 && (
            <span className="bg-slate-100 text-slate-600 font-bold px-3 py-1.5 rounded-full text-xs">
              Total: {inr(totalTarget)}
            </span>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      {isDummyGoals && (
        <div className="bg-amber-50 border-b border-amber-200 px-8 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 text-amber-700">
            <span className="text-base">⚠️</span>
            <p className="text-sm font-medium">
              These are <strong>suggested goals</strong> based on your profile — not saved. Click any card to configure and save.
            </p>
          </div>
          <button onClick={clearDummyGoals}
            className="text-xs font-bold text-amber-700 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ml-4">
            Clear & Start Fresh
          </button>
        </div>
      )}

      {/* Main split pane */}
      <div className="flex flex-1 min-h-0">
        {/* LEFT — Goal cards */}
        <div className="flex flex-col w-[55%] border-r border-slate-200 overflow-y-auto">
          <div className="p-6 grid grid-cols-2 gap-4 content-start">
            {/* Dummy goal cards */}
            {isDummyGoals && dummyGoalDetails.map(gd => {
              const opt = GOAL_OPTS.find(o => o.id === gd.id);
              if (!opt) return null;
              const Icon = opt.icon;
              return (
                <div key={gd.id} className="relative group">
                  <button onClick={() => setGoalDialog(opt)}
                    className="w-full flex flex-col gap-3 p-5 rounded-2xl border-2 border-amber-200 bg-amber-50/60 text-left hover:border-amber-300 hover:shadow-sm transition-all">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center shrink-0">
                        <Icon size={17} className="text-amber-700" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm text-slate-800">{opt.label}</p>
                        <p className="text-xs text-slate-400 truncate">{gd.note}</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between bg-white/80 rounded-xl px-3 py-2 border border-amber-100">
                      <p className="text-xs font-black text-[#2C4A70]">{inr(gd.targetAmount)}</p>
                      <p className="text-[10px] text-slate-400 font-semibold">
                        {gd.timelineMonths >= 12 ? `${gd.timelineMonths / 12}yr` : `${gd.timelineMonths}mo`}
                      </p>
                      <p className="text-[10px] text-slate-400">~{inr(Math.ceil(gd.targetAmount / gd.timelineMonths))}/mo</p>
                    </div>
                    <p className="text-[10px] text-amber-600 font-semibold flex items-center gap-1"><Pencil size={9} /> Click to configure</p>
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); setData(d => ({ ...d, dummyGoalDetails: (d.dummyGoalDetails || []).filter(x => x.id !== gd.id) })); }}
                    className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-300 hover:text-rose-500 hover:border-rose-200 shadow-sm">
                    <Trash2 size={11} />
                  </button>
                </div>
              );
            })}

            {/* Configured goal cards */}
            {!isDummyGoals && GOAL_OPTS.map(g => {
              const active = (data.goals || []).includes(g.id);
              const detail = (data.goalDetails || {})[g.id];
              const Icon = g.icon;
              return (
                <div key={g.id} className="relative group">
                  <button onClick={() => setGoalDialog(g)}
                    className={`w-full flex flex-col gap-3 p-5 rounded-2xl border-2 text-left transition-all
                      ${active ? 'border-[#526B5C] bg-[#526B5C]/5 shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${active ? 'bg-[#526B5C] text-white' : 'bg-slate-100 text-slate-400'}`}>
                        <Icon size={17} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`font-bold text-sm ${active ? 'text-[#2C4A70]' : 'text-slate-700'}`}>{g.label}</p>
                        <p className="text-xs text-slate-400 truncate">{g.desc}</p>
                      </div>
                      {active && (
                        <span className="bg-[#526B5C] text-white rounded-full p-0.5 shrink-0">
                          <Check size={11} strokeWidth={3} />
                        </span>
                      )}
                    </div>
                    {detail ? (
                      <div className="flex flex-col gap-2 mt-2">
                        <div className="flex items-center justify-between bg-white/80 rounded-xl px-3 py-2 border border-[#526B5C]/15">
                          <p className="text-xs font-black text-[#2C4A70]">{inr(detail.targetAmount)}</p>
                          <p className="text-[10px] text-slate-400 font-semibold">
                            {detail.timelineMonths >= 12 ? `${detail.timelineMonths / 12}yr` : `${detail.timelineMonths}mo`}
                          </p>
                          <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full
                            ${detail.priority === 'high' ? 'bg-rose-50 text-rose-500' : detail.priority === 'low' ? 'bg-slate-100 text-slate-400' : 'bg-amber-50 text-amber-500'}`}>
                            {detail.priority}
                          </span>
                        </div>
                        <button onClick={(e) => { e.stopPropagation(); setSelectedViz(detail); }}
                          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#2C4A70]/5 text-[#2C4A70] text-[11px] font-semibold hover:bg-[#2C4A70]/10 transition-colors border border-[#2C4A70]/15">
                          <TrendingUp size={12} /> View Projection
                        </button>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-300 flex items-center gap-1"><Plus size={10} /> Click to configure</p>
                    )}
                  </button>
                  {active && (
                    <button
                      onClick={e => { e.stopPropagation(); removeGoal(g.id); }}
                      className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-300 hover:text-rose-500 hover:border-rose-200 shadow-sm">
                      <Trash2 size={11} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Continue footer */}
          <div className="mt-auto border-t border-slate-200 bg-white px-6 py-4 flex justify-end shrink-0">
            <Btn onClick={handleComplete} disabled={configuredGoals.length === 0}>
              Looks good, continue <ArrowRight size={18} />
            </Btn>
          </div>
        </div>

        {/* RIGHT — Proton goal assistant */}
        <div className="w-[380px] shrink-0 flex flex-col border-l border-slate-100">
          <ProtonInline
            subtitle="Your financial companion"
            placeholder="Ask about saving strategies, timelines…"
            prompts={GOALS_AI_PROMPTS}
            showPromptsAlways
            initialMessage="I'm Proton, your financial companion. Ask me anything about saving strategies, timelines, or how to prioritise your financial milestones."
            onSend={handleGoalProtonSend}
          />
        </div>
      </div>

      {/* Goal dialog */}
      <AnimatePresence>
        {goalDialog && (
          <GoalDialog
            goal={goalDialog}
            existing={(data.goalDetails || {})[goalDialog.id]}
            assets={assets}
            onSave={saveGoalDetail}
            onRemove={removeGoal}
            onClose={() => setGoalDialog(null)}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {selectedViz && (
          <GoalVizModal
            apiGoal={{
              name:           GOAL_OPTS.find(g => g.id === selectedViz.id)?.label || selectedViz.id,
              goal_type:      GOAL_TYPE_MAP[selectedViz.id] || 'OTHERS',
              target_date:    (() => { const d = new Date(); d.setMonth(d.getMonth() + (selectedViz.timelineMonths || 12)); return d; })().toISOString().slice(0, 10),
              target_amount:  selectedViz.targetAmount,
              current_amount: selectedViz.alreadySaved || 0,
            }}
            userAge={30}
            onClose={() => setSelectedViz(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
