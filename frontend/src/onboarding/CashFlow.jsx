import React, { useState } from 'react';
import { FadeIn, Button, Input } from './components';
import { DEFAULT_EXPENSE_CATS } from './constants';

export const CFHubScreen = ({ onQuick, onDetailed, onSkip }) => (
  <div className="max-w-xl mx-auto py-12 px-6">
    <FadeIn>
      <h2 className="text-4xl font-extrabold text-slate-900 mb-3">Let's understand how money moves each month.</h2>
      <p className="text-lg text-slate-500 mb-8">This is where most people have their biggest 'aha' moment — seeing what actually comes in and goes out.</p>
      <div className="bg-slate-50 border border-slate-200 p-5 rounded-xl mb-10">
         <strong className="text-slate-800 text-sm">Why we ask:</strong>
         <p className="text-slate-500 text-sm mt-1">Cash flow is the engine of your financial life. Knowing it helps us show savings capacity, goal feasibility, and spending patterns.</p>
      </div>
      
      <div className="flex flex-col gap-4">
         <Button onClick={onQuick} className="w-full">Quick estimate (1-2 minutes)</Button>
         <Button onClick={onDetailed} variant="secondary" className="w-full">Detailed breakdown (5+ minutes)</Button>
      </div>
      <div className="mt-8 text-center"><button onClick={onSkip} className="text-sm font-semibold text-slate-400 hover:underline">I'll do this later</button></div>
    </FadeIn>
  </div>
);

export const CFQ1Screen = ({ data, onNext }) => {
  const [text, setText] = useState('');
  const [parsing, setParsing] = useState(false);
  
  const placeholders = {
    salaried: "Example: Salary 1.2L after tax, wife earns about 80K, some interest from FDs.",
    business: "Example: Business brings in roughly 3-5L/month but varies, rental income 25K.",
    homemaker: "Example: Husband's salary is about 1.5L, I earn 15K from tuition classes.",
    investor: "Example: Salary 2L, dividend income around 10K/quarter, some freelance income."
  };

  const parse = () => {
    setParsing(true);
    setTimeout(() => {
      onNext([{ id: 1, source: 'Primary', amount: '150000', freq: 'Monthly' }]); // mock parsed
    }, 1000);
  }

  return (
    <div className="max-w-2xl mx-auto py-12 px-6">
      <FadeIn>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Step 1 of 3</span>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">What comes in each month?</h2>
        <p className="text-slate-500 mb-6">Describe your income sources in your own words.</p>
        <textarea className="w-full bg-white border-2 border-slate-200 rounded-2xl p-5 text-slate-800 focus:outline-none focus:ring-4 focus:ring-indigo-500/20" rows={4} placeholder={placeholders[data.persona] || placeholders.salaried} value={text} onChange={(e) => setText(e.target.value)} />
        <div className="mt-8 flex justify-end">
          <Button onClick={parse} disabled={!text.trim() || parsing} className="w-fit">{parsing ? 'Processing...' : 'Next'}</Button>
        </div>
      </FadeIn>
    </div>
  )
}

export const CFQ2Screen = ({ data, onNext }) => {
  const [expenses, setExpenses] = useState({});
  const total = Object.values(expenses).reduce((acc, v) => acc + (parseFloat(v)||0), 0);

  return (
    <div className="max-w-2xl mx-auto py-12 px-6">
      <FadeIn>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Step 2 of 3</span>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Where does your money usually go?</h2>
        <p className="text-slate-500 mb-8">Don't worry about exact numbers. Rough monthly averages are perfect.</p>
        
        <div className="space-y-3">
          {DEFAULT_EXPENSE_CATS.map(cat => (
             (cat === 'Children' && parseInt(data.dependents || 0) === 0) ? null : 
             <div key={cat} className="flex items-center justify-between border-b border-slate-100 py-3">
                <span className="font-semibold text-slate-700">{cat}</span>
                <input type="number" placeholder="₹ 0" value={expenses[cat] || ''} onChange={(e) => setExpenses({...expenses, [cat]: e.target.value})} className="w-1/3 border border-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none" />
             </div>
          ))}
        </div>
        
        <div className="mt-8 p-4 bg-slate-50 rounded-xl flex justify-between items-center font-bold text-lg">
           <span className="text-slate-700">Total Rough Expenses:</span>
           <span className="text-rose-600">₹ {total}</span>
        </div>

        <div className="mt-8 flex justify-end"><Button onClick={() => onNext(expenses)} className="w-fit">Save and continue</Button></div>
      </FadeIn>
    </div>
  )
}

export const CFQ3Screen = ({ data, updateData, incomeNodes, expensesObj, onComplete }) => {
  const totalIncome = incomeNodes.reduce((acc, n) => acc + (parseFloat(n.amount)||0), 0);
  const totalExp = Object.values(expensesObj).reduce((acc, v) => acc + (parseFloat(v)||0), 0);
  const surplus = totalIncome - totalExp;
  
  const handleNext = () => {
    updateData({ cashflow: { income: totalIncome.toString(), expenses: expensesObj } });
    onComplete();
  }

  return (
    <div className="max-w-2xl mx-auto py-12 px-6">
      <FadeIn>
        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full mb-4 inline-block">Step 3 of 3</span>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Here's your monthly money flow.</h2>
        
        <div className="mt-10 mb-8">
           <div className="flex h-12 rounded-xl overflow-hidden shadow-inner">
             <div className="bg-emerald-500 flex justify-center items-center text-white font-bold text-sm" style={{width: `${(totalIncome / (totalIncome+totalExp)) * 100}%`}}>Income (₹{totalIncome})</div>
             <div className="bg-rose-500 flex justify-center items-center text-white font-bold text-sm" style={{width: `${(totalExp / (totalIncome+totalExp)) * 100}%`}}>Expenses (₹{totalExp})</div>
           </div>
           
           <div className={`mt-8 p-6 border-2 rounded-2xl ${surplus > 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
              <p className="text-sm font-bold uppercase tracking-widest opacity-60 mix-blend-multiply mb-2">{surplus > 0 ? 'Monthly Surplus' : 'Monthly Deficit'}</p>
              <p className={`text-4xl font-extrabold ${surplus > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>₹ {Math.abs(surplus)}</p>
              <p className="mt-2 text-sm text-slate-700 opacity-80 mix-blend-multiply">
                {surplus > 0 ? 'This could go toward your goals each month.' : 'Expenses seem higher than income. Let\'s look closely during Budgeting.'}
              </p>
           </div>
        </div>
        <div className="flex justify-end"><Button onClick={handleNext} className="w-fit">Looks good, continue</Button></div>
      </FadeIn>
    </div>
  )
}
