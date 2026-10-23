import React from 'react'
import { CheckCircle, TrendingUp, DollarSign, Info } from 'lucide-react'

function formatINR(amount) {
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`
  return `₹${amount}`
}

export function RecommendationCard({ item }) {
  const benefitColor =
    item.benefit_score >= 80
      ? 'text-green-600 bg-green-50'
      : item.benefit_score >= 60
      ? 'text-amber-600 bg-amber-50'
      : 'text-blue-600 bg-blue-50'

  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle size={15} className="text-green-500 flex-shrink-0" />
            <h4 className="font-medium text-gray-900 text-sm">{item.intervention}</h4>
          </div>
          {item.description && (
            <p className="text-xs text-gray-500 mb-2 ml-5">{item.description}</p>
          )}
          <div className="flex flex-wrap gap-3 ml-5">
            <div className="text-xs text-gray-600">
              <span className="font-medium">Qty:</span> {item.quantity}
            </div>
            <div className="text-xs text-gray-600">
              <span className="font-medium">Unit:</span> {formatINR(item.unit_cost)}
            </div>
            <div className="text-xs font-semibold text-gray-800">
              Total: {formatINR(item.total_cost)}
            </div>
          </div>
        </div>
        <div className={`text-xs font-semibold px-2 py-1 rounded-lg flex-shrink-0 ${benefitColor}`}>
          <div className="flex items-center gap-1">
            <TrendingUp size={11} />
            <span>{item.benefit_score}</span>
          </div>
          <div className="text-center text-gray-400 font-normal">benefit</div>
        </div>
      </div>
    </div>
  )
}

export function BudgetSummary({ result }) {
  if (!result) return null

  const utilizationColor =
    result.utilization_pct >= 90
      ? 'bg-green-500'
      : result.utilization_pct >= 70
      ? 'bg-blue-500'
      : 'bg-amber-500'

  return (
    <div className="card p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Budget Summary</h3>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Total Budget</div>
          <div className="text-lg font-bold text-gray-900">{formatINR(result.budget)}</div>
        </div>
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Allocated</div>
          <div className="text-lg font-bold text-green-700">{formatINR(result.total_cost)}</div>
        </div>
        <div className="text-center p-3 bg-blue-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Remaining</div>
          <div className="text-lg font-bold text-blue-700">{formatINR(result.remaining_budget)}</div>
        </div>
      </div>

      <div className="mb-2">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Budget Utilization</span>
          <span className="font-medium text-gray-700">{result.utilization_pct}%</span>
        </div>
        <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${utilizationColor}`}
            style={{ width: `${Math.min(result.utilization_pct, 100)}%` }}
          />
        </div>
      </div>

      {result.note && (
        <div className="flex items-start gap-2 mt-3 p-2.5 bg-amber-50 rounded-lg text-xs text-amber-700">
          <Info size={13} className="flex-shrink-0 mt-0.5" />
          <span>{result.note}</span>
        </div>
      )}
    </div>
  )
}
