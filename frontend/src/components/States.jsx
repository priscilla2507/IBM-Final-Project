import React from 'react'
import { Loader2 } from 'lucide-react'

export function LoadingState({ message = 'Loading…', fullPage = false }) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3 text-gray-500">
      <Loader2 size={28} className="animate-spin text-blue-500" />
      <p className="text-sm">{message}</p>
    </div>
  )

  if (fullPage) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[400px]">
        {content}
      </div>
    )
  }

  return (
    <div className="card p-10 flex items-center justify-center">
      {content}
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="card p-8 text-center">
      <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-3">
        <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      {message && <p className="text-sm text-gray-500 mb-4">{message}</p>}
      {onRetry && (
        <button onClick={onRetry} className="btn-primary text-sm">
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title = 'No data', message, icon: Icon, action }) {
  return (
    <div className="card p-10 text-center">
      {Icon && (
        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
          <Icon size={22} className="text-gray-400" />
        </div>
      )}
      <h3 className="font-semibold text-gray-700 mb-1">{title}</h3>
      {message && <p className="text-sm text-gray-400 mb-4">{message}</p>}
      {action}
    </div>
  )
}
