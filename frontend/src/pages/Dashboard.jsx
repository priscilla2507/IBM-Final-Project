import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MapPin, AlertTriangle, Shield, Sun, ArrowRight,
  Thermometer, Camera, Map, Wallet, RefreshCw,
} from 'lucide-react'
import { LoadingState, ErrorState } from '../components/States'
import { isDemo } from '../services/api'
import {
  DEMO_DASHBOARD_STATS, DEMO_WEATHER, DEMO_LOCATIONS,
} from '../services/demoService'
import { fetchLocations } from '../services/api'

const RISK_CONFIG = {
  low:       { label: 'Protective Facility', classes: 'bg-green-100 text-green-800 border border-green-200', dot: '#16a34a' },
  moderate:  { label: 'Moderate Risk',       classes: 'bg-amber-100 text-amber-800 border border-amber-200', dot: '#d97706' },
  high:      { label: 'High Heat Risk',      classes: 'bg-orange-100 text-orange-800 border border-orange-200', dot: '#ea580c' },
  very_high: { label: 'Critical Heat Risk',  classes: 'bg-red-100 text-red-800 border border-red-200', dot: '#dc2626' },
}

function RiskPill({ category, score }) {
  const cfg = RISK_CONFIG[category] || RISK_CONFIG.moderate
  const iconCls = { low: '🛡', moderate: '⚠', high: '🔥', very_high: '🔥' }
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${cfg.classes}`}>
      <span>{iconCls[category]}</span>
      {cfg.label}
      {score !== undefined && <span className="font-bold ml-0.5">{score}/100</span>}
    </span>
  )
}

function ShadeBar({ value }) {
  const color = value >= 50 ? '#22c55e' : value >= 25 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-medium text-gray-700 w-8 text-right">{value}%</span>
    </div>
  )
}

function StatCard({ title, value, sub, icon: Icon, iconBg, badge }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{title}</p>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconBg}`}>
          <Icon size={16} />
        </div>
      </div>
      <div className="text-4xl font-black text-gray-900 mb-1">{value}</div>
      <p className="text-xs text-gray-500">{sub}</p>
      {badge && <div className="mt-2">{badge}</div>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [locations, setLocations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [usingFallback, setUsingFallback] = useState(false)

  
  useEffect(() => {
    if (isDemo) {
      setStats(DEMO_DASHBOARD_STATS)
      setLocations(DEMO_LOCATIONS)
    } else {
      // Load the dashboard immediately with available sample data.
      setStats(DEMO_DASHBOARD_STATS)
      setLocations(DEMO_LOCATIONS)
      setUsingFallback(true)
    }

    setLoading(false)
  }, [])


  if (loading) return <LoadingState message="Loading dashboard…" fullPage />
  if (error) return <ErrorState title="Failed to load dashboard" message={error} onRetry={() => window.location.reload()} />

  const dist = stats?.risk_distribution || {}
  const w = DEMO_WEATHER

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page title */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold text-gray-900">Urban Heat Resilience Dashboard</h1>
          {isDemo && (
            <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-1 rounded-full font-semibold flex items-center gap-1">
              ⚡ Demo Mode Active
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500">
          Real-time heat risk intelligence, microclimate conditions, and shade infrastructure monitoring across Hyderabad.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Surveyed Locations"
          value={stats?.total_locations ?? '—'}
          sub="Monitored in Greater Hyderabad"
          icon={MapPin}
          iconBg="bg-blue-50 text-blue-500"
          badge={<span className="text-xs text-gray-400">Active GPS geo-tagged points</span>}
        />
        <StatCard
          title="High / Critical Hotspots"
          value={stats?.high_risk_locations ?? '—'}
          sub={`${stats ? Math.round((stats.high_risk_locations / stats.total_locations) * 100) : 0}% of total`}
          icon={AlertTriangle}
          iconBg="bg-red-50 text-red-500"
          badge={<span className="text-xs text-gray-400">Heat index regularly &gt; 42°C</span>}
        />
        <StatCard
          title="Protective Facilities"
          value={stats?.cooling_facilities ?? '—'}
          sub="Drinking water booths & shaded hubs"
          icon={Shield}
          iconBg="bg-green-50 text-green-500"
          badge={<span className="text-xs text-gray-400">Safe relief access zones</span>}
        />
        <StatCard
          title="Average Shade Coverage"
          value={`${stats?.avg_shade_coverage ?? 31}%`}
          sub="Target threshold is > 50%"
          icon={Sun}
          iconBg="bg-amber-50 text-amber-500"
          badge={<span className="text-xs text-gray-400">Critical deficit in transit hubs</span>}
        />
      </div>

      {/* Weather section */}
      <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-amber-400 text-sm">☀</span>
            <div>
              <span className="text-white font-semibold text-sm">Hyderabad Metropolitan Region</span>
              <span className="text-gray-400 text-xs ml-2">Source: {w.source} • Refreshed: {w.refreshed}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs bg-gray-700 text-gray-300 px-2.5 py-1 rounded-full font-medium">SIMULATED DATA</span>
            <button className="text-gray-400 hover:text-white">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {/* Heat stress advisory */}
        <div className="mx-5 mt-4 mb-3 flex items-center gap-2 px-4 py-2.5 bg-red-900/40 border border-red-700/50 rounded-lg">
          <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />
          <span className="text-xs text-red-200">
            <strong>Heat Stress Advisory:</strong> {w.heat_stress_advisory}
          </span>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 px-5 pb-5">
          {[
            { label: 'AMBIENT TEMP', value: `${w.temperature}°C`, sub: `Feels like ${w.feels_like}°C`, color: 'text-white' },
            { label: 'HEAT INDEX', value: `${w.heat_index}°C`, sub: 'Extreme Caution', color: 'text-orange-400' },
            { label: 'HUMIDITY', value: `${w.humidity}%`, sub: 'RH Relative', color: 'text-blue-400', icon: '💧' },
            { label: 'UV INDEX', value: String(w.uv_index), sub: w.uv_label, color: 'text-amber-400', icon: '☀' },
          ].map((item) => (
            <div key={item.label} className="p-4 border-r border-gray-700 last:border-0">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400 font-semibold tracking-wide">{item.label}</span>
                {item.icon && <span className="text-xs text-gray-500">{item.icon}</span>}
              </div>
              <div className={`text-3xl font-black ${item.color}`}>{item.value}</div>
              <div className="text-xs text-gray-400 mt-0.5">{item.sub}</div>
            </div>
          ))}
        </div>

        <div className="px-5 pb-4 flex items-center gap-4 text-xs text-gray-400 border-t border-gray-700 pt-3">
          <span>💨 Wind: {w.wind_speed} km/h</span>
          <span>🧭 Direction: {w.wind_direction}</span>
          <span className="ml-auto">Target: {w.coordinates}</span>
        </div>
      </div>

      {/* Decision Support + Vulnerability Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-1">Decision Support Actions</h3>
          <p className="text-xs text-gray-500 mb-4">Tools for municipal planners, field teams, and disaster management officers.</p>
          <div className="space-y-2">
            {[
              { label: 'Heat Risk Analysis', sub: 'Field survey & microclimate assessment', icon: Thermometer, path: '/heat-risk', color: 'bg-orange-500' },
              { label: 'Photo Analysis', sub: 'AI shade & canopy computer vision', icon: Camera, path: '/photo-analysis', color: 'bg-blue-500' },
              { label: 'Vulnerability Map', sub: 'Interactive GIS map of Hyderabad', icon: Map, path: '/vulnerability-map', color: 'bg-green-600' },
              { label: 'Budget Optimizer', sub: 'Optimize ₹15k – ₹25k mitigation allocation', icon: Wallet, path: '/budget-optimizer', color: 'bg-purple-600' },
            ].map(({ label, sub, icon: Icon, path, color }) => (
              <button
                key={path}
                onClick={() => navigate(path)}
                className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group text-left"
              >
                <div className={`w-8 h-8 ${color} rounded-lg flex items-center justify-center flex-shrink-0`}>
                  <Icon size={15} className="text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900">{label}</div>
                  <div className="text-xs text-gray-500">{sub}</div>
                </div>
                <ArrowRight size={14} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-400 italic">All algorithms run securely via FastAPI backend models.</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-gray-900">Vulnerability Distribution</h3>
              <p className="text-xs text-gray-500">Proportion of surveyed locations categorized by heat exposure severity index.</p>
            </div>
            <button onClick={() => navigate('/vulnerability-map')} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
              View All on GIS Map <ArrowRight size={12} />
            </button>
          </div>
          <div className="space-y-3">
            {[
              { label: 'Critical Heat Risk', count: dist.very_high || 0, color: '#dc2626', bg: 'bg-red-100' },
              { label: 'High Heat Risk', count: dist.high || 0, color: '#ea580c', bg: 'bg-orange-100' },
              { label: 'Moderate Risk', count: dist.moderate || 0, color: '#d97706', bg: 'bg-amber-100' },
              { label: 'Protective Facility', count: dist.low || 0, color: '#16a34a', bg: 'bg-green-100' },
            ].map((r) => (
              <div key={r.label} className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: r.color }} />
                <span className="text-sm text-gray-700 flex-1">{r.label}</span>
                <div className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${r.bg}`} style={{ color: r.color }}>
                  {r.count} locations
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-400 italic">Priority mitigation focused on Critical &amp; High zones</p>
        </div>
      </div>

      {/* Surveyed Locations table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="font-semibold text-gray-900">Recent Surveyed Locations</h3>
            <p className="text-xs text-gray-500 mt-0.5">Detailed inspection spots across Hyderabad GHMC zones.</p>
          </div>
          <button onClick={() => navigate('/vulnerability-map')} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
            Interactive Map View <ArrowRight size={12} />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Location &amp; Ward</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Coordinates</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Shade Coverage</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Heat Risk Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {locations.map((loc) => (
                <tr key={loc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="font-medium text-gray-900">{loc.name}</div>
                    <div className="text-xs text-gray-500">{loc.ward || loc.area}</div>
                  </td>
                  <td className="px-4 py-3.5 text-xs text-gray-600">{loc.type || loc.area}</td>
                  <td className="px-4 py-3.5 text-xs font-mono text-gray-600">
                    {loc.latitude?.toFixed(4)}°N, {loc.longitude?.toFixed(4)}°E
                  </td>
                  <td className="px-4 py-3.5 w-36">
                    <ShadeBar value={loc.shade_coverage || 0} />
                  </td>
                  <td className="px-4 py-3.5">
                    <RiskPill category={loc.risk_category} score={loc.risk_score} />
                  </td>
                  <td className="px-4 py-3.5">
                    <button
                      onClick={() => navigate('/heat-risk')}
                      className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                    >
                      Inspect <ArrowRight size={11} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
