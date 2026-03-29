import React, { useState } from 'react';
import { Sparkles, Briefcase, Check, Plus, Trash2 } from 'lucide-react';
import { FadeIn, Button, Input } from './components';
import { ASSET_CATS, LIABILITY_CATS } from './constants';

export const FMHubScreen = ({ onModeSelect }) => (
  <div className="max-w-xl mx-auto py-12 px-6 text-center">
    <FadeIn>
      <h2 className="text-4xl font-extrabold text-slate-900 mb-3">Let's map what you have.</h2>
      <p className="text-lg text-slate-500 mb-10">You can describe it in your own words or pick from a list. Everything stays securely on this device.</p>
      <div className="grid sm:grid-cols-2 gap-4">
        <button onClick={() => onModeSelect('nl')} className="group relative bg-white border-2 border-indigo-100 rounded-2xl p-6 text-left hover:border-indigo-500 transition-all duration-300">
          <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center mb-4 group-hover:bg-indigo-600 group-hover:text-white transition-colors"><Sparkles size={24} /></div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Use your own words</h3>
          <p className="text-sm text-slate-500">Type it casually like "I have 5L in HDFC".</p>
        </button>
        <button onClick={() => onModeSelect('gallery')} className="group relative bg-white border-2 border-slate-100 rounded-2xl p-6 text-left hover:border-slate-800 transition-all duration-300">
          <div className="w-12 h-12 bg-slate-100 text-slate-600 rounded-xl flex items-center justify-center mb-4 group-hover:bg-slate-800 group-hover:text-white transition-colors"><Briefcase size={24} /></div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Pick from categories</h3>
          <p className="text-sm text-slate-500">Select what applies to you step-by-step.</p>
        </button>
      </div>
      <div className="mt-8"><button className="text-sm font-semibold text-slate-400 hover:text-slate-600" onClick={() => onModeSelect('skip')}>Skip for now (I'll add it later)</button></div>
    </FadeIn>
  </div>
);

export const FMNLScreen = ({ data, updateData, onNext, onSkip }) => {
  const [text, setText] = useState('');
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState(null);

  const getPlaceholder = () => {
    switch(data.persona) {
      case 'business': return "Example: Current account in Kotak with about 8L, personal savings 2L in SBI, business loan 20L from HDFC.";
      case 'investor': return "Example: 25L in direct equity across Zerodha and Groww, 10L in mutual funds, 50L flat with 20L home loan.";
      default: return "Example: Salary 1.5L/month in HDFC, 3L in SBI savings, ICICI credit card with 40K due, 15L home loan from HDFC.";
    }
  };

  const handleParse = () => {
    setParsing(true);
    setTimeout(() => {
      let extAss = []; let extLia = [];
      const t = text.toLowerCase();
      const amtMatch = text.match(/(\d+(?:\.\d+)?)(L|K| Lakh| l| k| lacs| crore)/i);
      const amt = amtMatch ? amtMatch[0] : 'Approx';
      
      if (t.includes('sbi') || t.includes('hdfc') || t.includes('account')) extAss.push({ id: Date.now(), type: 'bank', name: 'Bank Account', value: amt });
      if (t.includes('loan') || t.includes('due') || t.includes('credit')) extLia.push({ id: Date.now() + 1, type: 'loan', name: 'Liability', value: amt });
      if (t.includes('equity') || t.includes('mutual') || t.includes('stock')) extAss.push({ id: Date.now() + 2, type: 'investment', name: 'Investments', value: 'Needs review' });

      setParsed({ assets: extAss, liabilities: extLia });
      setParsing(false);
    }, 1200);
  };

  const handleSave = () => { updateData({ assets: [...data.assets, ...parsed.assets], liabilities: [...data.liabilities, ...parsed.liabilities] }); onNext(); };

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <FadeIn>
        {!parsed ? (
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-2">In your own words, what do you own and owe?</h2>
            <p className="text-slate-500 mb-6 font-medium">Mention bank accounts, cards, loans, investments, property, gold — whatever matters.</p>
            <textarea className="w-full bg-white border-2 border-slate-200 rounded-2xl p-5 text-slate-800 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none font-medium leading-relaxed" rows={6} placeholder={getPlaceholder()} value={text} onChange={(e) => setText(e.target.value)} />
            <div className="mt-6 flex justify-between">
              <button className="text-sm font-semibold text-slate-400" onClick={onSkip}>Skip</button>
              <Button onClick={handleParse} disabled={!text.trim() || parsing} className="w-fit px-8">{parsing ? 'Parsing securely locally...' : 'Show my summary'}</Button>
            </div>
          </div>
        ) : (
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Here's what we understood.</h2>
            <p className="text-slate-500 mb-8 font-medium">You can correct anything that looks off. Rough numbers are perfectly fine.</p>
            <div className="grid md:grid-cols-2 gap-6 mb-10">
              <div className="bg-emerald-50/50 border border-emerald-100 rounded-2xl p-5">
                <h3 className="font-bold text-emerald-800 uppercase tracking-wider text-xs mb-4">Assets</h3>
                {parsed.assets.map(a => (<div key={a.id} className="bg-white p-3 rounded-lg border flex justify-between shadow-sm"><span className="font-bold text-slate-700">{a.name}</span><span className="text-sm text-emerald-600 font-bold">{a.value}</span></div>))}
                {!parsed.assets.length && <p className="text-sm text-slate-400">None found.</p>}
              </div>
              <div className="bg-rose-50/50 border border-rose-100 rounded-2xl p-5">
                <h3 className="font-bold text-rose-800 uppercase tracking-wider text-xs mb-4">Liabilities</h3>
                {parsed.liabilities.map(l => (<div key={l.id} className="bg-white p-3 rounded-lg border flex justify-between shadow-sm"><span className="font-bold text-slate-700">{l.name}</span><span className="text-sm text-rose-600 font-bold">{l.value}</span></div>))}
                {!parsed.liabilities.length && <p className="text-sm text-slate-400">None found.</p>}
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setParsed(null)} className="w-fit">Add more or retry</Button>
              <Button onClick={handleSave} className="w-fit px-8">Looks good, continue</Button>
            </div>
          </div>
        )}
      </FadeIn>
    </div>
  );
};

