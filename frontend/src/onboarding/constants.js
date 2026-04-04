// ─── Storage keys ─────────────────────────────────────────────────────────
export const SK = {
  sections:       'onboarding_v4_sections',
  profile:        'onboarding_v4_profile',
  mapping:        'onboarding_v4_mapping',
  goals:          'onboarding_v4_goals',
  cashflow:       'onboarding_v4_cashflow',
  annualexpenses: 'onboarding_v4_annualexpenses',
};

// ─── Profile ───────────────────────────────────────────────────────────────
export const PERSPECTIVES = [
  { id: 'salaried',   title: 'Salaried',   desc: 'Steady monthly paycheck.' },
  { id: 'business',   title: 'Business',   desc: 'Self-employed or business owner.' },
  { id: 'investor',   title: 'Investor',   desc: 'Focus on long term wealth building.' },
  { id: 'homemaker',  title: 'Homemaker',  desc: 'Managing family budgets & accounts.' },
  { id: 'freelancer', title: 'Freelancer', desc: 'Independent professional.' },
  { id: 'student',    title: 'Student',    desc: 'Education & early career.' },
  { id: 'retiree',    title: 'Retiree',    desc: 'Living on pensions & investments.' },
  { id: 'other',      title: 'Other',      desc: 'Clean slate for full customization.' },
];

// ─── Mapping ───────────────────────────────────────────────────────────────
export const DUMMY_DATA = {
  salaried: {
    assets: [
      { id: -1, name: 'HDFC Savings Account',    value: 850000,   type: 'bank',     detail: 'Primary salary account' },
      { id: -2, name: 'EPF / PF Corpus',          value: 450000,   type: 'other',    detail: 'Employer provident fund' },
      { id: -3, name: 'Nifty 50 Index Fund',      value: 320000,   type: 'stocks',   detail: 'SIP — monthly ₹5,000' },
    ],
    liabilities: [
      { id: -4, name: 'Credit Card (HDFC)',        value: 28000,    type: 'credit',   detail: 'Current billing cycle' },
    ],
  },
  business: {
    assets: [
      { id: -1, name: 'Current Account (ICICI)',   value: 1200000,  type: 'bank',     detail: 'Business operating account' },
      { id: -2, name: 'Commercial Property',       value: 8500000,  type: 'property', detail: 'Office / warehouse' },
      { id: -3, name: 'Equity Portfolio',          value: 600000,   type: 'stocks',   detail: 'Personal investments' },
      { id: -4, name: 'Fixed Deposits',            value: 500000,   type: 'bank',     detail: 'Short-term FDs' },
    ],
    liabilities: [
      { id: -5, name: 'Business Loan (SBI)',       value: 2500000,  type: 'loan',     detail: 'Working capital loan, 11%' },
      { id: -6, name: 'Credit Card (Amex)',        value: 75000,    type: 'credit',   detail: 'Business expenses' },
    ],
  },
  homemaker: {
    assets: [
      { id: -1, name: 'Joint Savings (SBI)',       value: 350000,   type: 'bank',     detail: 'Household savings account' },
      { id: -2, name: 'Gold & Jewellery',          value: 800000,   type: 'other',    detail: 'Approx. current market value' },
      { id: -3, name: 'Residential Apartment',     value: 6500000,  type: 'property', detail: 'Self-occupied home' },
      { id: -4, name: 'RD / SIP',                  value: 120000,   type: 'other',    detail: 'Recurring deposit' },
    ],
    liabilities: [
      { id: -5, name: 'Home Loan (LIC Housing)',   value: 3200000,  type: 'loan',     detail: '8.6% fixed, 18 yrs remaining' },
    ],
  },
  investor: {
    assets: [
      { id: -1, name: 'Zerodha Demat Portfolio',  value: 4500000,  type: 'stocks',   detail: 'Equity + ETFs' },
      { id: -2, name: 'Mutual Funds (HDFC)',       value: 2200000,  type: 'stocks',   detail: 'Large-cap & flexi-cap' },
      { id: -3, name: 'Residential Property',     value: 12000000, type: 'property', detail: 'Rental income asset' },
      { id: -4, name: 'Savings Account',          value: 600000,   type: 'bank',     detail: 'HDFC / ICICI liquid funds' },
      { id: -5, name: 'NPS Corpus',               value: 900000,   type: 'other',    detail: 'National Pension Scheme' },
    ],
    liabilities: [
      { id: -6, name: 'Home Loan (Axis)',         value: 5500000,  type: 'loan',     detail: '9.1% floating, 15 yrs remaining' },
      { id: -7, name: 'Margin Loan (Zerodha)',    value: 300000,   type: 'loan',     detail: 'Pledged securities' },
    ],
  },
};

export const SUGGESTED_PROMPTS = [
  "I have a savings account with ₹3L in HDFC",
  "I own a flat worth ₹45L in Bangalore",
  "I have a home loan of ₹28L at SBI",
  "My Zerodha portfolio is around ₹12L",
  "Credit card dues of ₹40K on HDFC",
];

