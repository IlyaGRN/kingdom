import { useState } from 'react'
import { AIDecisionLog, AIDecisionLogEntry, CombatResult } from '../types/game'

interface CombatLogEntry {
  combat: CombatResult
  timestamp: number
  attackerName: string
  defenderName: string | null
  holdingName: string
}

interface AIDecisionPanelProps {
  logs: AIDecisionLog[]
  combatLogs: CombatLogEntry[]
  onClear: () => void
  onClearCombats: () => void
}

export default function AIDecisionPanel({ logs, combatLogs, onClear, onClearCombats }: AIDecisionPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [expandedLogIdx, setExpandedLogIdx] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'decisions' | 'combats'>('combats')

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

  const formatTimestamp = (ts: number) => {
    try {
      const date = new Date(ts)
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      })
    } catch {
      return 'Unknown'
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
            AI Activity Log
          </span>
          <span className="bg-medieval-bronze text-medieval-navy px-2 py-0.5 rounded text-xs font-bold">
            {logs.length + combatLogs.length}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Tab buttons */}
          {isExpanded && (
            <div className="flex gap-1 mr-4">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setActiveTab('combats')
                }}
                className={`text-xs px-3 py-1 rounded transition-colors ${
                  activeTab === 'combats' 
                    ? 'bg-medieval-crimson text-white' 
                    : 'bg-white/20 hover:bg-white/30'
                }`}
              >
                ⚔️ Wars ({combatLogs.length})
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setActiveTab('decisions')
                }}
                className={`text-xs px-3 py-1 rounded transition-colors ${
                  activeTab === 'decisions' 
                    ? 'bg-medieval-bronze text-medieval-navy' 
                    : 'bg-white/20 hover:bg-white/30'
                }`}
              >
                🤔 Decisions ({logs.length})
              </button>
            </div>
          )}
          
          {(logs.length > 0 || combatLogs.length > 0) && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                if (activeTab === 'decisions') onClear()
                else onClearCombats()
              }}
              className="text-xs px-2 py-1 bg-medieval-crimson hover:bg-red-700 rounded transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Expandable content */}
      {isExpanded && (
        <div className="bg-parchment-100 border-t-2 border-medieval-bronze max-h-64 overflow-y-auto">
          {/* Combat Logs Tab */}
          {activeTab === 'combats' && (
            combatLogs.length === 0 ? (
              <div className="p-4 text-center text-medieval-stone text-sm">
                No battles have occurred yet. Watch AI players wage war!
              </div>
            ) : (
              <div className="divide-y divide-parchment-300">
                {[...combatLogs].reverse().map((entry, idx) => {
                  if (!entry || !entry.combat) {
                    return null
                  }
                  
                  const { combat, timestamp, attackerName, defenderName, holdingName } = entry
                  const isAttackerWin = combat.attacker_won
                  
                  return (
                    <div key={idx} className="px-4 py-3 hover:bg-parchment-200 transition-colors">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-xs text-medieval-stone w-20 flex-shrink-0">
                          {formatTimestamp(timestamp)}
                        </span>
                        <span className={`font-medieval text-sm ${isAttackerWin ? 'text-green-700' : 'text-medieval-crimson'}`}>
                          {attackerName}
                        </span>
                        <span className="text-medieval-stone">⚔️</span>
                        <span className={`font-medieval text-sm ${!isAttackerWin ? 'text-green-700' : 'text-medieval-crimson'}`}>
                          {defenderName || 'Undefended'}
                        </span>
                        <span className="text-xs text-medieval-stone">for</span>
                        <span className="font-medieval text-medieval-bronze text-sm">
                          {holdingName}
                        </span>
                      </div>
                      
                      {/* Combat details */}
                      <div className="flex items-center gap-4 text-xs">
                        <div className={`flex items-center gap-2 px-2 py-1 rounded ${isAttackerWin ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          <span className="font-bold">{attackerName}:</span>
                          <span>🎲{combat.attacker_roll}</span>
                          <span>⚔️{combat.attacker_soldiers_committed}</span>
                          <span>=</span>
                          <span className="font-bold">{combat.attacker_strength}</span>
                          <span className="text-red-600">(-{combat.attacker_losses})</span>
                        </div>
                        
                        <span className="text-lg">{isAttackerWin ? '>' : '<'}</span>
                        
                        <div className={`flex items-center gap-2 px-2 py-1 rounded ${!isAttackerWin ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          <span className="font-bold">{defenderName || 'Garrison'}:</span>
                          <span>🎲{combat.defender_roll}</span>
                          <span>🛡️{combat.defender_soldiers_committed}</span>
                          <span>=</span>
                          <span className="font-bold">{combat.defender_strength}</span>
                          <span className="text-red-600">(-{combat.defender_losses})</span>
                        </div>
                        
                        <span className={`ml-auto px-2 py-1 rounded font-bold ${isAttackerWin ? 'bg-green-600 text-white' : 'bg-blue-600 text-white'}`}>
                          {isAttackerWin ? `${attackerName} WINS!` : `${defenderName || 'Defense'} HOLDS!`}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          )}
          
          {/* Decisions Tab */}
          {activeTab === 'decisions' && (
            logs.length === 0 ? (
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
            )
          )}
        </div>
      )}
    </div>
  )
}

