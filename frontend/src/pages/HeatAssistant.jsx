import React, { useState, useRef, useEffect } from 'react'
import {
  MessageCircle, Send, RefreshCw, Info, AlertTriangle,
  Trash2, ChevronRight, Bot, User,
} from 'lucide-react'
import { chatWithAI } from '../services/api'

const LANGUAGES = [
  { value: 'english', label: 'English' },
  { value: 'hindi',   label: 'हिन्दी (Hindi)' },
  { value: 'telugu',  label: 'తెలుగు (Telugu)' },
]

const SUGGESTED_QUESTIONS = [
  'How can I protect myself during extreme heat?',
  'What are the warning signs of heat exhaustion?',
  'How can outdoor workers reduce heat exposure?',
  'What should I do if someone shows signs of heatstroke?',
  'How can I find cooling facilities nearby?',
  'How can a community reduce heat exposure within a limited budget?',
]

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mb-0.5 ${
        isUser ? 'bg-blue-600' : 'bg-gray-700'
      }`}>
        {isUser
          ? <User size={13} className="text-white" />
          : <Bot size={13} className="text-white" />
        }
      </div>
      {/* Bubble */}
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
        isUser
          ? 'bg-blue-600 text-white rounded-br-sm'
          : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
      }`}>
        {msg.error ? (
          <div className="flex items-start gap-2">
            <AlertTriangle size={13} className="text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-600">{msg.text}</p>
          </div>
        ) : (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
        )}
        {msg.disclaimer && (
          <p className="text-xs mt-2 opacity-60 italic leading-relaxed border-t border-current/20 pt-2">
            {msg.disclaimer}
          </p>
        )}
        <p className={`text-xs mt-1 ${isUser ? 'text-blue-200' : 'text-gray-400'}`}>
          {msg.time}
        </p>
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2">
      <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 bg-gray-700">
        <Bot size={13} className="text-white" />
      </div>
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function HeatAssistant() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      text: "Hello! I'm the ChhayaRakshak Heat Protection Assistant. I can help you understand heat risks, explain heat safety precautions, and guide you to the right features of this platform.\n\nPlease note: I provide general awareness guidance only — not medical advice. For emergencies, seek urgent medical assistance immediately (India: 112 / 108).",
      time: now(),
    },
  ])
  const [input, setInput] = useState('')
  const [language, setLanguage] = useState('english')
  const [loading, setLoading] = useState(false)
  const [retryQuestion, setRetryQuestion] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (question) => {
    const q = question || input.trim()
    if (!q || loading) return

    const userMsg = { id: Date.now(), role: 'user', text: q, time: now() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setRetryQuestion(null)
    setLoading(true)

    try {
      const res = await chatWithAI(q, language)
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: res.answer || res,
        disclaimer: res.disclaimer,
        time: now(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      setRetryQuestion(q)
      const errMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: err.message || 'The assistant is temporarily unavailable. Please try again.',
        error: true,
        time: now(),
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleClear = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        text: "Chat cleared. How can I help you with heat safety today?",
        time: now(),
      },
    ])
    setRetryQuestion(null)
    inputRef.current?.focus()
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-gray-900">Heat Protection Assistant</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Ask about heat safety, heat exhaustion warning signs, protection strategies, or how to use this platform.
        Available in English, Hindi, and Telugu.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* ── Sidebar: suggested questions + controls ── */}
        <div className="lg:col-span-1 space-y-4">
          {/* Language selector */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Language</h3>
            <div className="space-y-1.5">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.value}
                  onClick={() => setLanguage(lang.value)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                    language === lang.value
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          </div>

          {/* Suggested questions */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Suggested Questions</h3>
            <div className="space-y-1.5">
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  disabled={loading}
                  className="w-full text-left flex items-start gap-2 px-3 py-2.5 rounded-lg border border-gray-100 hover:border-blue-300 hover:bg-blue-50 text-xs text-gray-700 transition-all disabled:opacity-50"
                >
                  <ChevronRight size={12} className="flex-shrink-0 mt-0.5 text-blue-400" />
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Clear chat */}
          <button
            onClick={handleClear}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <Trash2 size={13} />
            Clear Chat
          </button>

          {/* Disclaimer */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
            <div className="flex items-start gap-2">
              <Info size={12} className="text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700 leading-relaxed">
                For general awareness only — not medical advice. Seek urgent medical assistance for emergencies.
              </p>
            </div>
          </div>
        </div>

        {/* ── Chat area ── */}
        <div className="lg:col-span-3 flex flex-col bg-gray-50 rounded-xl border border-gray-200 overflow-hidden" style={{ minHeight: '520px' }}>
          {/* Chat header */}
          <div className="flex items-center gap-3 px-5 py-3 bg-white border-b border-gray-200">
            <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center">
              <Bot size={15} className="text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">ChhayaRakshak Assistant</div>
              <div className="text-xs text-gray-500">Heat safety · Urban resilience · Platform guide</div>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400" />
              <span className="text-xs text-gray-500">Online</span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Retry bar */}
          {retryQuestion && !loading && (
            <div className="px-5 py-2 bg-amber-50 border-t border-amber-100 flex items-center gap-2">
              <AlertTriangle size={13} className="text-amber-500 flex-shrink-0" />
              <span className="text-xs text-amber-700 flex-1">Response failed.</span>
              <button
                onClick={() => sendMessage(retryQuestion)}
                className="text-xs text-amber-800 font-semibold underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Input area */}
          <div className="px-5 py-4 bg-white border-t border-gray-200">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about heat safety, precautions, warning signs…"
                rows={2}
                disabled={loading}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50"
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                aria-label="Send message"
              >
                {loading
                  ? <RefreshCw size={16} className="animate-spin" />
                  : <Send size={16} />
                }
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1.5">
              Press Enter to send · Shift+Enter for new line ·{' '}
              Language: <strong>{LANGUAGES.find((l) => l.value === language)?.label}</strong>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
