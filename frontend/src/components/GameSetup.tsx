import { useState } from 'react'
import { useGameStore } from '../store/gameStore'
import { createGame, startGame, autoAssignStartingTowns } from '../api/gameApi'
import { PlayerConfig, PLAYER_COLORS, AI_TYPES, PlayerType } from '../types/game'
import { visualConfig, getDefaultCrest } from '../config/visualConfig'

interface GameSetupProps {
  onGameCreated: () => void
  onBack: () => void
}

export default function GameSetup({ onGameCreated, onBack }: GameSetupProps) {
  const [playerCount, setPlayerCount] = useState(4)
  const [players, setPlayers] = useState<PlayerConfig[]>([
    { name: 'You', player_type: 'human', color: PLAYER_COLORS[0], crest: getDefaultCrest('human', 0) },
    { name: 'Baron Alpha', player_type: 'ai_openai', color: PLAYER_COLORS[1], crest: getDefaultCrest('ai_openai') },
    { name: 'Baron Beta', player_type: 'ai_openai', color: PLAYER_COLORS[2], crest: getDefaultCrest('ai_openai') },
    { name: 'Baron Gamma', player_type: 'ai_openai', color: PLAYER_COLORS[3], crest: getDefaultCrest('ai_openai') },
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
        crest: getDefaultCrest('ai_openai'),
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
    
    // When player_type changes, update the crest to the default for that type
    if (field === 'player_type') {
      const humanCount = newPlayers.slice(0, index).filter(p => p.player_type === 'human').length
      newPlayers[index].crest = getDefaultCrest(value, value === 'human' ? humanCount : 0)
    }
    
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
    <div 
      className="h-screen flex flex-col items-center justify-center p-4 bg-cover bg-center bg-no-repeat overflow-hidden relative"
      style={{ backgroundImage: `url('${visualConfig.gameSetup.backgroundImage}')` }}
    >
      {/* Blur overlay */}
      <div 
        className="absolute inset-0 backdrop-blur-sm pointer-events-none"
        style={{ 
          backdropFilter: `blur(${visualConfig.gameSetup.backgroundBlur}px)`,
          WebkitBackdropFilter: `blur(${visualConfig.gameSetup.backgroundBlur}px)`,
        }}
      />
      {/* Dark overlay */}
      <div 
        className="absolute inset-0 pointer-events-none" 
        style={{ backgroundColor: `rgba(0, 0, 0, ${visualConfig.gameSetup.overlayOpacity})` }}
      />
      
      <div className="card-parchment rounded-lg p-6 max-w-2xl w-full relative z-10">
        <h1 className="font-medieval text-2xl text-center mb-4 text-medieval-bronze">
          Game Setup
        </h1>

        {/* Player count selection */}
        <div className="mb-4">
          <div className="flex items-center gap-4">
            <label className="font-medieval text-base text-medieval-bronze whitespace-nowrap">
              Players:
            </label>
            <div className="flex gap-2">
              {[4, 5, 6].map(count => (
                <button
                  key={count}
                  onClick={() => handlePlayerCountChange(count)}
                  className={`px-4 py-2 rounded font-medieval text-base transition-all ${
                    playerCount === count
                      ? 'bg-medieval-gold text-white'
                      : 'bg-parchment-200 text-medieval-bronze hover:bg-parchment-300'
                  }`}
                >
                  {count}
                </button>
              ))}
            </div>
            <span className="text-sm text-medieval-stone">
              ({playerCount === 4 ? '10' : playerCount === 5 ? '11' : '12'} rounds)
            </span>
          </div>
        </div>

        {/* Player configuration */}
        <div className="space-y-2 mb-4">
          {players.map((player, index) => (
            <div 
              key={index}
              className="flex items-center gap-2 p-2 rounded bg-parchment-100 border border-parchment-300"
            >
              {/* Crest indicator */}
              <img 
                src={player.crest}
                alt="Crest"
                className="w-8 h-8 object-contain flex-shrink-0"
              />

              {/* Player name */}
              <input
                type="text"
                value={player.name}
                onChange={(e) => handlePlayerChange(index, 'name', e.target.value)}
                className="flex-1 px-2 py-1 rounded border border-parchment-300 bg-white text-medieval-bronze text-sm focus:outline-none focus:border-medieval-gold"
                placeholder="Player name"
              />

              {/* Player type */}
              <select
                value={player.player_type}
                onChange={(e) => handlePlayerChange(index, 'player_type', e.target.value as PlayerType)}
                className="px-2 py-1 rounded border border-parchment-300 bg-white text-medieval-bronze text-sm focus:outline-none focus:border-medieval-gold"
              >
                {AI_TYPES.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>

              {/* Crest selector */}
              <select
                value={player.crest}
                onChange={(e) => handlePlayerChange(index, 'crest', e.target.value)}
                className="px-2 py-1 rounded border border-parchment-300 bg-white text-medieval-bronze text-sm focus:outline-none focus:border-medieval-gold"
              >
                {visualConfig.crests.available.map(crest => (
                  <option key={crest.id} value={crest.path}>
                    {crest.label}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-3 p-2 rounded bg-red-100 border border-red-300 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 justify-center">
          <button
            onClick={onBack}
            className="px-6 py-2 rounded font-medieval text-base bg-parchment-300 text-medieval-bronze hover:bg-parchment-400 transition-colors"
          >
            Back
          </button>
          
          <button
            onClick={handleStartGame}
            disabled={isLoading}
            className="btn-medieval px-6 py-2 rounded text-base"
          >
            {isLoading ? 'Creating...' : 'Start Game'}
          </button>
        </div>
      </div>
    </div>
  )
}

