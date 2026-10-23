import React from 'react'

const RISK_CONFIG = {
  low: { label: 'Low Risk', classes: 'bg-green-100 text-green-800 border border-green-200' },
  moderate: { label: 'Moderate Risk', classes: 'bg-amber-100 text-amber-800 border border-amber-200' },
  high: { label: 'High Risk', classes: 'bg-orange-100 text-orange-800 border border-orange-200' },
  very_high: { label: 'Very High Risk', classes: 'bg-red-100 text-red-800 border border-red-200' },
}

export default function RiskBadge({ category, score, size = 'sm' }) {
  const config = RISK_CONFIG[category] || RISK_CONFIG.moderate
  const sizeClass = size === 'lg' ? 'px-3 py-1.5 text-sm font-semibold' : 'px-2 py-0.5 text-xs font-medium'

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full ${sizeClass} ${config.classes}`}>
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{
          backgroundColor: {
            low: '#16a34a',
            moderate: '#d97706',
            high: '#ea580c',
            very_high: '#dc2626',
          }[category] || '#d97706',
        }}
      />
      {config.label}
      {score !== undefined && <span className="opacity-70">({score})</span>}
    </span>
  )
}
