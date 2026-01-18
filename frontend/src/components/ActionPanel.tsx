import { Action, Holding, COMBAT_CARD_EFFECTS, Player, CardEffect } from '../types/game'
import { useGameStore } from '../store/gameStore'

interface ActionPanelProps {
  onPerformAction: (action: Action) => void
  selectedHolding: Holding | null
  onOpenCombatPrep: (holding: Holding) => void
}

/**
 * Check if a holding is within the player's domain (making its owner a vassal).
 * Players cannot attack/claim holdings in their domain without VASSAL_REVOLT.
 */
function isHoldingInDomain(player: Player, holding: Holding): boolean {
  // King controls the entire realm
  if (player.is_king) {
    return true
  }
  
  // Duke controls their duchy (both counties)
  for (const duchy of player.duchies || []) {
    let duchyCounties: string[] = []
    if (duchy === 'XU') {
      duchyCounties = ['X', 'U']
    } else if (duchy === 'QV') {
      duchyCounties = ['Q', 'V']
    }
    
    if (holding.county && duchyCounties.includes(holding.county)) {
      return true
    }
    if (holding.duchy === duchy) {
      return true
    }
  }
  
  // Count controls their county
  if (holding.county && (player.counties || []).includes(holding.county)) {
    return true
  }
  
  return false
}

/**
 * Check if player can attack a holding (considering vassal protection).
 */
function canAttackHolding(player: Player, holding: Holding): boolean {
  // Can't attack your own holdings
  if (holding.owner_id === player.id) {
    return false
  }
  
  // If holding is in player's domain, need Vassal Revolt to attack
  if (isHoldingInDomain(player, holding)) {
    const hasVassalRevolt = (player.active_effects || []).includes('vassal_revolt' as CardEffect)
    if (!hasVassalRevolt) {
      return false
    }
  }
  
  return true
}

