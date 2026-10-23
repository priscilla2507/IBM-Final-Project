import React, { useState } from 'react'
import {
  Camera, Scan, RefreshCw, Info, AlertTriangle, CheckCircle,
  Upload, X, Star,
} from 'lucide-react'
import { LoadingState, ErrorState } from '../components/States'
import { isDemo } from '../services/api'
import { DEMO_PHOTO_ANALYSES, DEMO_FIELD_PHOTOS } from '../services/demoService'
import { analyzeImage } from '../services/api'
import ImageUploader from '../components/ImageUploader'

const RISK_COLOR = {
  low: { text: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200' },
  moderate: { text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
  high: { text: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  very_high: { text: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
}

function MetricTile({ label, value, sub, color }) {
  return (
    <div className="text-center p-3 bg-gray-50 rounded-lg">
      <div className={`text-2xl font-black ${color}`}>{value}</div>
      <div className="text-xs font-semibold text-gray-700 mt-0.5">{label}</div>
      <div className="text-xs text-gray-400 mt-0.5">{sub}</div>
    </div>
  )
}

export default function PhotoAnalysis() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [demoPhotoId, setDemoPhotoId] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [demoIdx, setDemoIdx] = useState(0)

  const handleFileSelect = (file) => {
    setSelectedFile(file)
    setDemoPhotoId(null)
    setResult(null)
    setError(null)
    setDemoIdx((prev) => (prev + 1) % DEMO_PHOTO_ANALYSES.length)
  }

  const handleDemoPhotoSelect = (photo) => {
    setDemoPhotoId(photo.id)
    setSelectedFile(null)
    setResult(null)
    setError(null)
  }

  const handleAnalyze = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      if (isDemo) {
        await new Promise((r) => setTimeout(r, 1600))
        if (demoPhotoId) {
          const photo = DEMO_FIELD_PHOTOS.find((p) => p.id === demoPhotoId)
          setResult({ ...photo?.result, _demo: true })
        } else {
          setResult({ ...DEMO_PHOTO_ANALYSES[demoIdx], _demo: true })
        }
      } else {
        if (!selectedFile) return
        const res = await analyzeImage(selectedFile)
        setResult(res.data ?? res)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSelectedFile(null)
    setDemoPhotoId(null)
    setResult(null)
    setError(null)
  }

  const canAnalyze = selectedFile || demoPhotoId

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-gray-900">AI Shade &amp; Canopy Photo Analysis</h1>
        {isDemo && (
          <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-1 rounded-full font-semibold flex items-center gap-1">
            ⚡ Demo Mode Active
          </span>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Upload ground-level photographs of transit shelters, markets, or walkways to quantify visible shade, tree canopy, and thermal exposure via computer vision.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left — upload panel */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-1">Upload Site Photograph</h3>
            <p className="text-xs text-gray-500 mb-4">Supported formats: JPG, PNG. Max file size: 10 MB.</p>

            <ImageUploader onFileSelect={handleFileSelect} disabled={loading} />

            {(selectedFile || demoPhotoId) && (
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50 flex-1 justify-center"
                >
                  {loading ? <RefreshCw size={15} className="animate-spin" /> : <Scan size={15} />}
                  {loading ? 'Analysing…' : 'Run AI Analysis'}
                </button>
                <button onClick={handleReset} disabled={loading} className="btn-secondary px-4">
                  Reset
                </button>
              </div>
            )}

            {!selectedFile && !demoPhotoId && (
              <button
                onClick={() => {}}
                className="w-full mt-3 flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors opacity-50 cursor-not-allowed"
              >
                <Scan size={15} />
                Run AI Analysis
              </button>
            )}
          </div>

          {/* Demo field photos */}
          {isDemo && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-amber-500">✦</span>
                <h4 className="font-semibold text-gray-900 text-sm">Or Select Demo Hyderabad Field Photos</h4>
              </div>
              <div className="space-y-2">
                {DEMO_FIELD_PHOTOS.map((photo) => (
                  <button
                    key={photo.id}
                    onClick={() => handleDemoPhotoSelect(photo)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      demoPhotoId === photo.id
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="text-sm font-medium text-gray-900">{photo.label}</div>
                    <div className="text-xs text-gray-500">{photo.sublabel}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right — results panel */}
        <div>
          {!result && !loading && !error && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400 h-full flex flex-col items-center justify-center">
              <Camera size={44} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm font-medium text-gray-500">No Image Analysed Yet</p>
              <p className="text-xs mt-2 text-gray-400 max-w-xs leading-relaxed">
                Upload a site photograph on the left or click a demo sample image to calculate shade coverage, tree foliage, and thermal vulnerability via FastAPI computer vision.
              </p>
            </div>
          )}

          {loading && <LoadingState message="Running AI shade detection analysis…" />}

          {error && !loading && (
            <ErrorState title="Analysis failed" message={error} onRetry={handleAnalyze} />
          )}

          {result && !loading && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* Header */}
              <div className="px-5 py-4 border-b border-gray-100">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xs font-mono text-gray-500">ID: {result.analysis_id}</span>
                  {result._demo && (
                    <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-semibold">
                      SIMULATED RESPONSE
                    </span>
                  )}
                  <div className="ml-auto flex items-center gap-2">
                    <Star size={12} className="text-blue-500" />
                    <span className="text-xs font-semibold text-blue-700">
                      Model Confidence: {Math.round((result.confidence || 0.91) * 100)}%
                    </span>
                  </div>
                </div>
                <h3 className="font-bold text-gray-900">Computer Vision Shade Detection Output</h3>
              </div>

              <div className="p-5 space-y-4">
                {/* Observations grid — fields from backend */}
                <div>
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Observed Infrastructure
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { key: 'vegetation',       label: 'Vegetation' },
                      { key: 'shaded_areas',      label: 'Shaded Areas' },
                      { key: 'sun_exposed_areas', label: 'Sun-Exposed Areas' },
                      { key: 'shelters',          label: 'Shelters' },
                      { key: 'drinking_water',    label: 'Drinking Water' },
                    ].map(({ key, label }) => (
                      <div key={key} className="p-3 rounded-lg border border-gray-100 bg-gray-50">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${result[key]?.visible ? 'bg-green-500' : 'bg-gray-300'}`} />
                          <span className="text-xs font-semibold text-gray-700">{label}</span>
                          <span className={`ml-auto text-xs font-bold ${result[key]?.visible ? 'text-green-700' : 'text-gray-400'}`}>
                            {result[key]?.visible ? 'Visible' : 'Not visible'}
                          </span>
                        </div>
                        {result[key]?.description && (
                          <p className="text-xs text-gray-500 leading-relaxed">{result[key].description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Infrastructure gaps */}
                {result.infrastructure_gaps?.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                      Infrastructure Gaps
                    </div>
                    <ul className="space-y-1">
                      {result.infrastructure_gaps.map((gap, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-red-700">
                          <AlertTriangle size={12} className="flex-shrink-0 mt-0.5 text-red-400" />
                          {gap}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Explanation */}
                {result.explanation && (
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                    <p className="text-xs text-gray-700 leading-relaxed">{result.explanation}</p>
                  </div>
                )}

                {/* Limitations */}
                {result.limitations && (
                  <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
                    <div className="flex items-center gap-2 mb-1">
                      <Info size={12} className="text-amber-500 flex-shrink-0" />
                      <span className="text-xs font-semibold text-amber-800">Limitations</span>
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed">{result.limitations}</p>
                  </div>
                )}

                {result._demo && (
                  <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg text-xs text-blue-700">
                    <Info size={13} className="flex-shrink-0 mt-0.5" />
                    <span>
                      This is an illustrative simulated response. The actual FastAPI computer vision service has not processed this image.
                      Connect the backend to enable real CV analysis.
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