export const FMGalleryScreen = ({ data, onNext, onSwitchToNL }) => {
  const [selectedCats, setSelectedCats] = useState([]);
  const toggleCat = (id) => setSelectedCats(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);

  const handleNext = () => onNext(selectedCats);

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <FadeIn>
        <h2 className="text-3xl font-extrabold text-slate-900 mb-2">What all do you own and owe today?</h2>
        <p className="text-slate-500 mb-8 font-medium">Pick the categories that apply. We'll only ask details for those.</p>
        <div className="grid md:grid-cols-2 gap-8">
          <div><h3 className="text-xs font-bold text-emerald-600 uppercase mb-4">Things you own (Assets)</h3>
            <div className="grid gap-3">{ASSET_CATS.map(cat => {
               const isSelected = selectedCats.includes(cat.id);
               return <button key={cat.id} onClick={() => toggleCat(cat.id)} className={`flex items-start text-left p-4 rounded-xl border-2 transition-all ${isSelected ? 'border-emerald-500 bg-emerald-50' : 'border-slate-100 bg-white hover:border-emerald-200'}`}>
                  <div className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 mr-3 ${isSelected ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300'}`}>{isSelected && <Check size={12} strokeWidth={4} />}</div>
                  <div><h4 className={`font-bold text-sm ${isSelected ? 'text-emerald-900' : 'text-slate-800'}`}>{cat.label}</h4><p className="text-xs text-slate-500 mt-0.5">{cat.sub}</p></div>
               </button>
            })}</div>
          </div>
          <div><h3 className="text-xs font-bold text-rose-600 uppercase mb-4">What you owe (Liabilities)</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-2">{LIABILITY_CATS.map(cat => {
               const isSelected = selectedCats.includes(cat.id);
               return <button key={cat.id} onClick={() => toggleCat(cat.id)} className={`flex items-center text-left p-3 rounded-xl border-2 transition-all ${isSelected ? 'border-rose-500 bg-rose-50' : 'border-slate-100 bg-white hover:border-rose-200'}`}>
                  <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 mr-2.5 ${isSelected ? 'border-rose-500 bg-rose-500 text-white' : 'border-slate-300'}`}>{isSelected && <Check size={10} strokeWidth={4} />}</div>
                  <h4 className={`font-bold text-sm ${isSelected ? 'text-rose-900' : 'text-slate-800'}`}>{cat.label}</h4>
               </button>
            })}</div>
          </div>
        </div>
        <div className="mt-10 flex justify-between items-center">
           <button onClick={onSwitchToNL} className="text-sm font-semibold text-slate-400">Describe in words instead</button>
           <Button onClick={handleNext} disabled={!selectedCats.length} className="w-fit">Continue to details</Button>
        </div>
      </FadeIn>
    </div>
  );
}

export const FMChecklistScreen = ({ data, updateData, selectedCats, onComplete }) => {
  const [activeWizard, setActiveWizard] = useState(null); // 'banks', 'investments', 'property', 'loans'
  
  const hasBanks = selectedCats.includes('banks');
  const hasInv = selectedCats.includes('investments');
  const hasProp = selectedCats.includes('property');
  const hasLoans = LIABILITY_CATS.some(c => selectedCats.includes(c.id));
  
  const [completed, setCompleted] = useState({
    banks: !hasBanks, investments: !hasInv, property: !hasProp, loans: !hasLoans
  });

  const checkCompletion = (type) => { setCompleted(prev => ({ ...prev, [type]: true })); setActiveWizard(null); }
  
  const allComplete = completed.banks && completed.investments && completed.property && completed.loans;

  return (
    <div className="max-w-2xl mx-auto py-12 px-6">
      <FadeIn>
        {!activeWizard ? (
          <div>
             <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Let's add a few details.</h2>
             <div className="space-y-4 className mt-8">
               {hasBanks && (
                 <div className="p-5 border border-slate-200 rounded-xl bg-white flex justify-between items-center">
                   <div className="flex gap-3 items-center">
                     <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${completed.banks ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300'}`}>{completed.banks && <Check size={14} />}</div>
                     <span className="font-bold">Bank accounts & cash</span>
                   </div>
                   <Button variant={completed.banks ? "secondary" : "primary"} className="w-fit py-2 px-4 text-sm" onClick={() => setActiveWizard('banks')}>{completed.banks ? 'Edit' : 'Add'}</Button>
                 </div>
               )}
               {hasInv && (
                 <div className="p-5 border border-slate-200 rounded-xl bg-white flex justify-between items-center">
                   <div className="flex gap-3 items-center">
                     <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${completed.investments ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300'}`}>{completed.investments && <Check size={14} />}</div>
                     <span className="font-bold">Investments</span>
                   </div>
                   <Button variant={completed.investments ? "secondary" : "primary"} className="w-fit py-2 px-4 text-sm" onClick={() => setActiveWizard('investments')}>{completed.investments ? 'Edit' : 'Add'}</Button>
                 </div>
               )}
               {hasProp && (
                 <div className="p-5 border border-slate-200 rounded-xl bg-white flex justify-between items-center">
                   <div className="flex gap-3 items-center">
                     <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${completed.property ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300'}`}>{completed.property && <Check size={14} />}</div>
                     <span className="font-bold">Property</span>
                   </div>
                   <Button variant={completed.property ? "secondary" : "primary"} className="w-fit py-2 px-4 text-sm" onClick={() => setActiveWizard('property')}>{completed.property ? 'Edit' : 'Add'}</Button>
                 </div>
               )}
               {hasLoans && (
                 <div className="p-5 border border-slate-200 rounded-xl bg-white flex justify-between items-center">
                   <div className="flex gap-3 items-center">
                     <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${completed.loans ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300'}`}>{completed.loans && <Check size={14} />}</div>
                     <span className="font-bold">Loans and credit cards</span>
                   </div>
                   <Button variant={completed.loans ? "secondary" : "primary"} className="w-fit py-2 px-4 text-sm" onClick={() => setActiveWizard('loans')}>{completed.loans ? 'Edit' : 'Add'}</Button>
                 </div>
               )}
             </div>
             <div className="mt-10 flex justify-end">
               <Button onClick={onComplete} disabled={!allComplete} className="w-fit px-10">Continue to Dashboard</Button>
             </div>
          </div>
        ) : (
          <GenericMicroWizard 
            type={activeWizard} 
            data={data} 
            updateData={updateData} 
            onBack={() => setActiveWizard(null)} 
            onSave={() => checkCompletion(activeWizard)} 
          />
        )}
      </FadeIn>
    </div>
  )
}