export default function ActionPanel({ onPerformAction, selectedHolding, onOpenCombatPrep }: ActionPanelProps) {
  const { gameState, validActions } = useGameStore()

  if (!gameState) return null

  const currentPlayer = gameState.players[gameState.current_player_idx]
  if (!currentPlayer) return null

  const isHumanTurn = currentPlayer.player_type === 'human'
  const isPlayerTurn = gameState.phase === 'player_turn'
  
  // Check if selected holding is in player's domain (vassal protection)
  const selectedIsInDomain = selectedHolding ? isHoldingInDomain(currentPlayer, selectedHolding) : false
  const canAttackSelected = selectedHolding ? canAttackHolding(currentPlayer, selectedHolding) : false

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

  // Get fake claim actions for selected holding (check if action exists for valid action)
  const fakeClaimForSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'fake_claim' && a.target_holding_id === selectedHolding.id
      )
    : []
  
  // Check if player can fabricate claim on this holding (show disabled button if not enough gold)
  // Don't show for holdings player already owns, already has a claim on, or in their domain (vassal)
  const canFabricateClaimOnSelected = selectedHolding && 
    selectedHolding.holding_type === 'town' && 
    selectedHolding.owner_id !== currentPlayer.id &&
    !(currentPlayer.claims ?? []).includes(selectedHolding.id) &&
    canAttackSelected  // Don't show for vassal holdings
  
  // Get build fortification action for selected holding
  const buildFortForSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'build_fortification' && a.target_holding_id === selectedHolding.id
      )
    : []
  
  // Check if this is the player's own town (for showing fortify option)
  const isOwnTown = selectedHolding && 
    selectedHolding.owner_id === currentPlayer.id && 
    selectedHolding.holding_type === 'town'
  
  // Get relocate fortification actions TO selected holding (from any source)
  const relocateFortToSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'relocate_fortification' && a.target_holding_id === selectedHolding.id
      )
    : []
  
  // Get relocate fortification actions FROM selected holding (to any target)
  const relocateFortFromSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'relocate_fortification' && a.source_holding_id === selectedHolding.id
      )
    : []
  
  // Check if player has fortifications on selected holding
  const playerFortsOnSelected = selectedHolding?.fortifications_by_player?.[currentPlayer.id] ?? 0

  // Get claim town actions for selected holding (10g to capture unowned with claim)
  const claimTownForSelected = selectedHolding
    ? validActions.filter(
        a => a.action_type === 'claim_town' && a.target_holding_id === selectedHolding.id
      )
    : []

  // Get claim cards that can be played on the selected holding
  // Don't show claim cards for holdings in player's domain (vassal protection)
  const claimCardsForSelected = selectedHolding && canAttackSelected
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
    <div className="card-parchment rounded-lg p-3 h-full flex flex-col">
      {/* Header with phase */}
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-medieval text-lg text-medieval-bronze">
          {isPlayerTurn ? 'Actions' : 'Waiting...'}
        </h2>
        <span className="text-xs text-medieval-stone">
          R{gameState.current_round} • {gameState.victory_threshold}VP to win
        </span>
      </div>

      {gameState.war_fought_this_turn && (
        <div className="mb-2 text-xs text-medieval-crimson text-center">
          War already fought this turn
        </div>
      )}

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
        <div className="flex-1 overflow-y-auto space-y-2">
          {/* Selected holding attack - opens combat prep modal */}
          {selectedHolding && attackActionsForSelected.length > 0 && (
            <div className="p-2 bg-red-50 rounded border border-red-200">
              <button
                onClick={() => onOpenCombatPrep(selectedHolding)}
                className="btn-crimson w-full py-1.5 rounded text-sm"
              >
                ⚔️ Attack {selectedHolding.name}
              </button>
            </div>
          )}

          {/* Selected holding claim town (10g capture with valid claim) */}
          {selectedHolding && claimTownForSelected.length > 0 && (
            <div className="p-2 bg-green-50 rounded border border-green-200">
              <button
                onClick={() => handleActionClick(claimTownForSelected[0])}
                className="w-full py-1.5 rounded bg-green-600 hover:bg-green-700 text-white font-medieval text-sm"
              >
                🏰 Capture {selectedHolding.name} (10g)
              </button>
            </div>
          )}

          {/* Show hint when player has claim on unowned town but not enough gold */}
          {selectedHolding && 
           selectedHolding.owner_id === null && 
           (currentPlayer.claims ?? []).includes(selectedHolding.id) && 
           claimTownForSelected.length === 0 && 
           currentPlayer.gold < 10 && (
            <div className="p-2 bg-yellow-50 rounded border border-yellow-200 text-xs text-yellow-700">
              Need 10g to capture (have {currentPlayer.gold}g)
            </div>
          )}

          {/* Selected holding fake claim */}
          {selectedHolding && canFabricateClaimOnSelected && (
            <div className="p-2 bg-yellow-50 rounded border border-yellow-200">
              {fakeClaimForSelected.length > 0 ? (
                <button
                  onClick={() => handleActionClick(fakeClaimForSelected[0])}
                  className="btn-medieval w-full py-1.5 rounded text-sm"
                >
                  📜 Fabricate Claim (35g)
                </button>
              ) : (
                <button
                  disabled
                  className="w-full py-1.5 rounded bg-gray-300 text-gray-500 cursor-not-allowed font-medieval text-sm"
                >
                  Fabricate Claim (need 35g)
                </button>
              )}
            </div>
          )}

          {/* Play claim cards on selected holding */}
          {selectedHolding && claimCardsForSelected.length > 0 && (
            <div className="p-2 bg-purple-50 rounded border border-purple-200 space-y-1">
              {claimCardsForSelected.map((action, idx) => {
                const card = gameState.cards[action.card_id || '']
                return (
                  <button
                    key={idx}
                    onClick={() => handleActionClick({
                      ...action,
                      target_holding_id: selectedHolding.id
                    })}
                    className="w-full py-1.5 px-2 bg-purple-100 hover:bg-purple-200 rounded transition-colors text-sm font-medieval text-purple-800"
                  >
                    🃏 Use {card?.name || 'Claim Card'}
                  </button>
                )
              })}
            </div>
          )}

          {/* Play non-claim cards from hand (bonus cards) */}
          {nonClaimPlayCards.length > 0 && (
            <div className="space-y-1">
              {nonClaimPlayCards.map((action, idx) => {
                const card = gameState.cards[action.card_id || '']
                return (
                  <button
                    key={idx}
                    onClick={() => handleActionClick(action)}
                    className="w-full py-1.5 px-2 bg-purple-50 hover:bg-purple-100 rounded transition-colors text-left border border-purple-200 text-sm"
                  >
                    <span className="font-medieval text-purple-800">🃏 {card?.name || 'Card'}</span>
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
            <div className="p-1.5 bg-purple-50/50 rounded border border-purple-100 text-center text-xs text-purple-600">
              📍 Select a town to use claim cards
            </div>
          )}

          {/* Claim title */}
          {groupedActions.claim_title && (
            <div className="space-y-1">
              {groupedActions.claim_title.map((action, idx) => {
                const holding = gameState.holdings.find(h => h.id === action.target_holding_id)
                const cost = holding?.holding_type === 'county_castle' ? 25 
                           : holding?.holding_type === 'duchy_castle' ? 50 
                           : holding?.holding_type === 'king_castle' ? 75 : 0
                const titleName = holding?.holding_type === 'county_castle' ? `Count ${action.target_holding_id?.[0]?.toUpperCase()}`
                               : holding?.holding_type === 'duchy_castle' ? `Duke ${action.target_holding_id?.slice(0, 2).toUpperCase()}`
                               : 'King'
                return (
                  <button
                    key={idx}
                    onClick={() => handleActionClick(action)}
                    className="w-full py-1.5 px-2 bg-yellow-50 hover:bg-yellow-100 rounded transition-colors border border-yellow-200 font-medieval text-sm text-medieval-gold"
                  >
                    👑 Claim {titleName} ({cost}g)
                  </button>
                )
              })}
            </div>
          )}

          {/* Build fortification - show for any selected town */}
          {selectedHolding && selectedHolding.holding_type === 'town' && (
            <div className="p-2 bg-amber-50 rounded border border-amber-200 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-medieval-stone">
                <span>Forts: {selectedHolding.fortification_count}/3 (yours: {playerFortsOnSelected})</span>
                <span>Total: {currentPlayer.fortifications_placed || 0}/4</span>
              </div>
              
              {/* Capitol hint - show claim title option if fortified */}
              {isOwnTown && selectedHolding.is_capitol && playerFortsOnSelected >= 1 && (() => {
                const countyId = selectedHolding.county
                const castleId = `${countyId?.toLowerCase()}_castle`
                const claimAction = validActions.find(
                  a => a.action_type === 'claim_title' && a.target_holding_id === castleId
                )
                const alreadyCount = (currentPlayer.counties ?? []).includes(countyId ?? '')
                
                if (alreadyCount) return (
                  <div className="text-xs text-green-700 font-bold">✓ Count of {countyId}</div>
                )
                
                return claimAction ? (
                  <button
                    onClick={() => handleActionClick(claimAction)}
                    className="w-full py-1.5 rounded bg-yellow-500 hover:bg-yellow-600 text-white font-medieval text-sm"
                  >
                    👑 Claim Count {countyId} (25g)
                  </button>
                ) : (
                  <div className="text-xs text-yellow-700">★ Capitol fortified - need 25g for Count</div>
                )
              })()}
              
              {/* Capitol hint - need fortification */}
              {isOwnTown && selectedHolding.is_capitol && playerFortsOnSelected === 0 && (
                <div className="text-xs text-blue-700">💡 Fortify Capitol → Count title!</div>
              )}
              
              {/* Build new fortification */}
              {buildFortForSelected.length > 0 ? (
                <button
                  onClick={() => handleActionClick(buildFortForSelected[0])}
                  className="w-full py-1.5 rounded bg-amber-600 hover:bg-amber-700 text-white font-medieval text-sm"
                >
                  🏰 Build Fort (10g)
                </button>
              ) : isOwnTown && (
                <button
                  disabled
                  className="w-full py-1.5 rounded bg-gray-300 text-gray-500 cursor-not-allowed font-medieval text-sm"
                >
                  🏰 {currentPlayer.gold < 10 ? `Need 10g` : 'Max forts'}
                </button>
              )}
              
              {/* Move fortification FROM/TO - combined compact view */}
              {(playerFortsOnSelected > 0 && relocateFortFromSelected.length > 0) && (
                <select
                  onChange={(e) => {
                    const action = relocateFortFromSelected.find(a => a.target_holding_id === e.target.value)
                    if (action) handleActionClick(action)
                  }}
                  className="w-full py-1 px-2 text-sm rounded border border-blue-200 bg-blue-50"
                  defaultValue=""
                >
                  <option value="" disabled>🔄 Move fort to...</option>
                  {relocateFortFromSelected.map((action) => {
                    const target = gameState.holdings.find(h => h.id === action.target_holding_id)
                    return <option key={action.target_holding_id} value={action.target_holding_id}>{target?.name} (10g)</option>
                  })}
                </select>
              )}
              
              {relocateFortToSelected.length > 0 && (
                <select
                  onChange={(e) => {
                    const action = relocateFortToSelected.find(a => a.source_holding_id === e.target.value)
                    if (action) handleActionClick(action)
                  }}
                  className="w-full py-1 px-2 text-sm rounded border border-blue-200 bg-blue-50"
                  defaultValue=""
                >
                  <option value="" disabled>🔄 Move fort from...</option>
                  {relocateFortToSelected.map((action) => {
                    const source = gameState.holdings.find(h => h.id === action.source_holding_id)
                    return <option key={action.source_holding_id} value={action.source_holding_id}>{source?.name} (10g)</option>
                  })}
                </select>
              )}
            </div>
          )}
          
          {/* Hint to select a town for fortification */}
          {!selectedHolding && (currentPlayer.fortifications_placed || 0) < 4 && currentPlayer.gold >= 10 && groupedActions.build_fortification && (
            <div className="p-1.5 bg-amber-50/50 rounded border border-amber-100 text-center text-xs text-amber-600">
              🏰 Select a town to build forts
            </div>
          )}

          {/* End turn */}
          {groupedActions.end_turn && (
            <button
              onClick={() => handleActionClick(groupedActions.end_turn[0])}
              className="w-full py-2 bg-medieval-bronze hover:bg-medieval-bronze/90 text-white rounded transition-colors font-medieval text-sm"
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
            <h3 className="font-medieval text-xl text-medieval-gold mb-1">Game Over!</h3>
            <p className="text-medieval-stone text-sm">Check final scores</p>
          </div>
        </div>
      )}
    </div>
  )
}
