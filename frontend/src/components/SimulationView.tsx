import { useState, useEffect, useRef } from 'react'
import { createSimulation, simulationStep, getWinner } from '../api/gameApi'
import { GameState, Player, PlayerConfig, PLAYER_COLORS, AI_TYPES, PlayerType } from '../types/game'
import { useGameStore } from '../store/gameStore'
import Board from './Board'

interface SimulationViewProps {
  onBack: () => void
}

interface SimulationLog {
  round: number
  player: string
  action: string
  message: string
}

export default function SimulationView({ onBack }: SimulationViewProps) {
  const [isConfiguring, setIsConfiguring] = useState(true)
  const [playerCount, setPlayerCount] = useState(4)
  const [players, setPlayers] = useState<PlayerConfig[]>([
    { name: 'Baron Alpha', player_type: 'ai_openai', color: PLAYER_COLORS[0] },
    { name: 'Baron Beta', player_type: 'ai_openai', color: PLAYER_COLORS[1] },
    { name: 'Baron Gamma', player_type: 'ai_openai', color: PLAYER_COLORS[2] },
    { name: 'Baron Delta', player_type: 'ai_openai', color: PLAYER_COLORS[3] },
  ])
  const [speed, setSpeed] = useState(1000)
  
  const [localGameState, setLocalGameState] = useState<GameState | null>(null)
  const { setGameState: setStoreGameState } = useGameStore()
  const [isRunning, setIsRunning] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [logs, setLogs] = useState<SimulationLog[]>([])
  const [winner, setWinner] = useState<Player | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const logsEndRef = useRef<HTMLDivElement>(null)
  const runningRef = useRef(false)

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handlePlayerCountChange = (count: number) => {
    setPlayerCount(count)
    const newPlayers = [...players]
    
    const aiTypes: PlayerType[] = ['ai_openai', 'ai_openai', 'ai_openai', 'ai_openai', 'ai_openai', 'ai_openai']  // All GPT by default
    const names = ['Baron GPT', 'Baron Claude', 'Baron Gemini', 'Baron Grok', 'Baron GPT-2', 'Baron Claude-2']
    
    while (newPlayers.length < count) {
      const idx = newPlayers.length
      newPlayers.push({
        name: names[idx],
        player_type: aiTypes[idx],
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

  const handleStartSimulation = async () => {
    setError(null)
    setLogs([])
    setWinner(null)
    
    try {
      const { state } = await createSimulation(players, speed)
      setLocalGameState(state)
      setStoreGameState(state)
      setIsConfiguring(false)
      setIsRunning(true)
      runningRef.current = true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start simulation')
    }
  }

  // Simulation loop
  useEffect(() => {
    if (!isRunning || isPaused || !localGameState || localGameState.phase === 'game_over') {
      return
    }

    const runStep = async () => {
      if (!runningRef.current) return
      
      try {
        const result = await simulationStep(localGameState.id)
        
        if (result.state) {
          setLocalGameState(result.state)
          setStoreGameState(result.state)
          
          if (result.action) {
            const player = result.state.players.find(
              (p: Player) => p.id === result.action?.player_id
            )
            setLogs(prev => [...prev, {
              round: result.state.current_round,
              player: player?.name || 'Unknown',
              action: result.action?.action_type || 'unknown',
              message: result.message || '',
            }])
          }
          
          if (result.state.phase === 'game_over' || result.status === 'game_over') {
            runningRef.current = false
            setIsRunning(false)
            
            const winnerResult = await getWinner(localGameState.id)
            if (winnerResult.winner) {
              setWinner(winnerResult.winner)
            }
          }
        }
      } catch (err) {
        console.error('Simulation step error:', err)
      }
    }

    const timer = setTimeout(runStep, speed)
    return () => clearTimeout(timer)
  }, [isRunning, isPaused, localGameState, speed, setStoreGameState])

  const handlePauseResume = () => {
    if (isPaused) {
      runningRef.current = true
      setIsPaused(false)
    } else {
      runningRef.current = false
      setIsPaused(true)
    }
  }

  const handleStop = () => {
    runningRef.current = false
    setIsRunning(false)
    setIsPaused(false)
  }

  // Configuration screen
  if (isConfiguring) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8">
        <div className="card-parchment rounded-lg p-8 max-w-2xl w-full">
          <h1 className="font-medieval text-3xl text-center mb-2 text-medieval-bronze">
            AI Simulation
          </h1>
          <p className="text-center text-medieval-stone mb-8">
            Watch AI players compete against each other
          </p>

          {/* Player count */}
          <div className="mb-6">
            <label className="block font-medieval text-lg mb-3 text-medieval-bronze">
              Number of AI Players
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
                  {count}
                </button>
              ))}
            </div>
          </div>

          {/* AI players */}
          <div className="space-y-3 mb-6">
            {players.map((player, index) => (
              <div 
                key={index}
                className="flex items-center gap-4 p-3 rounded bg-parchment-100 border border-parchment-300"
              >
                <div 
                  className="w-8 h-8 rounded-full border-2 border-parchment-400"
                  style={{ backgroundColor: player.color }}
                />
                <input
                  type="text"
                  value={player.name}
                  onChange={(e) => handlePlayerChange(index, 'name', e.target.value)}
                  className="flex-1 px-3 py-2 rounded border border-parchment-300 bg-white text-medieval-bronze"
                />
                <select
                  value={player.player_type}
                  onChange={(e) => handlePlayerChange(index, 'player_type', e.target.value as PlayerType)}
                  className="px-3 py-2 rounded border border-parchment-300 bg-white text-medieval-bronze"
                >
                  {AI_TYPES.filter(t => t.value !== 'human').map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          {/* Speed control */}
          <div className="mb-8">
            <label className="block font-medieval text-lg mb-3 text-medieval-bronze">
              Simulation Speed
            </label>
            <div className="flex items-center gap-4">
              <span className="text-sm text-medieval-stone">Fast</span>
              <input
                type="range"
                min={100}
                max={3000}
                step={100}
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-sm text-medieval-stone">Slow</span>
            </div>
            <p className="text-center text-sm text-medieval-stone mt-2">
              {speed}ms per action
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded bg-red-100 border border-red-300 text-red-700">
              {error}
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-4 justify-center">
            <button
              onClick={onBack}
              className="px-8 py-3 rounded font-medieval text-lg bg-parchment-300 text-medieval-bronze hover:bg-parchment-400"
            >
              Back
            </button>
            <button
              onClick={handleStartSimulation}
              className="btn-medieval px-8 py-3 rounded text-lg"
            >
              Start Simulation
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Simulation view
  return (
    <div className="min-h-screen p-4 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={onBack}
          className="px-4 py-2 text-parchment-300 hover:text-parchment-100"
        >
          ← Exit Simulation
        </button>
        
        <h1 className="font-medieval text-2xl text-parchment-100">
          AI Simulation
        </h1>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handlePauseResume}
            className="px-4 py-2 rounded bg-parchment-300 text-medieval-bronze hover:bg-parchment-400"
          >
            {isPaused ? '▶️ Resume' : '⏸️ Pause'}
          </button>
          <button
            onClick={handleStop}
            className="px-4 py-2 rounded bg-medieval-crimson text-white hover:bg-red-800"
          >
            ⏹️ Stop
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 grid grid-cols-12 gap-4">
        {/* Left - Player standings */}
        <div className="col-span-2 card-parchment rounded-lg p-4">
          <h3 className="font-medieval text-lg text-medieval-bronze mb-4">Standings</h3>
          
          {localGameState && (
            <div className="space-y-3">
              {[...localGameState.players]
                .sort((a, b) => b.prestige - a.prestige)
                .map((player, idx) => (
                  <div 
                    key={player.id}
                    className="flex items-center gap-2 p-2 bg-parchment-100 rounded"
                  >
                    <span className="font-medieval text-sm text-medieval-stone">
                      #{idx + 1}
                    </span>
                    <div 
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: player.color }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-medieval-bronze truncate">
                        {player.name}
                      </p>
                      <p className="text-xs text-medieval-stone">
                        {player.prestige} VP • {player.holdings.length} towns
                      </p>
                    </div>
                  </div>
                ))
              }
            </div>
          )}
          
          {localGameState && (
            <div className="mt-4 pt-4 border-t border-parchment-300">
              <p className="text-sm text-medieval-stone">
                Round: {localGameState.current_round}/{localGameState.max_rounds}
              </p>
              <p className="text-sm text-medieval-stone">
                Phase: {localGameState.phase}
              </p>
            </div>
          )}
        </div>

        {/* Center - Board */}
        <div className="col-span-7">
          <div className="aspect-square max-h-[calc(100vh-120px)] mx-auto">
            {localGameState && <Board onHoldingClick={() => {}} />}
          </div>
        </div>

        {/* Right - Action log */}
        <div className="col-span-3 card-parchment rounded-lg p-4 flex flex-col">
          <h3 className="font-medieval text-lg text-medieval-bronze mb-4">Action Log</h3>
          
          <div className="flex-1 overflow-y-auto space-y-2">
            {logs.map((log, idx) => (
              <div 
                key={idx}
                className="p-2 bg-parchment-100 rounded text-sm"
              >
                <div className="flex items-center gap-2 text-medieval-stone">
                  <span className="text-xs">R{log.round}</span>
                  <span className="font-medieval text-medieval-bronze">{log.player}</span>
                </div>
                <p className="text-medieval-stone">
                  {log.action.replace('_', ' ')}: {log.message}
                </p>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      {/* Winner modal */}
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
              Simulation Complete!
            </h2>
            
            <p className="text-xl text-medieval-stone mb-4">
              <span style={{ color: winner.color }}>{winner.name}</span> wins!
            </p>
            
            <p className="text-medieval-stone mb-6">
              Final Prestige: {winner.prestige} VP
            </p>
            
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => setIsConfiguring(true)}
                className="px-6 py-2 rounded bg-parchment-300 text-medieval-bronze hover:bg-parchment-400"
              >
                New Simulation
              </button>
              <button
                onClick={onBack}
                className="btn-medieval px-6 py-2 rounded"
              >
                Return to Menu
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