// ─── Goals ─────────────────────────────────────────────────────────────────
export const TIMELINE_OPTS = [
  { label: '6 months',  months: 6   },
  { label: '1 year',    months: 12  },
  { label: '2 years',   months: 24  },
  { label: '3 years',   months: 36  },
  { label: '5 years',   months: 60  },
  { label: '10 years',  months: 120 },
  { label: '15 years',  months: 180 },
  { label: '20+ years', months: 240 },
];

export const DUMMY_GOALS = {
  salaried: [
    { id: 'emergency', targetAmount: 300000,  timelineMonths: 12, note: '3× monthly salary as safety net' },
    { id: 'retire',    targetAmount: 10000000, timelineMonths: 240, note: 'FIRE target at 50' },
    { id: 'home',      targetAmount: 2000000,  timelineMonths: 48, note: 'Down payment for home purchase' },
  ],
  business: [
    { id: 'emergency', targetAmount: 1000000,  timelineMonths: 6,   note: 'Business continuity reserve — 6 months ops cost' },
    { id: 'debt',      targetAmount: 2500000,  timelineMonths: 36,  note: 'Clear working capital loan' },
    { id: 'retire',    targetAmount: 20000000, timelineMonths: 180, note: 'Exit corpus target' },
  ],
  homemaker: [
    { id: 'emergency', targetAmount: 200000,  timelineMonths: 12, note: 'Household emergency buffer' },
    { id: 'education', targetAmount: 1500000, timelineMonths: 96, note: "Children's higher education fund" },
    { id: 'home',      targetAmount: 500000,  timelineMonths: 24, note: 'Home renovation fund' },
  ],
  investor: [
    { id: 'retire',    targetAmount: 50000000, timelineMonths: 120, note: 'FIRE corpus — 25× annual expenses' },
    { id: 'custom',    targetAmount: 5000000,  timelineMonths: 60,  note: 'Passive income portfolio target' },
    { id: 'debt',      targetAmount: 5500000,  timelineMonths: 48,  note: 'Prepay home loan early' },
  ],
};

export const GOALS_AI_PROMPTS = [
  'How much should I save monthly for retirement?',
  'Which goal should I prioritise first?',
  'Am I on track with my emergency fund?',
  'How can I reach my home goal faster?',
];

// ─── Dashboards ────────────────────────────────────────────────────────────
export const DASH_TABS = [
  { id: 'overview',  label: 'Dashboard', icon: 'LayoutDashboard' },
  { id: 'import',    label: 'Import',    icon: 'Upload'          },
  { id: 'budgets',   label: 'Budgets',   icon: 'PiggyBank'       },
  { id: 'goals',     label: 'Goals',     icon: 'Target'          },
  { id: 'wealth',    label: 'Insights',  icon: 'TrendingUp'      },
  { id: 'reports',   label: 'Reports',   icon: 'BarChart2'       },
  { id: 'settings',  label: 'Settings',  icon: 'Settings'        },
];

// ─── Cash Flow ─────────────────────────────────────────────────────────────
export const BUDGET_CATS = [
  { id: 'housing',       label: 'Housing',       pct: 0.30 },
  { id: 'transport',     label: 'Transport',     pct: 0.10 },
  { id: 'healthcare',    label: 'Healthcare',    pct: 0.05 },
  { id: 'savings',       label: 'Savings',       pct: 0.20 },
  { id: 'food',          label: 'Food',          pct: 0.15 },
  { id: 'utilities',     label: 'Utilities',     pct: 0.05 },
  { id: 'entertainment', label: 'Entertainment', pct: 0.05 },
  { id: 'misc',          label: 'Misc',          pct: 0.10 },
];

export const MONTHS_SHORT = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];

// ─── Hub / Navigation ──────────────────────────────────────────────────────
export const NAV = [
  { id: 'mapping',    label: 'Mapping',    icon: 'Layers',          desc: 'Assets & liabilities'    },
  { id: 'budgets',    label: 'Budgets',    icon: 'PiggyBank',       desc: 'Set monthly limits'      },
  { id: 'goals',      label: 'Goals',      icon: 'Target',          desc: 'Financial milestones'    },
  { id: 'cashflow',   label: 'Cash Flow',  icon: 'TrendingUp',      desc: 'Income & expenses'       },
  { id: 'dashboards', label: 'Dashboards', icon: 'LayoutDashboard', desc: 'Your financial overview' },
];

// ─── Default states ────────────────────────────────────────────────────────
export const DEFAULT_PROFILE  = { perspective: '', timeAvailable: '', legalName: '', partnerName: '', householdFor: '', householdType: '', dependents: 0 };
export const DEFAULT_MAPPING  = { rawAssetsMap: '', assets: [], liabilities: [] };
export const DEFAULT_GOALS    = { goals: [], incomeString: '', expenses: { housing: '', transport: '', food: '', utilities: '', other: '' }, completed: false };
export const DEFAULT_BUDGETS  = { income: '', categories: {} };
export const DEFAULT_ANNUAL   = { items: [], completed: false };
