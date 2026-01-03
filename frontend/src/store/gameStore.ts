import { create } from 'zustand'
import { GameState, Action, CombatResult, Holding } from '../types/game'

interface GameStore {
  // State
  gameState: GameState | null
  selectedHolding: Holding | null
  validActions: Action[]
  lastCombat: CombatResult | null
  isLoading: boolean
  error: string | null
  
  // Actions
  setGameState: (state: GameState) => void
  setSelectedHolding: (holding: Holding | null) => void
  setValidActions: (actions: Action[]) => void
  setLastCombat: (result: CombatResult | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  resetGame: () => void
  
  // Computed
  getCurrentPlayer: () => import('../types/game').Player | null
  getPlayerById: (id: string) => import('../types/game').Player | null
  getHoldingById: (id: string) => Holding | null
  getHoldingOwner: (holdingId: string) => import('../types/game').Player | null
}

export const useGameStore = create<GameStore>((set, get) => ({
  // Initial state
  gameState: null,
  selectedHolding: null,
  validActions: [],
  lastCombat: null,
  isLoading: false,
  error: null,
  
  // Setters
  setGameState: (state) => set({ gameState: state, error: null }),
  setSelectedHolding: (holding) => set({ selectedHolding: holding }),
  setValidActions: (actions) => set({ validActions: actions }),
  setLastCombat: (result) => set({ lastCombat: result }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  
  resetGame: () => set({
    gameState: null,
    selectedHolding: null,
    validActions: [],
    lastCombat: null,
    isLoading: false,
    error: null,
  }),
  
  // Computed getters
  getCurrentPlayer: () => {
    const state = get().gameState
    if (!state || state.current_player_idx >= state.players.length) return null
    return state.players[state.current_player_idx]
  },
  
  getPlayerById: (id) => {
    const state = get().gameState
    if (!state) return null
    return state.players.find(p => p.id === id) || null
  },
  
  getHoldingById: (id) => {
    const state = get().gameState
    if (!state) return null
    return state.holdings.find(h => h.id === id) || null
  },
  
  getHoldingOwner: (holdingId) => {
    const state = get().gameState
    if (!state) return null
    const holding = state.holdings.find(h => h.id === holdingId)
    if (!holding || !holding.owner_id) return null
    return state.players.find(p => p.id === holding.owner_id) || null
  },
}))

