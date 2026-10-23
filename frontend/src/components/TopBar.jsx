import React from 'react'
import { Sun, Wifi, WifiOff } from 'lucide-react'
import { useLocation } from 'react-router-dom'

const BREADCRUMBS = {
  '/': 'Urban Heat Decision Support System',
  '/heat-risk': 'Urban Heat Decision Support System',
  '/photo-analysis': 'Urban Heat Decision Support System',
  '/vulnerability-map': 'Urban Heat Decision Support System',
  '/budget-optimizer': 'Urban Heat Decision Support System',
}

export default function TopBar({ apiOnline = false, weather }) {
  const location = useLocation()
  const breadcrumb = BREADCRUMBS[location.pathname] || 'Urban Heat Decision Support System'

  return (
    <div
      className="flex items-center justify-between px-6 py-2.5 border-b border-gray-200 bg-white z-10 sticky top-0"
      style={{ minHeight: '48px' }}
    >
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold text-gray-900">ChhayaRakshak AI</span>
        <span className="text-gray-400">›</span>
        <span className="text-gray-500">{breadcrumb}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Weather chip */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-xs font-medium text-amber-800">
          <Sun size={13} className="text-amber-500" />
          <span>Hyd: {weather?.temperature ?? '39.4'}°C</span>
          <span className="text-amber-600">(HI: {weather?.feels_like ?? '44.5'}°C)</span>
        </div>

        {/* API status */}
        <div className="flex items-center gap-1.5 text-xs">
          <div className={`w-2 h-2 rounded-full ${apiOnline ? 'bg-green-400' : 'bg-amber-400'}`} />
          <span className="text-gray-500">FastAPI:</span>
          <span className={`font-medium ${apiOnline ? 'text-green-600' : 'text-amber-600'}`}>
  {apiOnline ? 'Connected' : 'Demo Fallback'}
</span>
        </div>
      </div>
    </div>
  )
}