// A reusable mini flow for adding assets
const GenericMicroWizard = ({ type, data, updateData, onBack, onSave }) => {
  const [items, setItems] = useState([]);
  const [adding, setAdding] = useState({ name: '', value: '', detail: '' });

  const commitItem = () => {
    if(!adding.name || !adding.value) return;
    const newItem = { id: Date.now(), type, name: adding.name, value: adding.value, detail: adding.detail };
    setItems([...items, newItem]);
    setAdding({ name: '', value: '', detail: '' });
  }

  const handleFinalSave = () => {
    if(adding.name && adding.value) commitItem();
    // Save to global state
    const isLoan = type === 'loans';
    if(isLoan) {
      updateData({ liabilities: [...data.liabilities, ...items] });
    } else {
      updateData({ assets: [...data.assets, ...items] });
    }
    onSave();
  }
  
  const labels = {
    banks: { title: 'Add bank accounts', fields: ['Institution name', 'Approximate balance', 'Account Type (Savings, Salary)'] },
    investments: { title: 'Add investments', fields: ['Platform/Fund', 'Current value', 'Type (MF, Stock, EPF)'] },
    property: { title: 'Add property', fields: ['Property name/location', 'Current market value', 'Type'] },
    loans: { title: 'Add loans & cards', fields: ['Lender', 'Outstanding balance', 'Type'] }
  }[type];

  return (
    <div>
      <button onClick={onBack} className="text-sm text-slate-400 mb-6 flex items-center gap-1 hover:text-slate-600">← Back to checklist</button>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">{labels.title}</h2>
      
      {items.map(i => (
        <div key={i.id} className="p-3 border border-slate-200 rounded-lg mb-3 flex items-center justify-between shadow-sm">
          <div><p className="font-bold text-sm text-slate-800">{i.name}</p><p className="text-xs text-slate-500">{i.detail}</p></div>
          <span className="font-semibold text-slate-700">{i.value}</span>
        </div>
      ))}

      <div className="bg-slate-50 border border-slate-200 p-5 rounded-xl space-y-4">
        <Input label={labels.fields[0]} value={adding.name} onChange={v => setAdding({...adding, name: v})} placeholder="e.g. HDFC Bank" />
        <Input label={labels.fields[1]} type="number" value={adding.value} onChange={v => setAdding({...adding, value: v})} placeholder="0" prefix="₹" />
        <Input label={labels.fields[2]} value={adding.detail} onChange={v => setAdding({...adding, detail: v})} placeholder="e.g. Savings account" />
        
        <Button variant="secondary" onClick={commitItem} disabled={!adding.name || !adding.value} className="py-2.5 text-sm">Add another {type.slice(0,-1)}</Button>
      </div>

      <div className="mt-8">
        <Button onClick={handleFinalSave}>Save and Return</Button>
      </div>
    </div>
  )
}
