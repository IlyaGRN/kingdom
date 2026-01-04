import { useState } from 'react'
import { useGameStore } from '../store/gameStore'
import { createGame, startGame, autoAssignStartingTowns } from '../api/gameApi'
import { PlayerConfig, PLAYER_COLORS, AI_TYPES, PlayerType } from '../types/game'

interface GameSetupProps {
  onGameCreated: () => void
  onBack: () => void
}

export default function GameSetup({ onGameCreated, onBack }: GameSetupProps) {
  const [playerCount, setPlayerCount] = useState(4)
  const [players, setPlayers] = useState<PlayerConfig[]>([
    { name: 'You', player_type: 'human', color: PLAYER_COLORS[0] },
    { name: 'Baron Alpha', player_type: 'ai_openai', color: PLAYER_COLORS[1] },
    { name: 'Baron Beta', player_type: 'ai_openai', color: PLAYER_COLORS[2] },
    { name: 'Baron Gamma', player_type: 'ai_openai', color: PLAYER_COLORS[3] },
  ])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { setGameState } = useGameStore()

  const handlePlayerCountChange = (count: number) => {
    setPlayerCount(count)
    const newPlayers = [...players]
    
    while (newPlayers.length < count) {
      const idx = newPlayers.length
      newPlayers.push({
        name: `Baron ${idx + 1}`,
        player_type: 'ai_openai',  // Default all new AI players to GPT
        color: PLAYER_COLORS[idx],
      })
    }
    
    while (newPlayers.length > count) {
      newPlayers.pop()
    }
    
    setPlayers(newPlayers)
  }

  const handlePlayerChange = (index: number, field: keyof PlayerConfig, value: string) => {
    const newPlayers = [...players]
    newPlayers[index] = { ...newPlayers[index], [field]: value }
    setPlayers(newPlayers)
  }

  const handleStartGame = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const { state } = await createGame(players)
      
      // Auto-assign starting towns to all players
      const { state: assignedState } = await autoAssignStartingTowns(state.id)
      setGameState(assignedState)
      
      // Start the game
      const { state: startedState } = await startGame(assignedState.id)
      setGameState(startedState)
      
      onGameCreated()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create game')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="card-parchment rounded-lg p-8 max-w-2xl w-full">
        <h1 className="font-medieval text-3xl text-center mb-8 text-medieval-bronze">
          Game Setup
        </h1>

        {/* Player count selection */}
        <div className="mb-8">
          <label className="block font-medieval text-lg mb-3 text-medieval-bronze">
            Number of Players
          </label>
          <div className="flex gap-2">
            {[4, 5, 6].map(count => (
              <button
                key={count}
                onClick={() => handlePlayerCountChange(count)}
                className={`px-6 py-3 rounded font-medieval text-lg transition-all ${
                  playerCount === count
                    ? 'bg-medieval-gold text-white'
                    : 'bg-parchment-200 text-medieval-bronze hover:bg-parchment-300'
                }`}
              >
                {count} Players
              </button>
            ))}
          </div>
          <p className="text-sm text-medieval-stone mt-2">
            Game length: {playerCount === 4 ? '10' : playerCount === 5 ? '11' : '12'} rounds
          </p>
        </div>

        {/* Player configuration */}
        <div className="space-y-4 mb-8">
          {players.map((player, index) => (
            <div 
              key={index}
              className="flex items-center gap-4 p-4 rounded bg-parchment-100 border border-parchment-300"
            >
              {/* Color indicator */}
              <div 
                className="w-8 h-8 rounded-full border-2 border-parchment-400 flex-shrink-0"
                style={{ backgroundColor: player.color }}
              />

              {/* Player name */}
              <input
                type="text"
                value={player.name}
                onChange={(e) => handlePlayerChange(index, 'name', e.target.value)}
                className="flex-1 px-3 py-2 rounded border border-parchment-300 bg-white text-medieval-bronze focus:outline-none focus:border-medieval-gold"
                placeholder="Player name"
              />

              {/* Player type */}
              <select
                value={player.player_type}
                onChange={(e) => handlePlayerChange(index, 'player_type', e.target.value as PlayerType)}
                className="px-3 py-2 rounded border border-parchment-300 bg-white text-medieval-bronze focus:outline-none focus:border-medieval-gold"
              >
                {AI_TYPES.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-4 p-3 rounded bg-red-100 border border-red-300 text-red-700">
            {error}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-4 justify-center">
          <button
            onClick={onBack}
            className="px-8 py-3 rounded font-medieval text-lg bg-parchment-300 text-medieval-bronze hover:bg-parchment-400 transition-colors"
          >
            Back
          </button>
          
          <button
            onClick={handleStartGame}
            disabled={isLoading}
            className="btn-medieval px-8 py-3 rounded text-lg"
          >
            {isLoading ? 'Creating...' : 'Start Game'}
          </button>
        </div>
      </div>
    </div>
  )
}

