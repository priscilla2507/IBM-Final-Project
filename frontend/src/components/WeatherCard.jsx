import React from 'react'
import { Cloud, Droplets, Wind, Eye, Thermometer, Sun } from 'lucide-react'

export default function WeatherCard({ weather, compact = false }) {
  if (!weather) return null

  const conditionIcon = {
    Sunny: Sun,
    'Partly Cloudy': Cloud,
    Cloudy: Cloud,
    Hazy: Cloud,
  }
  const ConditionIcon = conditionIcon[weather.condition] || Sun

  if (compact) {
    return (
      <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-sky-50 rounded-xl border border-blue-100">
        <ConditionIcon size={28} className="text-amber-500 flex-shrink-0" />
        <div>
          <div className="text-2xl font-bold text-gray-900">{weather.temperature}°C</div>
          <div className="text-sm text-gray-500">{weather.condition} · Feels {weather.feels_like}°C</div>
        </div>
        <div className="ml-auto text-right text-xs text-gray-500">
          <div>{weather.humidity}% humidity</div>
          <div>{weather.wind_speed} km/h wind</div>
        </div>
      </div>
    )
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">{weather.city}, {weather.state}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{weather.condition}</p>
        </div>
        <ConditionIcon size={32} className="text-amber-500" />
      </div>

      <div className="flex items-end gap-3 mb-4">
        <span className="text-5xl font-bold text-gray-900">{weather.temperature}°</span>
        <div className="pb-1 text-sm text-gray-500">
          <div>Feels {weather.feels_like}°C</div>
          <div>UV Index: {weather.uv_index}</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="flex flex-col items-center p-2.5 bg-gray-50 rounded-lg">
          <Droplets size={16} className="text-blue-500 mb-1" />
          <span className="text-sm font-semibold text-gray-800">{weather.humidity}%</span>
          <span className="text-xs text-gray-500">Humidity</span>
        </div>
        <div className="flex flex-col items-center p-2.5 bg-gray-50 rounded-lg">
          <Wind size={16} className="text-slate-500 mb-1" />
          <span className="text-sm font-semibold text-gray-800">{weather.wind_speed}</span>
          <span className="text-xs text-gray-500">km/h</span>
        </div>
        <div className="flex flex-col items-center p-2.5 bg-gray-50 rounded-lg">
          <Eye size={16} className="text-gray-500 mb-1" />
          <span className="text-sm font-semibold text-gray-800">{weather.visibility}</span>
          <span className="text-xs text-gray-500">km vis.</span>
        </div>
      </div>

      {weather.forecast && (
        <div className="border-t border-gray-100 pt-3">
          <div className="grid grid-cols-5 gap-1">
            {weather.forecast.map((f, i) => (
              <div key={i} className="flex flex-col items-center text-center">
                <span className="text-xs text-gray-500">{f.day}</span>
                <span className="text-sm font-semibold text-gray-800 mt-1">{f.high}°</span>
                <span className="text-xs text-gray-400">{f.low}°</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {weather.note && (
        <p className="mt-3 text-xs text-gray-400 italic">{weather.note}</p>
      )}
    </div>
  )
}
