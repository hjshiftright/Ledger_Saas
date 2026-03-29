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
