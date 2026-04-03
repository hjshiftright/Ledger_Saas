import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, Wallet, ShieldCheck, Home, Gem, TrendingUp,
  PieChart, Coins, Calculator, CreditCard, Car, User,
  GraduationCap, Info
} from 'lucide-react';

const ASSET_CATEGORIES = [
  { id: 'banks', label: 'Banks & Cash', type: 'asset', icon: <Wallet size={18}/>, desc: 'Update your liquid holdings for accurate mapping.' },
  { id: 'fixedDeposits', label: 'Fixed Deposits (FD)', type: 'asset', icon: <ShieldCheck size={18}/>, desc: 'Record your fixed term investments.' },
  { id: 'realEstate', label: 'Real Estate', type: 'asset', icon: <Home size={18}/>, desc: 'Add properties, plots, and real estate assets.' },
  { id: 'bullion', label: 'Gold & Jewellery', type: 'asset', icon: <Gem size={18}/>, desc: 'Log your precious metals and jewellery.' },
  { id: 'equity', label: 'Equity Holdings', type: 'asset', icon: <TrendingUp size={18}/>, desc: 'Stocks, shares, and demat accounts.' },
  { id: 'foreignEquity', label: 'Mutual Fund (MF)', type: 'asset', icon: <PieChart size={18}/>, desc: 'Domestic and international mutual funds.' },
  { id: 'others', label: 'Money Lent', type: 'asset', icon: <Coins size={18}/>, desc: 'Money owed to you by others.' },
  { id: 'providentFund', label: 'EPF / PPF / NPS', type: 'asset', icon: <Calculator size={18}/>, desc: 'Retirement and provident fund accounts.' },
];

const LIABILITY_CATEGORIES = [
  { id: 'creditCards', label: 'Credit Cards', type: 'liab', icon: <CreditCard size={18}/>, desc: 'Outstanding credit card balances.' },
  { id: 'homeLoans', label: 'Home Loan', type: 'liab', icon: <Home size={18}/>, desc: 'Mortgages and home loans.' },
  { id: 'vehicleLoans', label: 'Vehicle Loan', type: 'liab', icon: <Car size={18}/>, desc: 'Car and two-wheeler loans.' },
  { id: 'personalLoans', label: 'Personal Loan', type: 'liab', icon: <User size={18}/>, desc: 'Unsecured personal loans.' },
  { id: 'educationalLoans', label: 'Educational Loan', type: 'liab', icon: <GraduationCap size={18}/>, desc: 'Student and education loans.' },
];

// Helper icon mapping for the headers
const AssetIcon = () => (
  <div className="w-5 h-5 rounded flex items-center justify-center bg-[#526B5C] text-white overflow-hidden shrink-0">
    <Wallet size={12} />
  </div>
);

const LiabIcon = () => (
  <div className="w-5 h-5 rounded flex items-center justify-center bg-rose-600 text-white overflow-hidden shrink-0">
    <CreditCard size={12} />
  </div>
);

