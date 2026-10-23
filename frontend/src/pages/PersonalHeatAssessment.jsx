import React, { useState } from 'react'
import {
  User, Thermometer, RefreshCw, AlertTriangle, CheckCircle,
  Info, ChevronRight, Clock, Droplets, ShieldCheck, Heart,
} from 'lucide-react'
import { LoadingState, ErrorState } from '../components/States'
import { personalHeatAssessment } from '../services/api'

const AGE_RANGES = ['Under 5', '5-17', '18-59', '60+']
const ACTIVITY_TYPES = [
  'Construction / Manual Labour',
  'Agriculture / Field Work',
  'Street Vending / Outdoor Market',
  'Traffic / Municipal Worker',
  'Commuter (daily travel)',
  'Student / School Child',
  'Recreational (walking, sports)',
  'Domestic / Home-based',
  'Other',
]

const RISK_CONFIG = {
  low:       { label: 'Low Risk',       bg: 'bg-green-50',  border: 'border-green-300', text: 'text-green-800',  dot: 'bg-green-500', bar: 'bg-green-500' },
  moderate:  { label: 'Moderate Risk',  bg: 'bg-amber-50',  border: 'border-amber-300', text: 'text-amber-800',  dot: 'bg-amber-500', bar: 'bg-amber-500' },
  high:      { label: 'High Risk',      bg: 'bg-orange-50', border: 'border-orange-300',text: 'text-orange-800', dot: 'bg-orange-500',bar: 'bg-orange-500' },
  very_high: { label: 'Very High Risk', bg: 'bg-red-50',    border: 'border-red-300',   text: 'text-red-800',    dot: 'bg-red-500',   bar: 'bg-red-500' },
}

const IMPACT_STYLE = {
  high:     { icon: AlertTriangle, color: 'text-red-600',   bg: 'bg-red-50',    border: 'border-red-100' },
  moderate: { icon: Info,          color: 'text-amber-600', bg: 'bg-amber-50',  border: 'border-amber-100' },
  positive: { icon: CheckCircle,   color: 'text-green-600', bg: 'bg-green-50',  border: 'border-green-100' },
}

const PHASE_CONFIG = {
  before: { label: 'Before Going Outdoors', color: 'text-blue-700',  bg: 'bg-blue-50',   icon: Clock },
  during: { label: 'During Outdoor Exposure', color: 'text-orange-700', bg: 'bg-orange-50', icon: Thermometer },
  after:  { label: 'After Returning Indoors', color: 'text-green-700', bg: 'bg-green-50',  icon: Droplets },
}

function FieldLabel({ children, optional }) {
  return (
    <label className="block text-sm font-semibold text-gray-800 mb-1">
      {children}
      {optional && <span className="ml-1.5 text-xs font-normal text-gray-400">(optional)</span>}
    </label>
  )
}

