import React, { useState, useRef } from 'react'
import {
  ImagePlus, Scan, RefreshCw, Info, AlertTriangle, CheckCircle,
  Wallet, MapPin, Upload, X, BarChart3, Leaf, Droplets, Home,
  Sun, TreePine,
} from 'lucide-react'
import { LoadingState, ErrorState } from '../components/States'
import { analyzeAndOptimize } from '../services/api'
import ImageUploader from '../components/ImageUploader'

function formatINR(n) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
}

const RISK_DOT = {
  Low:      'bg-green-500',
  Moderate: 'bg-amber-500',
  High:     'bg-orange-500',
}

const INTERVENTION_ICONS = {
  'Public Drinking Water Station': Droplets,
  'Plant Shade Trees':             TreePine,
  'Cool Roof Coating':             Home,
  'Install Shade Structures':      Sun,
  'Cooling Shelter':               Home,
}

function BenefitBar({ score }) {
  const pct = Math.min(100, Math.max(0, score))
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-500' : 'bg-gray-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-semibold text-gray-600 w-8 text-right">{score}</span>
    </div>
  )
}

function ObservationChip({ label, visible, description }) {
  return (
    <div className={`p-3 rounded-lg border ${visible ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${visible ? 'bg-green-500' : 'bg-gray-300'}`} />
        <span className="text-xs font-semibold text-gray-700">{label}</span>
        <span className={`ml-auto text-xs font-bold ${visible ? 'text-green-700' : 'text-gray-400'}`}>
          {visible ? 'Visible' : 'Not visible'}
        </span>
      </div>
      {description && <p className="text-xs text-gray-500 leading-relaxed">{description}</p>}
    </div>
  )
}

