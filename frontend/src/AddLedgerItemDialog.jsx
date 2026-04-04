import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Wallet, ShieldCheck, Home, Gem, TrendingUp,
  PieChart, Coins, Calculator, CreditCard, Car, User,
  GraduationCap, ChevronDown,
} from 'lucide-react';

// ── Indian bank / institution lists ──────────────────────────────────────────

const BANK_GROUPS = [
  {
    label: 'Public Sector Banks',
    banks: [
      'State Bank of India (SBI)', 'Punjab National Bank (PNB)', 'Bank of Baroda',
      'Canara Bank', 'Union Bank of India', 'Bank of India', 'Central Bank of India',
      'Indian Bank', 'UCO Bank', 'Bank of Maharashtra', 'Punjab & Sind Bank',
      'Indian Overseas Bank',
    ],
  },
  {
    label: 'Private Sector Banks',
    banks: [
      'HDFC Bank', 'ICICI Bank', 'Axis Bank', 'Kotak Mahindra Bank', 'Yes Bank',
      'IndusInd Bank', 'IDFC First Bank', 'Federal Bank', 'South Indian Bank',
      'Karur Vysya Bank', 'City Union Bank', 'Bandhan Bank', 'DCB Bank', 'RBL Bank',
      'Jammu & Kashmir Bank', 'Karnataka Bank', 'Nainital Bank', 'Saraswat Bank',
      'Tamilnad Mercantile Bank', 'Dhanlaxmi Bank',
    ],
  },
  {
    label: 'Small Finance Banks',
    banks: [
      'AU Small Finance Bank', 'Equitas Small Finance Bank', 'Ujjivan Small Finance Bank',
      'Suryoday Small Finance Bank', 'ESAF Small Finance Bank', 'Jana Small Finance Bank',
      'Capital Small Finance Bank', 'Northeast Small Finance Bank', 'Fincare Small Finance Bank',
      'Unity Small Finance Bank',
    ],
  },
  {
    label: 'Payments Banks',
    banks: [
      'Airtel Payments Bank', 'India Post Payments Bank', 'FINO Payments Bank',
      'Jio Payments Bank',
    ],
  },
];

// FD institutions include banks + NBFCs + post office
const FD_EXTRA_GROUP = {
  label: 'Post Office & NBFCs',
  banks: [
    'India Post (Post Office)', 'LIC Housing Finance', 'Bajaj Finance',
    'Mahindra Finance', 'Shriram Finance', 'Sundaram Finance', 'Tata Capital',
    'Muthoot Finance', 'IIFL Finance', 'Aditya Birla Finance',
  ],
};

const FD_GROUPS = [...BANK_GROUPS, FD_EXTRA_GROUP];

// Lender dropdown for loan / liability categories
const LOAN_LENDER_GROUPS = [
  ...BANK_GROUPS,
  {
    label: 'Housing Finance Companies',
    banks: [
      'HDFC Ltd', 'LIC Housing Finance', 'PNB Housing Finance', 'Indiabulls Housing Finance',
      'Bajaj Housing Finance', 'GIC Housing Finance', 'Can Fin Homes', 'Repco Home Finance',
      'Aavas Financiers', 'Home First Finance',
    ],
  },
  {
    label: 'NBFCs & Other Lenders',
    banks: [
      'Bajaj Finance', 'Mahindra Finance', 'Shriram Finance', 'Tata Capital',
      'IIFL Finance', 'Aditya Birla Finance', 'Muthoot Finance', 'Fullerton India',
      'HDB Financial Services', 'Cholamandalam Finance', 'HDFC Credila', 'Avanse Financial',
    ],
  },
];

// ── Category meta ─────────────────────────────────────────────────────────────

