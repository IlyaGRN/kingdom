import { Action, Holding, COMBAT_CARD_EFFECTS } from '../types/game'
import { useGameStore } from '../store/gameStore'

interface ActionPanelProps {
  onPerformAction: (action: Action) => void
  selectedHolding: Holding | null
  onOpenCombatPrep: (holding: Holding) => void
}

export default function ActionPanel({ onPerformAction, selectedHolding, onOpenCombatPrep }: ActionPanelProps) {
  const { gameState, validActions } = useGameStore()

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

  const handleActionClick = (action: Action) => {
    onPerformAction(action)
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

  // Get claim town actions for selected holding (10g to capture unowned with claim)
  const claimTownForSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'claim_town' && a.target_holding_id === selectedHolding.id
      )
    : []

  // Get claim cards that can be played on the selected holding
  const claimCardsForSelected = selectedHolding
    ? (groupedActions.play_card || []).filter(action => {
        const card = gameState.cards[action.card_id || '']
        if (!card || card.card_type !== 'claim') return false
        
        // Check if the card's county matches the selected holding
        if (card.effect === 'claim_x' && selectedHolding.county === 'X') return true
        if (card.effect === 'claim_u' && selectedHolding.county === 'U') return true
        if (card.effect === 'claim_v' && selectedHolding.county === 'V') return true
        if (card.effect === 'claim_q' && selectedHolding.county === 'Q') return true
        if (card.effect === 'ultimate_claim') return true
        if (card.effect === 'duchy_claim') return true
        
        return false
      })
    : []

  // Get non-claim, non-combat play_card actions (bonus cards that aren't used in combat)
  const nonClaimPlayCards = (groupedActions.play_card || []).filter(action => {
    const card = gameState.cards[action.card_id || '']
    if (!card || card.card_type === 'claim') return false
    // Filter out combat cards - they're used in combat prep modal
    if (COMBAT_CARD_EFFECTS.includes(card.effect)) return false
    return true
  })

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
          {/* Selected holding attack - opens combat prep modal */}
          {selectedHolding && attackActionsForSelected.length > 0 && (
            <div className="p-3 bg-red-50 rounded border border-red-200">
              <h3 className="font-medieval text-sm text-medieval-crimson mb-2">
                Attack {selectedHolding.name}
              </h3>
              <p className="text-xs text-medieval-stone mb-2">
                You have a valid claim on this territory!
              </p>
              <button
                onClick={() => onOpenCombatPrep(selectedHolding)}
                className="btn-crimson w-full py-2 rounded"
              >
                ⚔️ Prepare Attack
              </button>
            </div>
          )}

          {/* Selected holding claim town (10g capture with valid claim) */}
          {selectedHolding && claimTownForSelected.length > 0 && (
            <div className="p-3 bg-green-50 rounded border border-green-200">
              <h3 className="font-medieval text-sm text-green-700 mb-2">
                Capture {selectedHolding.name}
              </h3>
              <p className="text-xs text-medieval-stone mb-2">
                You have a valid claim on this unowned town!
              </p>
              <button
                onClick={() => handleActionClick(claimTownForSelected[0])}
                className="w-full py-2 rounded bg-green-600 hover:bg-green-700 text-white font-medieval"
              >
                Pay 10 Gold to Capture
              </button>
            </div>
          )}

          {/* Show hint when player has claim on unowned town but not enough gold */}
          {selectedHolding && 
           selectedHolding.owner_id === null && 
           (currentPlayer.claims ?? []).includes(selectedHolding.id) && 
           claimTownForSelected.length === 0 && 
           currentPlayer.gold < 10 && (
            <div className="p-3 bg-yellow-50 rounded border border-yellow-200">
              <h3 className="font-medieval text-sm text-yellow-700 mb-2">
                Cannot Capture {selectedHolding.name}
              </h3>
              <p className="text-xs text-medieval-stone">
                You have a valid claim but need <span className="font-bold text-yellow-700">10 gold</span> to capture. 
                (Current: {currentPlayer.gold} gold)
              </p>
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
                Pay 35 Gold to Fabricate Claim
              </button>
            </div>
          )}

          {/* Cards are now auto-drawn at the beginning of each turn */}

          {/* Play claim cards on selected holding */}
          {selectedHolding && claimCardsForSelected.length > 0 && (
            <div className="p-3 bg-purple-50 rounded border border-purple-200">
              <h3 className="font-medieval text-sm text-purple-800 mb-2">
                Claim {selectedHolding.name}
              </h3>
              {claimCardsForSelected.map((action, idx) => {
                const card = gameState.cards[action.card_id || '']
                return (
                  <button
                    key={idx}
                    onClick={() => handleActionClick({
                      ...action,
                      target_holding_id: selectedHolding.id
                    })}
                    className="w-full p-2 mb-1 bg-purple-100 hover:bg-purple-200 rounded transition-colors text-left"
                  >
                    <span className="font-medieval text-sm text-purple-800">
                      🃏 Use {card?.name || 'Claim Card'}
                    </span>
                  </button>
                )
              })}
            </div>
          )}

          {/* Play non-claim cards from hand (bonus cards) */}
          {nonClaimPlayCards.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-medieval-stone">Play Card:</span>
              {nonClaimPlayCards.map((action, idx) => {
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

          {/* Show claim cards in hand (hint to select a town) */}
          {!selectedHolding && (groupedActions.play_card || []).some(a => {
            const card = gameState.cards[a.card_id || '']
            return card && card.card_type === 'claim'
          }) && (
            <div className="p-2 bg-purple-50/50 rounded border border-purple-100 text-center">
              <span className="text-xs text-purple-600">
                📍 Select a town on the board to use your claim cards
              </span>
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
                Fortify (10 Gold, {4 - (currentPlayer.fortifications_placed || 0)} remaining):
              </span>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {groupedActions.build_fortification.map((action, idx) => {
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
            </div>
          )}

          {/* Relocate fortification (only when all 4 placed) */}
          {groupedActions.relocate_fortification && (
            <div className="space-y-1">
              <span className="text-xs text-medieval-stone">
                Relocate Fortification (all 4 placed):
              </span>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {groupedActions.relocate_fortification.map((action, idx) => {
                  const source = gameState.holdings.find(h => h.id === action.source_holding_id)
                  const target = gameState.holdings.find(h => h.id === action.target_holding_id)
                  return (
                    <button
                      key={idx}
                      onClick={() => handleActionClick(action)}
                      className="w-full p-2 bg-blue-50 hover:bg-blue-100 rounded transition-colors text-left border border-blue-200"
                    >
                      <span className="text-sm text-blue-800">
                        🔄 {source?.name} → {target?.name}
                      </span>
                    </button>
                  )
                })}
              </div>
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
