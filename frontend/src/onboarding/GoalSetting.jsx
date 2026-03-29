import React, { useState } from 'react';
import { Check } from 'lucide-react';
import { FadeIn, Button, Input } from './components';
import { GOAL_TEMPLATES } from './constants';

export const GS1Screen = ({ data, updateData, onNext, onSkip }) => {
  const [selectedGoals, setSelectedGoals] = useState([]);
  const availableGoals = GOAL_TEMPLATES.filter(g => !g.condition || g.condition(data));

  const toggleGoal = (id) => setSelectedGoals(prev => prev.includes(id) ? prev.filter(g => g !== id) : prev.length < 3 ? [...prev, id] : prev);

  const handleNext = () => {
    // initialize goal objects
    const initialGoals = selectedGoals.map(sg => {
      const tmpl = availableGoals.find(a => a.id === sg);
      return { id: tmpl.id, type: tmpl.id, name: tmpl.label, status: 'Draft', detail: {} };
    });
    updateData({ goals: initialGoals });
    onNext(initialGoals);
  }

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <FadeIn>
        <h2 className="text-4xl font-extrabold text-slate-900 mb-3">What do you want your money to do for you?</h2>
        <p className="text-lg text-slate-500 mb-10">Select 1 to 3 goals to start.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
          {availableGoals.map(g => {
            const isSelected = selectedGoals.includes(g.id);
            const isAtMax = !isSelected && selectedGoals.length >= 3;
            const Icon = g.icon;
            return (
              <button 
                key={g.id} onClick={() => toggleGoal(g.id)} disabled={isAtMax}
                className={`relative p-5 rounded-2xl border-2 text-left transition-all overflow-hidden ${isSelected ? 'border-indigo-600 bg-indigo-50 shadow-md' : isAtMax ? 'border-slate-100 bg-slate-50 opacity-50 cursor-not-allowed' : 'border-slate-200 bg-white hover:border-indigo-300'}`}
              >
                {isSelected && <div className="absolute top-2 right-2 bg-indigo-600 text-white rounded-full p-0.5"><Check size={14} strokeWidth={3} /></div>}
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${g.color}`}><Icon size={20} /></div>
                <h3 className={`font-bold text-base mb-1 ${isSelected ? 'text-indigo-900' : 'text-slate-800'}`}>{g.label}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{g.desc}</p>
              </button>
            )
          })}
        </div>
        <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div><span className="font-bold text-slate-800">{selectedGoals.length} / 3 selected</span></div>
          <div className="flex gap-4">
             <button onClick={onSkip} className="text-sm font-semibold text-slate-400">Skip</button>
             <Button onClick={handleNext} disabled={selectedGoals.length === 0} className="w-fit px-8">Continue</Button>
          </div>
        </div>
      </FadeIn>
    </div>
  );
};

export const GSWizardScreen = ({ data, updateData, onComplete }) => {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [detail, setDetail] = useState({});

  const goal = data.goals[currentIdx];
  const isLast = currentIdx === data.goals.length - 1;

  const handleNextGoal = () => {
    // save current detail into the goal object
    const newGoals = [...data.goals];
    newGoals[currentIdx].detail = detail;
    updateData({ goals: newGoals });
    setDetail({}); // reset for next goal

    if (isLast) onComplete();
    else setCurrentIdx(prev => prev + 1);
  };

  const renderForm = () => {
    switch(goal.type) {
      case 'emergency': return (
        <div>
          <h2 className="text-2xl font-bold mb-4">Emergency Fund</h2>
          <p className="text-slate-500 mb-6">How many months of expenses would make you feel safe?</p>
          <div className="space-y-6">
            <Input type="range" min="1" max="12" step="1" value={detail.months || 6} onChange={v => setDetail({...detail, months: v})} />
            <div className="text-center font-bold text-indigo-700 text-xl">{detail.months || 6} months</div>
            <p className="text-xs text-slate-500 text-center">Most planners suggest 3–6 months. You can choose what feels right for you.</p>
          </div>
        </div>
      );
      case 'home': return (
        <div>
          <h2 className="text-2xl font-bold mb-4">Buy a Home</h2>
          <div className="space-y-4">
             <Input label="What price range are you considering?" prefix="₹" placeholder="e.g. 8000000" type="number" value={detail.price || ''} onChange={v => setDetail({...detail, price: v})} />
             <div>
               <label className="block text-sm font-semibold text-slate-700 mb-2">When do you hope to buy?</label>
               <select className="w-full border border-slate-200 p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none bg-white" onChange={e => setDetail({...detail, timeframe: e.target.value})} value={detail.timeframe || ''}>
                 <option value="">Select timeframe</option>
                 <option value="1-2">1-2 years</option>
                 <option value="3-5">3-5 years</option>
                 <option value="5-10">5-10 years</option>
                 <option value="exploring">Just exploring</option>
               </select>
             </div>
             <Input label="How much can you put as a down payment today?" prefix="₹" type="number" value={detail.downpayment || ''} onChange={v => setDetail({...detail, downpayment: v})} />
          </div>
        </div>
      );
      case 'education': return (
        <div>
          <h2 className="text-2xl font-bold mb-4">Children's Education</h2>
          <div className="space-y-4">
             <Input label="Which child is this for?" placeholder="Name" value={detail.childName || ''} onChange={v => setDetail({...detail, childName: v})} />
             <Input label="Rough estimated cost?" prefix="₹" type="number" value={detail.cost || ''} onChange={v => setDetail({...detail, cost: v})} />
             <Input label="When will you need this?" type="number" placeholder="In how many years" value={detail.years || ''} onChange={v => setDetail({...detail, years: v})} />
          </div>
        </div>
      );
      case 'retire': return (
        <div>
          <h2 className="text-2xl font-bold mb-4">Retire by a certain age</h2>
          <div className="space-y-4">
             <Input label="At what age would you like to stop working for money?" type="number" placeholder="e.g. 50" value={detail.retireAge || ''} onChange={v => setDetail({...detail, retireAge: v})} />
             <Input label="Your current age?" type="number" placeholder="e.g. 30" value={detail.currentAge || ''} onChange={v => setDetail({...detail, currentAge: v})} />
             <Input label="Rough monthly lifestyle cost in today's money?" prefix="₹" type="number" placeholder="e.g. 50000" value={detail.lifestyleCost || ''} onChange={v => setDetail({...detail, lifestyleCost: v})} />
          </div>
        </div>
      );
      case 'debt': return (
        <div>
          <h2 className="text-2xl font-bold mb-4">Pay Off Debt</h2>
          <div className="space-y-4">
            <p className="text-sm text-slate-600">Which debts would you like to focus on first?</p>
            {data.liabilities.map(l => (
              <label key={l.id} className="flex items-center gap-3 p-3 border rounded-lg bg-white">
                <input type="checkbox" onChange={(e) => {
                  const s = new Set(detail.targets || []);
                  if(e.target.checked) s.add(l.id); else s.delete(l.id);
                  setDetail({...detail, targets: Array.from(s)});
                }} />
                <span>{l.name} - ₹{l.value}</span>
              </label>
            ))}
            {!data.liabilities.length && <p className="text-sm text-slate-500 italic">No debts tracked yet.</p>}
            <Input label="Any extra amount you can put toward debt each month?" prefix="₹" type="number" value={detail.extra || ''} onChange={v => setDetail({...detail, extra: v})} />
          </div>
        </div>
      );
      default: return (
        <div>
          <h2 className="text-2xl font-bold mb-4">Set Your Goal</h2>
          <div className="space-y-4">
            <Input label="Goal name" value={detail.goalName || ''} onChange={v => setDetail({...detail, goalName: v})} placeholder="e.g. Car, Vacation..." />
            <Input label="Target amount" prefix="₹" type="number" value={detail.target || ''} onChange={v => setDetail({...detail, target: v})} />
            <Input label="In how many years?" type="number" value={detail.years || ''} onChange={v => setDetail({...detail, years: v})} />
          </div>
        </div>
      );
    }
  }

  return (
    <div className="max-w-md mx-auto py-12 px-6">
      <FadeIn key={currentIdx}>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Goal {currentIdx + 1} of {data.goals.length}</span>
        {renderForm()}
        <div className="mt-10">
          <Button onClick={handleNextGoal}>{isLast ? 'Complete Goals' : 'Next Goal'}</Button>
        </div>
      </FadeIn>
    </div>
  )
}

export const GSSummaryScreen = ({ data, onNext }) => (
  <div className="max-w-xl mx-auto py-12 px-6 text-center">
    <FadeIn>
      <h2 className="text-3xl font-extrabold text-slate-900 mb-8">Here are your goals.</h2>
      <div className="space-y-4 mb-10">
        {data.goals.map((g, idx) => (
          <div key={idx} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between text-left">
            <div>
              <h3 className="font-bold text-slate-800 text-lg">{g.name}</h3>
              <p className="text-xs text-slate-500">Tracking will start once cash flow is established.</p>
            </div>
            <div className="w-12 h-12 rounded-full border-4 border-slate-100 flex items-center justify-center font-bold text-xs text-slate-400">0%</div>
          </div>
        ))}
      </div>
      <Button onClick={onNext} className="w-fit mx-auto px-10">Continue to Cash Flow</Button>
    </FadeIn>
  </div>
);