const ASSET_CATEGORIES = [
  { id: 'banks',         label: 'Banks & Cash',    type: 'asset', icon: <Wallet size={18}/>,      desc: 'Savings, current accounts and cash.' },
  { id: 'fixedDeposits', label: 'Fixed Deposits',  type: 'asset', icon: <ShieldCheck size={18}/>, desc: 'FDs, RDs and term deposits.' },
  { id: 'realEstate',    label: 'Real Estate',     type: 'asset', icon: <Home size={18}/>,        desc: 'Properties, plots, and land.' },
  { id: 'bullion',       label: 'Gold & Jewellery',type: 'asset', icon: <Gem size={18}/>,         desc: 'Precious metals and jewellery.' },
  { id: 'equity',        label: 'Equity Holdings', type: 'asset', icon: <TrendingUp size={18}/>,  desc: 'Stocks, shares, and demat accounts.' },
  { id: 'foreignEquity', label: 'Mutual Funds',    type: 'asset', icon: <PieChart size={18}/>,    desc: 'Domestic mutual funds and ELSS.' },
  { id: 'others',        label: 'Money Lent',      type: 'asset', icon: <Coins size={18}/>,       desc: 'Money owed to you by others.' },
  { id: 'providentFund', label: 'EPF / PPF / NPS', type: 'asset', icon: <Calculator size={18}/>,  desc: 'Provident fund and retirement savings.' },
];

const LIABILITY_CATEGORIES = [
  { id: 'creditCards',      label: 'Credit Cards',     type: 'liab', icon: <CreditCard size={18}/>,    desc: 'Outstanding credit card balances.' },
  { id: 'homeLoans',        label: 'Home Loan',        type: 'liab', icon: <Home size={18}/>,          desc: 'Mortgages and home loans.' },
  { id: 'vehicleLoans',     label: 'Vehicle Loan',     type: 'liab', icon: <Car size={18}/>,           desc: 'Car and two-wheeler loans.' },
  { id: 'personalLoans',    label: 'Personal Loan',    type: 'liab', icon: <User size={18}/>,          desc: 'Unsecured personal loans.' },
  { id: 'educationalLoans', label: 'Educational Loan', type: 'liab', icon: <GraduationCap size={18}/>, desc: 'Student and education loans.' },
  { id: 'moneyBorrowed',    label: 'Money Borrowed',   type: 'liab', icon: <Coins size={18}/>,         desc: 'Money you owe to friends or family.' },
];

// ── Per-category form config ──────────────────────────────────────────────────

