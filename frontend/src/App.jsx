import React, { useState } from 'react'
import ImportWizard from './ImportWizard'
import OnboardingV2 from './OnboardingV2'
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
    return <OnboardingV2 onComplete={handleOnboardingComplete} />
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top nav */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 flex items-center gap-1 h-14">
          <span className="text-lg font-bold text-indigo-700 mr-6">Ledger</span>
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-semibold transition-colors
                ${tab === id
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-500 hover:text-indigo-600 hover:bg-indigo-50'}`}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
          
          {/* Dev: Reset Onboarding button */}
          <button
            onClick={resetOnboarding}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            title="Reset Onboarding (Dev)"
          >
            <RefreshCw size={12} />
            Reset Onboarding
          </button>

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Sign out"
          >
            <LogOut size={12} />
            Sign Out
          </button>
        </div>
      </header>

      {tab === 'dashboard' && <PersonalDashboard onboardingData={onboardingData} onStartImport={handleStartImport} onNavigate={setTab} />}
      {tab === 'import'    && <ImportWizard onImportComplete={handleImportComplete} onNavigate={setTab} />}
      {tab === 'budgets'   && <BudgetsPage />}
      {tab === 'goals'     && <GoalsPage />}
      {tab === 'wealth'    && <WealthDashboard />}
      {tab === 'reports'   && <ReportsPage />}
      {tab === 'settings'  && <SettingsPage />}

      {/* AI Chat — always visible regardless of active tab */}
      <ChatWidget onNavigate={setTab} />
    </div>
  )
}

export default App

