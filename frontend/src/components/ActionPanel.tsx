import { useState } from 'react'
import { Action, Holding } from '../types/game'
import { useGameStore } from '../store/gameStore'

interface ActionPanelProps {
  onPerformAction: (action: Action) => void
  selectedHolding: Holding | null
}

export default function ActionPanel({ onPerformAction, selectedHolding }: ActionPanelProps) {
  const { gameState, validActions } = useGameStore()
  const [soldiersToCommit, setSoldiersToCommit] = useState(200)

  if (!gameState) return null

  const currentPlayer = gameState.players[gameState.current_player_idx]
  if (!currentPlayer) return null

  const isHumanTurn = currentPlayer.player_type === 'human'
  const isPlayerTurn = gameState.phase === 'player_turn'

  // Group actions by type
  const groupedActions = validActions.reduce((acc, action) => {
    if (!acc[action.action_type]) {
      acc[action.action_type] = []
    }
    acc[action.action_type].push(action)
    return acc
  }, {} as Record<string, Action[]>)

  const getActionLabel = (actionType: string): string => {
    const labels: Record<string, string> = {
      draw_card: '📜 Draw Card',
      move: '🚶 Move',
      recruit: '⚔️ Recruit',
      build_fortification: '🏰 Build Fortification (10G)',
      claim_title: '👑 Claim Title',
      attack: '⚔️ Attack',
      fake_claim: '📝 Fabricate Claim (35G)',
      play_card: '🃏 Play Card',
      end_turn: '⏭️ End Turn',
    }
    return labels[actionType] || actionType
  }

  const handleActionClick = (action: Action) => {
    // For attack actions, add soldier count
    if (action.action_type === 'attack') {
      onPerformAction({
        ...action,
        soldiers_count: soldiersToCommit,
      })
    } else {
      onPerformAction(action)
    }
  }

  // Get attack actions for selected holding
  const attackActionsForSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'attack' && a.target_holding_id === selectedHolding.id
      )
    : []

  // Get fake claim actions for selected holding
  const fakeClaimForSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'fake_claim' && a.target_holding_id === selectedHolding.id
      )
    : []

  return (
    <div className="card-parchment rounded-lg p-4 h-full flex flex-col">
      {/* Header */}
      <div className="mb-4">
        <h2 className="font-medieval text-xl text-medieval-bronze">
          {isPlayerTurn ? 'Actions' : 'Waiting...'}
        </h2>
        
        {isPlayerTurn && (
          <div className="flex items-center gap-2 mt-2">
            <span className="text-sm text-medieval-stone">
              Victory at {gameState.victory_threshold} VP
            </span>
          </div>
        )}
      </div>

      {/* Phase indicator */}
      <div className="mb-4 p-2 bg-parchment-100 rounded text-center">
        <span className="text-sm text-medieval-stone">
          Round {gameState.current_round} •{' '}
          {gameState.phase.replace('_', ' ').toUpperCase()}
        </span>
        {gameState.war_fought_this_turn && (
          <span className="text-xs text-medieval-crimson block mt-1">
            War already fought this turn
          </span>
        )}
      </div>

      {/* Non-human turn message */}
      {!isHumanTurn && isPlayerTurn && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-2 border-medieval-gold border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-medieval-stone">
              {currentPlayer.name} is thinking...
            </p>
          </div>
        </div>
      )}

      {/* Action buttons for human player */}
      {isHumanTurn && isPlayerTurn && (
        <div className="flex-1 overflow-y-auto space-y-3">
          {/* Selected holding attack */}
          {selectedHolding && attackActionsForSelected.length > 0 && (
            <div className="p-3 bg-red-50 rounded border border-red-200">
              <h3 className="font-medieval text-sm text-medieval-crimson mb-2">
                Attack {selectedHolding.name}
              </h3>
              
              <div className="mb-3">
                <label className="text-xs text-medieval-stone block mb-1">
                  Soldiers to commit (min 200):
                </label>
                <input
                  type="range"
                  min={200}
                  max={currentPlayer.soldiers}
                  step={100}
                  value={soldiersToCommit}
                  onChange={(e) => setSoldiersToCommit(Number(e.target.value))}
                  className="w-full"
                />
                <div className="text-center font-medieval text-lg text-medieval-crimson">
                  {soldiersToCommit} soldiers
                </div>
              </div>
              
              <button
                onClick={() => handleActionClick(attackActionsForSelected[0])}
                className="btn-crimson w-full py-2 rounded"
              >
                Launch Attack
              </button>
            </div>
          )}

          {/* Selected holding fake claim */}
          {selectedHolding && fakeClaimForSelected.length > 0 && (
            <div className="p-3 bg-yellow-50 rounded border border-yellow-200">
              <h3 className="font-medieval text-sm text-medieval-gold mb-2">
                Fabricate Claim on {selectedHolding.name}
              </h3>
              <button
                onClick={() => handleActionClick(fakeClaimForSelected[0])}
                className="btn-medieval w-full py-2 rounded"
              >
                Pay 35 Gold to Claim
              </button>
            </div>
          )}

          {/* Draw card */}
          {groupedActions.draw_card && (
            <button
              onClick={() => handleActionClick(groupedActions.draw_card[0])}
              className="w-full p-3 bg-parchment-100 hover:bg-parchment-200 rounded transition-colors text-left"
            >
              <span className="font-medieval text-medieval-bronze">
                {getActionLabel('draw_card')}
              </span>
              {!gameState.card_drawn_this_turn && (
                <span className="text-xs text-medieval-stone block">
                  Once per turn (max 4 towns to draw)
                </span>
              )}
            </button>
          )}

          {/* Play cards from hand */}
          {groupedActions.play_card && groupedActions.play_card.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-medieval-stone">Play Card:</span>
              {groupedActions.play_card.map((action, idx) => {
                const card = gameState.cards[action.card_id || '']
                return (
                  <button
                    key={idx}
                    onClick={() => handleActionClick(action)}
                    className="w-full p-2 bg-purple-50 hover:bg-purple-100 rounded transition-colors text-left border border-purple-200"
                  >
                    <span className="font-medieval text-sm text-purple-800">
                      🃏 {card?.name || 'Unknown Card'}
                    </span>
                    {card?.description && (
                      <span className="text-xs text-medieval-stone block truncate">
                        {card.description}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Claim title */}
          {groupedActions.claim_title && (
            <div className="space-y-1">
              <span className="text-xs text-medieval-stone">Claim Title:</span>
              {groupedActions.claim_title.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleActionClick(action)}
                  className="w-full p-2 bg-yellow-50 hover:bg-yellow-100 rounded transition-colors text-left border border-yellow-200"
                >
                  <span className="font-medieval text-sm text-medieval-gold">
                    👑 {action.target_holding_id}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Build fortification */}
          {groupedActions.build_fortification && (
            <div className="space-y-1">
              <span className="text-xs text-medieval-stone">
                Fortify (10 Gold, {2 - currentPlayer.fortifications_placed} remaining):
              </span>
              {groupedActions.build_fortification.slice(0, 5).map((action, idx) => {
                const holding = gameState.holdings.find(h => h.id === action.target_holding_id)
                return (
                  <button
                    key={idx}
                    onClick={() => handleActionClick(action)}
                    className="w-full p-2 bg-parchment-100 hover:bg-parchment-200 rounded transition-colors text-left"
                  >
                    <span className="text-sm text-medieval-bronze">
                      🏰 {holding?.name || action.target_holding_id}
                    </span>
                  </button>
                )
              })}
            </div>
          )}

          {/* End turn */}
          {groupedActions.end_turn && (
            <button
              onClick={() => handleActionClick(groupedActions.end_turn[0])}
              className="w-full p-3 bg-medieval-bronze hover:bg-medieval-bronze/90 text-white rounded transition-colors font-medieval"
            >
              End Turn
            </button>
          )}
        </div>
      )}

      {/* Game over state */}
      {gameState.phase === 'game_over' && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h3 className="font-medieval text-2xl text-medieval-gold mb-2">
              Game Over!
            </h3>
            <p className="text-medieval-stone">
              Check the final scores
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
