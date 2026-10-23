import React from 'react'

const LEGEND_ITEMS = [
  { label: 'Low Risk (0–30)', color: '#22c55e' },
  { label: 'Moderate Risk (31–60)', color: '#f59e0b' },
  { label: 'High Risk (61–75)', color: '#f97316' },
  { label: 'Very High Risk (76–100)', color: '#ef4444' },
]

const FACILITY_ITEMS = [
  { label: 'Shade Shelter', color: '#3b82f6' },
  { label: 'Drinking Water', color: '#06b6d4' },
  { label: 'Tree Canopy', color: '#16a34a' },
]

export default function MapLegend({ showFacilities = false }) {
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">Risk Level</h4>
      <div className="space-y-2 mb-4">
        {LEGEND_ITEMS.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xs text-gray-600">{item.label}</span>
          </div>
        ))}
      </div>

      {showFacilities && (
        <>
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">Facilities</h4>
          <div className="space-y-2">
            {FACILITY_ITEMS.map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs text-gray-600">{item.label}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
