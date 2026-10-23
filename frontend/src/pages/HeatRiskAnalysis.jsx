import React, { useState } from 'react'
import {
  Thermometer, RefreshCw, Search, ChevronDown,
  Shield, AlertTriangle, CheckCircle, Info, Send,
} from 'lucide-react'
import { LoadingState, ErrorState } from '../components/States'
import { isDemo } from '../services/api'
import {
  DEMO_LOCATIONS, DEMO_ASSESSMENTS, DEMO_WEATHER, DEMO_LANDMARK_PRESETS,
} from '../services/demoService'
import { submitWeatherAssessment } from '../services/api'

const AREA_TYPES = [
  'Transit Hub (Bus Stop / Metro / Rail)',
  'Open-Air Market',
  'Commercial Market / Heritage',
  'Urban Park / Protective Facility',
  'Residential Colony',
  'Industrial / Construction Area',
  'Educational Institution',
  'Commercial IT Corridor',
]

const SURFACE_TYPES = [
  'Dark Asphalt / Tar (High Heat Retention)',
  'Concrete Slab (High Heat Retention)',
  'Granite Cobblestone (Very High Heat)',
  'Interlocking Pavers (Moderate Heat)',
  'Grass & Paved Pathway (Low Heat)',
  'Red Oxide Compound (Moderate Heat)',
]

const SHADE_OPTIONS = [
  'None / Fully Exposed',
  'Sparse / Minimal (<25% cover)',
  'Moderate (25–50% cover)',
  'Good (50–75% cover)',
  'Dense (>75% cover)',
]

const FOOTFALL_OPTIONS = [
  'Low (<100 people/hr)',
  'Moderate (100–500 people/hr)',
  'High (500–1,000 people/hr)',
  'Extreme (>1,000 people/hr continuously)',
]

const DEMOGRAPHICS = [
  'Commuters', 'Students', 'Street Vendors', 'Daily Wage Laborers',
  'Elderly Citizens', 'Children', 'Traffic Police / Municipal Workers',
]

const PRIORITY_COLORS = {
  'Immediate': 'bg-red-500 text-white',
  'Medium Term': 'bg-amber-500 text-white',
  'Long Term': 'bg-blue-600 text-white',
  'Low Priority': 'bg-gray-400 text-white',
}

const IMPACT_CLASSES = {
  high: 'bg-red-100 text-red-800 border border-red-200',
  moderate: 'bg-orange-100 text-orange-800 border border-orange-200',
  positive: 'bg-green-100 text-green-800 border border-green-200',
}

