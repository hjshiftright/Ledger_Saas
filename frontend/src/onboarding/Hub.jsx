import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers, PiggyBank, Target, TrendingUp, LayoutDashboard,
  Check, Lock, Edit2, RefreshCw, LogOut, User,
} from 'lucide-react';
import { API } from '../api.js';
import MappingSection from './MappingSection.jsx';
import BudgetsSection from './BudgetsSection.jsx';
import GoalsSection from './GoalsSection.jsx';
import CashFlowSection from './CashFlowSection.jsx';
import DashboardsSection from './DashboardsSection.jsx';
import { saveJson } from './utils.js';
import {
  SK,
  DEFAULT_MAPPING, DEFAULT_BUDGETS, DEFAULT_GOALS, DEFAULT_ANNUAL,
} from './constants.js';
import { DEFAULT_CASHFLOW } from './CashFlowSection.jsx';

const NAV_ICONS = { Layers, PiggyBank, Target, TrendingUp, LayoutDashboard };

const NAV = [
  { id: 'mapping',    label: 'Accounts',   icon: Layers,          desc: 'Assets & liabilities'    },
  { id: 'budgets',    label: 'Budgets',    icon: PiggyBank,       desc: 'Set monthly limits'      },
  { id: 'goals',      label: 'Goals',      icon: Target,          desc: 'Financial milestones'    },
  { id: 'cashflow',   label: 'Cash Flow',  icon: TrendingUp,      desc: 'Income & expenses'       },
  { id: 'dashboards', label: 'Dashboards', icon: LayoutDashboard, desc: 'Your financial overview' },
];

