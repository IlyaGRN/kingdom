import { useState } from 'react'
import { AIDecisionLog, AIDecisionLogEntry } from '../types/game'

interface AIDecisionPanelProps {
  logs: AIDecisionLog[]
  onClear: () => void
}

export default function AIDecisionPanel({ logs, onClear }: AIDecisionPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [expandedLogIdx, setExpandedLogIdx] = useState<number | null>(null)

  const getStatusColor = (status: AIDecisionLogEntry['status']) => {
    switch (status) {
      case 'chosen':
        return 'text-green-600 bg-green-50'
      case 'skipped':
        return 'text-yellow-600 bg-yellow-50'
      case 'unavailable':
        return 'text-gray-500 bg-gray-50'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: AIDecisionLogEntry['status']) => {
    switch (status) {
      case 'chosen':
        return '✓'
      case 'skipped':
        return '○'
      case 'unavailable':
        return '✗'
      default:
        return '?'
    }
  }

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      })
    } catch {
      return timestamp
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40">
      {/* Header bar - always visible */}
      <div 
        className="bg-medieval-navy text-white px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-opacity-90 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">
            {isExpanded ? '▼' : '▲'}
          </span>
          <span className="font-medieval text-sm">
            AI Decision Log
          </span>
          <span className="bg-medieval-bronze text-medieval-navy px-2 py-0.5 rounded text-xs font-bold">
            {logs.length}
          </span>
        </div>
        
        {logs.length > 0 && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onClear()
            }}
            className="text-xs px-2 py-1 bg-medieval-crimson hover:bg-red-700 rounded transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Expandable content */}
      {isExpanded && (
        <div className="bg-parchment-100 border-t-2 border-medieval-bronze max-h-64 overflow-y-auto">
          {logs.length === 0 ? (
            <div className="p-4 text-center text-medieval-stone text-sm">
              No AI decisions logged yet. Wait for AI players to take their turns.
            </div>
          ) : (
            <div className="divide-y divide-parchment-300">
              {/* Show logs in reverse order (newest first) */}
              {[...logs].reverse().map((log, idx) => {
                const originalIdx = logs.length - 1 - idx
                const isLogExpanded = expandedLogIdx === originalIdx
                
                return (
                  <div key={originalIdx} className="hover:bg-parchment-200 transition-colors">
                    {/* Log summary row */}
                    <div 
                      className="px-4 py-2 flex items-center gap-4 cursor-pointer"
                      onClick={() => setExpandedLogIdx(isLogExpanded ? null : originalIdx)}
                    >
                      <span className="text-xs text-medieval-stone w-20 flex-shrink-0">
                        {formatTime(log.timestamp)}
                      </span>
                      <span className="font-medieval text-medieval-bronze text-sm w-28 flex-shrink-0">
                        {log.player_name}
                      </span>
                      <span className="text-sm text-green-700 font-mono bg-green-50 px-2 py-0.5 rounded">
                        {log.chosen_action}
                      </span>
                      <span className="text-xs text-medieval-stone flex-1 truncate">
                        {log.reason}
                      </span>
                      <span className="text-medieval-stone">
                        {isLogExpanded ? '−' : '+'}
                      </span>
                    </div>

                    {/* Expanded detail view */}
                    {isLogExpanded && (
                      <div className="px-4 pb-3 bg-white/50">
                        <div className="text-xs text-medieval-stone mb-2">
                          Valid actions: {log.valid_actions.join(', ')}
                        </div>
                        <div className="space-y-1">
                          {log.considered.map((entry, entryIdx) => (
                            <div 
                              key={entryIdx}
                              className={`flex items-start gap-2 text-xs p-1.5 rounded ${getStatusColor(entry.status)}`}
                            >
                              <span className="font-bold w-4 flex-shrink-0">
                                {getStatusIcon(entry.status)}
                              </span>
                              <span className="font-mono w-24 flex-shrink-0">
                                {entry.action}
                              </span>
                              <span className="flex-1">
                                {entry.reason}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

