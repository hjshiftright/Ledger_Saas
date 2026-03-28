import React, { useState, useEffect } from 'react';
import { API } from './api.js';
import { 
  Briefcase, Building2, TrendingUp, Target, GraduationCap, 
  Heart, Plane, Home, Car, Upload, FileText, PlusCircle,
  ChevronRight, Wallet, PiggyBank, CreditCard, AlertCircle,
  CheckCircle2, ArrowUpRight, ArrowDownRight, RefreshCw
} from 'lucide-react';
import { motion
} from 'framer-motion';

const PROFILE_TYPE_INFO = {
  salaried_employee: { name: 'Salaried Employee', icon: Briefcase, emoji: '💼' },
  business_owner: { name: 'Business Owner', icon: Building2, emoji: '🏪' },
  early_investor: { name: 'Early Investor', icon: TrendingUp, emoji: '📈' },
};

const GOAL_INFO = {
  retirement: { name: 'Retirement', icon: Target, emoji: '🏝️', color: 'text-orange-600', bgColor: 'bg-orange-50' },
  child_education: { name: "Children's Education", icon: GraduationCap, emoji: '🎓', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  child_marriage: { name: "Children's Marriage", icon: Heart, emoji: '💍', color: 'text-pink-600', bgColor: 'bg-pink-50' },
  dream_holidays: { name: 'Dream Vacations', icon: Plane, emoji: '🏖️', color: 'text-cyan-600', bgColor: 'bg-cyan-50' },
  home_purchase: { name: 'Dream Home', icon: Home, emoji: '🏠', color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
  dream_car: { name: 'Dream Car', icon: Car, emoji: '🚗', color: 'text-indigo-600', bgColor: 'bg-indigo-50' },
};

const BASE = 'http://127.0.0.1:8000/api/v1';

// Map backend goal_type to display info
const GOAL_TYPE_INFO = {
  RETIREMENT: { emoji: '\uD83C\uDFDD\uFE0F', color: 'text-orange-600', bgColor: 'bg-orange-50' },
  EMERGENCY:  { emoji: '\uD83D\uDEE1\uFE0F', color: 'text-red-600',    bgColor: 'bg-red-50'    },
  HOME:       { emoji: '\uD83C\uDFE0',        color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
  EDUCATION:  { emoji: '\uD83C\uDF93',        color: 'text-blue-600',   bgColor: 'bg-blue-50'   },
  VEHICLE:    { emoji: '\uD83D\uDE97',        color: 'text-indigo-600', bgColor: 'bg-indigo-50' },
  VACATION:   { emoji: '\uD83C\uDFD6\uFE0F', color: 'text-cyan-600',   bgColor: 'bg-cyan-50'   },
  WEDDING:    { emoji: '\uD83D\uDC8D',        color: 'text-pink-600',   bgColor: 'bg-pink-50'   },
  OTHERS:     { emoji: '\uD83C\uDFAF',        color: 'text-slate-600',  bgColor: 'bg-slate-50'  },
};

export default function PersonalDashboard({ onboardingData, onStartImport, onNavigate }) {
  const [showAllGoals, setShowAllGoals] = useState(false);
  const [dbData, setDbData] = useState(null);
  const [dbGoals, setDbGoals] = useState(null); // loaded from /api/v1/goals

  // Load profile/assets/liabilities from dashboard endpoint
  useEffect(() => {
    API.dashboard.load()
      .then(data => setDbData(data))
      .catch(err => console.warn('Dashboard: could not load from backend', err));
  }, []);

  // Load goals directly from the goals endpoint (full data, same as GoalsPage)
  useEffect(() => {
    fetch(`${BASE}/goals`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => setDbGoals(data))
      .catch(err => console.warn('Dashboard: could not load goals', err));
  }, []);

  // Derive display values: prefer DB data, fall back to localStorage
  const localProfile = onboardingData?.profile || {};
  const profile = {
    ...localProfile,
    name: dbData?.name || localProfile.name || '',
    age:  dbData?.age  ?? localProfile.age  ?? '',
  };

  const totalAssets = dbData
    ? Object.values(dbData.assets).flat().reduce((s, a) => s + (a.balance || 0), 0)
    : (onboardingData?.totalAssets || 0);

  const totalLiabilities = dbData
    ? Object.values(dbData.liabilities).flat().reduce((s, l) => s + (l.balance || 0), 0)
    : (onboardingData?.totalLiabilities || 0);

  const netWorth = totalAssets - totalLiabilities;

  // Compute goals display shape from DB goals (GoalOut format)
  const today = new Date();
  const goals = dbGoals?.length
    ? dbGoals.map(g => {
        const targetDate = g.target_date ? new Date(g.target_date) : null;
        const yearsAway = targetDate
          ? Math.max(1, Math.round((targetDate - today) / (365.25 * 24 * 3600 * 1000)))
          : 10;
        const target = parseFloat(g.target_amount) || 0;
        const current = parseFloat(g.current_amount) || 0;
        const gap = Math.max(0, target - current);
        return {
          id:                  String(g.id),
          name:                g.name,
          goal_type:           g.goal_type,
          yearsAway,
          requiredCorpus:      target,
          currentAmount:       current,
          progress_pct:        g.progress_pct,
          monthlySavingNeeded: yearsAway > 0 ? Math.ceil(gap / (yearsAway * 12)) : 0,
        };
      })
    : [];

  const totalMonthlySavings = goals.reduce((s, g) => s + (g.monthlySavingNeeded || 0), 0);

  const profileInfo = PROFILE_TYPE_INFO[profile.profileType] || { name: 'User', emoji: '\uD83D\uDC64', icon: null };
  
  // Format currency
  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    return `₹${amount?.toLocaleString('en-IN') || 0}`;
  };

  return (
    <div className="w-full px-4 md:px-8 py-6 max-w-[1600px] mx-auto space-y-6 lg:space-y-8">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Hey, {profile.name || 'there'} 👋</h1>
          <p className="text-slate-500 text-sm mt-1">{profileInfo.emoji} {profileInfo.name}{profile.city ? ` · ${profile.city}` : ''}{profile.age ? ` · ${profile.age} yrs` : ''}</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-slate-400 font-medium">Net Worth</div>
          <div className={`text-3xl font-bold ${netWorth >= 0 ? 'text-indigo-700' : 'text-rose-600'}`}>
            {netWorth >= 0 ? '+' : ''}{formatCurrency(netWorth)}
          </div>
        </div>
      </div>

      <div className="lg:grid lg:grid-cols-12 lg:gap-8 lg:items-start space-y-6 lg:space-y-0">
        {/* Left Column: Stats & Goals */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">
          {/* Stats Grid */}
          <div className="grid md:grid-cols-3 gap-6">
            {/* Assets Card */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl p-5 shadow-sm border border-slate-100"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
                  <Wallet className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Assets</div>
                  <div className="text-2xl font-bold text-green-700">{formatCurrency(totalAssets)}</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-4 pt-4 border-t border-slate-50">
                <ArrowUpRight className="w-3.5 h-3.5" />
                <span>Everything you own</span>
              </div>
            </motion.div>

            {/* Liabilities Card */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-xl p-5 shadow-sm border border-slate-100"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Liabilities</div>
                  <div className="text-2xl font-bold text-red-700">{formatCurrency(totalLiabilities)}</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-4 pt-4 border-t border-slate-50">
                <ArrowDownRight className="w-3.5 h-3.5" />
                <span>What you owe</span>
              </div>
            </motion.div>

            {/* Monthly Savings Needed Card */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl p-5 shadow-sm border border-slate-100"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
                  <PiggyBank className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Target SIP</div>
                  <div className="text-2xl font-bold text-indigo-700">{formatCurrency(totalMonthlySavings)}</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-4 pt-4 border-t border-slate-50">
                <Target className="w-3.5 h-3.5" />
                <span>To hit all goals on time</span>
              </div>
            </motion.div>
          </div>

          {/* Financial Goals */}
          {goals.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-100">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">🎯 Things you're working towards</h2>
                  <p className="text-slate-500 text-sm mt-1">Monthly SIP needed to stay on track</p>
                </div>
                {goals.length > 4 && (
                  <button
                    onClick={() => setShowAllGoals(!showAllGoals)}
                    className="text-sm border border-indigo-200 bg-indigo-50 px-3 py-1.5 rounded-lg text-indigo-700 hover:bg-indigo-100 font-medium whitespace-nowrap transition-colors"
                  >
                    {showAllGoals ? 'Show fewer' : `See all ${goals.length}`}
                  </button>
                )}
              </div>
              
              <div className="grid md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-5">
                {(showAllGoals ? goals : goals.slice(0, 4)).map((goal, index) => {
                  const info = GOAL_TYPE_INFO[goal.goal_type] || GOAL_TYPE_INFO.OTHERS;
                  const pct = Math.min(100, Math.round(goal.progress_pct || 0));
                  return (
                    <motion.div
                      key={goal.id || index}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.1 }}
                      className={`${info.bgColor} rounded-xl p-5 border border-slate-100 shadow-sm flex flex-col`}
                    >
                      <div className="flex items-start gap-4 mb-4">
                        <span className="text-3xl bg-white w-12 h-12 flex items-center justify-center rounded-xl shadow-sm">{info.emoji}</span>
                        <div className="flex-1">
                          <div className="font-bold text-slate-900 leading-tight">{goal.name}</div>
                          <div className="text-xs font-medium text-slate-500 mt-1">{goal.yearsAway} yr{goal.yearsAway !== 1 ? 's' : ''} away</div>
                        </div>
                      </div>
                      {/* Progress bar */}
                      <div className="mb-4 flex-1">
                        <div className="flex justify-between text-xs font-medium text-slate-500 mb-1.5">
                          <span>{formatCurrency(goal.currentAmount || 0)} saved</span>
                          <span>{pct}%</span>
                        </div>
                        <div className="w-full bg-slate-200/60 rounded-full h-2">
                          <div className={`h-2 rounded-full transition-all duration-500 ${info.color.replace('text-','bg-')}`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                      <div className="flex justify-between items-end pt-3 border-t border-slate-200/50">
                        <div>
                          <div className="text-xs font-medium text-slate-500">Monthly SIP</div>
                          <div className={`text-lg font-bold ${info.color}`}>
                            {formatCurrency(goal.monthlySavingNeeded || 0)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs font-medium text-slate-500">Target</div>
                          <div className="text-sm font-bold text-slate-700">
                            {formatCurrency(goal.requiredCorpus || 0)}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>

              {goals.length > 0 && (
                <div className="mt-6 pt-5 border-t border-slate-100 flex justify-between items-center bg-slate-50 rounded-xl px-5 py-4">
                  <span className="text-slate-600 font-medium">Across all goals, put away at least</span>
                  <span className="text-2xl font-bold text-indigo-700">{formatCurrency(totalMonthlySavings)}<span className="text-sm font-medium text-slate-500">/mo</span></span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Actions, Next Steps, Money Lent, Profile */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-6">
          {/* Quick Actions - Import Data Prominently */}
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center shrink-0 shadow-sm border border-amber-200/50">
                <Upload className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h3 className="text-base font-bold text-amber-900">Import Bank Statement</h3>
                <p className="text-sm text-amber-700/80 mt-1 leading-snug">Drop a PDF or CSV — AI reads, categorises, you approve</p>
              </div>
            </div>
            <button
              onClick={onStartImport}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-amber-600 text-white text-sm font-bold rounded-xl hover:bg-amber-700 transition-colors shadow-sm"
            >
              <FileText className="w-4 h-4" />
              Start New Import
            </button>
          </div>

          {/* Next Steps */}
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">🗺️ Your path forward</h2>
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 hover:bg-indigo-50 transition-colors group">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-indigo-600 font-bold text-xs">1</span>
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-800">Categorise & Approve</div>
                  <div className="text-xs text-slate-500 mt-0.5 leading-snug">AI categorises each row — you approve before saving</div>
                  <button onClick={() => onNavigate?.('import')} className="mt-2 text-xs text-indigo-600 group-hover:text-indigo-800 font-bold flex items-center gap-1">
                    Review drafts <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
              
              <div className="flex items-start gap-3 p-3 bg-emerald-50/50 rounded-xl border border-emerald-100 hover:bg-emerald-50 transition-colors group">
                <div className="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-emerald-700 font-bold text-xs">2</span>
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-800">Set budget limits</div>
                  <div className="text-xs text-slate-500 mt-0.5 leading-snug">Monthly limits per category — Ledger flags when close</div>
                  <button onClick={() => onNavigate?.('budgets')} className="mt-2 text-xs text-emerald-600 group-hover:text-emerald-800 font-bold flex items-center gap-1">
                    Set up budgets <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
              
              <div className="flex items-start gap-3 p-3 bg-violet-50/50 rounded-xl border border-violet-100 hover:bg-violet-50 transition-colors group">
                <div className="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-violet-700 font-bold text-xs">3</span>
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-800">Review Insights</div>
                  <div className="text-xs text-slate-500 mt-0.5 leading-snug">Track net worth growth and deep analytics</div>
                  <button onClick={() => onNavigate?.('wealth')} className="mt-2 text-xs text-violet-600 group-hover:text-violet-800 font-bold flex items-center gap-1">
                    View wealth <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Money Lent — Interest Forecast */}
          {(() => {
            const lentItems = (dbData?.assets?.moneyLent || []).filter(l => l.balance > 0 && l.interest_rate > 0);
            if (!lentItems.length) return null;
            const today = new Date();
            const totalAnnualInterest = lentItems.reduce((s, l) => s + l.balance * (l.interest_rate / 100), 0);
            return (
              <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
                <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">🤝 Interest Forecast</h2>
                <div className="space-y-4">
                  {lentItems.map((l, i) => {
                    const lentDate = l.lent_date ? new Date(l.lent_date) : null;
                    const daysElapsed = lentDate ? Math.max(0, Math.floor((today - lentDate) / 86400000)) : null;
                    const accruedInterest = lentDate ? parseFloat(((l.balance * (l.interest_rate / 100) * daysElapsed) / 365).toFixed(2)) : null;
                    const monthlyInterest = parseFloat((l.balance * (l.interest_rate / 100) / 12).toFixed(2));
                    const annualInterest = parseFloat((l.balance * (l.interest_rate / 100)).toFixed(2));
                    return (
                      <div key={i} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm font-bold text-slate-800">{l.name}</span>
                          <span className="text-xs font-bold text-indigo-600 bg-indigo-100 px-2.5 py-1 rounded-lg border border-indigo-200">{l.interest_rate}% p.a.</span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <p className="text-slate-500 font-medium mb-0.5">Principal</p>
                            <p className="text-sm font-bold text-slate-800">{formatCurrency(l.balance)}</p>
                          </div>
                          {daysElapsed !== null && (
                            <div>
                              <p className="text-slate-500 font-medium mb-0.5">Accrued ({daysElapsed}d)</p>
                              <p className="text-sm font-bold text-emerald-600">{formatCurrency(accruedInterest)}</p>
                            </div>
                          )}
                          <div>
                            <p className="text-slate-500 font-medium mb-0.5">Monthly yield</p>
                            <p className="text-sm font-bold text-emerald-600">{formatCurrency(monthlyInterest)}</p>
                          </div>
                          <div>
                            <p className="text-slate-500 font-medium mb-0.5">Annual yield</p>
                            <p className="text-sm font-bold text-emerald-600">{formatCurrency(annualInterest)}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-600">Total projected annual interest</span>
                  <span className="text-lg font-bold text-emerald-600">{formatCurrency(totalAnnualInterest)}</span>
                </div>
              </div>
            );
          })()}

          {/* Profile Summary (Collapsible) */}
          <details className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden group">
            <summary className="px-5 py-4 cursor-pointer hover:bg-slate-50 flex items-center justify-between outline-none">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">👤 Profile Summary</h2>
              <ChevronRight className="w-5 h-5 text-slate-400 transform transition-transform group-open:rotate-90" />
            </summary>
            <div className="px-5 pb-5 pt-2 border-t border-slate-100">
              <div className="grid grid-cols-2 gap-4 text-sm mt-3">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs font-medium text-slate-500 mb-1">Profile Type</div>
                  <div className="font-bold text-slate-800">{profileInfo.emoji} {profileInfo.name}</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs font-medium text-slate-500 mb-1">Location</div>
                  <div className="font-bold text-slate-800">📍 {profile.city || 'Not set'}</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs font-medium text-slate-500 mb-1">Age</div>
                  <div className="font-bold text-slate-800">{profile.age || 'Not set'} years</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs font-medium text-slate-500 mb-1">Income</div>
                  <div className="font-bold text-slate-800 capitalize">{profile.incomeRange?.replace(/_/g, ' ') || 'Not set'}</div>
                </div>
                {(profile.maritalStatus || profile.childrenCount > 0) && (
                  <div className="col-span-2 bg-slate-50 p-3 rounded-xl border border-slate-100 flex gap-6">
                    {profile.maritalStatus && (
                      <div>
                        <div className="text-xs font-medium text-slate-500 mb-1">Status</div>
                        <div className="font-bold text-slate-800 capitalize">{profile.maritalStatus}</div>
                      </div>
                    )}
                    {profile.childrenCount > 0 && (
                      <div>
                        <div className="text-xs font-medium text-slate-500 mb-1">Children</div>
                        <div className="font-bold text-slate-800">{profile.childrenCount}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
