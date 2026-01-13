import { useEffect, useCallback, useState, useRef } from 'react'
import { useGameStore } from '../store/gameStore'
import { getValidActions, performAction, processIncome, getWinner } from '../api/gameApi'
import { Action, Holding, Player, DrawnCardInfo } from '../types/game'
import Board from './Board'
import PlayerMat from './PlayerMat'
import ActionPanel from './ActionPanel'
import CombatModal from './CombatModal'
import ClaimActionModal from './ClaimActionModal'
import CombatPrepModal from './CombatPrepModal'
import DefenseModal from './DefenseModal'
import AIDecisionPanel from './AIDecisionPanel'
import CardDrawModal from './CardDrawModal'

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
    combatLogs,
    addCombatLog,
    clearCombatLogs,
  } = useGameStore()

  const [winner, setWinner] = useState<Player | null>(null)
  const [showCombat, setShowCombat] = useState(false)
  const [claimModalHolding, setClaimModalHolding] = useState<Holding | null>(null)
  
  // Card draw modal state
  const [drawnCardToShow, setDrawnCardToShow] = useState<DrawnCardInfo | null>(null)
  const lastShownCardRef = useRef<string | null>(null)
  
  // Combat prep modal state
  const [combatPrepTarget, setCombatPrepTarget] = useState<{
    holding: Holding
    defender: Player | null
  } | null>(null)
  
  // Sidebar state for collapsible right panel
  const [sidebarOpen, setSidebarOpen] = useState(true)
  
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

  // Show card draw popup when a new card is drawn
  // For AI players, only show popup for global events (Crusade, etc.), otherwise just log
  useEffect(() => {
    if (!gameState?.last_drawn_card) return
    
    const cardInfo = gameState.last_drawn_card
    // Use a unique key to track if we've shown this card already
    const cardKey = `${cardInfo.card_id}-${cardInfo.player_id}-${gameState.current_round}-${gameState.current_player_idx}`
    
    if (lastShownCardRef.current !== cardKey) {
      lastShownCardRef.current = cardKey
      
      // Check if this is an AI player draw
      const player = gameState.players.find(p => p.id === cardInfo.player_id)
      const isAI = player?.player_type !== 'human'
      const isGlobalEvent = cardInfo.card_type === 'global_event'
      
      if (isAI && !isGlobalEvent) {
        // For AI non-global cards, just log instead of showing popup
        console.log(`${cardInfo.player_name} drew ${cardInfo.is_hidden ? 'a hidden card' : cardInfo.card_name}`)
      } else {
        // Show popup for human players and AI global events
        setDrawnCardToShow(cardInfo)
      }
    }
  }, [gameState?.last_drawn_card, gameState?.current_round, gameState?.current_player_idx, gameState?.players])

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
          
          // Capture combat result if present (AI wars)
          if (result.combat_result && result.state) {
            const combat = result.combat_result
            const attacker = result.state.players.find((p: Player) => p.id === combat.attacker_id)
            const defender = result.state.players.find((p: Player) => p.id === combat.defender_id)
            const holding = result.state.holdings.find((h: Holding) => h.id === combat.target_holding_id)
            
            addCombatLog({
              combat,
              timestamp: Date.now(),
              attackerName: attacker?.name || 'Unknown',
              defenderName: defender?.name || null,
              holdingName: holding?.name || 'Unknown Territory',
            })
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
            const state = await response.json()  // API returns state directly, not {state: ...}
            if (state) setGameState(state)
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

  // Build defense modal data with null safety
  const defenseModalData = (() => {
    if (!showDefenseModal || !gameState?.pending_combat || !humanPlayer) return null
    
    const targetHolding = gameState.holdings.find(h => h.id === gameState.pending_combat!.target_holding_id)
    const attacker = gameState.players.find(p => p.id === gameState.pending_combat!.attacker_id)
    
    if (!targetHolding || !attacker) return null
    
    return {
      pendingCombat: gameState.pending_combat,
      targetHolding,
      attacker,
      defender: humanPlayer,
    }
  })()

  if (!gameState) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-parchment-300">Loading game...</p>
      </div>
    )
  }

  const currentPlayer = gameState.players[gameState.current_player_idx]

  return (
    <div className="h-screen overflow-hidden relative">
      {/* Game info panel - fixed top left */}
      <div className="fixed top-0 left-0 z-40 bg-medieval-navy/90 text-white px-3 py-2 rounded-br-lg shadow-lg">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-xs text-parchment-300 hover:text-parchment-100 transition-colors"
          >
            ← Back
          </button>
          <div className="border-l border-parchment-400/50 pl-3">
            <h1 className="font-medieval text-sm text-parchment-100">
              Machiavelli's Kingdom
            </h1>
            <p className="text-parchment-400 text-[10px]">
              Round {gameState.current_round} • {gameState.victory_threshold} VP
            </p>
          </div>
          {currentPlayer && (
            <div className="flex items-center gap-1.5 border-l border-parchment-400/50 pl-3">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: currentPlayer.color }}
              />
              <span className="text-parchment-300 text-xs">
                {currentPlayer.name}'s Turn
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Left sidebar - Player mats */}
      <div className="absolute left-0 top-16 bottom-0 flex z-30">
        {/* Collapsible Left Sidebar */}
        <div 
          className={`transition-all duration-300 flex-shrink-0 overflow-hidden ${sidebarOpen ? 'w-72' : 'w-0'}`}
        >
          <div className="w-72 h-full flex flex-col bg-parchment-100/90 border-r border-parchment-300">
            {/* Player mats - scrollable */}
            <div className="flex-1 overflow-y-auto space-y-2 p-2">
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
          </div>
        </div>
        
        {/* Left sidebar toggle button */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="flex-shrink-0 bg-parchment-200 hover:bg-parchment-300 text-medieval-bronze px-1 py-4 transition-all self-center"
        >
          {sidebarOpen ? '←' : '→'}
        </button>
      </div>

      {/* Board - strictly centered on screen */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="h-full aspect-square max-h-full">
          <Board onHoldingClick={handleHoldingClick} />
        </div>
      </div>

      {/* Right sidebar - Action panel */}
      <div className="absolute right-0 top-0 h-full z-30">
        <div className="h-full bg-parchment-100/90 border-l border-parchment-300 w-72 overflow-y-auto p-2">
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
          holdings={gameState.holdings}
          onDefend={handleDefend}
        />
      )}

      {/* AI Activity Log Panel */}
      <AIDecisionPanel 
        logs={decisionLogs} 
        combatLogs={combatLogs}
        onClear={clearDecisionLogs}
        onClearCombats={clearCombatLogs}
      />

      {/* Card draw modal */}
      {drawnCardToShow && (
        <CardDrawModal
          drawnCard={drawnCardToShow}
          card={gameState.cards[drawnCardToShow.card_id]}
          onClose={() => setDrawnCardToShow(null)}
        />
      )}

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

