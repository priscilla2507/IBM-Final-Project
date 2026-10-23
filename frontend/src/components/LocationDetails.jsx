import React from 'react'
import RiskBadge from './RiskBadge'
import { MapPin, Thermometer, Trees, Building2, Clock } from 'lucide-react'

const FACILITY_LABELS = {
  shade_shelter: 'Shade Shelter',
  drinking_water: 'Drinking Water',
  seating: 'Seating',
  trees: 'Trees',
}

export default function LocationDetails({ location, onClose }) {
  if (!location) return null

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 mr-2">
          <h3 className="font-semibold text-gray-900 text-sm leading-tight">{location.name}</h3>
          <div className="flex items-center gap-1 mt-1">
            <MapPin size={12} className="text-gray-400" />
            <span className="text-xs text-gray-500">{location.area}</span>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        )}
      </div>

      <div className="mb-3">
        <RiskBadge category={location.risk_category} score={location.risk_score} />
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="p-2 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-1 mb-0.5">
            <Thermometer size={12} className="text-orange-500" />
            <span className="text-xs text-gray-500">Surface Temp.</span>
          </div>
          <span className="text-sm font-semibold text-gray-800">
            {location.surface_temp_est ? `~${location.surface_temp_est}°C` : 'N/A'}
          </span>
        </div>
        <div className="p-2 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-1 mb-0.5">
            <Trees size={12} className="text-green-500" />
            <span className="text-xs text-gray-500">Shade Cover</span>
          </div>
          <span className="text-sm font-semibold text-gray-800">
            {location.shade_coverage !== undefined ? `${location.shade_coverage}%` : 'N/A'}
          </span>
        </div>
      </div>

      {location.facilities && location.facilities.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-600 mb-1.5">Available Facilities</p>
          <div className="flex flex-wrap gap-1.5">
            {location.facilities.map((f) => (
              <span key={f} className="text-xs bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 rounded-full">
                {FACILITY_LABELS[f] || f}
              </span>
            ))}
          </div>
        </div>
      )}

      {location.notes && (
        <p className="text-xs text-gray-500 italic leading-relaxed">{location.notes}</p>
      )}

      {location.last_assessed && (
        <div className="flex items-center gap-1 mt-3 pt-3 border-t border-gray-100">
          <Clock size={11} className="text-gray-400" />
          <span className="text-xs text-gray-400">Assessed {location.last_assessed}</span>
        </div>
      )}
    </div>
  )
}
