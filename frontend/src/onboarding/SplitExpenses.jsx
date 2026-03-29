import React, { useState } from 'react';
import { FadeIn, Button, Input } from './components';

export const SEHubScreen = ({ onSetup, onSkip }) => (
  <div className="max-w-xl mx-auto py-12 px-6">
    <FadeIn>
      <h2 className="text-4xl font-extrabold text-slate-900 mb-3">Let's set up shared expense tracking.</h2>
      <p className="text-lg text-slate-500 mb-10">If you share costs with a partner or housemate, this helps everyone know where they stand — no awkward conversations needed.</p>
      <div className="bg-indigo-50 border border-indigo-100 p-5 rounded-xl mb-10">
         <strong className="text-indigo-800 text-sm">Why we ask:</strong>
         <p className="text-indigo-600 font-medium text-sm mt-1">Tracking shared expenses prevents misunderstandings and makes splitting fair and transparent.</p>
      </div>
      
      <div className="flex gap-4">
         <Button onClick={onSetup} className="flex-1">Set it up</Button>
         <Button onClick={onSkip} variant="secondary" className="flex-1">Not relevant for me</Button>
      </div>
    </FadeIn>
  </div>
);

export const SEMasterScreen = ({ data, updateData, onComplete }) => {
  const [step, setStep] = useState(1);
  const [partner, setPartner] = useState(data.partnerName || '');
  const [rule, setRule] = useState('50-50');
  const [ratio, setRatio] = useState({ you: 50, them: 50 });
  const [cats, setCats] = useState(Object.keys(data.cashflow?.expenses || {}).filter(c => c !== 'Housing' && c !== 'Transport')); // prefill all cats except a few

  const toggleCat = (cat) => setCats(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]);

  const handleComplete = () => {
    updateData({ splitInfo: { partner, rule, ratio, categories: cats } });
    onComplete();
  }

  const expenseKeys = Object.keys(data.cashflow?.expenses || {});

  return (
    <div className="max-w-2xl mx-auto py-12 px-6">
      <FadeIn key={step}>
        {step === 1 && (
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-6">Who do you share expenses with?</h2>
            <div className="bg-slate-50 border border-slate-200 p-5 rounded-xl">
               <Input label="Name or Alias" value={partner} onChange={setPartner} placeholder="e.g. Partner, Housemate" />
            </div>
            <div className="mt-8 flex justify-end"><Button onClick={() => setStep(2)} disabled={!partner} className="w-fit">Next</Button></div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-6">How do you generally split things?</h2>
            <div className="space-y-4">
               <label className={`block flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${rule === '50-50' ? 'bg-indigo-50 border-indigo-600' : 'bg-white border-slate-200'}`}>
                 <input type="radio" name="rule" checked={rule === '50-50'} onChange={() => setRule('50-50')} className="w-5 h-5 text-indigo-600 focus:ring-indigo-500" />
                 <span className="font-bold text-slate-800">50-50 Split</span>
               </label>
               <label className={`block flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${rule === 'ratio' ? 'bg-indigo-50 border-indigo-600' : 'bg-white border-slate-200'}`}>
                 <input type="radio" name="rule" checked={rule === 'ratio'} onChange={() => setRule('ratio')} className="w-5 h-5 text-indigo-600 focus:ring-indigo-500" />
                 <div><p className="font-bold text-slate-800">Custom Ratio</p><p className="text-xs text-slate-500 font-medium">Split based on income or mutual agreement</p></div>
               </label>
            </div>
            {rule === 'ratio' && (
              <div className="mt-6 flex gap-4 items-center bg-slate-50 p-6 rounded-2xl border border-slate-200">
                 <div className="flex-1"><label className="text-sm font-bold block mb-2 text-indigo-800">You (%)</label><input type="number" value={ratio.you} onChange={e => {setRatio({you: parseInt(e.target.value), them: 100 - parseInt(e.target.value)})}} className="w-full text-indigo-900 font-bold border border-indigo-200 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 text-center text-xl shadow-sm"/></div>
                 <div className="text-slate-400 font-bold">:</div>
                 <div className="flex-1"><label className="text-sm font-bold block mb-2 text-indigo-800">{partner} (%)</label><input type="number" value={ratio.them} onChange={e => {setRatio({them: parseInt(e.target.value), you: 100 - parseInt(e.target.value)})}} className="w-full text-indigo-900 font-bold border border-indigo-200 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 text-center text-xl shadow-sm"/></div>
              </div>
            )}
            <div className="mt-8 flex justify-between"><Button onClick={() => setStep(1)} variant="secondary" className="w-fit">Back</Button><Button onClick={() => setStep(3)} className="w-fit">Next</Button></div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-6">Which expenses are shared?</h2>
            <p className="text-slate-500 mb-8 font-medium">Categories not checked are treated as your personal expenses.</p>
            <div className="grid sm:grid-cols-2 gap-3 mb-10 text-sm">
               {expenseKeys.map(k => {
                 const isChecked = cats.includes(k);
                 return (
                   <label key={k} className={`flex items-center gap-3 p-3 border rounded-xl font-bold transition-all shadow-sm ${isChecked ? 'bg-indigo-50 border-indigo-200 text-indigo-900' : 'bg-white border-slate-200 text-slate-600'}`}>
                     <input type="checkbox" checked={isChecked} onChange={() => toggleCat(k)} className="w-4 h-4 rounded text-indigo-600" />
                     {k}
                   </label>
                 )
               })}
            </div>
            <div className="mt-8 flex justify-between"><Button onClick={() => setStep(2)} variant="secondary" className="w-fit">Back</Button><Button onClick={() => setStep(4)} className="w-fit">Next</Button></div>
          </div>
        )}

        {step === 4 && (
          <div className="text-center">
            <h2 className="text-3xl font-extrabold text-slate-900 mb-8">Shared expense tracking is ready.</h2>
            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 shadow-sm mb-10 max-w-sm mx-auto">
               <div className="flex justify-between text-xs font-bold uppercase tracking-widest text-slate-400 mb-4 px-2"><span>You owe</span><span>{partner} owes</span></div>
               <div className="h-6 w-full rounded-full bg-slate-200 overflow-hidden flex relative"><div className="w-1/2 bg-slate-300"/><div className="absolute inset-0 border-line flex justify-center"><div className="h-full w-0.5 bg-white"></div></div></div>
               <div className="flex justify-between font-extrabold mt-3 text-lg"><span className="text-slate-800">₹0</span><span className="text-slate-800">₹0</span></div>
            </div>
            <p className="text-slate-500 font-medium mb-12 leading-relaxed max-w-md mx-auto">As you log shared expenses from your dashboard, we'll keep a running balance so settlements are easy.</p>
            <Button onClick={handleComplete} className="w-fit mx-auto px-10">Go to Dashboard</Button>
          </div>
        )}
      </FadeIn>
    </div>
  )
}
