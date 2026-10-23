
import axios from 'axios'

// ─── Backend URLs ────────────────────────────────────────────────────────────
const MAIN_API_URL =
  import.meta.env.VITE_MAIN_API_URL || 'http://127.0.0.1:8001'

const WEATHER_API_URL =
  import.meta.env.VITE_WEATHER_API_URL || 'http://127.0.0.1:8000'

const AI_API_URL =
  import.meta.env.VITE_AI_API_URL || 'http://127.0.0.1:8002'

// ─── Data Mode ──────────────────────────────────────────────────────────────
export const isDemo = import.meta.env.VITE_USE_DEMO_DATA === 'true'

// ─── Axios Instances ────────────────────────────────────────────────────────
// Main backend: assessments, AI chat, budget optimization
const apiClient = axios.create({
  baseURL: MAIN_API_URL,
  timeout: 15000,
})

// Weather-risk backend: locations and weather
export const weatherApiClient = axios.create({
  baseURL: WEATHER_API_URL,
  timeout: 15000,
})

// AI intelligence backend: image analysis
export const aiApiClient = axios.create({
  baseURL: AI_API_URL,
  timeout: 30000,
})

// ─── Response Interceptors ──────────────────────────────────────────────────
const handleResponse = (response) => response.data

const handleError = (error) => {
  const message =
    error.response?.data?.detail ||
    error.response?.data?.message ||
    error.message ||
    'An unexpected error occurred'

  return Promise.reject(new Error(message))
}

apiClient.interceptors.response.use(handleResponse, handleError)
weatherApiClient.interceptors.response.use(handleResponse, handleError)
aiApiClient.interceptors.response.use(handleResponse, handleError)

// ─── Health ─────────────────────────────────────────────────────────────────
export const checkHealth = () => apiClient.get('/health')

// ─── Locations ──────────────────────────────────────────────────────────────
export const fetchLocations = () =>
  weatherApiClient.get('/api/locations')

// ─── Weather ────────────────────────────────────────────────────────────────
export const fetchWeather = (lat, lon) =>
  weatherApiClient.get('/api/weather', {
    params: { lat, lon },
  })

// ─── Assessments ────────────────────────────────────────────────────────────
export const submitAssessment = (payload) =>
  apiClient.post('/api/assessments', payload)

// Meghana's Weather Risk Assessment
export const submitWeatherAssessment = (payload) =>
  weatherApiClient.post('/api/assessments', payload)
// ─── Image Analysis ─────────────────────────────────────────────────────────
export const analyzeImage = (file, metadata = {}) => {
  const formData = new FormData()

  formData.append('file', file)

  Object.entries(metadata).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, String(value))
    }
  })

  // Send image requests to the AI backend on port 8002.
  return aiApiClient.post('/api/analyze-image', formData)
}

// ─── AI Chat ─────────────────────────────────────────────────────────────────
export const chatWithAI = (question, language = 'english') =>
  apiClient.post('/api/chat', {
    question,
    language,
  })

// ─── Budget Optimizer ───────────────────────────────────────────────────────
export const optimizeBudget = (payload) =>
  apiClient.post('/api/optimize', payload)

// ─── Personal Heat Assessment ───────────────────────────────────────────────
export const personalHeatAssessment = (payload) =>
  apiClient.post('/api/personal-assessment', payload)

// ─── Analyze and Optimize (image + budget) ──────────────────────────────────
export const analyzeAndOptimize = (file, budget, locationName) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('budget', String(budget))
  formData.append('location_name', locationName)
  return apiClient.post('/api/analyze-and-optimize', formData)
}

// ─── Default Export ─────────────────────────────────────────────────────────
export default apiClient