export default function Hub({ sections, setSections, profileData, setProfileData, userEmail, onLogout }) {
  const [mappingData,  setMappingData]  = useState(DEFAULT_MAPPING);
  const [budgetsData,  setBudgetsData]  = useState(DEFAULT_BUDGETS);
  const [goalsData,    setGoalsData]    = useState(DEFAULT_GOALS);
  const [cashflowData, setCashflowData] = useState(DEFAULT_CASHFLOW);
  const [annualData,   setAnnualData]   = useState(DEFAULT_ANNUAL);
  const [dbReady,      setDbReady]      = useState(false);

  useEffect(() => {
    API.dashboard.load()
      .then(dbData => {
        if (!dbData) return;
        const flatAssets = Object.entries(dbData.assets || {}).flatMap(([cat, items]) =>
          items.map(a => ({ id: a.id, name: a.name, value: a.balance, type: cat }))
        );
        const flatLiabilities = Object.entries(dbData.liabilities || {}).flatMap(([cat, items]) =>
          items.map(l => ({ id: l.id, name: l.name, value: l.balance, type: cat }))
        );
        if (flatAssets.length || flatLiabilities.length) {
          setMappingData(d => ({ ...d, assets: flatAssets, liabilities: flatLiabilities }));
        }
        // Note: we do NOT put DB goal objects into goalsData.goals here.
        // GoalsSection treats `goals` as string IDs (e.g. 'emergency'),
        // but DB records use integer primary keys — mixing them incorrectly enables
        // the Continue button without the user actually configuring any goals.
      })
      .catch(() => {})
      .finally(() => setDbReady(true));
  }, []);

  const [active, setActive] = useState(() => {
    if (!sections.mapping)  return 'mapping';
    if (!sections.budgets)  return 'budgets';
    if (!sections.goals)    return 'goals';
    if (!sections.cashflow) return 'cashflow';
    return 'dashboards';
  });

  const canAccess = {
    mapping:    true,
    budgets:    Boolean(sections.mapping),
    goals:      Boolean(sections.budgets),
    cashflow:   Boolean(sections.goals),
    dashboards: true,
  };

  const completeSection = (id) => {
    const updated = { ...sections, [id]: true };
    setSections(updated);
    saveJson(SK.sections, updated);
    if (id === 'mapping')  setActive('budgets');
    if (id === 'budgets')  setActive('goals');
    if (id === 'goals')    setActive('cashflow');
    if (id === 'cashflow') setActive('dashboards');
  };

  const resetAll = () => {
    Object.values(SK).forEach(k => localStorage.removeItem(k));
    localStorage.removeItem('onboarding_v2_complete');
    localStorage.removeItem('onboarding_v2_data');
    window.location.reload();
  };

  const firstName = profileData.legalName?.split(' ')[0] || '';

  if (!dbReady) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F7F8F9]">
        <div className="w-8 h-8 rounded-full border-2 border-[#2C4A70] border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#F7F8F9] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-slate-200 flex flex-col shrink-0">
        {/* Brand */}
        <div className="h-16 flex items-center px-5 border-b border-slate-100">
          <span className="text-base italic font-serif font-bold text-[#2C4A70] leading-tight">The Private Ledger</span>
        </div>

        {/* Profile summary */}
        {firstName && (
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#2C4A70] text-white flex items-center justify-center text-sm font-bold shrink-0">
              {firstName[0].toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-700 truncate">{firstName}</p>
              <button onClick={() => { setSections(s => ({ ...s, profiling: false })); }}
                className="text-xs text-slate-400 hover:text-[#2C4A70] flex items-center gap-1 transition-colors">
                <Edit2 size={10} /> Edit profile
              </button>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {NAV.map(({ id, label, icon: Icon, desc }) => {
            const enabled  = canAccess[id];
            const done     = sections[id];
            const isActive = active === id;
            return (
              <button key={id} onClick={() => enabled && setActive(id)} disabled={!enabled}
                title={!enabled ? 'Complete the previous step first' : desc}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all
                  ${isActive ? 'bg-[#2C4A70] text-white shadow-md shadow-[#2C4A70]/20'
                    : enabled ? 'text-slate-600 hover:text-[#2C4A70] hover:bg-indigo-50'
                    : 'text-slate-300 cursor-not-allowed'}`}>
                <Icon size={17} className="shrink-0" />
                <span className="flex-1 text-left">{label}</span>
                {done && !isActive && <Check size={13} className="text-[#526B5C]" strokeWidth={3} />}
                {!enabled && <Lock size={13} />}
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-slate-100 space-y-0.5">
          {userEmail && <p className="px-4 py-1 text-xs text-slate-400 truncate" title={userEmail}>{userEmail}</p>}
          <button onClick={resetAll} className="w-full flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
            <RefreshCw size={13} /> Reset Setup
          </button>
          {onLogout && (
            <button onClick={onLogout} className="w-full flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors">
              <LogOut size={13} /> Sign Out
            </button>
          )}
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto flex flex-col">
        <AnimatePresence mode="wait">
          {active === 'mapping' && (
            <motion.div key="mapping" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
              <MappingSection data={mappingData} setData={setMappingData} perspective={profileData.perspective} onComplete={() => completeSection('mapping')} />
            </motion.div>
          )}
          {active === 'budgets' && (
            <motion.div key="budgets" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
              <BudgetsSection data={budgetsData} setData={setBudgetsData} onBack={() => setActive('mapping')} onComplete={() => completeSection('budgets')} />
            </motion.div>
          )}
          {active === 'goals' && (
            <motion.div key="goals" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
              <GoalsSection data={goalsData} setData={setGoalsData} perspective={profileData.perspective} assets={mappingData.assets || []} onComplete={() => completeSection('goals')} />
            </motion.div>
          )}
          {active === 'cashflow' && (
            <motion.div key="cashflow" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1 flex flex-col h-full">
              <CashFlowSection
                data={cashflowData}
                setData={setCashflowData}
                annualData={annualData}
                setAnnualData={setAnnualData}
                onBack={() => setActive('goals')}
                onComplete={() => completeSection('cashflow')}
              />
            </motion.div>
          )}
          {active === 'dashboards' && (
            <motion.div key="dashboards" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1 flex flex-col h-full">
              <DashboardsSection
                onboardingData={{ profile: profileData, mapping: mappingData, budgets: budgetsData, goals: goalsData, cashflow: cashflowData, annualExpenses: annualData }}
                completedSections={sections}
                onNavigate={setActive}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