export default function HeatRiskAnalysis() {
  const [selectedPreset, setSelectedPreset] = useState('')
  const [locationName, setLocationName] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [areaType, setAreaType] = useState(AREA_TYPES[0])
  const [surfaceType, setSurfaceType] = useState(SURFACE_TYPES[0])
  const [shadeAvailability, setShadeAvailability] = useState(SHADE_OPTIONS[1])
  const [footfall, setFootfall] = useState(FOOTFALL_OPTIONS[2])
  const [canopyDensity, setCanopyDensity] = useState(10)
  const [selectedDemographics, setSelectedDemographics] = useState(['Commuters', 'Students'])
  const [hydrationPresent, setHydrationPresent] = useState(false)
  const [notes, setNotes] = useState('')
  const [weather, setWeather] = useState(isDemo ? DEMO_WEATHER : null)
  const [assessment, setAssessment] = useState(null)
  const [loadingAssessment, setLoadingAssessment] = useState(false)
  const [assessmentError, setAssessmentError] = useState(null)

  const handlePresetChange = (e) => {
    const id = parseInt(e.target.value)
    if (!id) { setSelectedPreset(''); return }
    const preset = DEMO_LANDMARK_PRESETS.find((p) => p.id === id)
    if (preset) {
      setSelectedPreset(e.target.value)
      setLocationName(preset.name)
      setLatitude(String(preset.latitude))
      setLongitude(String(preset.longitude))
      setAreaType(preset.area_type || AREA_TYPES[0])
      setAssessment(null)
      setAssessmentError(null)
    }
  }

  const toggleDemographic = (d) => {
    setSelectedDemographics((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    )
  }

  const handleAssess = async () => {
    const lat = parseFloat(latitude)
    const lon = parseFloat(longitude)
    if (isNaN(lat) || isNaN(lon)) return
    setLoadingAssessment(true)
    setAssessmentError(null)
    try {
      if (isDemo) {
        await new Promise((r) => setTimeout(r, 1200))
        const locId = parseInt(selectedPreset)
        const result = locId ? DEMO_ASSESSMENTS[locId] : DEMO_ASSESSMENTS[2]
        setAssessment({ ...result, latitude: lat, longitude: lon, _demo: true })
      } else {
        const res = await submitWeatherAssessment({
          latitude: lat, longitude: lon, location_name: locationName,
          area_type: areaType, surface_type: surfaceType,
          shade_availability: shadeAvailability, footfall, canopy_density: canopyDensity,
          demographics: selectedDemographics, hydration_present: hydrationPresent, notes,
        })
        setAssessment(res)
      }
    } catch (err) {
      setAssessmentError(err.message)
    } finally {
      setLoadingAssessment(false)
    }
  }

  const hasCoords = !isNaN(parseFloat(latitude)) && !isNaN(parseFloat(longitude))

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-gray-900">Heat Risk Analysis &amp; Assessment</h1>
        {isDemo && (
          <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-1 rounded-full font-semibold flex items-center gap-1">
            ⚡ Demo Mode Active
          </span>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Submit field observations and microclimate parameters to evaluate localized heat risk via FastAPI predictive scoring models.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form — left 2/3 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-orange-500 text-lg">🔥</span>
              <h3 className="font-semibold text-gray-900">Field Survey Observation Form</h3>
            </div>
            <p className="text-xs text-gray-500 mb-5">All fields are passed directly to the scoring backend</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Landmark preset */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Select Hyderabad Landmark / Ward Preset</label>
                <div className="relative">
                  <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={selectedPreset}
                    onChange={handlePresetChange}
                  >
                    <option value="">— Select landmark —</option>
                    {DEMO_LANDMARK_PRESETS.map((p) => (
                      <option key={p.id} value={p.id}>{p.label}</option>
                    ))}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Location name */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Location / Specific Point Name *</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. Koti Women's College Bus Stop"
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                />
              </div>

              {/* Latitude */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Latitude (°N) *</label>
                <input
                  type="number"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="17.3888"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  step="any"
                />
              </div>

              {/* Longitude */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Longitude (°E) *</label>
                <input
                  type="number"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="78.4842"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  step="any"
                />
              </div>

              {/* Area type */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Area Type / Land Use</label>
                <div className="relative">
                  <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={areaType}
                    onChange={(e) => setAreaType(e.target.value)}
                  >
                    {AREA_TYPES.map((a) => <option key={a}>{a}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Shade availability */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Visible Shade Availability</label>
                <div className="relative">
                  <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={shadeAvailability}
                    onChange={(e) => setShadeAvailability(e.target.value)}
                  >
                    {SHADE_OPTIONS.map((s) => <option key={s}>{s}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Primary ground surface */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Primary Ground Surface</label>
                <div className="relative">
                  <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={surfaceType}
                    onChange={(e) => setSurfaceType(e.target.value)}
                  >
                    {SURFACE_TYPES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Footfall */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Pedestrian Exposure / Footfall</label>
                <div className="relative">
                  <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={footfall}
                    onChange={(e) => setFootfall(e.target.value)}
                  >
                    {FOOTFALL_OPTIONS.map((f) => <option key={f}>{f}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Canopy density slider */}
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-gray-600">Observed Tree Canopy Density</label>
                <span className="text-xs font-bold text-blue-600">{canopyDensity}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={canopyDensity}
                onChange={(e) => setCanopyDensity(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0% (Zero Foliage)</span>
                <span>50% (Moderate Overhead Leaf Cover)</span>
                <span>100% (Continuous Dense Canopy)</span>
              </div>
            </div>

            {/* Demographics */}
            <div className="mt-4">
              <label className="block text-xs font-medium text-gray-600 mb-2">Observed Vulnerable Demographics</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {DEMOGRAPHICS.map((d) => {
                  const active = selectedDemographics.includes(d)
                  return (
                    <button
                      key={d}
                      onClick={() => toggleDemographic(d)}
                      className={`text-xs px-3 py-2 rounded-lg border text-left transition-colors ${
                        active
                          ? 'bg-blue-50 border-blue-400 text-blue-700 font-medium'
                          : 'border-gray-300 text-gray-600 hover:border-gray-400'
                      }`}
                    >
                      {active ? '✓ ' : '+ '}{d}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Hydration toggle */}
            <div className="mt-4 p-3 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-700">Free Hydration Facility Present?</div>
                  <div className="text-xs text-gray-500 mt-0.5">Functional municipal water ATM, earthen matka, or shaded water cooler within 50m.</div>
                </div>
                <button
                  onClick={() => setHydrationPresent(!hydrationPresent)}
                  className={`w-12 h-6 rounded-full transition-colors relative flex-shrink-0 ${hydrationPresent ? 'bg-blue-600' : 'bg-gray-300'}`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow absolute top-0.5 transition-transform ${hydrationPresent ? 'translate-x-6' : 'translate-x-0.5'}`} />
                </button>
              </div>
            </div>

            {/* Surveyor notes */}
            <div className="mt-4">
              <label className="block text-xs font-medium text-gray-600 mb-1">Field Surveyor Notes (Optional)</label>
              <textarea
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                placeholder="Observed local microclimate factors, wind obstructions, or building reflections..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={handleAssess}
                disabled={!hasCoords || loadingAssessment}
                className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loadingAssessment ? <RefreshCw size={15} className="animate-spin" /> : <Send size={15} />}
                {loadingAssessment ? 'Running Assessment…' : 'Run Backend Assessment'}
              </button>
            </div>
          </div>
        </div>

        {/* Right column — weather + policy */}
        <div className="space-y-4">
          {/* Weather panel */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Selected Coordinates Weather</span>
              <span className="text-xs font-mono text-gray-500">17.389°N, 78.494°E</span>
            </div>
            <div className="flex items-end gap-2 mb-2">
              <span className="text-4xl font-black text-gray-900">{weather?.temperature ?? 39.4}°C</span>
              <span className="text-sm text-gray-500 pb-1">Feels {weather?.feels_like ?? 43.1}°C</span>
            </div>
            <div className="flex gap-4 mb-3">
              <div className="text-center p-2 bg-red-50 rounded-lg flex-1">
                <div className="text-xs text-gray-500 mb-0.5">HI</div>
                <div className="font-bold text-red-600 text-sm">{weather?.heat_index ?? 44.5}°C</div>
              </div>
              <div className="text-center p-2 bg-blue-50 rounded-lg flex-1">
                <div className="text-xs text-gray-500 mb-0.5">UV INDEX</div>
                <div className="font-bold text-amber-600 text-sm">{weather?.uv_index ?? 9.2} (Very High)</div>
              </div>
              <div className="text-center p-2 bg-blue-50 rounded-lg flex-1">
                <div className="text-xs text-gray-500 mb-0.5">RELATIVE HUMIDITY</div>
                <div className="font-bold text-blue-600 text-sm">{weather?.humidity ?? 48}%</div>
              </div>
            </div>
            <p className="text-xs text-gray-400">Source: IMD AWS Hyderabad / Open-Meteo Heat Alert Stream</p>
          </div>

          {/* Backend integrity policy */}
        
        </div>
      </div>

      {/* Results section */}
      {loadingAssessment && (
        <div className="mt-6"><LoadingState message="Running backend heat risk assessment…" /></div>
      )}

      {assessmentError && !loadingAssessment && (
        <div className="mt-6"><ErrorState title="Assessment failed" message={assessmentError} onRetry={handleAssess} /></div>
      )}

      {assessment && !loadingAssessment && (
        <div className="mt-6 bg-white rounded-xl border border-gray-200 overflow-hidden">
          {/* Result header */}
          <div className="px-6 py-5 border-b border-gray-100">
            <div className="flex items-center gap-3 mb-1">
              <span className="text-xs font-mono text-gray-500">ASSESSMENT ID: {assessment.assessment_id}</span>
              {assessment._demo && (
                <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-semibold">
                  SIMULATED RESULT
                </span>
              )}
              <div className="ml-auto flex items-center gap-2">
                <AlertTriangle size={14} className={assessment.risk_score >= 75 ? 'text-red-500' : 'text-orange-500'} />
                <span className="font-semibold text-gray-800">
                  {assessment.risk_category === 'very_high' ? 'Critical' : assessment.risk_category === 'high' ? 'High' : 'Moderate'} Heat Risk
                </span>
                <span className="font-bold text-gray-600">{assessment.risk_score}/100</span>
              </div>
            </div>
            <h2 className="text-xl font-bold text-gray-900">Risk Evaluation: {assessment.location}</h2>
          </div>
          <div className="p-6 space-y-6">
            {/* Score + model info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">Computed Heat Risk Score</div>
                <div className="text-5xl font-black text-gray-900">{assessment.risk_score}</div>
                <div className="text-xs text-gray-500 mt-1">/ 100</div>
                <div className="text-xs font-semibold text-gray-600 mt-1">
                  Category: {assessment.risk_category?.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">Model Verification Status</div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
                    <CheckCircle size={10} className="text-white" />
                  </div>
                  <span className="text-sm font-semibold text-gray-800">{assessment.model_version}</span>
                </div>
                <div className="text-xs text-gray-500">{assessment.model_valid}</div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-2">Model Limitations</div>
                <p className="text-xs text-gray-600 leading-relaxed">{assessment.model_limitations}</p>
              </div>
            </div>

            {/* Contributing factors */}
            {assessment.factors?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle size={15} className="text-amber-500" />
                  <h4 className="font-semibold text-gray-900">Primary Contributing Vulnerability Factors</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {assessment.factors.map((f, i) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className="text-sm font-semibold text-gray-800">{f.label}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold whitespace-nowrap ${IMPACT_CLASSES[f.impact] || IMPACT_CLASSES.moderate}`}>
                          {f.impact === 'positive' ? 'Positive Factor' : f.impact === 'high' ? 'High Impact' : 'Medium Impact'}
                        </span>
                      </div>
                      {f.detail && <p className="text-xs text-gray-500 leading-relaxed">{f.detail}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations table */}
            {assessment.recommendations?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Shield size={15} className="text-blue-500" />
                  <h4 className="font-semibold text-gray-900">Backend Heat-Safety Recommendations &amp; Mitigation Roadmap</h4>
                </div>
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Priority</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Recommended Intervention</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Est. Cost (INR)</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Timeframe</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {assessment.recommendations.map((rec, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <span className={`text-xs px-2 py-1 rounded font-semibold ${PRIORITY_COLORS[rec.priority] || 'bg-gray-400 text-white'}`}>
                              {rec.priority}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-800">{rec.label}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-gray-900">
                            {rec.cost ? `₹${rec.cost.toLocaleString('en-IN')}` : '—'}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500">{rec.timeframe}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {assessment._demo && (
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg text-xs text-blue-700">
                <Info size={13} className="flex-shrink-0 mt-0.5" />
                <span>
                  These results are illustrative sample data for demonstration purposes.
                  Live mode will display actual FastAPI backend risk calculations.
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