function HealthToggle({ label, detail, value, onChange }) {
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
        value ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
      }`}
      onClick={() => onChange(value === null ? true : value === true ? false : null)}
      role="checkbox"
      aria-checked={value === true ? 'true' : value === false ? 'false' : 'mixed'}
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onChange(value === null ? true : value === true ? false : null)}
    >
      <div className={`w-4 h-4 mt-0.5 rounded flex-shrink-0 border-2 flex items-center justify-center ${
        value === true ? 'border-blue-500 bg-blue-500' : value === false ? 'border-gray-400 bg-white' : 'border-gray-300 bg-white'
      }`}>
        {value === true && <CheckCircle size={10} className="text-white" />}
        {value === false && <span className="text-gray-400 text-xs font-bold">✕</span>}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-800">{label}</div>
        <div className="text-xs text-gray-500 mt-0.5">{detail}</div>
      </div>
    </div>
  )
}

export default function PersonalHeatAssessment() {
  const [form, setForm] = useState({
    location_name: 'Hyderabad, Telangana',
    age_range: '18-59',
    outdoor_activity: '',
    outdoor_duration_hours: 4,
    has_water_access: true,
    has_shade_access: true,
    is_pregnant: null,
    has_chronic_condition: null,
    takes_heat_affecting_medication: null,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activePhase, setActivePhase] = useState('before')

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload = {
        location_name: form.location_name,
        age_range: form.age_range,
        outdoor_duration_hours: parseFloat(form.outdoor_duration_hours) || 0,
        outdoor_activity: form.outdoor_activity || undefined,
        has_water_access: form.has_water_access,
        has_shade_access: form.has_shade_access,
        is_pregnant: form.is_pregnant === null ? undefined : form.is_pregnant,
        has_chronic_condition: form.has_chronic_condition === null ? undefined : form.has_chronic_condition,
        takes_heat_affecting_medication: form.takes_heat_affecting_medication === null ? undefined : form.takes_heat_affecting_medication,
      }
      const res = await personalHeatAssessment(payload)
      setResult(res)
      setActivePhase('before')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const risk = result ? RISK_CONFIG[result.risk_category] : null
  const phasePrecautions = result
    ? (result.precautions || []).filter((p) => p.phase === activePhase)
    : []

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-gray-900">Personal Heat Protection Assessment</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Receive a personalised heat-risk evaluation based on your profile and current local weather.
        All health fields are optional and are not stored. Results are for general awareness only — not medical advice.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* ── Left: Form ── */}
        <div className="lg:col-span-2 space-y-4">
          <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-5">

            {/* Location */}
            <div>
              <FieldLabel>Location</FieldLabel>
              <input
                type="text"
                value={form.location_name}
                onChange={(e) => set('location_name', e.target.value)}
                placeholder="e.g. Hyderabad, Telangana"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                required
                minLength={2}
              />
            </div>

            {/* Age range */}
            <div>
              <FieldLabel>Age Range</FieldLabel>
              <div className="grid grid-cols-2 gap-2">
                {AGE_RANGES.map((range) => (
                  <button
                    key={range}
                    type="button"
                    onClick={() => set('age_range', range)}
                    className={`px-3 py-2 text-sm rounded-lg border transition-all ${
                      form.age_range === range
                        ? 'border-blue-500 bg-blue-600 text-white font-semibold'
                        : 'border-gray-200 text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>

            {/* Outdoor activity */}
            <div>
              <FieldLabel optional>Outdoor Activity / Occupation</FieldLabel>
              <select
                value={form.outdoor_activity}
                onChange={(e) => set('outdoor_activity', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                <option value="">Select activity type…</option>
                {ACTIVITY_TYPES.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>

            {/* Duration */}
            <div>
              <FieldLabel>Approximate Outdoor Exposure</FieldLabel>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={12}
                  step={0.5}
                  value={form.outdoor_duration_hours}
                  onChange={(e) => set('outdoor_duration_hours', e.target.value)}
                  className="flex-1 accent-blue-600"
                />
                <span className="text-sm font-semibold text-gray-800 w-16 text-right">
                  {form.outdoor_duration_hours} hrs
                </span>
              </div>
            </div>

            {/* Water / Shade access */}
            <div>
              <FieldLabel>Access While Outdoors</FieldLabel>
              <div className="space-y-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.has_water_access}
                    onChange={(e) => set('has_water_access', e.target.checked)}
                    className="w-4 h-4 accent-blue-600"
                  />
                  <span className="text-sm text-gray-700">I have reliable access to drinking water</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.has_shade_access}
                    onChange={(e) => set('has_shade_access', e.target.checked)}
                    className="w-4 h-4 accent-blue-600"
                  />
                  <span className="text-sm text-gray-700">I have access to shade or cool spaces</span>
                </label>
              </div>
            </div>

            {/* Health context — optional */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Heart size={14} className="text-pink-500" />
                <FieldLabel optional>Health Context</FieldLabel>
              </div>
              <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                These optional fields help improve your risk estimate. They are not stored or shared.
                Selecting a field three times cycles through Yes → No → Not answered.
              </p>
              <div className="space-y-2">
                <HealthToggle
                  label="Currently pregnant"
                  detail="Pregnancy increases metabolic heat load and fluid requirements."
                  value={form.is_pregnant}
                  onChange={(v) => set('is_pregnant', v)}
                />
                <HealthToggle
                  label="Chronic health condition"
                  detail="e.g. heart disease, diabetes, kidney disease, or similar."
                  value={form.has_chronic_condition}
                  onChange={(v) => set('has_chronic_condition', v)}
                />
                <HealthToggle
                  label="Medications affecting heat tolerance"
                  detail="e.g. diuretics, blood pressure medication, antihistamines."
                  value={form.takes_heat_affecting_medication}
                  onChange={(v) => set('takes_heat_affecting_medication', v)}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !form.location_name.trim()}
              className="w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              {loading
                ? <><RefreshCw size={15} className="animate-spin" /> Assessing…</>
                : <><ShieldCheck size={15} /> Get My Assessment</>
              }
            </button>
          </form>
        </div>

        {/* ── Right: Results ── */}
        <div className="lg:col-span-3 space-y-4">
          {!result && !loading && !error && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center flex flex-col items-center justify-center min-h-80">
              <User size={44} className="mb-3 text-gray-200" />
              <p className="text-sm font-medium text-gray-500">No Assessment Yet</p>
              <p className="text-xs mt-2 text-gray-400 max-w-xs leading-relaxed">
                Fill in your profile on the left and click "Get My Assessment" to receive personalised heat-protection guidance.
              </p>
            </div>
          )}

          {loading && <LoadingState message="Fetching weather and computing your assessment…" />}
          {error && !loading && (
            <ErrorState title="Assessment failed" message={error} onRetry={handleSubmit} />
          )}

          {result && !loading && (
            <>
              {/* Risk banner */}
              <div className={`rounded-xl border p-5 ${risk.bg} ${risk.border}`}>
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-3 h-3 rounded-full flex-shrink-0 ${risk.dot}`} />
                  <span className={`text-lg font-bold ${risk.text}`}>{result.risk_label}</span>
                  <span className={`ml-auto text-2xl font-black ${risk.text}`}>{result.risk_score}<span className="text-sm font-semibold">/100</span></span>
                </div>
                {/* Score bar */}
                <div className="w-full h-2 bg-gray-200 rounded-full mb-3">
                  <div
                    className={`h-2 rounded-full transition-all ${risk.bar}`}
                    style={{ width: `${result.risk_score}%` }}
                  />
                </div>
                <p className={`text-sm leading-relaxed ${risk.text}`}>{result.risk_explanation}</p>
                <p className="text-xs text-gray-500 mt-2">
                  Location: <strong>{result.location_resolved}</strong>
                  {result.weather?.weather_available && result.weather.temperature != null && (
                    <> · {result.weather.temperature.toFixed(1)}°C, {result.weather.humidity}% RH</>
                  )}
                  {!result.weather?.weather_available && (
                    <> · <span className="text-amber-600">Weather unavailable — partial score</span></>
                  )}
                </p>
              </div>

              {/* Contributing factors */}
              {result.contributing_factors?.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Contributing Factors</h3>
                  <div className="space-y-2">
                    {result.contributing_factors.map((f, i) => {
                      const cfg = IMPACT_STYLE[f.impact] || IMPACT_STYLE.moderate
                      const Icon = cfg.icon
                      return (
                        <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.bg} ${cfg.border}`}>
                          <Icon size={14} className={`flex-shrink-0 mt-0.5 ${cfg.color}`} />
                          <div className="min-w-0">
                            <div className={`text-sm font-semibold ${cfg.color}`}>{f.label}</div>
                            <div className="text-xs text-gray-600 mt-0.5 leading-relaxed">{f.detail}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Precautions — phased */}
              {result.precautions?.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <div className="border-b border-gray-100 flex">
                    {Object.entries(PHASE_CONFIG).map(([phase, cfg]) => (
                      <button
                        key={phase}
                        onClick={() => setActivePhase(phase)}
                        className={`flex-1 py-3 text-xs font-semibold transition-all ${
                          activePhase === phase
                            ? 'border-b-2 border-blue-500 text-blue-700 bg-blue-50'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        {cfg.label.split(' ')[0]}
                      </button>
                    ))}
                  </div>
                  <div className="p-5">
                    <div className="flex items-center gap-2 mb-3">
                      {React.createElement(PHASE_CONFIG[activePhase].icon, { size: 14, className: PHASE_CONFIG[activePhase].color })}
                      <span className={`text-sm font-semibold ${PHASE_CONFIG[activePhase].color}`}>
                        {PHASE_CONFIG[activePhase].label}
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {phasePrecautions.map((p, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <ChevronRight size={14} className="flex-shrink-0 mt-0.5 text-blue-400" />
                          {p.action}
                        </li>
                      ))}
                      {phasePrecautions.length === 0 && (
                        <li className="text-sm text-gray-400 italic">No specific precautions for this phase.</li>
                      )}
                    </ul>
                  </div>
                </div>
              )}

              {/* Warning signs */}
              {result.warning_signs?.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle size={14} className="text-red-500" />
                    <h3 className="text-sm font-semibold text-red-700 uppercase tracking-wide">Warning Signs — Seek Medical Help</h3>
                  </div>
                  <ul className="space-y-1.5">
                    {result.warning_signs.map((w, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-red-700">
                        <span className="w-1.5 h-1.5 mt-1.5 rounded-full bg-red-400 flex-shrink-0" />
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Emergency guidance */}
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={14} className="text-red-600" />
                  <span className="text-sm font-bold text-red-800">Emergency Guidance</span>
                </div>
                <p className="text-xs text-red-700 leading-relaxed">{result.emergency_guidance}</p>
              </div>

              {/* Disclaimer */}
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                <div className="flex items-start gap-2">
                  <Info size={13} className="text-gray-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-gray-500 leading-relaxed">{result.disclaimer}</p>
                </div>
              </div>

              {/* Reassess button */}
              <button
                onClick={() => { setResult(null); setError(null) }}
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors"
              >
                <RefreshCw size={14} />
                Update Profile &amp; Reassess
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
