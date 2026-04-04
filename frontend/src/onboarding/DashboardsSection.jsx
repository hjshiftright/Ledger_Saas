import React, { useState } from 'react';
import {
  LayoutDashboard, Upload, PiggyBank, Target, TrendingUp, BarChart2, Settings,
} from 'lucide-react';
import PersonalDashboard from '../PersonalDashboard';
import WealthDashboard from '../WealthDashboard';
import BudgetsPage from '../BudgetsPage';
import GoalsPage from '../GoalsPage';
import ReportsPage from '../ReportsPage';
import ImportWizard from '../ImportWizard';

const ICON_MAP = { LayoutDashboard, Upload, PiggyBank, Target, TrendingUp, BarChart2, Settings };

const DASH_TABS = [
  { id: 'overview',  label: 'Dashboard', icon: LayoutDashboard },
  { id: 'import',    label: 'Import',    icon: Upload          },
  { id: 'budgets',   label: 'Budgets',   icon: PiggyBank       },
  { id: 'goals',     label: 'Goals',     icon: Target          },
  { id: 'wealth',    label: 'Insights',  icon: TrendingUp      },
  { id: 'reports',   label: 'Reports',   icon: BarChart2       },
  { id: 'settings',  label: 'Settings',  icon: Settings        },
];

export default function DashboardsSection({ onboardingData, completedSections = {}, onNavigate }) {
  const [tab, setTab] = useState('overview');

  const missing = [
    !completedSections.mapping  && { id: 'mapping',  label: 'Accounts',  desc: 'your assets & liabilities' },
    !completedSections.goals    && { id: 'goals',     label: 'Goals',     desc: 'your financial goals'      },
    !completedSections.cashflow && { id: 'cashflow',  label: 'Cash Flow', desc: 'your income & expenses'    },
  ].filter(Boolean);

  return (
    <div className="flex flex-col h-full">
      {/* Sample data disclaimer */}
      {missing.length > 0 && (
        <div className="shrink-0 bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-start gap-2.5">
            <span className="text-base shrink-0 mt-0.5">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-amber-800">You're viewing sample data — this is not your real financial picture.</p>
              <p className="text-xs text-amber-700 mt-0.5">
                Complete{' '}
                {missing.map((s, i) => (
                  <span key={s.id}>
                    <button onClick={() => onNavigate(s.id)} className="font-bold underline underline-offset-2 hover:text-amber-900 transition-colors">{s.label}</button>
                    {i < missing.length - 2 ? ', ' : i === missing.length - 2 ? ' and ' : ''}
                  </span>
                ))}
                {' '}to see your actual numbers.
              </p>
            </div>
          </div>
          {missing.length === 1 && (
            <button onClick={() => onNavigate(missing[0].id)}
              className="shrink-0 text-xs font-bold text-amber-800 border border-amber-300 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
              Go to {missing[0].label} →
            </button>
          )}
        </div>
      )}

      {/* Sub-tab bar */}
      <div className="bg-white border-b border-slate-200 px-6 flex items-center gap-0.5 overflow-x-auto shrink-0">
        {DASH_TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-3.5 text-sm font-semibold whitespace-nowrap border-b-2 transition-all
              ${tab === id ? 'border-[#2C4A70] text-[#2C4A70]' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}>
            <Icon size={15} />{label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-[1600px] mx-auto">
          {tab === 'overview'  && <PersonalDashboard onboardingData={onboardingData} onStartImport={() => setTab('import')} onNavigate={setTab} />}
          {tab === 'import'    && <ImportWizard onImportComplete={() => setTab('overview')} onNavigate={setTab} />}
          {tab === 'budgets'   && <BudgetsPage />}
          {tab === 'goals'     && <GoalsPage />}
          {tab === 'wealth'    && <WealthDashboard />}
          {tab === 'reports'   && <ReportsPage />}
        </div>
      </div>
    </div>
  );
}
