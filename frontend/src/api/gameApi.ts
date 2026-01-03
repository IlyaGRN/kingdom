import { GameState, Action, PlayerConfig, CombatResult } from '../types/game'

const API_BASE = '/api'

interface ApiError {
  detail: string
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function createGame(playerConfigs: PlayerConfig[]): Promise<{ game_id: string; state: GameState }> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_configs: playerConfigs }),
  })
  return handleResponse(response)
}

export async function getGameState(gameId: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${gameId}`)
  return handleResponse(response)
}

export async function getValidActions(gameId: string, playerId: string): Promise<{ actions: Action[] }> {
  const response = await fetch(`${API_BASE}/games/${gameId}/valid-actions/${playerId}`)
  return handleResponse(response)
}

export async function performAction(
  gameId: string, 
  action: Action
): Promise<{ success: boolean; message: string; state: GameState; combat_result: CombatResult | null }> {
  const response = await fetch(`${API_BASE}/games/${gameId}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(action),
  })
  return handleResponse(response)
}

export async function assignStartingTown(
  gameId: string, 
  playerId: string, 
  townId: string
): Promise<{ status: string; state: GameState }> {
  const response = await fetch(
    `${API_BASE}/games/${gameId}/assign-town?player_id=${playerId}&town_id=${townId}`,
    { method: 'POST' }
  )
  return handleResponse(response)
}

export async function autoAssignStartingTowns(
  gameId: string
): Promise<{ status: string; state: GameState }> {
  const response = await fetch(
    `${API_BASE}/games/${gameId}/auto-assign-towns`,
    { method: 'POST' }
  )
  return handleResponse(response)
}

export async function startGame(gameId: string): Promise<{ status: string; state: GameState }> {
  const response = await fetch(`${API_BASE}/games/${gameId}/start`, {
    method: 'POST',
  })
  return handleResponse(response)
}

export async function processIncome(gameId: string): Promise<{ status: string; state: GameState }> {
  const response = await fetch(`${API_BASE}/games/${gameId}/income`, {
    method: 'POST',
  })
  return handleResponse(response)
}

export async function getPrestige(gameId: string): Promise<{ prestige: Record<string, number> }> {
  const response = await fetch(`${API_BASE}/games/${gameId}/prestige`)
  return handleResponse(response)
}

export async function getWinner(gameId: string): Promise<{ 
  winner: import('../types/game').Player | null; 
  game_over: boolean;
  prestige: Record<string, number>;
}> {
  const response = await fetch(`${API_BASE}/games/${gameId}/winner`)
  return handleResponse(response)
}

// Simulation endpoints
export async function createSimulation(
  playerConfigs: PlayerConfig[], 
  speedMs: number = 1000
): Promise<{ game_id: string; state: GameState; speed_ms: number }> {
  const response = await fetch(`${API_BASE}/simulation/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_configs: playerConfigs, speed_ms: speedMs }),
  })
  return handleResponse(response)
}

export async function simulationStep(gameId: string): Promise<{
  status: string;
  action?: Action;
  message?: string;
  state: GameState;
}> {
  const response = await fetch(`${API_BASE}/simulation/${gameId}/step`, {
    method: 'POST',
  })
  return handleResponse(response)
}

export async function runFullSimulation(
  gameId: string, 
  maxSteps: number = 1000
): Promise<{
  status: string;
  steps: number;
  state: GameState;
  winner: import('../types/game').Player | null;
}> {
  const response = await fetch(`${API_BASE}/simulation/${gameId}/run?max_steps=${maxSteps}`, {
    method: 'POST',
  })
  return handleResponse(response)
}

