import React, { useState } from 'react'
import axios from 'axios'
import {
  Wallet, RefreshCw, RotateCcw, Info, TrendingUp, AlertCircle, CheckCircle, Download, ChevronDown, MapPin,CloudSun,
  Thermometer,
} from 'lucide-react'
import { LoadingState, ErrorState } from '../components/States'
import { BUDGET_PRESETS, PRIORITY_ZONES } from '../services/demoService'

const BACKEND_URL = 'http://127.0.0.1:8001'

function formatINR(n) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
}

function formatINRShort(n) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`
  if (n >= 1000) return `₹${(n / 1000).toFixed(0)}K`
  return `₹${n}`
}

function BenefitStars({ score }) {
  const filled = Math.round(score / 20)
  return (
    <span className="text-amber-500 text-xs">
      {'★'.repeat(filled)}{'☆'.repeat(5 - filled)}
      <span className="text-gray-500 ml-1">{score}/100</span>
    </span>
  )
}

const getPriorityLevel = (score) => {
  if (score >= 70) return 'High';
  if (score >= 40) return 'Medium';
  return 'Low';
};

export default function BudgetOptimizer() {
  const [budgetInput, setBudgetInput] = useState('')
  const [selectedPreset, setSelectedPreset] = useState(null)
  const [priorityZone, setPriorityZone] = useState('all_high')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [validationMsg, setValidationMsg] = useState('')
  const [locationName, setLocationName] = useState('')
  const [optimizationLocation, setOptimizationLocation] = useState('')
const [assessment, setAssessment] = useState(null)
const [assessmentLoading, setAssessmentLoading] = useState(false)
const [assessmentError, setAssessmentError] = useState('')

  const parsedBudget = parseInt(String(budgetInput).replace(/,/g, ''), 10)
  const isValidBudget = !isNaN(parsedBudget) && parsedBudget >= 280

  const handlePresetClick = (amount) => {
    setSelectedPreset(amount)
    setBudgetInput(String(amount))
    setValidationMsg('')
    setResult(null)
    setError(null)
  }

  const handleBudgetChange = (e) => {
    const raw = e.target.value.replace(/[^0-9]/g, '')
    setBudgetInput(raw)
    setSelectedPreset(null)
    setValidationMsg('')
    setResult(null)
    setError(null)
    
  }

  
const handleOptimize = async () => {
 
  if (!isValidBudget) {
    setValidationMsg('Please enter a valid budget of at least ₹280.')
    return
  }
  if (optimizationLocation.trim().length < 2) {
  setValidationMsg('Please enter a valid target location.')
  return
}

  setLoading(true)
  setError(null)
  setResult(null)

  try {
    
const response = await axios.post(
  `${BACKEND_URL}/api/optimize`,
  {
    budget: parsedBudget,
    location_name: optimizationLocation.trim(),
  },
  {
    headers: { 'Content-Type': 'application/json' },
    timeout: 300000,
  }
)

    const data = response.data
    console.log('Optimization API response:', data)
    console.log(
      'WorldPop population:',
      data.estimated_resident_population
    )
    console.log('Population fields:', {
    population: data.estimated_resident_population,
    year: data.population_data_year,
    source: data.population_source,
    area: data.population_area_km2,
  })
    const recommendations = data.recommendations || []
    const budget = Number(data.budget ?? parsedBudget)
    const totalCost = Number(data.total_cost || 0)

  
setResult({
  plan_id: data.optimization_run_id,
  budget,
  total_cost: totalCost,
  total_benefit_score: Number(data.total_benefit_score || 0),
  remaining_budget: Number(
    data.remaining_budget ?? budget - totalCost
  ),
  utilization_pct:
    budget > 0 ? Math.round((totalCost / budget) * 100) : 0,
  // WorldPop resident population estimate
estimated_resident_population:
  data.estimated_resident_population ?? null,
population_data_year: data.population_data_year ?? null,
population_source: data.population_source ?? null,
population_area_km2: data.population_area_km2 ?? null,

  location_name: data.location_name || optimizationLocation.trim(),
  gemini_location_summary: data.gemini_location_summary || '',
  weather: data.weather || null,
  heat_score: data.heat_score ?? null,
  risk_level: data.risk_level || null,

  strategy_rationale: `OR-Tools selected ${recommendations.length} intervention(s) with a combined benefit score of ${data.total_benefit_score || 0}.`,

  
interventions: recommendations.map((item) => ({
  intervention: item.intervention_type,
  spec: item.explanation,
  target_location: item.location_name,
  unit_cost: Number(item.estimated_cost),
  benefit_score: Number(item.benefit_score),
  priority_level: getPriorityLevel(
    Number(item.benefit_score)
  ),
})),


  note: data.costs_are_illustrative
    ? 'Costs and benefit scores are illustrative planning estimates, not verified local costs or measured health outcomes.'
    : '',
})

  } catch (err) {
    const detail = err.response?.data?.detail
    setError(
      Array.isArray(detail)
        ? detail.map((item) => item.msg).join(', ')
        : typeof detail === 'string'
          ? detail
          : err.message || 'Failed to optimize budget.'
    )
  } finally {
    setLoading(false)
  }
}


const handleAssessHeatRisk = async () => {
  const name = locationName.trim()

  if (name.length < 2) {
    setAssessmentError('Please enter a valid location name.')
    return
  }

  setAssessmentLoading(true)
  setAssessmentError('')
  setAssessment(null)

  try {
    const response = await axios.post(
      `${BACKEND_URL}/api/assessments/`,
      {
        location_name: name,
        location_type: 'City',
      },
      { timeout: 30000 }
    )

    setAssessment(response.data)
  } catch (err) {
    const detail = err.response?.data?.detail

    setAssessmentError(
      typeof detail === 'string'
        ? detail
        : err.message || 'Unable to assess heat risk.'
    )
  } finally {
    setAssessmentLoading(false)
  }
}


const handleReset = () => {
  setBudgetInput('')
  setSelectedPreset(null)
  setResult(null)
  setError(null)
  setValidationMsg('')
  setOptimizationLocation('')
}
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-gray-900">Urban Heat Mitigation Budget Optimizer</h1>
      </div>
      <p className="text-sm text-gray-500">
        Calculate optimal resource allocation for shade canopies, cool roof coatings, and hydration points within municipal or disaster management budgetary constraints.
      </p>

      
{/* Heat Risk Assessment */}
<div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
  <div className="flex items-center gap-3">
    <div className="p-3 bg-orange-100 rounded-xl">
      <Thermometer size={24} className="text-orange-600" />
    </div>
    <div>
      <h2 className="text-lg font-bold text-gray-900">
        Live Heat-Risk Assessment
      </h2>
      <p className="text-sm text-gray-500">
        Enter a location to fetch weather and assess heat risk.
      </p>
    </div>
  </div>

  <div className="flex flex-col sm:flex-row gap-3">
    <div className="relative flex-1">
      <MapPin
        size={17}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
      />
      <input
        type="text"
        value={locationName}
        onChange={(e) => setLocationName(e.target.value)}
        onKeyDown={(e) =>
          e.key === 'Enter' && handleAssessHeatRisk()
        }
        placeholder="e.g. Hyderabad, Telangana"
        className="w-full border border-gray-300 rounded-lg pl-10 pr-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
      />
    </div>

    <button
      onClick={handleAssessHeatRisk}
      disabled={assessmentLoading}
      className="flex items-center justify-center gap-2 px-5 py-3 bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50"
    >
      <CloudSun size={17} />
      {assessmentLoading ? 'Fetching Weather...' : 'Assess Heat Risk'}
    </button>
  </div>

  {assessmentError && (
    <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">
      {assessmentError}
    </div>
  )}

  {assessment && (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h3 className="font-bold text-gray-900">
            {assessment.location.name}
          </h3>
          <p className="text-xs text-gray-500">
            Weather time: {assessment.weather.time}
          </p>
        </div>

        <span
          className={`inline-flex w-fit px-3 py-1 rounded-full text-sm font-semibold ${
            assessment.assessment.risk_level === 'High'
              ? 'bg-red-100 text-red-700'
              : assessment.assessment.risk_level === 'Moderate'
                ? 'bg-amber-100 text-amber-700'
                : 'bg-green-100 text-green-700'
          }`}
        >
          {assessment.assessment.risk_level} Risk
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            label: 'Temperature',
            value: `${assessment.weather.temperature}°C`,
          },
          {
            label: 'Feels Like',
            value: `${assessment.weather.apparent_temperature ?? '—'}°C`,
          },
          {
            label: 'Humidity',
            value: `${assessment.weather.humidity}%`,
          },
          {
            label: 'Risk Score',
            value: `${assessment.assessment.risk_score}/100`,
          },
        ].map((item) => (
          <div
            key={item.label}
            className="p-4 rounded-xl bg-gray-50 border border-gray-100"
          >
            <p className="text-xs text-gray-500 mb-2">
              {item.label}
            </p>
            <p className="text-xl font-bold text-gray-900">
              {item.value}
            </p>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-500">
        Assessment ID: {assessment.assessment.id}.
        This preliminary score is illustrative and is not a
        validated medical or heat-health prediction.
      </p>
    </div>
  )}
</div>

      {/* Input card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Specify Mitigation Investment Envelope</h3>
        <p className="text-xs text-gray-500 mb-5">
          The FastAPI mathematical optimizer allocates interventions to maximize daily citizen heat-protection benefit scores without exceeding the budget limit.
        </p>

        {/* Preset tiles */}
        <div className="mb-5">
          <p className="text-xs font-semibold text-gray-600 mb-2">Standard Municipal &amp; Disaster Management Scenarios:</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {BUDGET_PRESETS.map((preset) => (
              <button
                key={preset.amount}
                onClick={() => handlePresetClick(preset.amount)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  selectedPreset === preset.amount
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className={`text-lg font-black mb-1 ${selectedPreset === preset.amount ? 'text-blue-700' : 'text-gray-900'}`}>
                  {preset.label}
                </div>
                <div className="text-xs text-gray-500 leading-tight">{preset.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          {/* Budget input */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Available Budget (INR ₹) *</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-medium text-sm">₹</span>
              <input
                type="text"
                inputMode="numeric"
                className={`w-full border rounded-lg pl-7 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${validationMsg ? 'border-red-400' : 'border-gray-300'}`}
                placeholder="e.g. 15000"
                value={budgetInput}
                onChange={handleBudgetChange}
                onKeyDown={(e) => e.key === 'Enter' && handleOptimize()}
              />
            </div>
            {validationMsg && (
              <div className="mt-1 flex items-center gap-1.5 text-xs text-red-600">
                <AlertCircle size={12} />
                {validationMsg}
              </div>
            )}
            {isValidBudget && !validationMsg && (
              <p className="mt-1 text-xs text-gray-500">{formatINR(parsedBudget)}</p>
            )}
            <p className="mt-1 text-xs text-gray-400">
              Example: 15000 (Fifteen Thousand) or 25000 (Twenty-Five Thousand)
            </p>
          </div>

          {/* Priority zone */}
        {/* Optimization location */}
        <div>
                 <label className="block text-xs font-medium text-gray-600 mb-1">
                     Target Location *
  </label>
  <div className="relative">
    <MapPin
      size={16}
      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
    />
    <input
      type="text"
      value={optimizationLocation}
      onChange={(e) => setOptimizationLocation(e.target.value)}
      placeholder="e.g. Gokarna, Karnataka"
      className="w-full border border-gray-300 rounded-lg pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  </div>
  <p className="mt-1 text-xs text-gray-400">
    Enter the city or region for which you want to optimize heat-mitigation interventions.
  </p>
</div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleOptimize}
          disabled={loading || !isValidBudget || !optimizationLocation.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <TrendingUp size={15} />}
            {loading ? 'Calculating Optimal Intervention Portfolio…' : 'Run Optimization Engine'}
          </button>
          <button onClick={handleReset} disabled={loading} className="btn-secondary flex items-center gap-2 text-sm">
            <RotateCcw size={14} />
            Reset
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && <LoadingState message="Running FastAPI optimization engine…" />}
      {error && !loading && <ErrorState title="Optimization failed" message={error} onRetry={handleOptimize} />}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-4">
          {/* Plan header */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <div className="flex items-center gap-3 mb-1">
                <span className="text-xs font-mono text-gray-500">PLAN ID: {result.plan_id}</span>
                <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-semibold">
                   OPTIMIZATION COMPLETE
                </span>
                <div className="ml-auto flex items-center gap-2">
                  <CheckCircle size={14} className="text-green-500" />
                  <span className="text-sm font-semibold text-green-700">Budget Constraint Satisfied</span>
                  <button className="ml-3 flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 border border-blue-200 px-2.5 py-1.5 rounded-lg">
                    <Download size={12} />
                    Export Report
                  </button>
                </div>
              </div>
              <h2 className="text-xl font-bold text-gray-900">Optimal Mitigation Deployment Portfolio</h2>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-gray-100 border-b border-gray-100">
              {[
                { label: 'Budget Allocated', value: formatINRShort(result.budget), sub: 'Allocated limit', color: 'text-gray-900' },
                { label: 'Total Projected Cost', value: formatINRShort(result.total_cost), sub: `${result.utilization_pct}% Budget Utilization`, color: 'text-green-600' },
                { label: 'Remaining Surplus', value: formatINRShort(result.remaining_budget), sub: 'Under budget reserve', color: 'text-blue-600' },
                {
  label: 'Estimated Resident Population',
  value:
    result.estimated_resident_population != null
      ? result.estimated_resident_population.toLocaleString('en-IN')
      : '—',
  sub:
    result.population_area_km2 != null
      ? `${result.population_area_km2.toFixed(2)} km² · WorldPop ${result.population_data_year ?? ''}`
      : 'Population data unavailable',
  color: 'text-purple-600',
},
              ].map((s) => (
                <div key={s.label} className="p-5">
                  <div className="text-xs text-gray-500 mb-1">{s.label}</div>
                  <div className={`text-3xl font-black ${s.color}`}>{s.value}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{s.sub}</div>
                </div>
              ))}
            </div>

            {/* Strategy rationale */}
            {result.strategy_rationale && (
              <div className="px-6 py-3 bg-blue-50 border-b border-blue-100 flex items-start gap-2">
                <Info size={13} className="text-blue-500 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-800 font-medium">
                  <span className="font-semibold">Backend Optimization Strategy Rationale</span><br />
                  {result.strategy_rationale}
                </p>
              </div>
            )}

            {/* Interventions table */}
            {result.interventions?.length > 0 && (
              <div className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Wallet size={15} className="text-gray-500" />
                  <h4 className="font-semibold text-gray-900">Selected Intervention Allocation Breakdown</h4>
                </div>
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Intervention &amp; Specification</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Target Location &amp; Ward</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Priority Level</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Unit Cost (INR)</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Benefit Score(INR)</th>
                        
                        
                      </tr>
                    </thead>

                  <tbody className="divide-y divide-gray-100">
                    {result.interventions.map((item, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        {/* Intervention & Specification */}
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-gray-900">
                            {item.intervention}
                          </div>
                          {item.spec && (
                            <div className="text-xs text-gray-500 mt-0.5 leading-relaxed max-w-xs">
                              {item.spec}
                            </div>
                          )}
                        </td>

                        {/* Target Location */}
                        <td className="px-4 py-3.5">
                          <div className="text-sm text-gray-700">
                            {item.target_location}
                          </div>
                        </td>

                        {/* Priority Level + Score underneath */}
                        <td className="px-4 py-3.5">
                          <div className="flex flex-col items-start gap-1">
                            <span
                              className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                                item.priority_level === 'High'
                                  ? 'bg-red-100 text-red-700'
                                  : item.priority_level === 'Medium'
                                    ? 'bg-amber-100 text-amber-700'
                                    : 'bg-green-100 text-green-700'
                              }`}
                            >
                              {item.priority_level}
                            </span>

                           
                          </div>
                        </td>

                        {/* Unit Cost: actual amount required */}
                        <td className="px-4 py-3.5">
                          <span className="text-sm font-medium text-gray-900">
                            ₹{Number(item.unit_cost || 0).toLocaleString('en-IN')}
                          </span>
                        </td>

                        {/* Benefit Score: stars + score */}
                        <td className="px-4 py-3.5">
                          <BenefitStars score={item.benefit_score} />
                        </td>
                      </tr>
                    ))}
                  </tbody>

                  </table>
                </div>

                {result.note && (
                  <div className="mt-4 flex items-start gap-2 p-3 bg-amber-50 rounded-lg text-xs text-amber-700">
                    <Info size={13} className="flex-shrink-0 mt-0.5" />
                    <span>{result.note}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