export default function AreaAnalysis() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [locationName, setLocationName] = useState('Hyderabad, Telangana')
  const [budget, setBudget] = useState(100000)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileSelect = (file) => {
    setSelectedFile(file)
    setResult(null)
    setError(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(URL.createObjectURL(file))
  }

  const handleAnalyze = async () => {
    if (!selectedFile) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await analyzeAndOptimize(selectedFile, parseInt(budget, 10), locationName.trim())
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSelectedFile(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
  }

  const img = result?.image_analysis
  const recs = result?.recommendations || []
  const remaining = result?.remaining_budget ?? (budget - (result?.total_cost ?? 0))

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-gray-900">AI Area Analysis &amp; Budget Plan</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Upload a photo of a public outdoor space to identify heat vulnerabilities and generate a
        prioritised, budget-optimised heat-protection intervention plan.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Left: Upload + Inputs ── */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-1">Upload Area Photograph</h3>
            <p className="text-xs text-gray-500 mb-4">Supported formats: JPG, PNG · Max 10 MB</p>
            <ImageUploader onFileSelect={handleFileSelect} disabled={loading} />
            {previewUrl && (
              <div className="mt-3 relative">
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="w-full rounded-lg object-cover max-h-48 border border-gray-200"
                />
                <button
                  onClick={handleReset}
                  className="absolute top-2 right-2 w-6 h-6 bg-black/50 rounded-full flex items-center justify-center text-white hover:bg-black/70 transition-colors"
                  aria-label="Remove image"
                >
                  <X size={12} />
                </button>
              </div>
            )}
          </div>

          {/* Location + Budget */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">
                <MapPin size={13} className="inline mr-1 text-gray-500" />
                Location
              </label>
              <input
                type="text"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                placeholder="e.g. Hyderabad, Telangana"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">
                <Wallet size={13} className="inline mr-1 text-gray-500" />
                Available Budget (INR)
              </label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                min={1000}
                step={1000}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <p className="text-xs text-gray-400 mt-1">{formatINR(parseInt(budget, 10) || 0)}</p>
            </div>

            {selectedFile ? (
              <div className="flex gap-3">
                <button
                  onClick={handleAnalyze}
                  disabled={loading || !locationName.trim() || !budget}
                  className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
                >
                  {loading
                    ? <><RefreshCw size={15} className="animate-spin" /> Analysing…</>
                    : <><Scan size={15} /> Analyse &amp; Generate Plan</>
                  }
                </button>
                <button
                  onClick={handleReset}
                  disabled={loading}
                  className="px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  Reset
                </button>
              </div>
            ) : (
              <button
                disabled
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg opacity-40 cursor-not-allowed"
              >
                <ImagePlus size={15} />
                Upload an Image First
              </button>
            )}
          </div>

          {/* Illustration of how it works */}
          {!result && !loading && (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">How it works</p>
              <ol className="space-y-1.5">
                {[
                  'Upload a photo of a public outdoor space',
                  'Select the location and enter your budget',
                  'Gemini AI analyses heat-related vulnerabilities',
                  'OR-Tools optimizer selects the best interventions',
                  'View findings, cost breakdown, and implementation plan',
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center flex-shrink-0 text-xs">{i + 1}</span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>

        {/* ── Right: Results ── */}
        <div className="space-y-4">
          {!result && !loading && !error && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center flex flex-col items-center justify-center min-h-80">
              <BarChart3 size={44} className="mb-3 text-gray-200" />
              <p className="text-sm font-medium text-gray-500">No Analysis Yet</p>
              <p className="text-xs mt-2 text-gray-400 max-w-xs leading-relaxed">
                Upload a photograph, enter your location and budget, then click "Analyse &amp; Generate Plan".
              </p>
            </div>
          )}

          {loading && (
            <LoadingState message="Analysing image and generating optimised intervention plan…" />
          )}

          {error && !loading && (
            <ErrorState title="Analysis failed" message={error} onRetry={handleAnalyze} />
          )}

          {result && !loading && (
            <>
              {/* Budget summary */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                  <Wallet size={14} className="text-blue-500" />
                  Budget Summary
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Available',  value: formatINR(result.budget),      color: 'text-gray-800' },
                    { label: 'Proposed',   value: formatINR(result.total_cost),  color: 'text-blue-700' },
                    { label: 'Remaining',  value: formatINR(remaining),          color: remaining >= 0 ? 'text-green-700' : 'text-red-700' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className={`text-lg font-black ${color}`}>{value}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>
                {/* Budget bar */}
                <div className="mt-3">
                  <div className="w-full h-2 bg-gray-100 rounded-full">
                    <div
                      className="h-2 bg-blue-500 rounded-full transition-all"
                      style={{ width: `${Math.min(100, result.budget ? (result.total_cost / result.budget) * 100 : 0)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>₹0</span>
                    <span>{formatINR(result.budget)}</span>
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${RISK_DOT[result.risk_level] || 'bg-gray-400'}`} />
                  <span className="text-xs text-gray-600">
                    Heat risk: <strong>{result.risk_level}</strong> (score {result.heat_score}/100) · {result.location_resolved}
                  </span>
                </div>
                {result.costs_are_illustrative && (
                  <p className="text-xs text-amber-700 mt-2 flex items-start gap-1">
                    <Info size={11} className="flex-shrink-0 mt-0.5" />
                    Costs are illustrative planning estimates, not verified local quotes.
                  </p>
                )}
              </div>

              {/* Image findings */}
              {img ? (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <Scan size={14} className="text-blue-500" />
                    Image Findings
                  </h3>
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    {[
                      { key: 'vegetation',        label: 'Vegetation' },
                      { key: 'shaded_areas',       label: 'Shade' },
                      { key: 'sun_exposed_areas',  label: 'Sun Exposure' },
                      { key: 'shelters',           label: 'Shelters' },
                      { key: 'drinking_water',     label: 'Drinking Water' },
                    ].map(({ key, label }) => (
                      <ObservationChip
                        key={key}
                        label={label}
                        visible={img[key]?.visible}
                        description={img[key]?.description}
                      />
                    ))}
                  </div>
                  {img.infrastructure_gaps?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Infrastructure Gaps</p>
                      <ul className="space-y-1">
                        {img.infrastructure_gaps.map((g, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-red-700">
                            <AlertTriangle size={11} className="flex-shrink-0 mt-0.5 text-red-400" />
                            {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {img.explanation && (
                    <p className="text-xs text-gray-700 bg-blue-50 border border-blue-100 rounded-lg p-3 leading-relaxed mb-2">
                      {img.explanation}
                    </p>
                  )}
                  {img.limitations && (
                    <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-3">
                      <Info size={11} className="flex-shrink-0 mt-0.5" />
                      <span>{img.limitations}</span>
                    </div>
                  )}
                  {img.human_verification_required && (
                    <p className="text-xs text-gray-400 mt-2 italic">
                      ⚠ AI findings are preliminary observations. Human verification is required before any intervention decision.
                    </p>
                  )}
                </div>
              ) : (
                result.image_error && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                    <div className="flex items-start gap-2">
                      <AlertTriangle size={13} className="text-amber-500 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-amber-800 leading-relaxed">
                        Image analysis was unavailable: {result.image_error}. The budget plan was generated using weather-based scoring only.
                      </p>
                    </div>
                  </div>
                )
              )}

              {/* Recommended interventions */}
              {recs.length > 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <CheckCircle size={14} className="text-green-500" />
                    Recommended Interventions ({recs.length})
                  </h3>
                  <div className="space-y-3">
                    {recs.map((rec, i) => {
                      const Icon = INTERVENTION_ICONS[rec.intervention_type] || Leaf
                      return (
                        <div key={i} className="p-4 rounded-lg border border-gray-100 bg-gray-50">
                          <div className="flex items-start gap-3 mb-2">
                            <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                              <Icon size={15} className="text-blue-700" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-semibold text-gray-900">{rec.intervention_type}</div>
                              <div className="text-xs text-blue-700 font-semibold mt-0.5">
                                {formatINR(rec.estimated_cost)}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-xs text-gray-400">Priority</div>
                            </div>
                          </div>
                          <BenefitBar score={rec.benefit_score} />
                          {rec.explanation && (
                            <p className="text-xs text-gray-500 mt-2 leading-relaxed">{rec.explanation}</p>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                  <div className="flex items-start gap-2">
                    <Info size={13} className="text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-800">
                      No interventions could be selected within the available budget. Try increasing the budget or selecting a different location.
                    </p>
                  </div>
                </div>
              )}

              {/* Try again */}
              <button
                onClick={handleReset}
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Upload size={14} />
                Upload Another Image
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
