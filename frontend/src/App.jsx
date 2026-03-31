import React, { useState } from 'react'
import OnboardingV4 from './OnboardingV4'
import LandingPage from './LandingPage'
import './index.css'

function App() {
  // ── Authentication state ──────────────────────────────────────────────────
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const token = sessionStorage.getItem('ledger_auth_token')
    const valid = Boolean(token && token !== 'undefined' && token.split('.').length === 3)
    if (!valid) sessionStorage.removeItem('ledger_auth_token')
    return valid
  })

  const handleAuthenticated = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    sessionStorage.removeItem('ledger_auth_token')
    sessionStorage.removeItem('ledger_user_email')
    sessionStorage.removeItem('ledger_user_id')
    // Clear all onboarding localStorage so the next user starts fresh
    ;['onboarding_v4_sections','onboarding_v4_profile','onboarding_v4_mapping','onboarding_v4_goals',
      'onboarding_v4_complete','onboarding_v2_complete','onboarding_v2_data'].forEach(k => localStorage.removeItem(k))
    setIsAuthenticated(false)
  }

  if (!isAuthenticated) {
    return <LandingPage onAuthenticated={handleAuthenticated} />
  }

  return (
    <OnboardingV4
      userEmail={sessionStorage.getItem('ledger_user_email') || ''}
      onLogout={handleLogout}
    />
  )
}

export default App
