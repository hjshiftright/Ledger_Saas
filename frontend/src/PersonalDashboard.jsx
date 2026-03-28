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
    <div className="max-w-6xl mx-auto px-6 py-6 space-y-5">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Hey, {profile.name || 'there'} 👋</h1>
          <p className="text-slate-500 text-xs mt-0.5">{profileInfo.emoji} {profileInfo.name}{profile.city ? ` · ${profile.city}` : ''}{profile.age ? ` · ${profile.age} yrs` : ''}</p>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-400">Net Worth</div>
          <div className={`text-2xl font-bold ${netWorth >= 0 ? 'text-indigo-700' : 'text-rose-600'}`}>
            {netWorth >= 0 ? '+' : ''}{formatCurrency(netWorth)}
          </div>
        </div>
      </div>

      {/* Quick Actions - Import Data Prominently */}
      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
            <Upload className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <div className="text-sm font-semibold text-amber-900">Bring in a bank statement</div>
            <div className="text-xs text-amber-700">Drop a PDF or CSV — AI reads, categorises, you approve</div>
          </div>
        </div>
        <button
          onClick={onStartImport}
          className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 transition-colors whitespace-nowrap"
        >
          <FileText className="w-4 h-4" />
          Import
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Assets Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-4 shadow-sm border border-slate-100"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-lg bg-green-100 flex items-center justify-center">
              <Wallet className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <div className="text-xs text-slate-500">Everything you own</div>
              <div className="text-xl font-bold text-green-700">{formatCurrency(totalAssets)}</div>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <ArrowUpRight className="w-3 h-3" />
            <span>cash, investments, property &amp; more</span>
          </div>
        </motion.div>

        {/* Liabilities Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-4 shadow-sm border border-slate-100"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-lg bg-red-100 flex items-center justify-center">
              <CreditCard className="w-4 h-4 text-red-600" />
            </div>
            <div>
              <div className="text-xs text-slate-500">What you owe</div>
              <div className="text-xl font-bold text-red-700">{formatCurrency(totalLiabilities)}</div>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <ArrowDownRight className="w-3 h-3" />
            <span>loans, credit cards &amp; borrowed money</span>
          </div>
        </motion.div>

        {/* Monthly Savings Needed Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-4 shadow-sm border border-slate-100"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-100 flex items-center justify-center">
              <PiggyBank className="w-4 h-4 text-indigo-600" />
            </div>
            <div>
              <div className="text-xs text-slate-500">Set aside each month</div>
              <div className="text-xl font-bold text-indigo-700">{formatCurrency(totalMonthlySavings)}</div>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Target className="w-3 h-3" />
            <span>to reach every goal you've set on time</span>
          </div>
        </motion.div>
      </div>

      {/* Financial Goals */}
      {goals.length > 0 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-700 flex items-center gap-1.5">🎯 Things you're working towards</h2>
              <p className="text-slate-400 text-xs mt-0.5">Monthly SIP to stay on track</p>
            </div>
            {goals.length > 3 && (
              <button
                onClick={() => setShowAllGoals(!showAllGoals)}
                className="text-sm text-indigo-600 hover:text-indigo-800 font-medium whitespace-nowrap"
              >
                {showAllGoals ? 'Show fewer' : `See all ${goals.length}`}
              </button>
            )}
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(showAllGoals ? goals : goals.slice(0, 3)).map((goal, index) => {
              const info = GOAL_TYPE_INFO[goal.goal_type] || GOAL_TYPE_INFO.OTHERS;
              const pct = Math.min(100, Math.round(goal.progress_pct || 0));
              return (
                <motion.div
                  key={goal.id || index}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className={`${info.bgColor} rounded-xl p-4 border border-slate-100 shadow-sm`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{info.emoji}</span>
                    <div>
                      <div className="font-semibold text-slate-900">{goal.name}</div>
                      <div className="text-xs text-slate-500">{goal.yearsAway} yr{goal.yearsAway !== 1 ? 's' : ''} away</div>
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                      <span>{formatCurrency(goal.currentAmount || 0)} saved</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="w-full bg-white/60 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${info.color.replace('text-','bg-')}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                  <div className="flex justify-between items-end">
                    <div>
                      <div className="text-[10px] text-slate-500">Monthly SIP needed</div>
                      <div className={`text-base font-bold ${info.color}`}>
                        {formatCurrency(goal.monthlySavingNeeded || 0)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-slate-500">Target</div>
                      <div className="text-xs font-semibold text-slate-600">
                        {formatCurrency(goal.requiredCorpus || 0)}
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {goals.length > 0 && (
            <div className="mt-6 pt-4 border-t border-slate-100 flex justify-between items-center">
              <span className="text-slate-500 text-sm">Across all goals, put away at least</span>
              <span className="text-2xl font-bold text-indigo-700">{formatCurrency(totalMonthlySavings)}<span className="text-sm font-medium text-slate-400">/mo</span></span>
            </div>
          )}
        </div>
      )}

      {/* Money Lent — Interest Forecast */}
      {(() => {
        const lentItems = (dbData?.assets?.moneyLent || []).filter(l => l.balance > 0 && l.interest_rate > 0);
        if (!lentItems.length) return null;
        const today = new Date();
        const totalAnnualInterest = lentItems.reduce((s, l) => s + l.balance * (l.interest_rate / 100), 0);
        return (
          <div className="bg-white rounded-xl p-5 border border-slate-100 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 mb-3">🤝 Money Lent — Interest Forecast</h2>
            <div className="space-y-3">
              {lentItems.map((l, i) => {
                const lentDate = l.lent_date ? new Date(l.lent_date) : null;
                const daysElapsed = lentDate ? Math.max(0, Math.floor((today - lentDate) / 86400000)) : null;
                const accruedInterest = lentDate ? parseFloat(((l.balance * (l.interest_rate / 100) * daysElapsed) / 365).toFixed(2)) : null;
                const monthlyInterest = parseFloat((l.balance * (l.interest_rate / 100) / 12).toFixed(2));
                const annualInterest = parseFloat((l.balance * (l.interest_rate / 100)).toFixed(2));
                return (
                  <div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-800">{l.name}</span>
                      <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{l.interest_rate}% p.a.</span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      <div>
                        <p className="text-slate-500">Principal</p>
                        <p className="font-semibold text-slate-700">{formatCurrency(l.balance)}</p>
                      </div>
                      {daysElapsed !== null && (
                        <div>
                          <p className="text-slate-500">Accrued ({daysElapsed}d)</p>
                          <p className="font-semibold text-emerald-700">{formatCurrency(accruedInterest)}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-slate-500">Monthly interest</p>
                        <p className="font-semibold text-emerald-700">{formatCurrency(monthlyInterest)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Annual interest</p>
                        <p className="font-semibold text-emerald-700">{formatCurrency(annualInterest)}</p>
                      </div>
                    </div>
                    {l.lent_date && (
                      <p className="text-xs text-slate-400 mt-1.5">Lent on {new Date(l.lent_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between items-center">
              <span className="text-xs text-slate-500">Total projected annual interest</span>
              <span className="text-base font-bold text-emerald-700">{formatCurrency(totalAnnualInterest)}</span>
            </div>
          </div>
        );
      })()}

      {/* Next Steps */}
      <div className="bg-white rounded-xl p-5 border border-slate-100 shadow-sm">
        <h2 className="text-sm font-bold text-slate-700 mb-3">🗺️ Your path forward</h2>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="flex items-start gap-2.5 p-3 bg-amber-50 rounded-lg border border-amber-100">
            <div className="w-6 h-6 rounded-full bg-amber-200 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-amber-700 font-bold text-xs">1</span>
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-700">Bring in a statement</div>
              <div className="text-xs text-slate-500">Drop a PDF or CSV — we sort them automatically</div>
              <button onClick={() => onNavigate?.('import')} className="mt-1.5 text-xs text-amber-600 hover:text-amber-800 font-medium flex items-center gap-0.5">
                Start importing <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="flex items-start gap-2.5 p-3 bg-indigo-50 rounded-lg border border-indigo-100">
            <div className="w-6 h-6 rounded-full bg-indigo-200 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-indigo-600 font-bold text-sm">2</span>
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-700">Let AI do the heavy lifting</div>
              <div className="text-xs text-slate-500">Categorises each row — you approve before anything is saved</div>
              <button onClick={() => onNavigate?.('import')} className="mt-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-0.5">
                Categorise &amp; approve <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>
          
          <div className="flex items-start gap-2.5 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
            <div className="w-6 h-6 rounded-full bg-emerald-200 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-emerald-700 font-bold text-xs">3</span>
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-700">Tell it what you can spend</div>
              <div className="text-xs text-slate-500">Monthly limits per category — Ledger flags when you're close</div>
              <button onClick={() => onNavigate?.('budgets')} className="mt-1.5 text-xs text-emerald-600 hover:text-emerald-800 font-medium flex items-center gap-0.5">
                Set up budgets <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>
          
          <div className="flex items-start gap-2.5 p-3 bg-violet-50 rounded-lg border border-violet-100">
            <div className="w-6 h-6 rounded-full bg-violet-200 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-violet-700 font-bold text-xs">4</span>
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-700">Watch your goals get closer</div>
              <div className="text-xs text-slate-500">Track net worth growth and distance to each goal</div>
              <button onClick={() => onNavigate?.('goals')} className="mt-1.5 text-xs text-violet-600 hover:text-violet-800 font-medium flex items-center gap-0.5">
                Check your goals <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Profile Summary (Collapsible) */}
      <details className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <summary className="px-5 py-3 cursor-pointer hover:bg-slate-50 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-700">👤 Your profile at a glance</h2>
          <ChevronRight className="w-5 h-5 text-slate-400 transform transition-transform details-open:rotate-90" />
        </summary>
        <div className="px-6 pb-6 border-t border-slate-200 pt-4">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-slate-500">Profile Type</div>
              <div className="font-medium text-slate-900">{profileInfo.emoji} {profileInfo.name}</div>
            </div>
            <div>
              <div className="text-slate-500">Location</div>
              <div className="font-medium text-slate-900">📍 {profile.city || 'Not set'}</div>
            </div>
            <div>
              <div className="text-slate-500">Age</div>
              <div className="font-medium text-slate-900">{profile.age || 'Not set'} years</div>
            </div>
            <div>
              <div className="text-slate-500">Income Range</div>
              <div className="font-medium text-slate-900">{profile.incomeRange?.replace(/_/g, ' ') || 'Not set'}</div>
            </div>
            {profile.maritalStatus && (
              <div>
                <div className="text-slate-500">Marital Status</div>
                <div className="font-medium text-slate-900 capitalize">{profile.maritalStatus}</div>
              </div>
            )}
            {profile.childrenCount > 0 && (
              <div>
                <div className="text-slate-500">Children</div>
                <div className="font-medium text-slate-900">{profile.childrenCount}</div>
              </div>
            )}
          </div>
        </div>
      </details>
    </div>
  );
}