const CATEGORY_CONFIG = {
  banks: {
    typeLabel: 'Account Type',
    typeOptions: ['Savings Account', 'Current Account', 'Salary Account', 'Recurring Deposit'],
    balanceLabel: 'Current Balance',
    extra: null, showOwner: true, useBankDropdown: true,
  },
  fixedDeposits: {
    typeLabel: 'Deposit Type',
    typeOptions: ['Fixed Deposit (FD)', 'Recurring Deposit (RD)', 'Post Office TD', 'Company FD'],
    balanceLabel: 'Principal Amount',
    extra: { label: 'Interest Rate (%)', placeholder: 'e.g. 7.5' },
    showOwner: false, useBankDropdown: true, fdMode: true,
  },
  realEstate: {
    nameLabel: 'Property / Location', namePlaceholder: 'e.g. 2BHK Flat, Whitefield, Bangalore',
    typeLabel: 'Property Type',
    typeOptions: ['Residential', 'Commercial', 'Land / Plot', 'Under Construction', 'Agricultural'],
    balanceLabel: 'Current Market Value',
    extra: null, showOwner: false,
  },
  bullion: {
    nameLabel: 'Description', namePlaceholder: 'e.g. Gold Jewellery, Gold Coins',
    typeLabel: 'Type',
    typeOptions: ['Gold Jewellery', 'Gold Coins / Bars', 'Silver', 'Platinum', 'Sovereign Gold Bond'],
    balanceLabel: 'Current Market Value',
    extra: { label: 'Weight (grams)', placeholder: 'e.g. 100' }, showOwner: false,
  },
  equity: {
    nameLabel: 'Broker / Platform', namePlaceholder: 'e.g. Zerodha, Groww, ICICI Direct',
    typeLabel: 'Instrument',
    typeOptions: ['Stocks / Shares', 'ETF', 'REITs', 'InvITs', 'Sovereign Gold Bond'],
    balanceLabel: 'Current Market Value',
    extra: null, showOwner: false,
  },
  foreignEquity: {
    nameLabel: 'Fund House / AMC', namePlaceholder: 'e.g. HDFC MF, Axis AMC, Mirae Asset',
    typeLabel: 'Fund Category',
    typeOptions: ['Equity Fund', 'Index Fund', 'ELSS (Tax Saving)', 'Hybrid Fund', 'Debt Fund', 'Liquid Fund'],
    balanceLabel: 'Current Value (NAV × Units)',
    extra: null, showOwner: false,
  },
  others: {
    // Money Lent — uses custom form layout (moneyLentMode)
    nameLabel: 'Borrower Name', namePlaceholder: 'e.g. Ramesh Kumar, Friend, Business Partner',
    typeLabel: 'Relationship',
    typeOptions: ['Family', 'Friend', 'Business Partner', 'Colleague', 'Other'],
    balanceLabel: 'Amount Lent',
    moneyLentMode: true, showOwner: false,
  },
  providentFund: {
    nameLabel: 'Scheme / Account', namePlaceholder: 'e.g. EPF – Employer Name, PPF – SBI',
    typeLabel: 'Scheme Type',
    typeOptions: ['EPF (Employee PF)', 'PPF (Public PF)', 'NPS – Tier I', 'NPS – Tier II', 'GPF', 'VPF'],
    balanceLabel: 'Current Corpus',
    extra: null, showOwner: false,
  },
  creditCards: {
    nameLabel: 'Bank / Issuer', namePlaceholder: 'e.g. HDFC Regalia, SBI SimplyCLICK',
    typeLabel: 'Network',
    typeOptions: ['Visa', 'MasterCard', 'RuPay', 'Amex', 'Diners Club'],
    balanceLabel: 'Outstanding Balance',
    extra: { label: 'Credit Limit (₹)', placeholder: 'e.g. 2,00,000' }, showOwner: false,
    useLoanDropdown: true,
  },
  homeLoans: {
    nameLabel: 'Lender / Bank', namePlaceholder: 'e.g. SBI, HDFC, LIC Housing Finance',
    typeLabel: 'Loan Type',
    typeOptions: ['Home Loan', 'Loan Against Property', 'Top-Up Loan', 'NRI Home Loan'],
    balanceLabel: 'Outstanding Principal',
    extra: { label: 'Interest Rate (%) / Monthly EMI', placeholder: 'e.g. 8.5% / ₹25,000' }, showOwner: false,
    useLoanDropdown: true,
  },
  vehicleLoans: {
    nameLabel: 'Lender / Bank', namePlaceholder: 'e.g. HDFC, Axis, Mahindra Finance',
    typeLabel: 'Vehicle Type',
    typeOptions: ['Car Loan', 'Two-Wheeler Loan', 'Commercial Vehicle Loan'],
    balanceLabel: 'Outstanding Balance',
    extra: { label: 'Monthly EMI (₹)', placeholder: 'e.g. 15,000' }, showOwner: false,
    useLoanDropdown: true,
  },
  personalLoans: {
    nameLabel: 'Lender / Bank', namePlaceholder: 'e.g. ICICI, Bajaj Finance, HDFC',
    typeLabel: 'Purpose',
    typeOptions: ['Personal Use', 'Medical Emergency', 'Home Renovation', 'Travel', 'Other'],
    balanceLabel: 'Outstanding Balance',
    extra: { label: 'Monthly EMI (₹)', placeholder: 'e.g. 8,000' }, showOwner: false,
    useLoanDropdown: true,
  },
  educationalLoans: {
    nameLabel: 'Lender / Bank', namePlaceholder: 'e.g. SBI, HDFC Credila, Union Bank',
    typeLabel: 'Level',
    typeOptions: ['Graduate Studies', 'Post Graduate', 'Vocational / Skill Development', 'School'],
    balanceLabel: 'Outstanding Balance',
    extra: { label: 'Monthly EMI (₹)', placeholder: 'e.g. 5,000' }, showOwner: false,
    useLoanDropdown: true,
  },
  moneyBorrowed: {
    nameLabel: 'Lender Name', namePlaceholder: 'e.g. Suresh Kumar, Uncle, Business Associate',
    typeLabel: 'Relationship',
    typeOptions: ['Family', 'Friend', 'Business Partner', 'Colleague', 'Other'],
    balanceLabel: 'Amount Borrowed',
    moneyBorrowedMode: true, showOwner: false,
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const AssetIcon = () => (
  <div className="w-5 h-5 rounded flex items-center justify-center bg-[#526B5C] text-white shrink-0">
    <Wallet size={12} />
  </div>
);
const LiabIcon = () => (
  <div className="w-5 h-5 rounded flex items-center justify-center bg-rose-600 text-white shrink-0">
    <CreditCard size={12} />
  </div>
);

const inputCls = "w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]/20 focus:border-[#1E3A5F]/50 transition-all text-sm font-medium";
const labelCls = "block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5";

const TYPE_TO_CAT = {
  bank: 'banks', property: 'realEstate', stocks: 'equity',
  other: 'others', loan: 'homeLoans', credit: 'creditCards', card: 'creditCards',
};

function inrFmt(n) {
  if (!n || isNaN(n)) return '—';
  return '₹' + Math.round(n).toLocaleString('en-IN');
}

function formatAmountWithCommas(valStr) {
  if (valStr === undefined || valStr === null) return '';
  const rawValue = String(valStr).replace(/[^0-9.]/g, '');
  if (!rawValue) return '';
  const parts = rawValue.split('.');
  const integerPart = parts[0];
  if (integerPart === '') return '0.' + (parts.slice(1).join('') || '');
  const formattedInteger = Number(integerPart).toLocaleString('en-IN');
  return parts.length > 1 ? `${formattedInteger}.${parts.slice(1).join('')}` : formattedInteger;
}

// Simple interest projection for Money Lent
function computeLentProjection(principal, rateStr, lentDateStr, returnDateStr) {
  const P = parseFloat(String(principal).replace(/[,\s]/g, '')) || 0;
  const r = parseFloat(rateStr) || 0;
  if (!P) return null;

  let months = 12; // default if no dates
  if (lentDateStr && returnDateStr) {
    const start  = new Date(lentDateStr);
    const end    = new Date(returnDateStr);
    if (!isNaN(start) && !isNaN(end) && end > start) {
      months = Math.max(1, Math.round((end - start) / (1000 * 60 * 60 * 24 * 30.44)));
    }
  }

  const years    = months / 12;
  const interest = r > 0 ? P * r * years / 100 : 0;
  const total    = P + interest;
  return { months, interest, total };
}

// Grouped bank dropdown
function BankDropdown({ groups, value, onChange, className }) {
  return (
    <div className="relative">
      <select value={value} onChange={e => onChange(e.target.value)}
        className={`${className} appearance-none pr-9 cursor-pointer`}>
        <option value="">— Select bank —</option>
        {groups.map(g => (
          <optgroup key={g.label} label={g.label}>
            {g.banks.map(b => <option key={b} value={b}>{b}</option>)}
          </optgroup>
        ))}
        <option value="Other">Other (not listed)</option>
      </select>
      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AddLedgerItemDialog({ isOpen, onClose, onAdd, defaultCategory = null, initialEntry = null }) {
  const [selectedCatId,   setSelectedCatId]   = useState('banks');
  const [selectedCatType, setSelectedCatType] = useState('asset');

  // Generic fields
  const [institution,  setInstitution]  = useState('');
  const [accountType,  setAccountType]  = useState('');
  const [balance,      setBalance]      = useState('');
  const [owner,        setOwner]        = useState('Self');
  const [extraValue,   setExtraValue]   = useState('');
  const [description,  setDescription]  = useState('');

  // Bank / FD specific
  const [bankSelected, setBankSelected] = useState(''); // dropdown value

  // Money Lent specific
  const [lentDate,      setLentDate]      = useState('');
  const [interestRate,  setInterestRate]  = useState('');
  const [returnDate,    setReturnDate]    = useState('');

  const config = CATEGORY_CONFIG[selectedCatId] || CATEGORY_CONFIG.realEstate;

  const resetForm = (catId) => {
    const cfg = CATEGORY_CONFIG[catId] || {};
    setInstitution('');
    setAccountType(cfg.typeOptions?.[0] || '');
    setBalance('');
    setOwner('Self');
    setExtraValue('');
    setDescription('');
    setBankSelected('');
    setLentDate('');
    setInterestRate('');
    setReturnDate('');
  };

  useEffect(() => {
    if (!isOpen) return;
    if (initialEntry) {
      const catId = TYPE_TO_CAT[initialEntry.type] || 'banks';
      const cfg   = CATEGORY_CONFIG[catId] || {};
      setSelectedCatId(catId);
      setSelectedCatType(initialEntry._kind === 'liability' ? 'liab' : 'asset');
      setInstitution(initialEntry.name || '');
      setAccountType(cfg.typeOptions?.[0] || '');
      setBalance(initialEntry.value ? formatAmountWithCommas(initialEntry.value) : '');
      setExtraValue('');
      setDescription(initialEntry.detail || '');
      setOwner('Self');
      setBankSelected('');
      setLentDate('');
      setInterestRate('');
      setReturnDate('');
    } else {
      resetForm(selectedCatId);
    }
  }, [isOpen, initialEntry]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!initialEntry) resetForm(selectedCatId);
  }, [selectedCatId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!defaultCategory || !isOpen) return;
    const isAsset = ASSET_CATEGORIES.some(c => c.id === defaultCategory);
    if (isAsset) { setSelectedCatType('asset'); setSelectedCatId(defaultCategory); return; }
    if (LIABILITY_CATEGORIES.some(c => c.id === defaultCategory)) {
      setSelectedCatType('liab'); setSelectedCatId(defaultCategory);
    }
  }, [defaultCategory, isOpen]);

  if (!isOpen) return null;

  const activeCategory = [...ASSET_CATEGORIES, ...LIABILITY_CATEGORIES].find(c => c.id === selectedCatId);
  const isLiab         = selectedCatType === 'liab';
  const isBankCat      = selectedCatId === 'banks' || selectedCatId === 'fixedDeposits';
  const isLoanCat      = config.useLoanDropdown === true;
  const isMoneyLent    = selectedCatId === 'others';
  const isMoneyBorrowed = selectedCatId === 'moneyBorrowed';
  const isMoneyMode    = isMoneyLent || isMoneyBorrowed;

  // Resolve the final institution name
  const resolvedInstitution = (isBankCat || isLoanCat)
    ? (bankSelected && bankSelected !== 'Other' ? bankSelected : institution.trim())
    : institution.trim();

  const canCommit = resolvedInstitution || balance.trim();

  // Money lent projection
  const projection = isMoneyLent
    ? computeLentProjection(balance, interestRate, lentDate, returnDate)
    : null;

  const handleCommit = (keepOpen = false) => {
    const typePart  = accountType ? ` – ${accountType}` : '';
    const finalName = resolvedInstitution
      ? `${resolvedInstitution}${typePart}`
      : accountType || 'Unnamed Entry';

    let descParts = [];
    if (isMoneyLent) {
      if (lentDate)     descParts.push(`Lent on: ${lentDate}`);
      if (interestRate) descParts.push(`Rate: ${interestRate}% p.a.`);
      if (returnDate)   descParts.push(`Return by: ${returnDate}`);
    } else {
      if (config.extra && extraValue.trim()) descParts.push(`${config.extra.label}: ${extraValue.trim()}`);
    }
    if (description.trim()) descParts.push(description.trim());

    const entry = {
      name:        finalName,
      balance:     parseFloat(String(balance).replace(/[,\s]/g, '')) || 0,
      description: descParts.join(' | '),
      owner:       config.showOwner ? owner : '',
    };
    onAdd(selectedCatId, selectedCatType, entry);
    
    if (!keepOpen) {
      onClose();
    } else {
      resetForm(selectedCatId);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 backdrop-blur-sm bg-slate-900/30">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col font-sans"
            style={{ maxHeight: '90vh' }}
          >
            {/* Header */}
            <div className="flex justify-between items-start px-8 pt-6 pb-4 shrink-0 border-b border-slate-100">
              <div>
                <h2 className="text-2xl font-black text-[#1E3A5F] font-serif mb-0.5">
                  {initialEntry ? 'Edit Entry' : 'Add to Your Ledger'}
                </h2>
                <p className="text-slate-400 text-sm">All amounts in Indian Rupees (₹)</p>
              </div>
              <button onClick={onClose}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors mt-1">
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="flex flex-col md:flex-row flex-1 overflow-hidden">

              {/* Sidebar */}
              <div className="w-full md:w-52 shrink-0 border-r border-slate-100 overflow-y-auto py-5 space-y-6">
                <div className="px-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AssetIcon />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-[#1E3A5F]">What I own</span>
                  </div>
                  <div className="space-y-0.5">
                    {ASSET_CATEGORIES.map(cat => (
                      <button key={cat.id}
                        onClick={() => { setSelectedCatId(cat.id); setSelectedCatType('asset'); }}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors
                          ${selectedCatId === cat.id
                            ? 'bg-[#1E3A5F]/8 text-[#1E3A5F] font-semibold'
                            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`}>
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="px-4">
                  <div className="flex items-center gap-2 mb-2">
                    <LiabIcon />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-rose-600">What I owe</span>
                  </div>
                  <div className="space-y-0.5">
                    {LIABILITY_CATEGORIES.map(cat => (
                      <button key={cat.id}
                        onClick={() => { setSelectedCatId(cat.id); setSelectedCatType('liab'); }}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors
                          ${selectedCatId === cat.id
                            ? 'bg-rose-50 text-rose-700 font-semibold'
                            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`}>
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Form */}
              <div className="flex-1 overflow-y-auto p-8">
                {/* Category header */}
                <div className="flex items-center gap-3 mb-6">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-sm shrink-0
                    ${isLiab ? 'bg-rose-500' : 'bg-[#1E3A5F]'}`}>
                    {activeCategory?.icon}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-[#1E3A5F] leading-tight">{activeCategory?.label}</h3>
                    <p className="text-slate-400 text-xs">{activeCategory?.desc}</p>
                  </div>
                </div>

                {/* ── MONEY LENT / MONEY BORROWED form ───────────────── */}
                {isMoneyMode ? (
                  <div className="space-y-5">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      {/* Person name */}
                      <div>
                        <label className={labelCls}>{config.nameLabel}</label>
                        <input type="text" placeholder={config.namePlaceholder} value={institution}
                          onChange={e => setInstitution(e.target.value)} className={inputCls} />
                      </div>
                      {/* Relationship */}
                      <div>
                        <label className={labelCls}>{config.typeLabel}</label>
                        <div className="relative">
                          <select value={accountType} onChange={e => setAccountType(e.target.value)}
                            className={`${inputCls} appearance-none pr-9 cursor-pointer`}>
                            {config.typeOptions.map(o => <option key={o}>{o}</option>)}
                          </select>
                          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        </div>
                      </div>
                      {/* Amount */}
                      <div>
                        <label className={labelCls}>{isMoneyBorrowed ? 'Amount Borrowed (₹)' : 'Amount Lent (₹)'}</label>
                        <div className="relative">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-sm pointer-events-none">₹</span>
                          <input type="text" inputMode="numeric" placeholder="0" value={balance}
                            onChange={e => setBalance(formatAmountWithCommas(e.target.value))} className={`${inputCls} pl-8`} />
                        </div>
                      </div>
                      {/* Date */}
                      <div>
                        <label className={labelCls}>{isMoneyBorrowed ? 'Date Borrowed' : 'Date Lent'}</label>
                        <input type="date" value={lentDate} onChange={e => setLentDate(e.target.value)}
                          className={inputCls} />
                      </div>
                      {/* Interest rate */}
                      <div>
                        <label className={labelCls}>Interest Rate (% per annum) <span className="font-normal normal-case text-slate-300">optional</span></label>
                        <input type="text" inputMode="decimal" placeholder="e.g. 8  (leave blank if interest-free)"
                          value={interestRate} onChange={e => setInterestRate(e.target.value)} className={inputCls} />
                      </div>
                      {/* Settlement date */}
                      <div>
                        <label className={labelCls}>{isMoneyBorrowed ? 'Expected Repayment Date' : 'Expected Return Date'} <span className="font-normal normal-case text-slate-300">optional</span></label>
                        <input type="date" value={returnDate} onChange={e => setReturnDate(e.target.value)}
                          className={inputCls} />
                      </div>
                    </div>

                    {/* Projection panel */}
                    {projection && (
                      isMoneyBorrowed ? (
                        <div className="rounded-xl border border-rose-100 bg-rose-50 p-4">
                          <p className="text-[10px] font-bold text-rose-700 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                            <TrendingUp size={12} /> Total You Will Owe
                          </p>
                          <div className="grid grid-cols-3 gap-3 text-center">
                            <div>
                              <p className="text-[10px] text-slate-400 mb-0.5">Principal</p>
                              <p className="font-bold text-slate-700 text-sm">{inrFmt(parseFloat(String(balance).replace(/[,\s]/g, '')))}</p>
                            </div>
                            <div>
                              <p className="text-[10px] text-slate-400 mb-0.5">
                                Interest accrued{projection.months ? ` (${projection.months}m)` : ''}
                              </p>
                              <p className="font-bold text-rose-600 text-sm">
                                {projection.interest > 0 ? `+ ${inrFmt(projection.interest)}` : 'Interest-free'}
                              </p>
                            </div>
                            <div className="border-l border-rose-200">
                              <p className="text-[10px] text-slate-400 mb-0.5">Total to repay</p>
                              <p className="font-black text-rose-700 text-base">{inrFmt(projection.total)}</p>
                            </div>
                          </div>
                          {!returnDate && (
                            <p className="text-[10px] text-slate-400 mt-2 text-center">Estimated over 12 months — add repayment date for exact projection</p>
                          )}
                        </div>
                      ) : (
                        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
                          <p className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                            <TrendingUp size={12} /> Projected Return
                          </p>
                          <div className="grid grid-cols-3 gap-3 text-center">
                            <div>
                              <p className="text-[10px] text-slate-400 mb-0.5">Principal</p>
                              <p className="font-bold text-slate-700 text-sm">{inrFmt(parseFloat(String(balance).replace(/[,\s]/g, '')))}</p>
                            </div>
                            <div>
                              <p className="text-[10px] text-slate-400 mb-0.5">
                                Interest earned{projection.months ? ` (${projection.months}m)` : ''}
                              </p>
                              <p className="font-bold text-emerald-600 text-sm">
                                {projection.interest > 0 ? `+ ${inrFmt(projection.interest)}` : 'Interest-free'}
                              </p>
                            </div>
                            <div className="border-l border-emerald-200">
                              <p className="text-[10px] text-slate-400 mb-0.5">Total expected</p>
                              <p className="font-black text-emerald-700 text-base">{inrFmt(projection.total)}</p>
                            </div>
                          </div>
                          {!returnDate && (
                            <p className="text-[10px] text-slate-400 mt-2 text-center">Estimated over 12 months — add return date for exact projection</p>
                          )}
                        </div>
                      )
                    )}

                    {/* Notes */}
                    <div>
                      <label className={labelCls}>Notes <span className="font-normal normal-case text-slate-300">(optional)</span></label>
                      <textarea placeholder="Any additional context…" value={description}
                        onChange={e => setDescription(e.target.value)} rows={2}
                        className={`${inputCls} resize-none`} />
                    </div>
                  </div>

                ) : (
                  /* ── ALL OTHER categories ──────────────────────────── */
                  <div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">

                      {/* Bank dropdown (banks / fixedDeposits) OR plain text */}
                      {isBankCat || isLoanCat ? (
                        <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-5">
                          <div>
                            <label className={labelCls}>
                              {selectedCatId === 'fixedDeposits' ? 'Bank / Institution' : (isLoanCat ? 'Lender / Bank' : 'Bank Name')}
                            </label>
                            <BankDropdown
                              groups={selectedCatId === 'fixedDeposits' ? FD_GROUPS : (isLoanCat ? LOAN_LENDER_GROUPS : BANK_GROUPS)}
                              value={bankSelected}
                              onChange={setBankSelected}
                              className={inputCls}
                            />
                          </div>
                          {/* Show free-text input only when "Other" is selected */}
                          {bankSelected === 'Other' && (
                            <div>
                              <label className={labelCls}>Specify Bank / Institution</label>
                              <input type="text" placeholder="Enter name" value={institution}
                                onChange={e => setInstitution(e.target.value)} className={inputCls} />
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <label className={labelCls}>{config.nameLabel}</label>
                          <input type="text" placeholder={config.namePlaceholder} value={institution}
                            onChange={e => setInstitution(e.target.value)} className={inputCls} />
                        </div>
                      )}

                      {/* Type selector */}
                      <div>
                        <label className={labelCls}>{config.typeLabel}</label>
                        <div className="relative">
                          <select value={accountType} onChange={e => setAccountType(e.target.value)}
                            className={`${inputCls} appearance-none pr-9 cursor-pointer`}>
                            {config.typeOptions.map(opt => <option key={opt}>{opt}</option>)}
                          </select>
                          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        </div>
                      </div>

                      {/* Amount */}
                      <div>
                        <label className={labelCls}>{config.balanceLabel} (₹)</label>
                        <div className="relative">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-sm pointer-events-none">₹</span>
                          <input type="text" inputMode="numeric" placeholder="0" value={balance}
                            onChange={e => setBalance(formatAmountWithCommas(e.target.value))} className={`${inputCls} pl-8`} />
                        </div>
                      </div>

                      {/* 4th slot: extra field or Owner */}
                      {config.extra ? (
                        <div>
                          <label className={labelCls}>{config.extra.label}</label>
                          <input type="text" placeholder={config.extra.placeholder} value={extraValue}
                            onChange={e => {
                              if (config.extra.label.includes('(₹)')) {
                                setExtraValue(formatAmountWithCommas(e.target.value));
                              } else {
                                setExtraValue(e.target.value);
                              }
                            }} className={inputCls} />
                        </div>
                      ) : config.showOwner ? (
                        <div>
                          <label className={labelCls}>Account Owner</label>
                          <input type="text" placeholder="e.g. Self, Joint, Spouse" value={owner}
                            onChange={e => setOwner(e.target.value)} className={inputCls} />
                        </div>
                      ) : null}
                    </div>

                    {/* Notes */}
                    <div className="mb-7">
                      <label className={labelCls}>Notes <span className="font-normal normal-case text-slate-300">(optional)</span></label>
                      <textarea placeholder="Any additional context…" value={description}
                        onChange={e => setDescription(e.target.value)} rows={2}
                        className={`${inputCls} resize-none`} />
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-3 mt-6">
                  <button onClick={onClose}
                    className="px-5 py-2.5 rounded-lg text-sm font-semibold text-slate-500 hover:bg-slate-100 transition-colors">
                    Cancel
                  </button>
                  {initialEntry ? (
                    <button onClick={() => handleCommit(false)} disabled={!canCommit}
                      className={`px-6 py-2.5 rounded-lg text-sm font-bold text-white transition-colors shadow-sm
                        disabled:opacity-40 disabled:cursor-not-allowed
                        ${isLiab ? 'bg-rose-500 hover:bg-rose-600' : 'bg-[#1E3A5F] hover:bg-[#1E3A5F]/90'}`}>
                      Save Changes
                    </button>
                  ) : (
                    <>
                      <button onClick={() => handleCommit(true)} disabled={!canCommit}
                        className={`px-6 py-2.5 rounded-lg text-sm font-bold transition-colors shadow-sm
                          disabled:opacity-40 disabled:cursor-not-allowed
                          ${isLiab ? 'bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100' : 'bg-[#1E3A5F]/5 text-[#1E3A5F] border border-[#1E3A5F]/20 hover:bg-[#1E3A5F]/10'}`}>
                        Save & Add Another
                      </button>
                      <button onClick={() => handleCommit(false)} disabled={!canCommit}
                        className={`px-6 py-2.5 rounded-lg text-sm font-bold text-white transition-colors shadow-sm
                          disabled:opacity-40 disabled:cursor-not-allowed
                          ${isLiab ? 'bg-rose-500 hover:bg-rose-600' : 'bg-[#1E3A5F] hover:bg-[#1E3A5F]/90'}`}>
                        Save & Close
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
