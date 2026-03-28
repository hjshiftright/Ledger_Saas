import React, { useState } from 'react'
import ImportWizard from './ImportWizard'
import OnboardingV3 from './OnboardingV3'
import PersonalDashboard from './PersonalDashboard'
import SettingsPage from './SettingsPage'
import BudgetsPage from './BudgetsPage'
import GoalsPage from './GoalsPage'
import ReportsPage from './ReportsPage'
import WealthDashboard from './WealthDashboard'
import ChatWidget from './ChatWidget'
import LandingPage from './LandingPage'
import { LayoutDashboard, Upload, RefreshCw, Settings, User, PiggyBank, Target, BarChart2, TrendingUp, LogOut } from 'lucide-react'
import './index.css'

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'import',    label: 'Import',    icon: Upload },
  { id: 'budgets',   label: 'Budgets',   icon: PiggyBank },
  { id: 'goals',     label: 'Goals',     icon: Target },
  { id: 'wealth',    label: 'Insights',   icon: TrendingUp },
  { id: 'reports',   label: 'Reports',   icon: BarChart2 },
  { id: 'settings',  label: 'Settings',  icon: Settings },
]

function App() {
  const [tab, setTab] = useState('dashboard')

  // ── Authentication state ──────────────────────────────────────────────────
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => Boolean(sessionStorage.getItem('ledger_auth_token'))
  )

  // Show onboarding immediately if it hasn't been completed yet
  const [showOnboarding, setShowOnboarding] = useState(
    () => localStorage.getItem('onboarding_v2_complete') !== 'true'
  )
  const [onboardingData, setOnboardingData] = useState(
    () => {
      try { return JSON.parse(localStorage.getItem('onboarding_v2_data') || 'null') } catch { return null }
    }
  )

  // Called by ImportWizard after a successful commit
  const handleImportComplete = () => {
    setTab('dashboard')
  }

  // Called when user finishes the onboarding wizard
  const handleOnboardingComplete = (data) => {
    localStorage.setItem('onboarding_v2_complete', 'true')
    localStorage.setItem('onboarding_v2_data', JSON.stringify(data))
    setOnboardingData(data)
    setShowOnboarding(false)
  }

  // Reset onboarding — clears all saved data and relaunches the wizard
  const resetOnboarding = () => {
    localStorage.removeItem('onboarding_v2_complete')
    localStorage.removeItem('onboarding_v2_data')
    setOnboardingData(null)
    setShowOnboarding(true)
  }

  // ── Auth handlers ─────────────────────────────────────────────────────────
  const handleAuthenticated = () => {
    // Re-sync onboarding state from localStorage after a successful auth
    const isComplete = localStorage.getItem('onboarding_v2_complete') === 'true'
    setShowOnboarding(!isComplete)
    try {
      setOnboardingData(JSON.parse(localStorage.getItem('onboarding_v2_data') || 'null'))
    } catch {
      setOnboardingData(null)
    }
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    sessionStorage.removeItem('ledger_auth_token')
    sessionStorage.removeItem('ledger_user_email')
    sessionStorage.removeItem('ledger_user_id')
    // Note: onboarding state persists in localStorage
    setIsAuthenticated(false)
    setShowOnboarding(true)
    setOnboardingData(null)
  }

  const handleStartImport = () => setTab('import')

  // ── Landing page (not authenticated) ──────────────────────────────────────
  if (!isAuthenticated) {
    return <LandingPage onAuthenticated={handleAuthenticated} />
  }

  // Onboarding overlay — shown after first import commit
  if (showOnboarding) {
    return (
      <OnboardingV3
        onComplete={handleOnboardingComplete}
        userEmail={sessionStorage.getItem('ledger_user_email') || ''}
      />
    )
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden text-slate-900">
      {/* Left Sidebar Nav */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col z-30 flex-shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-slate-100">
          <span className="text-xl font-bold text-indigo-700">Ledger</span>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1.5">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors
                ${tab === id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-500 hover:text-indigo-700 hover:bg-indigo-50'}`}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-100 space-y-2">
          {/* Dev: Reset Onboarding button */}
          <button
            onClick={resetOnboarding}
            className="w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
            title="Reset Onboarding (Dev)"
          >
            <RefreshCw size={16} />
            Reset Onboarding
          </button>

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm font-medium text-slate-500 hover:text-red-700 hover:bg-red-50 transition-colors"
            title="Sign out"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto relative bg-slate-50/50">
        <div className="w-full max-w-[1600px] mx-auto">
          {tab === 'dashboard' && <PersonalDashboard onboardingData={onboardingData} onStartImport={handleStartImport} onNavigate={setTab} />}
          {tab === 'import'    && <ImportWizard onImportComplete={handleImportComplete} onNavigate={setTab} />}
          {tab === 'budgets'   && <BudgetsPage />}
          {tab === 'goals'     && <GoalsPage />}
          {tab === 'wealth'    && <WealthDashboard />}
          {tab === 'reports'   && <ReportsPage />}
          {tab === 'settings'  && <SettingsPage />}
        </div>
      </main>

      {/* AI Chat — always visible regardless of active tab */}
      <ChatWidget onNavigate={setTab} />
    </div>
  )
}

export default App

