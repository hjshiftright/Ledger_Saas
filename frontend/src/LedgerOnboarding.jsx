import React, { useState, useEffect } from 'react';
import { 
  Briefcase, Home, GraduationCap, Check, 
  ArrowRight, ShieldAlert, Palmtree, Target,
  Bot, CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API } from './api.js';

// --- DATA: PERSONAS & TEMPLATES ---
const PERSONAS = {
  salaried: {
    id: 'salaried', name: 'The Salaried Professional', icon: Briefcase,
    desc: 'You earn a fixed salary, pay EMIs or rent, and invest in mutual funds or stocks.',
    defaults: { workType: 'Salaried', takeHome: 120000, expenses: 70000, age: 29 },
  },
  household: {
    id: 'household', name: 'Household / Family Manager', icon: Home,
    desc: 'You manage joint finances, multiple income sources, and plan for family goals.',
    defaults: { workType: 'Business/Mixed', takeHome: 250000, expenses: 140000, age: 42 },
  },
  starter: {
    id: 'starter', name: 'The Early Starter', icon: GraduationCap,
    desc: 'You just started working, want to build good habits, and need simple tracking.',
    defaults: { workType: 'Entry Level', takeHome: 50000, expenses: 35000, age: 22 },
  }
};

const CATALOGUE = {
  assets: {
    banks: ['HDFC', 'SBI', 'ICICI', 'Axis', 'Kotak', 'IDFC First', 'PNB'],
    investments: ['EPF', 'PPF', 'Zerodha', 'Groww', 'Kuvera', 'FD', 'Real Estate']
  },
  liabilities: {
    loans: ['HDFC Home Loan', 'SBI Home Loan', 'Vehicle Loan', 'Personal Loan', 'Education Loan'],
    cards: ['HDFC Credit Card', 'SBI Card', 'ICICI Amazon Pay', 'Axis Flipkart', 'Amex', 'OneCard']
  }
};

