import React, { useState, useEffect, useMemo } from 'react';
import { 
  Plus, Trash2, TrendingUp, TrendingDown, 
  Wallet, Landmark, Building2, PieChart, 
  Coins, Gem, MoreHorizontal, CreditCard, 
  Home, Car, User, GraduationCap, 
  Target, Plane, Heart, Calculator,
  ArrowRight, ShieldCheck, Info, ChevronRight,
  ChevronDown, RefreshCcw, Save
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API } from './api.js';
import AddLedgerItemDialog from './AddLedgerItemDialog';

// --- CONSTANTS ---
const BANK_OPTIONS = ['HDFC', 'SBI', 'ICICI', 'Axis', 'Kotak', 'IDFC First', 'PNB', 'IndusInd', 'Standard Chartered', 'Other / Custom'];
const GOAL_ICONS = {
  "Kid's Education": GraduationCap,
  "Marriage": Heart,
  "Holiday": Plane,
  "Retirement": Target,
  "Custom": Target
};

const INFLATION_RATE = 0.06; // 6% default inflation for India

export default function NetWorthDashboard() {
  const [activeTab, setActiveTab] = useState('assets'); // 'assets', 'liabilities', 'goals', 'summary'
  const [age, setAge] = useState(30);
  const [monthlyIncome, setMonthlyIncome] = useState(150000);
  const [monthlyExpenses, setMonthlyExpenses] = useState(50000);
  const [name, setName] = useState('Rahul');
  
  // -- ASSET STATE --
  const [assets, setAssets] = useState({
    banks: [{ id: 1, name: 'HDFC Bank', balance: 0 }],
    realEstate: [{ id: 1, name: 'Primary Residence', balance: 0 }],
    equity: [{ id: 1, name: 'Mutual Funds', balance: 0 }],
    foreignEquity: [{ id: 1, name: 'S&P 500 Index', balance: 0 }],
    providentFund: [{ id: 1, name: 'EPF', balance: 0 }],
    fixedDeposits: [{ id: 1, name: 'FD (SBI)', balance: 0 }],
    bullion: [{ id: 1, name: 'Gold Jewellery', balance: 0 }],
    others: [{ id: 1, name: 'Cash on Hand', balance: 0 }]
  });

  // -- LIABILITY STATE --
  const [liabilities, setLiabilities] = useState({
    creditCards: [{ id: 1, name: 'ICICI Amazon Pay', balance: 0 }],
    homeLoans: [{ id: 1, name: 'HDFC Home Loan', balance: 0 }],
    vehicleLoans: [],
    personalLoans: [],
    educationalLoans: []
  });

  // -- GOALS STATE --
  const [goals, setGoals] = useState([
    { id: 1, name: "Kid's Education", target: 5000000, years: 15, current: 0 },
    { id: 2, name: "Retirement", target: 50000000, years: 30, current: 0 }
  ]);

  // -- CALCULATIONS --
  const totalAssets = useMemo(() => {
    return Object.values(assets).flat().reduce((sum, item) => sum + (parseFloat(item.balance) || 0), 0);
  }, [assets]);

  const totalLiabilities = useMemo(() => {
    return Object.values(liabilities).flat().reduce((sum, item) => sum + (parseFloat(item.balance) || 0), 0);
  }, [liabilities]);

  const netWorth = totalAssets - totalLiabilities;

  const surplus = monthlyIncome - monthlyExpenses;

  // Expected Net Worth based on simple "Age Multiplier" (e.g., Age * Annual Expense / 5)
  // or a more sophisticated retirement projection.
  const expectedNW = useMemo(() => {
    // Basic Health Rule: (Age - 22) * Annual Surplus
    return Math.max(0, (age - 22) * surplus * 3); // 3x multiplier as a healthy target
  }, [age, surplus]);

  // Inflation adjusted retirement need
  const inflationAdjustedExpenses = useMemo(() => {
    const yearsToRetire = Math.max(0, 60 - age);
    return monthlyExpenses * Math.pow(1 + INFLATION_RATE, yearsToRetire);
  }, [age, monthlyExpenses]);

  const requiredCorpusAt60 = useMemo(() => {
    // 25x Rule (4% withdrawal) adjusted for inflation
    return inflationAdjustedExpenses * 12 * 25;
  }, [inflationAdjustedExpenses]);

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [addDialogCategory, setAddDialogCategory] = useState(null);

  // -- LOAD DATA --
  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await API.dashboard.load();
        if (data) {
          setName(data.name || 'Rahul');
          setAge(data.age || 30);
          setMonthlyIncome(data.monthly_income || 150000);
          setMonthlyExpenses(data.monthly_expenses || 50000);
          
          if (Object.keys(data.assets).length > 0) setAssets(data.assets);
          if (Object.keys(data.liabilities).length > 0) setLiabilities(data.liabilities);
          if (data.goals.length > 0) setGoals(data.goals);
        }
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // -- HANDLERS --
  const handleSaveDashboard = async () => {
    setSaving(true);
    try {
      const payload = {
        name,
        age,
        monthly_income: monthlyIncome,
        monthly_expenses: monthlyExpenses,
        assets,
        liabilities,
        goals
      };
      await API.dashboard.save(payload);
      alert("Snapshot saved successfully!");
    } catch (err) {
      console.error("Save failed:", err);
      alert("Failed to save snapshot.");
    } finally {
      setSaving(false);
    }
  };

  const addItem = (category, type) => {
    setAddDialogCategory(category);
    setIsAddDialogOpen(true);
  };

  const handleDialogAdd = (category, type, entryData) => {
    const setter = type === 'asset' ? setAssets : setLiabilities;
    setter(prev => ({
      ...prev,
      [category]: [...(prev[category] || []), { 
        id: Date.now(), 
        name: entryData.name, 
        balance: entryData.balance,
        description: entryData.description,
        owner: entryData.owner 
      }]
    }));
  };

  const removeItem = (category, id, type) => {
    const setter = type === 'asset' ? setAssets : setLiabilities;
    setter(prev => ({
      ...prev,
      [category]: (prev[category] || []).filter(item => item.id !== id)
    }));
  };

  const updateItem = (category, id, field, value, type) => {
    const setter = type === 'asset' ? setAssets : setLiabilities;
    setter(prev => ({
      ...prev,
      [category]: (prev[category] || []).map(item => item.id === id ? { ...item, [field]: value } : item)
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="flex flex-col items-center gap-4">
          <RefreshCcw className="animate-spin text-indigo-600" size={40} />
          <span className="font-bold text-slate-500">Loading your kingdom...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] flex">
      {/* SIDEBAR NAVIGATION */}
      <div className="w-20 lg:w-64 bg-white border-r border-slate-200 flex flex-col items-center lg:items-start py-8 px-4 lg:px-6 sticky top-0 h-screen shrink-0">
        <div className="flex items-center gap-3 mb-12 px-2">
          <div className="w-10 h-10 premium-gradient rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
            <TrendingUp size={24} />
          </div>
          <span className="text-xl font-bold tracking-tight hidden lg:block">Ledger 3.0</span>
        </div>

        <nav className="space-y-2 w-full">
          <NavItem icon={<PieChart size={20} />} label="Asset Vault" active={activeTab === 'assets'} onClick={() => setActiveTab('assets')} />
          <NavItem icon={<CreditCard size={20} />} label="Liabilities" active={activeTab === 'liabilities'} onClick={() => setActiveTab('liabilities')} />
          <NavItem icon={<Target size={20} />} label="Goal Planner" active={activeTab === 'goals'} onClick={() => setActiveTab('goals')} />
          <NavItem icon={<Info size={20} />} label="Financial Summary" active={activeTab === 'summary'} onClick={() => setActiveTab('summary')} />
        </nav>

        <div className="mt-auto w-full pt-8 border-t border-slate-100 hidden lg:block">
           <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-2xl border border-slate-100">
             <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold">
               {name[0]}
             </div>
             <div>
               <div className="text-sm font-bold truncate">{name}</div>
               <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{age} Years Old</div>
             </div>
           </div>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 p-4 lg:p-12 max-w-7xl mx-auto w-full">
        {/* TOP STATUS BAR */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-slate-900 font-display">
              Good Evening, <span className="text-indigo-600">{name}</span>
            </h1>
            <p className="text-slate-500 font-medium leading-relaxed max-w-md">Let's audit your financial kingdom and track your journey to wealth.</p>
          </div>
          
          <div className="flex gap-4">
             <div className="glass-card px-6 py-4 rounded-3xl min-w-[200px] border-indigo-100">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Current Net Worth</div>
                <div className="text-3xl font-black text-slate-900 tracking-tight">
                  <span className="text-base font-bold mr-1 text-slate-400">₹</span>
                  {netWorth.toLocaleString('en-IN')}
                </div>
             </div>
             <div className="glass-card px-6 py-4 rounded-3xl min-w-[200px] border-emerald-100 bg-emerald-50/20">
                <div className="text-[10px] font-bold text-emerald-600/70 uppercase tracking-widest mb-1">vs. Expected</div>
                <div className={`text-2xl font-black tracking-tight ${netWorth >= expectedNW ? 'text-emerald-600' : 'text-amber-500'}`}>
                  {((netWorth / expectedNW) * 100).toFixed(0)}%
                </div>
             </div>
          </div>
        </header>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* LEFT/CENTER: DYNAMIC INPUTS */}
          <div className="lg:col-span-2 space-y-8">
            <AnimatePresence mode="wait">
              {activeTab === 'assets' && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-6">
                  <SectionTitle title="Asset Vault" subtitle="Entry for everything you own" icon={<Landmark className="text-indigo-600" size={24} />} />
                  
                  <AssetGroup 
                    title="Bank Accounts" 
                    icon={<Landmark size={18} />} 
                    items={assets.banks || []} 
                    onAdd={() => addItem('banks', 'asset')} 
                    onRemove={(id) => removeItem('banks', id, 'asset')}
                    onUpdate={(id, f, v) => updateItem('banks', id, f, v, 'asset')}
                    isBank
                  />
                  <AssetGroup title="Real Estate Information" icon={<Home size={18} />} items={assets.realEstate || []} onAdd={() => addItem('realEstate', 'asset')} onRemove={(id) => removeItem('realEstate', id, 'asset')} onUpdate={(id, f, v) => updateItem('realEstate', id, f, v, 'asset')} />
                  <AssetGroup title="Equity & Mutual Funds" icon={<TrendingUp size={18} />} items={assets.equity || []} onAdd={() => addItem('equity', 'asset')} onRemove={(id) => removeItem('equity', id, 'asset')} onUpdate={(id, f, v) => updateItem('equity', id, f, v, 'asset')} />
                  <AssetGroup title="Foreign Stocks / ETFs" icon={<Plane size={18} />} items={assets.foreignEquity || []} onAdd={() => addItem('foreignEquity', 'asset')} onRemove={(id) => removeItem('foreignEquity', id, 'asset')} onUpdate={(id, f, v) => updateItem('foreignEquity', id, f, v, 'asset')} />
                  <AssetGroup title="EPF / PPF Retirement" icon={<Calculator size={18} />} items={assets.providentFund || []} onAdd={() => addItem('providentFund', 'asset')} onRemove={(id) => removeItem('providentFund', id, 'asset')} onUpdate={(id, f, v) => updateItem('providentFund', id, f, v, 'asset')} />
                  <AssetGroup title="Fixed Deposits" icon={<ShieldCheck size={18} />} items={assets.fixedDeposits || []} onAdd={() => addItem('fixedDeposits', 'asset')} onRemove={(id) => removeItem('fixedDeposits', id, 'asset')} onUpdate={(id, f, v) => updateItem('fixedDeposits', id, f, v, 'asset')} />
                  <AssetGroup title="Bullion (Gold & Silver)" icon={<Gem size={18} />} items={assets.bullion || []} onAdd={() => addItem('bullion', 'asset')} onRemove={(id) => removeItem('bullion', id, 'asset')} onUpdate={(id, f, v) => updateItem('bullion', id, f, v, 'asset')} />
                  <AssetGroup title="Any Other Assets" icon={<MoreHorizontal size={18} />} items={assets.others || []} onAdd={() => addItem('others', 'asset')} onRemove={(id) => removeItem('others', id, 'asset')} onUpdate={(id, f, v) => updateItem('others', id, f, v, 'asset')} />
                </motion.div>
              )}

              {activeTab === 'liabilities' && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-6">
                  <SectionTitle title="Liability Ledger" subtitle="Entry for everything you owe" icon={<CreditCard className="text-rose-500" size={24} />} />
                  
                  <AssetGroup title="Credit Cards" color="rose" icon={<CreditCard size={18} />} items={liabilities.creditCards || []} onAdd={() => addItem('creditCards', 'liab')} onRemove={(id) => removeItem('creditCards', id, 'liab')} onUpdate={(id, f, v) => updateItem('creditCards', id, f, v, 'liab')} />
                  <AssetGroup title="Home Loans" color="rose" icon={<Home size={18} />} items={liabilities.homeLoans || []} onAdd={() => addItem('homeLoans', 'liab')} onRemove={(id) => removeItem('homeLoans', id, 'liab')} onUpdate={(id, f, v) => updateItem('homeLoans', id, f, v, 'liab')} />
                  <AssetGroup title="Vehicle Loans" color="rose" icon={<Car size={18} />} items={liabilities.vehicleLoans || []} onAdd={() => addItem('vehicleLoans', 'liab')} onRemove={(id) => removeItem('vehicleLoans', id, 'liab')} onUpdate={(id, f, v) => updateItem('vehicleLoans', id, f, v, 'liab')} />
                  <AssetGroup title="Personal Loans" color="rose" icon={<User size={18} />} items={liabilities.personalLoans || []} onAdd={() => addItem('personalLoans', 'liab')} onRemove={(id) => removeItem('personalLoans', id, 'liab')} onUpdate={(id, f, v) => updateItem('personalLoans', id, f, v, 'liab')} />
                  <AssetGroup title="Educational Loans" color="rose" icon={<GraduationCap size={18} />} items={liabilities.educationalLoans || []} onAdd={() => addItem('educationalLoans', 'liab')} onRemove={(id) => removeItem('educationalLoans', id, 'liab')} onUpdate={(id, f, v) => updateItem('educationalLoans', id, f, v, 'liab')} />
                </motion.div>
              )}

              {activeTab === 'goals' && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-8">
                  <SectionTitle title="Future Goals" subtitle="Define what wealth means to you" icon={<Target className="text-indigo-600" size={24} />} />
                  
                  <div className="grid md:grid-cols-2 gap-6">
                    {goals.map(goal => {
                      const Icon = GOAL_ICONS[goal.name] || Target;
                      return (
                        <div key={goal.id} className="glass-card p-6 rounded-3xl relative overflow-hidden group">
                          <div className="absolute top-0 right-0 p-8 text-indigo-50/20 pointer-events-none group-hover:scale-110 transition-transform">
                            <Icon size={80} />
                          </div>
                          <div className="flex items-center gap-4 mb-6">
                             <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                               <Icon size={24} />
                             </div>
                             <input 
                              type="text" 
                              value={goal.name} 
                              onChange={(e) => setGoals(goals.map(g => g.id === goal.id ? {...g, name: e.target.value} : g))}
                              className="bg-transparent border-none font-bold text-xl outline-none w-full" 
                             />
                          </div>
                          
                          <div className="space-y-4">
                            <div>
                               <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Target Amount (₹)</label>
                               <input 
                                type="number" 
                                value={goal.target} 
                                onChange={(e) => setGoals(goals.map(g => g.id === goal.id ? {...g, target: parseFloat(e.target.value) || 0} : g))}
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-lg font-bold outline-none focus:border-indigo-500 transition-colors" 
                               />
                            </div>
                            <div className="flex gap-4">
                               <div className="flex-1">
                                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Years away</label>
                                  <input 
                                   type="number" 
                                   value={goal.years} 
                                   onChange={(e) => setGoals(goals.map(g => g.id === goal.id ? {...g, years: parseInt(e.target.value) || 0} : g))}
                                   className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 font-bold outline-none focus:border-indigo-500 transition-colors" 
                                  />
                               </div>
                               <div className="flex-1">
                                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Already Saved</label>
                                  <input 
                                   type="number" 
                                   value={goal.current} 
                                   onChange={(e) => setGoals(goals.map(g => g.id === goal.id ? {...g, current: parseFloat(e.target.value) || 0} : g))}
                                   className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 font-bold outline-none focus:border-indigo-500 transition-colors" 
                                  />
                               </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                    <button 
                      onClick={() => setGoals([...goals, { id: Date.now(), name: 'Custom Goal', target: 1000000, years: 10, current: 0 }])}
                      className="border-2 border-dashed border-slate-200 rounded-3xl p-6 flex flex-col items-center justify-center gap-4 text-slate-400 hover:border-indigo-200 hover:text-indigo-400 hover:bg-indigo-50/20 transition-all"
                    >
                      <Plus size={32} />
                      <span className="font-bold">Add Custom Goal</span>
                    </button>
                  </div>
                </motion.div>
              )}

              {activeTab === 'summary' && (
                <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="space-y-8">
                   <SectionTitle title="Financial Summary" subtitle="Your wealth at a glance" icon={<PieChart className="text-indigo-600" size={24} />} />
                   
                   <div className="grid md:grid-cols-2 gap-8">
                      <div className="glass-card p-8 rounded-3xl space-y-8">
                         <h3 className="text-xl font-bold">Net Worth Distribution</h3>
                         <div className="space-y-4">
                            <StatBar label="Banks" value={Object.values(assets.banks || {}).reduce((s,i)=>s+(parseFloat(i.balance)||0),0)} total={totalAssets} color="bg-indigo-500" />
                            <StatBar label="Real Estate" value={Object.values(assets.realEstate || {}).reduce((s,i)=>s+(parseFloat(i.balance)||0),0)} total={totalAssets} color="bg-emerald-500" />
                            <StatBar label="Equity" value={Object.values(assets.equity || {}).reduce((s,i)=>s+(parseFloat(i.balance)||0),0)} total={totalAssets} color="bg-amber-500" />
                            <StatBar label="Other Assets" value={totalAssets - Object.entries(assets).filter(([k])=>['banks','realEstate','equity'].includes(k)).reduce((s,[,v])=>s+v.reduce((s2,i)=>s2+(parseFloat(i.balance)||0),0),0)} total={totalAssets} color="bg-slate-400" />
                         </div>
                      </div>

                      <div className="glass-card p-8 rounded-3xl space-y-6">
                         <h3 className="text-xl font-bold">Retirement Readiness</h3>
                         <div className="p-6 bg-slate-900 text-white rounded-2xl space-y-1">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Required Corpus at 60</div>
                            <div className="text-3xl font-black">₹{(requiredCorpusAt60 / 10000000).toFixed(2)} Cr</div>
                            <div className="text-xs text-slate-400 mt-2 italic">Considering 6% inflation and 4% withdrawal rate</div>
                         </div>
                         <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                               <span className="text-slate-500 font-medium tracking-tight">Current Progress</span>
                               <span className="font-bold">{((netWorth / requiredCorpusAt60) * 100).toFixed(2)}%</span>
                            </div>
                            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                               <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, (netWorth / requiredCorpusAt60) * 100)}%` }} />
                            </div>
                         </div>
                      </div>
                   </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* RIGHT SIDEBAR: PERSISTENT SETTINGS & STATS */}
          <div className="space-y-8">
            <div className="glass-card p-8 rounded-3xl space-y-8">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <User size={20} className="text-indigo-600" />
                Your Profile
              </h3>
              
              <div className="space-y-6">
                 <div>
                   <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Your Name</label>
                   <input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 font-bold outline-none focus:border-indigo-500 transition-colors" />
                 </div>
                 <div className="flex gap-4">
                   <div className="flex-1">
                     <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Age</label>
                     <input type="number" value={age} onChange={e => setAge(parseInt(e.target.value) || 0)} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 font-bold outline-none focus:border-indigo-500 transition-colors" />
                   </div>
                   <div className="flex-1">
                     <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Retire at</label>
                     <div className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-2 font-bold text-slate-400 cursor-not-allowed">
                        60
                     </div>
                   </div>
                 </div>
                 <div className="grid grid-cols-2 gap-4">
                   <div>
                     <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Monthly Income (₹)</label>
                     <input type="number" value={monthlyIncome} onChange={e => setMonthlyIncome(parseFloat(e.target.value) || 0)} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 font-bold outline-none focus:border-indigo-500 transition-colors" />
                   </div>
                   <div>
                     <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Monthly Cost (₹)</label>
                     <input type="number" value={monthlyExpenses} onChange={e => setMonthlyExpenses(parseFloat(e.target.value) || 0)} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 font-bold outline-none focus:border-indigo-500 transition-colors" />
                   </div>
                 </div>
                 <div className="bg-indigo-50 p-4 rounded-2xl flex justify-between items-center">
                    <span className="text-xs font-bold text-indigo-700 uppercase tracking-wider">Investable Surplus</span>
                    <span className="text-lg font-black text-indigo-700">₹{surplus.toLocaleString('en-IN')}</span>
                 </div>
                 <p className="text-[10px] text-slate-400 mt-1 font-medium italic text-center">Cost adjusted for inflation ({INFLATION_RATE * 100}%): ₹{inflationAdjustedExpenses.toLocaleString('en-IN', { maximumFractionDigits: 0 })} at age 60.</p>
              </div>

              <div className="pt-8 border-t border-slate-100">
                <button 
                  onClick={handleSaveDashboard}
                  disabled={saving}
                  className="btn-premium w-full text-sm disabled:opacity-50"
                >
                   {saving ? <RefreshCcw className="animate-spin" size={18} /> : <Save size={18} />}
                   {saving ? "Saving..." : "Save Snapshot"}
                </button>
              </div>
            </div>

            {/* AGE VS NET WORTH BENCHMARK */}
            <div className="glass-card p-8 rounded-3xl bg-slate-900 text-white border-none space-y-6 overflow-hidden relative">
              <div className="absolute -bottom-8 -right-8 opacity-10">
                 <Landmark size={150} />
              </div>
              <h3 className="text-xl font-bold relative z-10">Age Benchmark</h3>
              <div className="relative z-10">
                 <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Health Metric (Age {age})</div>
                 <div className="text-sm text-slate-400 mb-4">You should aim for <span className="text-white font-bold">₹{expectedNW.toLocaleString('en-IN')}</span></div>
                 
                 <div className="space-y-4">
                    <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                       <span>Gap Analysis</span>
                       <span className={netWorth >= expectedNW ? 'text-emerald-400' : 'text-rose-400'}>
                         {netWorth >= expectedNW ? 'Above' : 'Below'} by ₹{Math.abs(netWorth - expectedNW).toLocaleString('en-IN')}
                       </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                       <div className={`h-full rounded-full transition-all duration-1000 ${netWorth >= expectedNW ? 'bg-emerald-500' : 'bg-rose-500'}`} style={{ width: `${Math.min(100, (netWorth / expectedNW) * 100)}%` }} />
                    </div>
                 </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <AddLedgerItemDialog 
        isOpen={isAddDialogOpen} 
        onClose={() => setIsAddDialogOpen(false)} 
        onAdd={handleDialogAdd} 
        defaultCategory={addDialogCategory}
      />
    </div>
  );
}

// --- REUSABLE COMPONENTS ---

function NavItem({ icon, label, active, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl font-bold transition-all ${active ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100 active:scale-95' : 'text-slate-500 hover:bg-slate-100'}`}
    >
      <span className="shrink-0">{icon}</span>
      <span className="text-sm hidden lg:block tracking-tight font-display">{label}</span>
    </button>
  );
}

function SectionTitle({ title, subtitle, icon }) {
  return (
    <div className="flex items-center gap-5">
      <div className="w-14 h-14 rounded-2xl glass-card flex items-center justify-center shadow-md">
        {icon}
      </div>
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight font-display">{title}</h2>
        <p className="text-slate-500 text-sm font-medium">{subtitle}</p>
      </div>
    </div>
  );
}

function AssetGroup({ title, icon, items, onAdd, onRemove, onUpdate, isBank, color = 'indigo' }) {
  const [isOpen, setIsOpen] = useState(true);
  
  const accentClass = color === 'rose' ? 'text-rose-500' : 'text-indigo-600';
  const bgClass = color === 'rose' ? 'bg-rose-50' : 'bg-indigo-50';
  const focusClass = color === 'rose' ? 'focus-within:border-rose-300' : 'focus-within:border-indigo-300';

  return (
    <div className="animate-in">
       <div className="flex items-center justify-between mb-3 px-2">
          <button onClick={() => setIsOpen(!isOpen)} className="flex items-center gap-2 group">
             <div className="transition-transform duration-300" style={{ transform: isOpen ? 'rotate(0deg)' : 'rotate(-90deg)' }}>
                <ChevronDown size={16} className="text-slate-400" />
             </div>
             <div className={`flex items-center gap-2 font-bold text-xs uppercase tracking-widest transition-colors ${isOpen ? accentClass : 'text-slate-400 group-hover:text-slate-600'}`}>
                {icon}
                {title}
             </div>
          </button>
          <button onClick={onAdd} className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${bgClass} ${accentClass} hover:scale-110 active:scale-90`}>
             <Plus size={16} strokeWidth={3} />
          </button>
       </div>
       
       {isOpen && (
         <div className="space-y-3">
            <AnimatePresence initial={false}>
              {items.map(item => (
                <motion.div 
                  key={item.id}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={`glass-card p-3 rounded-2xl flex items-center gap-4 transition-all ${focusClass}`}
                >
                  <div className="flex-1 flex gap-4">
                    {isBank ? (
                      <div className="flex-1 flex gap-2">
                        <select 
                          value={BANK_OPTIONS.includes(item.name.replace(' Bank', '')) ? item.name.replace(' Bank', '') : 'Other / Custom'} 
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val !== 'Other / Custom') onUpdate(item.id, 'name', val + ' Bank');
                            else onUpdate(item.id, 'name', '');
                          }}
                          className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-2 text-sm font-bold w-1/3 outline-none appearance-none cursor-pointer hover:bg-indigo-50/50 transition-colors"
                        >
                           <option value="" disabled>Select Bank</option>
                           {BANK_OPTIONS.map(b => <option key={b} value={b}>{b === 'Other / Custom' ? b : b + ' Bank'}</option>)}
                        </select>
                        <input 
                          type="text" 
                          placeholder="Or type custom bank name..." 
                          value={item.name} 
                          onChange={(e) => onUpdate(item.id, 'name', e.target.value)}
                          className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-2 text-sm font-bold flex-1 outline-none" 
                        />
                      </div>
                    ) : (
                      <input 
                        type="text" 
                        placeholder="Description..." 
                        value={item.name} 
                        onChange={(e) => onUpdate(item.id, 'name', e.target.value)}
                        className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-2 text-sm font-bold flex-1 outline-none" 
                      />
                    )}
                    <div className="flex items-center bg-white border border-slate-100 rounded-xl px-4 py-2 w-40">
                      <span className="text-slate-300 text-xs font-bold mr-1">₹</span>
                      <input 
                        type="number" 
                        placeholder="0.00" 
                        value={item.balance || ''} 
                        onChange={(e) => onUpdate(item.id, 'balance', e.target.value)}
                        className="bg-transparent w-full text-right font-black text-slate-800 outline-none text-sm" 
                      />
                    </div>
                  </div>
                  <button onClick={() => onRemove(item.id)} className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-all">
                    <Trash2 size={16} />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
            {items.length > 0 && (
              <button 
                onClick={onAdd}
                className={`w-full py-3 border-2 border-dashed border-slate-200 rounded-2xl text-slate-400 text-xs font-bold uppercase tracking-widest hover:border-${color}-200 hover:text-${color}-500 hover:bg-${bgClass.replace('bg-', '')} transition-all flex items-center justify-center gap-2 mt-2`}
              >
                <Plus size={14} strokeWidth={3} />
                Add Another {title.split(' ')[0]}
              </button>
            )}
            {items.length === 0 && (
              <button 
                onClick={onAdd}
                className={`w-full py-8 border-2 border-dashed border-slate-200 rounded-3xl text-slate-400 text-sm font-bold flex flex-col items-center justify-center gap-2 hover:border-${color}-200 hover:text-${color}-500 hover:bg-${bgClass.replace('bg-', '')} transition-all`}
              >
                <Plus size={24} strokeWidth={2} />
                <span>Add {title}</span>
              </button>
            )}
         </div>
       )}
    </div>
  );
}

function StatBar({ label, value, total, color }) {
  const percentage = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="space-y-2">
       <div className="flex justify-between items-end">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{label}</span>
          <span className="text-sm font-black">₹{value.toLocaleString('en-IN')}</span>
       </div>
       <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <motion.div initial={{ width: 0 }} animate={{ width: `${percentage}%` }} transition={{ duration: 1 }} className={`h-full rounded-full ${color}`} />
       </div>
    </div>
  );
}
