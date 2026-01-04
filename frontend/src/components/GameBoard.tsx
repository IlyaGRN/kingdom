import { useEffect, useCallback, useState } from 'react'
import { useGameStore } from '../store/gameStore'
import { getValidActions, performAction, processIncome, getWinner } from '../api/gameApi'
import { Action, Holding, Player } from '../types/game'
import Board from './Board'
import PlayerMat from './PlayerMat'
import ActionPanel from './ActionPanel'
import CombatModal from './CombatModal'
import ClaimActionModal from './ClaimActionModal'
import CombatPrepModal from './CombatPrepModal'
import DefenseModal from './DefenseModal'
import AIDecisionPanel from './AIDecisionPanel'

interface GameBoardProps {
  onBack: () => void
}

export default function GameBoard({ onBack }: GameBoardProps) {
  const { 
    gameState, 
    setGameState, 
    selectedHolding,
    setSelectedHolding,
    setValidActions,
    lastCombat,
    setLastCombat,
    decisionLogs,
    addDecisionLog,
    clearDecisionLogs,
  } = useGameStore()

  const [winner, setWinner] = useState<Player | null>(null)
  const [showCombat, setShowCombat] = useState(false)
  const [claimModalHolding, setClaimModalHolding] = useState<Holding | null>(null)
  
  // Combat prep modal state
  const [combatPrepTarget, setCombatPrepTarget] = useState<{
    holding: Holding
    defender: Player | null
  } | null>(null)
  
  // Defense modal shows automatically when pending_combat targets this human player

  // Fetch valid actions when turn changes
  const fetchValidActions = useCallback(async () => {
    if (!gameState) return
    
    const currentPlayer = gameState.players[gameState.current_player_idx]
    
    if (!currentPlayer || currentPlayer.player_type !== 'human') {
      setValidActions([])
      return
    }
    
    try {
      const { actions } = await getValidActions(gameState.id, currentPlayer.id)
      setValidActions(actions)
    } catch (error) {
      console.error('Failed to fetch valid actions:', error)
    }
  }, [gameState, setValidActions])

  useEffect(() => {
    if (gameState?.phase === 'player_turn') {
      fetchValidActions()
    }
  }, [gameState?.phase, gameState?.current_player_idx, fetchValidActions])

  // Handle income phase
  useEffect(() => {
    const handleIncome = async () => {
      if (!gameState || gameState.phase !== 'income') return
      
      try {
        const { state } = await processIncome(gameState.id)
        setGameState(state)
      } catch (error) {
        console.error('Failed to process income:', error)
      }
    }
    
    const timer = setTimeout(handleIncome, 1000)
    return () => clearTimeout(timer)
  }, [gameState?.phase, gameState?.id, setGameState])

  // Check for game over
  useEffect(() => {
    const checkWinner = async () => {
      if (!gameState || gameState.phase !== 'game_over') return
      
      try {
        const result = await getWinner(gameState.id)
        if (result.winner) {
          setWinner(result.winner)
        }
      } catch (error) {
        console.error('Failed to get winner:', error)
      }
    }
    
    checkWinner()
  }, [gameState?.phase, gameState?.id])

  // AI turn handling - loop until AI ends turn (with max actions limit)
  useEffect(() => {
    let isActive = true
    const MAX_ACTIONS_PER_TURN = 15 // Prevent runaway AI turns
    
    const runAITurn = async () => {
      if (!gameState || gameState.phase !== 'player_turn') return
      
      let currentPlayerIdx = gameState.current_player_idx
      const startingPlayerIdx = currentPlayerIdx
      let currentGameId = gameState.id
      let actionCount = 0
      
      const currentPlayer = gameState.players[currentPlayerIdx]
      if (!currentPlayer || currentPlayer.player_type === 'human') return
      
      // Keep taking actions until turn ends, player changes, or max reached
      while (isActive && actionCount < MAX_ACTIONS_PER_TURN) {
        try {
          actionCount++
          
          const response = await fetch(`/api/simulation/${currentGameId}/step`, {
            method: 'POST',
          })
          
          if (!response.ok) {
            const errorText = await response.text()
            console.error(`AI step failed: ${response.status} - ${errorText}`)
            break
          }
          
          const result = await response.json()
          
          // Capture decision log if present
          if (result.decision_log) {
            addDecisionLog(result.decision_log)
          }
          
          if (result.state) {
            setGameState(result.state)
            
            // Check if turn changed (AI ended turn or new phase)
            if (result.state.current_player_idx !== startingPlayerIdx ||
                result.state.phase !== 'player_turn') {
              break // AI turn is over
            }
            
            currentPlayerIdx = result.state.current_player_idx
          } else {
            break // No state returned, stop
          }
          
          // Small delay between actions for visibility
          await new Promise(resolve => setTimeout(resolve, 300))
          
        } catch (error) {
          console.error('AI turn failed:', error)
          break
        }
      }
      
      // If we hit max actions, force end turn
      if (actionCount >= MAX_ACTIONS_PER_TURN && isActive) {
        console.log('AI hit max actions limit, forcing end turn')
        try {
          await fetch(`/api/games/${currentGameId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action_type: 'end_turn',
              player_id: currentPlayer.id
            })
          })
          // Refresh game state
          const response = await fetch(`/api/games/${currentGameId}`)
          if (response.ok) {
            const { state } = await response.json()
            setGameState(state)
          }
        } catch (error) {
          console.error('Failed to force end turn:', error)
        }
      }
    }
    
    // Start AI turn after a short delay
    const timer = setTimeout(runAITurn, 500)
    
    return () => {
      isActive = false
      clearTimeout(timer)
    }
  }, [gameState?.phase, gameState?.current_player_idx, gameState?.id, setGameState])

  const handleHoldingClick = (holding: Holding) => {
    if (selectedHolding?.id === holding.id) {
      setSelectedHolding(null)
    } else {
      setSelectedHolding(holding)
    }
  }

  const handlePerformAction = async (action: Action) => {
    if (!gameState) return
    
    // Check if this is a claim card being played
    const isClaimCardPlay = action.action_type === 'play_card' && action.card_id && action.target_holding_id
    let claimCardTargetId: string | null = null
    
    if (isClaimCardPlay) {
      const card = gameState.cards[action.card_id!]
      if (card?.card_type === 'claim') {
        claimCardTargetId = action.target_holding_id!
      }
    }
    
    try {
      const result = await performAction(gameState.id, action)
      
      if (result.combat_result) {
        setLastCombat(result.combat_result)
        setShowCombat(true)
      }
      
      setGameState(result.state)
      setSelectedHolding(null)
      
      // If a claim card was played, show the claim action modal
      if (claimCardTargetId && result.state) {
        const targetHolding = result.state.holdings.find((h: Holding) => h.id === claimCardTargetId)
        if (targetHolding) {
          setClaimModalHolding(targetHolding)
        }
      }
    } catch (error) {
      console.error('Action failed:', error)
    }
  }

  const handleCloseCombat = () => {
    setShowCombat(false)
    setLastCombat(null)
  }

  const handleClaimCapture = async () => {
    if (!gameState || !claimModalHolding) return
    
    const currentPlayer = gameState.players[gameState.current_player_idx]
    if (!currentPlayer) return
    
    // Find the claim_town action for this holding
    const { actions } = await getValidActions(gameState.id, currentPlayer.id)
    const captureAction = actions.find(
      a => a.action_type === 'claim_town' && a.target_holding_id === claimModalHolding.id
    )
    
    if (captureAction) {
      await handlePerformAction(captureAction)
    }
    setClaimModalHolding(null)
  }

  const handleClaimAttack = async (soldiers: number) => {
    if (!gameState || !claimModalHolding) return
    
    const currentPlayer = gameState.players[gameState.current_player_idx]
    if (!currentPlayer) return
    
    // Find the attack action for this holding
    const { actions } = await getValidActions(gameState.id, currentPlayer.id)
    const attackAction = actions.find(
      a => a.action_type === 'attack' && a.target_holding_id === claimModalHolding.id
    )
    
    if (attackAction) {
      await handlePerformAction({
        ...attackAction,
        soldiers_count: soldiers,
      })
    }
    setClaimModalHolding(null)
  }

  const handleCloseClaimModal = () => {
    setClaimModalHolding(null)
  }

  // Open combat prep modal when player wants to attack
  const handleOpenCombatPrep = (targetHolding: Holding) => {
    if (!gameState) return
    const defender = gameState.players.find(p => p.id === targetHolding.owner_id) || null
    setCombatPrepTarget({ holding: targetHolding, defender })
  }

  // Execute attack from combat prep modal
  const handleCombatAttack = async (soldiers: number, cardIds: string[]) => {
    if (!gameState || !combatPrepTarget) return
    
    const currentPlayer = gameState.players[gameState.current_player_idx]
    if (!currentPlayer) return
    
    const attackAction: Action = {
      action_type: 'attack',
      player_id: currentPlayer.id,
      target_holding_id: combatPrepTarget.holding.id,
      soldiers_count: soldiers,
      attack_cards: cardIds,
    }
    
    try {
      const result = await performAction(gameState.id, attackAction)
      
      if (result.combat_result) {
        setLastCombat(result.combat_result)
        setShowCombat(true)
      }
      
      setGameState(result.state)
      setCombatPrepTarget(null)
      setSelectedHolding(null)
    } catch (error) {
      console.error('Attack failed:', error)
    }
  }

  const handleCloseCombatPrep = () => {
    setCombatPrepTarget(null)
  }

  // Handle defend action when human player is attacked
  const handleDefend = async (soldiers: number, cardIds: string[]) => {
    if (!gameState?.pending_combat) return
    
    const defendAction: Action = {
      action_type: 'defend',
      player_id: gameState.pending_combat.defender_id,
      soldiers_count: soldiers,
      defense_cards: cardIds,
    }
    
    try {
      const result = await performAction(gameState.id, defendAction)
      
      if (result.combat_result) {
        setLastCombat(result.combat_result)
        setShowCombat(true)
      }
      
      setGameState(result.state)
    } catch (error) {
      console.error('Defense failed:', error)
    }
  }

  // Check if current human player needs to defend
  const humanPlayer = gameState?.players.find(p => p.player_type === 'human')
  const showDefenseModal = gameState?.pending_combat && 
    humanPlayer && 
    gameState.pending_combat.defender_id === humanPlayer.id

  // Get data for defense modal
  const defenseModalData = showDefenseModal && gameState?.pending_combat ? {
    pendingCombat: gameState.pending_combat,
    targetHolding: gameState.holdings.find(h => h.id === gameState.pending_combat!.target_holding_id)!,
    attacker: gameState.players.find(p => p.id === gameState.pending_combat!.attacker_id)!,
    defender: humanPlayer!,
  } : null

  if (!gameState) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-parchment-300">Loading game...</p>
      </div>
    )
  }

  const currentPlayer = gameState.players[gameState.current_player_idx]

  return (
    <div className="min-h-screen p-4 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={onBack}
          className="px-4 py-2 text-parchment-300 hover:text-parchment-100 transition-colors"
        >
          ← Back to Menu
        </button>
        
        <div className="text-center">
          <h1 className="font-medieval text-2xl text-parchment-100">
            Machiavelli's Kingdom
          </h1>
          <p className="text-parchment-400 text-sm">
            Round {gameState.current_round} • Goal: {gameState.victory_threshold} VP
          </p>
        </div>
        
        <div className="text-right">
          {currentPlayer && (
            <div className="flex items-center gap-2">
              <div 
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: currentPlayer.color }}
              />
              <span className="text-parchment-300 text-sm">
                {currentPlayer.name}'s Turn
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main game area */}
      <div className="flex-1 grid grid-cols-12 gap-4">
        {/* Left sidebar - Player mats */}
        <div className="col-span-3 space-y-3 overflow-y-auto max-h-[calc(100vh-120px)]">
          {gameState.players.map((player, idx) => (
            <PlayerMat
              key={player.id}
              player={player}
              isCurrentPlayer={idx === gameState.current_player_idx}
              cards={gameState.cards}
              holdings={gameState.holdings}
            />
          ))}
        </div>

        {/* Center - Game board */}
        <div className="col-span-6">
          <div className="aspect-square max-h-[calc(100vh-120px)] mx-auto">
            <Board onHoldingClick={handleHoldingClick} />
          </div>
        </div>

        {/* Right sidebar - Actions */}
        <div className="col-span-3">
          <ActionPanel
            onPerformAction={handlePerformAction}
            selectedHolding={selectedHolding}
            onOpenCombatPrep={handleOpenCombatPrep}
          />
        </div>
      </div>

      {/* Combat modal */}
      {showCombat && lastCombat && (
        <CombatModal
          combat={lastCombat}
          players={gameState.players}
          holdings={gameState.holdings}
          onClose={handleCloseCombat}
        />
      )}

      {/* Claim action modal */}
      {claimModalHolding && currentPlayer && (
        <ClaimActionModal
          holding={claimModalHolding}
          currentPlayer={currentPlayer}
          onCapture={handleClaimCapture}
          onAttack={handleClaimAttack}
          onClose={handleCloseClaimModal}
        />
      )}

      {/* Combat prep modal (attacker selecting soldiers + cards) */}
      {combatPrepTarget && currentPlayer && (
        <CombatPrepModal
          targetHolding={combatPrepTarget.holding}
          defender={combatPrepTarget.defender}
          currentPlayer={currentPlayer}
          cards={gameState.cards}
          onAttack={handleCombatAttack}
          onCancel={handleCloseCombatPrep}
        />
      )}

      {/* Defense modal (human defender responding to attack) */}
      {defenseModalData && (
        <DefenseModal
          pendingCombat={defenseModalData.pendingCombat}
          targetHolding={defenseModalData.targetHolding}
          attacker={defenseModalData.attacker}
          defender={defenseModalData.defender}
          cards={gameState.cards}
          onDefend={handleDefend}
        />
      )}

      {/* AI Decision Log Panel */}
      <AIDecisionPanel 
        logs={decisionLogs} 
        onClear={clearDecisionLogs} 
      />

      {/* Game over modal */}
      {winner && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="card-parchment rounded-lg p-8 max-w-md text-center">
            <svg 
              className="w-20 h-20 mx-auto text-medieval-gold mb-4 crown-pulse" 
              viewBox="0 0 24 24" 
              fill="currentColor"
            >
              <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm0 2h14v2H5v-2z"/>
            </svg>
            
            <h2 className="font-medieval text-3xl text-medieval-bronze mb-2">
              Victory!
            </h2>
            
            <p className="text-xl text-medieval-stone mb-4">
              <span style={{ color: winner.color }}>{winner.name}</span> wins!
            </p>
            
            <p className="text-medieval-stone mb-6">
              Final Prestige: {winner.prestige} VP
            </p>
            
            <button
              onClick={onBack}
              className="btn-medieval px-8 py-3 rounded text-lg"
            >
              Return to Menu
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