export default function LedgerOnboarding() {
  const [step, setStep] = useState(1);
  const [data, setData] = useState({ name: '', persona: null, assets: [], liabilities: [], balances: {}, netWorth: 0, loading: false });

  const nextStep = () => setStep(s => Math.min(s + 1, 5));
  const prevStep = () => setStep(s => Math.max(s - 1, 1));

  // --- STEPS CONFIGURATION ---
  const stepConfig = {
    1: { title: 'PROFILE & PERSONA', component: <ProfilePersonaStep data={data} setData={setData} next={nextStep} /> },
    2: { title: 'THE MONEY MAP', component: <MoneyMapStep data={data} setData={setData} prev={prevStep} next={nextStep} /> },
    3: { title: 'OPENING BALANCES', component: <OpeningBalancesStep data={data} setData={setData} prev={prevStep} next={nextStep} /> },
    4: { title: 'GOAL PLANNER', component: <GoalPlannerStep data={data} prev={prevStep} next={nextStep} /> },
    5: { title: 'REVIEW', component: <ReviewStep data={data} prev={prevStep} /> }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-500/30 flex flex-col items-center pt-8 overflow-hidden">
      {/* HEADER PROGRESS BAR */}
      <div className="w-full max-w-5xl px-8 mb-12">
        <h1 className="text-2xl font-bold mb-8">Ledger</h1>
        <div className="flex justify-between relative">
           <div className="absolute top-1/2 left-0 right-0 h-1 bg-slate-200 -z-10 -translate-y-1/2 rounded-full"></div>
           {[1, 2, 3, 4, 5].map(i => (
             <div key={i} className={`flex-1 ${i === 1 ? 'text-left' : i === 5 ? 'text-right' : 'text-center'} relative`}>
               <div className={`text-[10px] font-bold tracking-widest uppercase mb-2 ${step >= i ? 'text-indigo-600' : 'text-slate-400'}`}>STEP {i} OF 5</div>
               {step >= i && <div className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">{stepConfig[i].title}</div>}
               <div className={`h-1 w-full rounded-full transition-all duration-500 ${step >= i ? 'bg-indigo-600' : 'bg-transparent'}`}></div>
             </div>
           ))}
        </div>
      </div>

      <div className="w-full max-w-5xl flex gap-12 px-8 flex-1">
        {/* LEFT MAIN CONTENT */}
        <div className="flex-1 max-w-3xl pb-24">
           {stepConfig[step].component}
        </div>

        {/* RIGHT SIDEBAR (AI ASSISTANT TEXT) */}
        <div className="w-80 hidden lg:block shrink-0">
          <div className="bg-indigo-50/50 border border-indigo-100/50 rounded-2xl p-6 sticky top-8">
            <div className="flex items-center gap-3 mb-4 text-indigo-700">
               <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                 <Bot className="w-4 h-4" />
               </div>
               <div>
                 <div className="text-xs font-bold uppercase tracking-wider">LEDGER ASSISTANT</div>
                 <div className="text-xs opacity-70">{stepConfig[step].title}</div>
               </div>
            </div>
            <div className="text-sm text-indigo-900/80 leading-relaxed bg-white p-4 rounded-xl shadow-sm border border-indigo-50 space-y-4">
               {step === 1 && <p>To save you time, I use 'Personas'. Selecting a persona instantly pre-fills your estimated income, expenses, and a standard Chart of Accounts used by similar people in India. You don't have to type everything from scratch.</p>}
               {step === 2 && <p>Let's map out where your money lives. Select the banks and cards you use. I'll automatically create the correct double-entry ledger accounts for them behind the scenes.</p>}
               {step === 3 && <p>Here are the accounts we generated from your map. Enter your current balances to set your starting Net Worth. Don't know the exact penny? Approximations are perfectly fine.</p>}
               {step === 4 && <p>I've calculated your Monthly Surplus based on the profile you selected. I also used standard PRD math (6% inflation, 25x annual expenses) to project what your Retirement Corpus needs to be. Select the goals you want to track to see if they are realistic!</p>}
               {step === 5 && <p>Almost done! Review your starting Net Worth and Financial Plan. If everything looks good, click 'Launch Dashboard' and I'll finalize your double-entry accounts.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------
// STEP 1: PROFILE & PERSONA (GUIDED WIZARD)
// ----------------------------------------------------
function ProfilePersonaStep({ data, setData, next }) {
  const [name, setName] = useState(data.name || '');
  const [selectedP, setSelectedP] = useState(data.persona?.id || null);

  const handleNext = () => {
    setData({ ...data, name, persona: PERSONAS[selectedP] });
    next();
  };

  return (
     <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-10">
        <div>
          <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">Let's find your starting point.</h2>
          <p className="text-lg text-slate-500">Tell us your name and pick the profile that best matches your life right now.</p>
        </div>

        <div className="space-y-4">
          <label className="text-sm font-bold text-slate-900">What should we call you?</label>
          <input 
            type="text" 
            placeholder="e.g. Rahul" 
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full max-w-sm px-4 py-3 bg-white border-2 border-slate-200 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all font-medium"
          />
        </div>

        <div className="space-y-4">
          <label className="text-sm font-bold text-slate-900 block">Select your financial persona:</label>
          <div className="grid md:grid-cols-3 gap-4">
            {Object.values(PERSONAS).map(p => {
              const Icon = p.icon;
              const isSel = selectedP === p.id;
              return (
                 <button 
                  key={p.id}
                  onClick={() => setSelectedP(p.id)}
                  className={`text-left p-6 rounded-2xl border-2 transition-all block relative ${isSel ? 'border-indigo-600 bg-indigo-50/30 shadow-md shadow-indigo-100' : 'border-slate-200 bg-white hover:border-slate-300'}`}
                 >
                   {isSel && <div className="absolute top-4 right-4 w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center"><Check className="w-3 h-3" strokeWidth={3} /></div>}
                   <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${isSel ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
                     <Icon className="w-6 h-6" />
                   </div>
                   <h3 className="font-bold text-slate-900 text-lg mb-2">{p.name}</h3>
                   <p className="text-sm text-slate-500 leading-relaxed mb-4">{p.desc}</p>
                   <div className="text-xs font-semibold text-slate-400">Pre-fills: ~₹{p.defaults.takeHome / 1000}k income, ~₹{p.defaults.expenses / 1000}k exp.</div>
                 </button>
              )
            })}
          </div>
        </div>

        <div className="flex justify-end pt-8 border-t border-slate-200">
           <button 
             onClick={handleNext} 
             disabled={!name || !selectedP}
             className="bg-indigo-600 text-white px-8 py-3.5 rounded-xl font-bold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-indigo-200 transition-all active:scale-95"
           >
             Continue <ArrowRight className="w-5 h-5" />
           </button>
        </div>
     </motion.div>
  );
}

// ----------------------------------------------------
// STEP 2: THE MONEY MAP (ASSETS & LIABILITIES CATALOGUE)
// ----------------------------------------------------
function MoneyMapStep({ data, setData, prev, next }) {
  const [assets, setAssets] = useState(data.assets || []);
  const [liabilities, setLiabilities] = useState(data.liabilities || []);

  const toggleAsset = (item) => {
    if(assets.includes(item)) setAssets(assets.filter(i => i !== item));
    else setAssets([...assets, item]);
  };

  const toggleLiab = (item) => {
    if(liabilities.includes(item)) setLiabilities(liabilities.filter(i => i !== item));
    else setLiabilities([...liabilities, item]);
  };

  const handleNext = () => {
    setData({ ...data, assets, liabilities });
    next();
  };

  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-10">
      <div>
        <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">Map your financial life.</h2>
        <p className="text-lg text-slate-500">Select the banks, apps, and loans you currently use.</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm space-y-8">
         {/* WHAT YOU OWN (ASSETS) */}
         <div>
             <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-600 mb-4 bg-emerald-50 inline-block px-3 py-1 rounded-full">WHAT YOU OWN (ASSETS)</h3>
             <div className="mb-6">
                <h4 className="text-sm font-bold text-slate-700 mb-3">BANKS & ACCOUNTS</h4>
                <div className="flex flex-wrap gap-3">
                  {CATALOGUE.assets.banks.map(item => (
                     <button 
                       key={item} onClick={() => toggleAsset(item)}
                       className={`px-4 py-2 rounded-xl text-sm font-bold transition-all border-2 ${assets.includes(item) ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}
                     >{item}</button>
                  ))}
                </div>
             </div>
             <div>
                <h4 className="text-sm font-bold text-slate-700 mb-3">INVESTMENTS & BROKERS</h4>
                <div className="flex flex-wrap gap-3">
                  {CATALOGUE.assets.investments.map(item => (
                     <button 
                       key={item} onClick={() => toggleAsset(item)}
                       className={`px-4 py-2 rounded-xl text-sm font-bold transition-all border-2 ${assets.includes(item) ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}
                     >{item}</button>
                  ))}
                </div>
             </div>
         </div>

         <div className="h-px bg-slate-200 w-full" />

         {/* WHAT YOU OWE (LIABILITIES) */}
         <div>
             <h3 className="text-xs font-bold uppercase tracking-wider text-rose-500 mb-4 bg-rose-50 inline-block px-3 py-1 rounded-full">WHAT YOU OWE (LIABILITIES)</h3>
             <div className="mb-6">
                <h4 className="text-sm font-bold text-slate-700 mb-3">LOANS</h4>
                <div className="flex flex-wrap gap-3">
                  {CATALOGUE.liabilities.loans.map(item => (
                     <button 
                       key={item} onClick={() => toggleLiab(item)}
                       className={`px-4 py-2 rounded-xl text-sm font-bold transition-all border-2 ${liabilities.includes(item) ? 'bg-rose-50 border-rose-500 text-rose-700' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}
                     >{item}</button>
                  ))}
                </div>
             </div>
             <div>
                <h4 className="text-sm font-bold text-slate-700 mb-3">CREDIT CARDS</h4>
                <div className="flex flex-wrap gap-3">
                  {CATALOGUE.liabilities.cards.map(item => (
                     <button 
                       key={item} onClick={() => toggleLiab(item)}
                       className={`px-4 py-2 rounded-xl text-sm font-bold transition-all border-2 ${liabilities.includes(item) ? 'bg-rose-50 border-rose-500 text-rose-700' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}
                     >{item}</button>
                  ))}
                </div>
             </div>
         </div>
      </div>

      <div className="flex justify-between items-center pt-8 border-t border-slate-200">
         <button onClick={prev} className="text-slate-500 font-bold hover:text-slate-900 transition-colors">← Back</button>
         <button onClick={handleNext} className="bg-indigo-600 text-white px-8 py-3.5 rounded-xl font-bold hover:bg-indigo-700 flex items-center gap-2 shadow-lg shadow-indigo-200 transition-all active:scale-95">
           Continue <ArrowRight className="w-5 h-5" />
         </button>
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------
// STEP 3: OPENING BALANCES
// ----------------------------------------------------
function OpeningBalancesStep({ data, setData, prev, next }) {
  const [balances, setBalances] = useState(data.balances || { "Cash on Hand": "" });
  const [apiLogs, setApiLogs] = useState([]);

  const updateBalance = (key, val) => setBalances(b => ({...b, [key]: val}));

  // Live preview before server calculates true net worth
  const currentAssets = ['Cash on Hand', ...data.assets].reduce((sum, k) => sum + (parseFloat(balances[k]) || 0), 0);
  const currentLiabilities = data.liabilities.reduce((sum, k) => sum + (parseFloat(balances[k]) || 0), 0);
  const expectedNetWorth = currentAssets - currentLiabilities;

  const logApiCall = (message, status = 'info') => {
    setApiLogs(prevLogs => [...prevLogs, { message, status, timestamp: new Date().toLocaleTimeString() }]);
  };

  const handleNext = async () => {
    setData(p => ({ ...p, loading: true }));
    setApiLogs([]); // Clear logs for new attempt

    try {
      logApiCall("Starting API calls...");

      // 1. Create profile (idempotent — ignore any error since profile can already exist)
      logApiCall("1. Creating profile...");
      try {
        await API.profile.create({ display_name: data.name, base_currency: "INR", financial_year_start_month: 4, tax_regime: "NEW", date_format: "DD/MM/YYYY", number_format: "INDIAN" });
        logApiCall("✓ Profile created.", "success");
      } catch(e) {
        logApiCall(`Profile: ${e.message} — continuing.`, "warning");
      }

      // 2. Initialize COA (idempotent — ignore any error since COA may already be seeded)
      logApiCall("2. Initializing Chart of Accounts...");
      try {
        await API.coa.initialize();
        logApiCall("✓ COA initialized.", "success");
      } catch(e) {
        logApiCall(`COA init: ${e.message} — continuing.`, "warning");
      }

      // 3. Create institution
      logApiCall("3. Creating 'My Ledger' institution...");
      const inst = await API.institutions.create({ name: "My Ledger", institution_type: "BANK" });
      logApiCall(`Institution '${inst.name}' created.`, "success");

      // 4. Fetch COA tree and find non-placeholder leaf IDs
      logApiCall("4. Fetching Chart of Accounts tree...");
      const coaRes = await fetch("http://127.0.0.1:8000/api/v1/onboarding/coa/tree").then(r => r.json());
      logApiCall("COA tree fetched.", "success");
      
      // Only match non-placeholder (actual leaf) nodes
      const findLeafId = (nodes, name) => {
        for (let n of nodes) {
          if (n.name.toLowerCase() === name.toLowerCase() && !n.is_placeholder) return n.id;
          if (n.children?.length) {
            const res = findLeafId(n.children, name);
            if (res) return res;
          }
        }
        return null;
      };

      // "Cash in Hand" is the actual leaf under the "Cash" placeholder (code 1201)
      const cashId = findLeafId(coaRes.items, "Cash in Hand");

      const accMap = {};
      if (cashId) accMap["Cash on Hand"] = cashId;

      // 5. Create bank accounts from the assets selected in step 2
      logApiCall("5. Creating bank accounts...");
      for (let asset of data.assets) {
        try {
          const acc = await API.accounts.createBank({
            display_name: asset,
            institution_id: inst.id,
            account_number_masked: "0000",
            bank_account_type: "SAVINGS"
          });
          accMap[asset] = acc.coa?.id ?? acc.id;
          logApiCall(`Bank account '${asset}' created.`, "success");
        } catch(e) { 
          console.error("Bank account error:", asset, e); 
          logApiCall(`Failed to create bank account '${asset}': ${e.message}`, "error");
        }
      }

      // 6. Create credit card accounts from the liabilities selected in step 2
      logApiCall("6. Creating credit card accounts...");
      for (let liab of data.liabilities) {
        try {
          const acc = await API.accounts.createCard({
            display_name: liab,
            institution_id: inst.id,
            last_four_digits: "0000",
            credit_limit: 100000,
            billing_cycle_day: 1,
            interest_rate_annual: 0
          });
          accMap[liab] = acc.coa?.id ?? acc.id;
          logApiCall(`Credit card account '${liab}' created.`, "success");
        } catch(e) { 
          console.error("Credit card error:", liab, e); 
          logApiCall(`Failed to create credit card account '${liab}': ${e.message}`, "error");
        }
      }

      // 7. Post opening balances for all fields that have a value and a mapped account ID
      logApiCall("7. Submitting opening balances...");
      const balanceEntries = Object.entries(balances)
        .filter(([k, v]) => v && parseFloat(v) > 0 && accMap[k])
        .map(([k, v]) => ({
          account_id: accMap[k],
          balance_amount: parseFloat(v),
          balance_date: new Date().toISOString().split('T')[0]
        }));

      if (balanceEntries.length > 0) {
        await API.openingBalances.submitBulk(balanceEntries);
        logApiCall(`${balanceEntries.length} opening balances submitted.`, "success");
      } else {
        logApiCall("No opening balances to submit.", "info");
      }

      // 8. Compute Net Worth
      logApiCall("8. Computing Net Worth...");
      const nw = await API.netWorth.compute(new Date().toISOString().split('T')[0]);
      logApiCall(`Net Worth computed: ₹${nw.net_worth?.toLocaleString('en-IN') || 0}`, "success");
      setData(prev => ({ ...prev, balances, netWorth: nw.net_worth ?? 0, loading: false }));
      
      // Pause for 1.5 seconds so the user can see the success log before navigating
      setTimeout(() => {
        next();
      }, 1500);
    } catch (err) {
      console.error("Onboarding error:", err);
      logApiCall(`Onboarding failed: ${err.message || 'Unknown error'}`, "error");
      setData(prev => ({ ...prev, balances, loading: false }));
    }
  };

  const logColors = { success: 'text-emerald-600', error: 'text-rose-600', warning: 'text-amber-500', info: 'text-slate-500' };
  const logIcons  = { success: '✓', error: '✗', warning: '⚠', info: '›' };

  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-10">
      <div>
        <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">Putting numbers to your map.</h2>
        <p className="text-lg text-slate-500">Enter current balances to establish your initial Net Worth.</p>
      </div>

      {/* API LOG OVERLAY during loading */}
      {(data.loading || apiLogs.length > 0) && (
        <div className="bg-slate-950 text-slate-100 rounded-2xl p-5 font-mono text-xs space-y-2 shadow-2xl border border-slate-700">
          <div className="flex items-center gap-2 text-slate-400 mb-3 pb-2 border-b border-slate-800">
            <span className="w-3 h-3 rounded-full bg-rose-500 inline-block"/>
            <span className="w-3 h-3 rounded-full bg-amber-400 inline-block"/>
            <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"/>
            <span className="ml-2 font-bold tracking-widest uppercase text-[10px]">API Call Log</span>
          </div>
          {apiLogs.map((log, i) => (
            <div key={i} className={`flex gap-3 items-start ${logColors[log.status] || 'text-slate-400'}`}>
              <span className="shrink-0 font-bold">{logIcons[log.status] || '›'}</span>
              <span className="text-slate-400 shrink-0">[{log.timestamp}]</span>
              <span>{log.message}</span>
            </div>
          ))}
          {data.loading && (
            <div className="flex items-center gap-2 text-indigo-400 pt-1">
              <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <span>Processing...</span>
            </div>
          )}
        </div>
      )}

      {/* Error state with retry hint */}
      {data.apiError && !data.loading && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-700 text-sm font-medium">
          ✗ {data.apiError} — Check the log above and try again. Make sure the backend server is running.
        </div>
      )}

      <div className="space-y-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-600">ASSETS</h3>
        
        {['Cash on Hand', ...data.assets].map(item => (
          <div key={item} className="bg-white border border-slate-200 rounded-2xl p-4 flex justify-between items-center shadow-sm">
             <span className="font-bold text-slate-700">{item}</span>
             <div className="flex items-center bg-slate-100 rounded-lg px-4 py-2 w-48 focus-within:ring-2 focus-within:ring-indigo-500">
               <span className="text-slate-400 mr-2 font-medium">₹</span>
               <input type="number" value={balances[item] || ''} onChange={(e) => updateBalance(item, e.target.value)} placeholder="0.00" className="bg-transparent outline-none w-full text-right font-bold text-slate-900" />
             </div>
          </div>
        ))}

        {data.liabilities.length > 0 && (
           <>
              <h3 className="text-xs font-bold uppercase tracking-wider text-rose-500 pt-4">LIABILITIES</h3>
              {data.liabilities.map(item => (
                <div key={item} className="bg-white border border-slate-200 rounded-2xl p-4 flex justify-between items-center shadow-sm">
                   <span className="font-bold text-slate-700">{item}</span>
                   <div className="flex items-center bg-rose-50 rounded-lg px-4 py-2 w-48 focus-within:ring-2 focus-within:ring-rose-500">
                     <span className="text-rose-400 mr-2 font-medium">₹</span>
                     <input type="number" value={balances[item] || ''} onChange={(e) => updateBalance(item, e.target.value)} placeholder="0.00" className="bg-transparent outline-none w-full text-right font-bold text-rose-900" />
                   </div>
                </div>
              ))}
           </>
        )}

        <div className="bg-slate-900 text-white rounded-2xl p-6 flex justify-between items-center shadow-xl shadow-slate-900/20 mt-8">
           <div>
             <div className="font-bold tracking-widest text-xs uppercase text-slate-400 mb-1">STARTING NET WORTH</div>
             <div className="text-slate-500 text-sm">Assets minus Liabilities</div>
           </div>
           <div className={`text-4xl font-black ${expectedNetWorth >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
             {expectedNetWorth < 0 ? '-' : ''}₹{Math.abs(expectedNetWorth).toLocaleString('en-IN')}
           </div>
        </div>
      </div>

      <div className="flex justify-between items-center pt-8 border-t border-slate-200">
         <button onClick={prev} disabled={data.loading} className="text-slate-500 font-bold hover:text-slate-900 transition-colors disabled:opacity-50">← Back</button>
         <button onClick={handleNext} disabled={data.loading} className="bg-indigo-600 text-white px-8 py-3.5 rounded-xl font-bold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-indigo-200 transition-all active:scale-95">
           {data.loading ? 'Calculating...' : 'Calculate Net Worth'} <ArrowRight className="w-5 h-5" />
         </button>
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------
// STEP 4: GOAL PLANNER
// ----------------------------------------------------
function GoalPlannerStep({ data, prev, next }) {
  const surplus = data.persona?.defaults.takeHome - data.persona?.defaults.expenses;

  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-10">
      <div>
        <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">Goal Planner.</h2>
        <p className="text-lg text-slate-500">Let's see if your goals are realistic based on your surplus.</p>
      </div>

      <div className="bg-indigo-50/50 border border-indigo-100 rounded-3xl p-6 flex justify-between items-center">
         <div>
           <div className="font-bold text-indigo-900 mb-1">Your Monthly Surplus</div>
           <div className="text-indigo-600/70 text-sm">Income minus Expenses. Available for SIPs.</div>
         </div>
         <div className="text-3xl font-black text-indigo-600">₹{surplus?.toLocaleString('en-IN') || '50,000'}</div>
      </div>

      <div className="space-y-4">
         <div className="bg-white border border-slate-200 rounded-2xl p-6 flex items-center gap-4 hover:border-indigo-300 transition-colors cursor-pointer group">
           <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center shrink-0 group-hover:bg-indigo-100 text-slate-500 group-hover:text-indigo-600 transition-colors">
              <ShieldAlert className="w-6 h-6" />
           </div>
           <div className="flex-1">
             <div className="font-bold text-lg text-slate-900">Emergency Fund</div>
             <div className="text-slate-500 text-sm">6 months of expenses to protect against shocks.</div>
           </div>
           <div className="text-xl font-bold text-slate-900">₹{(data.persona?.defaults.expenses * 6).toLocaleString('en-IN') || '4,20,000'}</div>
         </div>

         <div className="bg-white border border-slate-200 rounded-2xl p-6 flex items-center gap-4 hover:border-indigo-300 transition-colors cursor-pointer group">
           <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center shrink-0 group-hover:bg-indigo-100 text-slate-500 group-hover:text-indigo-600 transition-colors">
              <Palmtree className="w-6 h-6" />
           </div>
           <div className="flex-1">
             <div className="font-bold text-lg text-slate-900">Retirement at Age 60</div>
             <div className="text-slate-500 text-sm">Inflation adjusted future living costs.</div>
           </div>
           <div className="text-xl font-bold text-slate-900">₹12.79 Cr</div>
         </div>
      </div>

      <div className="flex justify-between items-center pt-8 border-t border-slate-200">
         <button onClick={prev} className="text-slate-500 font-bold hover:text-slate-900 transition-colors">← Back</button>
         <button onClick={next} className="bg-indigo-600 text-white px-8 py-3.5 rounded-xl font-bold hover:bg-indigo-700 flex items-center gap-2 shadow-lg shadow-indigo-200 transition-all active:scale-95">
           Continue <ArrowRight className="w-5 h-5" />
         </button>
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------
// STEP 5: REVIEW
// ----------------------------------------------------
function ReviewStep({ data, prev }) {
  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-10 text-center flex flex-col items-center">
      <div className="w-24 h-24 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-6 mt-8">
        <CheckCircle2 className="w-12 h-12" />
      </div>
      <div>
        <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">You're all set, {data.name}!</h2>
        <p className="text-lg text-slate-500 max-w-lg mx-auto">We've translated your profile into a professional double-entry ledger. Your base accounts are ready.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 w-full max-w-md mt-6 text-left">
         <div className="bg-white border border-slate-200 p-4 rounded-xl">
           <div className="text-xs text-slate-500 font-bold mb-1">PERSONA</div>
           <div className="font-bold text-slate-900">{data.persona?.name || 'Unknown'}</div>
         </div>
         <div className="bg-white border border-slate-200 p-4 rounded-xl">
           <div className="text-xs text-slate-500 font-bold mb-1">STARTING NET WORTH</div>
           <div className="font-bold text-slate-900">₹{data.netWorth?.toLocaleString('en-IN') || 0}</div>
         </div>
         <div className="bg-white border border-slate-200 p-4 rounded-xl col-span-2">
           <div className="text-xs text-slate-500 font-bold mb-1">MAPPED ACCOUNTS</div>
           <div className="font-bold text-slate-900">{data.assets.length + data.liabilities.length > 0 ? [...data.assets, ...data.liabilities].join(', ') : 'Base templates only'}</div>
         </div>
      </div>

      <div className="pt-8 w-full flex justify-center">
         <button className="bg-emerald-600 text-white px-10 py-4 text-lg rounded-xl font-bold hover:bg-emerald-700 flex items-center gap-3 shadow-xl shadow-emerald-200 transition-all active:scale-95">
           Launch Dashboard <ArrowRight className="w-6 h-6" />
         </button>
      </div>
    </motion.div>
  );
}