export default function AddLedgerItemDialog({ isOpen, onClose, onAdd, defaultCategory = null, initialEntry = null }) {
  const [selectedCatId, setSelectedCatId] = useState('banks');
  const [selectedCatType, setSelectedCatType] = useState('asset');

  // Form State
  const [institution, setInstitution] = useState('');
  const [accountType, setAccountType] = useState('Savings Account');
  const [balance, setBalance] = useState('');
  const [owner, setOwner] = useState('Primary / Joint');
  const [description, setDescription] = useState('');

  // Reset form when category changes or modal opens
  useEffect(() => {
    if (initialEntry) {
      setInstitution(initialEntry.name || '');
      setBalance(initialEntry.value || '');
      setDescription(initialEntry.detail || '');
      // map type back to category
      const map = { bank: 'banks', property: 'realEstate', stocks: 'equity', other: 'others', loan: 'homeLoans', credit: 'creditCards', card: 'creditCards' };
      const cat = map[initialEntry.type] || 'banks';
      setSelectedCatId(cat);
      setSelectedCatType(initialEntry._kind === 'liability' ? 'liab' : 'asset');
    } else {
      setInstitution('');
      setAccountType(selectedCatType === 'asset' ? 'Savings Account' : 'Loan');
      setBalance('');
      setOwner('Primary / Joint');
      setDescription('');
    }
  }, [selectedCatId, selectedCatType, isOpen, initialEntry]);

  useEffect(() => {
    if (defaultCategory && isOpen) {
      // Find whether it's an asset or liability and its id
      const isAsset = ASSET_CATEGORIES.some(c => c.id === defaultCategory);
      if (isAsset) {
         setSelectedCatType('asset');
         setSelectedCatId(defaultCategory);
      } else {
         const isLiab = LIABILITY_CATEGORIES.some(c => c.id === defaultCategory);
         if (isLiab) {
            setSelectedCatType('liab');
            setSelectedCatId(defaultCategory);
         }
      }
    }
  }, [defaultCategory, isOpen]);

  if (!isOpen) return null;

  const activeCategory = [...ASSET_CATEGORIES, ...LIABILITY_CATEGORIES].find(c => c.id === selectedCatId);

  const handleCommit = () => {
    // Construct the name based on institution and account type
    let finalName = institution;
    if (accountType && accountType !== 'Select') {
       finalName = institution ? `${institution} - ${accountType}` : accountType;
    }
    
    const entry = {
      name: finalName || 'Unnamed Entry',
      balance: parseFloat(balance) || 0,
      description,
      owner
    };
    onAdd(selectedCatId, selectedCatType, entry);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 backdrop-blur-sm bg-slate-900/30">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl overflow-hidden flex flex-col font-sans"
            style={{ maxHeight: '90vh' }}
          >
            {/* Header */}
            <div className="flex justify-between items-start pt-8 pb-4 px-10 shrink-0">
              <div>
                <h2 className="text-3xl font-black text-[#1E3A5F] font-serif mb-1">Add to Your Ledger</h2>
                <p className="text-slate-500 text-sm">Categorize and record your private financial entries.</p>
              </div>
              <button 
                onClick={onClose}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Main Content Split */}
            <div className="flex flex-col md:flex-row flex-1 overflow-hidden px-8 pb-8 gap-8">
              
              {/* LEFT SIDEBAR (SCROLLABLE) */}
              <div className="w-full md:w-64 shrink-0 overflow-y-auto pr-2 custom-scrollbar space-y-8">
                
                {/* Assets Section */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <AssetIcon />
                    <h3 className="text-xs font-bold uppercase tracking-[1.5px] text-[#1E3A5F]">Things You Own<br/><span className="text-[#526B5C] font-semibold tracking-wider text-[10px]">(ASSETS)</span></h3>
                  </div>
                  <div className="space-y-1">
                    {ASSET_CATEGORIES.map(cat => (
                      <button
                        key={cat.id}
                        onClick={() => { setSelectedCatId(cat.id); setSelectedCatType('asset'); }}
                        className={`w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${selectedCatId === cat.id ? 'bg-slate-100 text-slate-800 font-semibold' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Liabilities Section */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <LiabIcon />
                    <h3 className="text-xs font-bold uppercase tracking-[1.5px] text-[#1E3A5F]">What You Owe<br/><span className="text-rose-600 font-semibold tracking-wider text-[10px]">(LIABILITIES)</span></h3>
                  </div>
                  <div className="space-y-1">
                    {LIABILITY_CATEGORIES.map(cat => (
                      <button
                        key={cat.id}
                        onClick={() => { setSelectedCatId(cat.id); setSelectedCatType('liab'); }}
                        className={`w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${selectedCatId === cat.id ? 'bg-slate-100 text-slate-800 font-semibold' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* RIGHT CONTENT AREA */}
              <div className="flex-1 bg-[#F8F9FA] rounded-xl flex flex-col relative overflow-hidden">
                <div className="flex-1 overflow-y-auto p-8 relative z-10">
                  {/* Category Header */}
                  <div className="flex items-start gap-4 mb-8">
                    <div className="w-12 h-12 rounded-xl bg-[#1E3A5F] flex items-center justify-center text-white shadow-md shrink-0">
                      {activeCategory?.icon}
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-[#1E3A5F] mb-1">{activeCategory?.label} Details</h3>
                      <p className="text-slate-500 text-sm">{activeCategory?.desc}</p>
                    </div>
                  </div>

                  {/* Form Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    {/* Institution */}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Institution</label>
                      <input 
                        type="text" 
                        placeholder="e.g. JPMorgan Chase"
                        value={institution}
                        onChange={(e) => setInstitution(e.target.value)}
                        className="w-full bg-slate-200/50 border border-slate-200 rounded-lg px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]/20 focus:border-[#1E3A5F]/50 transition-all text-sm font-medium"
                      />
                    </div>

                    {/* Account Type */}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Account Type</label>
                      <div className="relative">
                        <select 
                          value={accountType}
                          onChange={(e) => setAccountType(e.target.value)}
                          className="w-full bg-slate-200/50 border border-slate-200 rounded-lg pl-4 pr-10 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]/20 focus:border-[#1E3A5F]/50 transition-all text-sm font-medium appearance-none cursor-pointer"
                        >
                          <option>Select</option>
                          <option>Savings Account</option>
                          <option>Current Account</option>
                          <option>Fixed Deposit</option>
                          <option>Loan Account</option>
                          <option>Credit Card</option>
                          <option>Demat Account</option>
                          <option>Other</option>
                        </select>
                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-400">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                      </div>
                    </div>

                    {/* Approximate Balance */}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Approximate Balance</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                          <span className="text-slate-400 font-medium sm:text-sm">$</span>
                        </div>
                        <input 
                          type="text" 
                          placeholder="0.00"
                          value={balance}
                          onChange={(e) => setBalance(e.target.value)}
                          className="w-full bg-slate-200/50 border border-slate-200 rounded-lg pl-8 pr-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]/20 focus:border-[#1E3A5F]/50 transition-all text-sm font-medium"
                        />
                      </div>
                    </div>

                    {/* Owner */}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Owner</label>
                      <input 
                        type="text" 
                        placeholder="Primary / Joint"
                        value={owner}
                        onChange={(e) => setOwner(e.target.value)}
                        className="w-full bg-slate-200/50 border border-slate-200 rounded-lg px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]/20 focus:border-[#1E3A5F]/50 transition-all text-sm font-medium"
                      />
                    </div>
                  </div>

                  {/* Description */}
                  <div className="mb-8">
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Entry Description (Optional)</label>
                    <textarea 
                      placeholder="Additional context for this entry..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={3}
                      className="w-full bg-slate-200/50 border border-slate-200 rounded-lg px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]/20 focus:border-[#1E3A5F]/50 transition-all text-sm font-medium resize-none"
                    ></textarea>
                  </div>

                  {/* Form Actions */}
                  <div className="flex justify-end gap-4 mt-auto">
                    <button 
                      onClick={onClose}
                      className="px-6 py-3 rounded-lg text-sm font-bold text-[#1E3A5F] hover:bg-slate-200 transition-colors"
                    >
                      Discard
                    </button>
                    <button 
                      onClick={handleCommit}
                      className="px-6 py-3 rounded-lg text-sm font-bold bg-[#1E3A5F] text-white hover:bg-[#1E3A5F]/90 transition-colors shadow-md flex items-center gap-2"
                    >
                      Commit Entry
                    </button>
                  </div>
                </div>

                {/* Bottom decorative/advice area - Absolute positioned if we want it to show below visually, or just in normal flow if we have space. The mockup shows it bleeding out but let's put it as a nice info box in the lower part of the form. */}
                <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-slate-100 to-transparent pointer-events-none opacity-50 z-0"></div>
                
              </div>
            </div>

            {/* Modal Footer - Status Bar */}
            <div className="bg-slate-100/80 px-8 py-3 flex justify-between items-center text-xs font-semibold text-slate-400 shrink-0 border-t border-slate-200/60">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#526B5C] animate-pulse"></div>
                Drafting Private Entry...
              </div>
              <div>Last auto-save: Just now</div>
            </div>

          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
