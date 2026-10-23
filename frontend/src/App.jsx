import React, { Suspense, lazy, useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import DemoBanner from './components/DemoBanner'
import { LoadingState } from './components/States'
import { DEMO_WEATHER } from './services/demoService'
import { isDemo, checkHealth } from './services/api'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const HeatRiskAnalysis = lazy(() => import('./pages/HeatRiskAnalysis'))
const PhotoAnalysis = lazy(() => import('./pages/PhotoAnalysis'))
const VulnerabilityMap = lazy(() => import('./pages/VulnerabilityMap'))
const BudgetOptimizer = lazy(() => import('./pages/BudgetOptimizer'))
const PersonalHeatAssessment = lazy(() => import('./pages/PersonalHeatAssessment'))
const HeatAssistant = lazy(() => import('./pages/HeatAssistant'))
const AreaAnalysis = lazy(() => import('./pages/AreaAnalysis'))

function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center min-h-[60vh]">
      <LoadingState message="Loading…" fullPage />
    </div>
  )
}

export default function App() {
    const [apiOnline, setApiOnline] = useState(false)

  useEffect(() => {
    checkHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false))
  }, [])
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />

        <div className="flex-1 flex flex-col min-w-0">
          {/* Top navigation bar */}
          <TopBar apiOnline={apiOnline} weather={isDemo ? DEMO_WEATHER : null} />

          {/* Demo mode banner */}
          <DemoBanner
            onCheckBackend={() => Promise.resolve()}
            onSwitchLive={() => alert('Set VITE_USE_DEMO_DATA=false in .env.local and restart the dev server to switch to Live API mode.')}
          />

          {/* Mobile spacing */}
          <div className="lg:hidden h-14" />

          {/* Page content */}
          <main className="flex-1 overflow-y-auto">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/heat-risk" element={<HeatRiskAnalysis />} />
                <Route path="/personal-assessment" element={<PersonalHeatAssessment />} />
                <Route path="/heat-assistant" element={<HeatAssistant />} />
                <Route path="/photo-analysis" element={<PhotoAnalysis />} />
                <Route path="/area-analysis" element={<AreaAnalysis />} />
                <Route path="/vulnerability-map" element={<VulnerabilityMap />} />
                <Route path="/budget-optimizer" element={<BudgetOptimizer />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </main>

          {/* Footer */}
          <div className="border-t border-gray-200 py-2 px-6 text-center text-xs text-gray-400 bg-white">
            ChhayaRakshak AI — Hyderabad Urban Heat Vulnerability &amp; Shade Protection Decision Platform
          </div>
        </div>
      </div>
    </BrowserRouter>
  )
}
