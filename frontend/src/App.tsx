import { useState } from 'react'
import { useGameStore } from './store/gameStore'
import MainMenu from './components/MainMenu'
import GameSetup from './components/GameSetup'
import GameBoard from './components/GameBoard'
import SimulationView from './components/SimulationView'

type Screen = 'menu' | 'setup' | 'game' | 'simulation'

function App() {
  const [screen, setScreen] = useState<Screen>('menu')
  const { gameState, resetGame } = useGameStore()

  const handleStartGame = () => {
    setScreen('setup')
  }

  const handleStartSimulation = () => {
    setScreen('simulation')
  }

  const handleGameCreated = () => {
    setScreen('game')
  }

  const handleBackToMenu = () => {
    resetGame()
    setScreen('menu')
  }

  return (
    <div className="min-h-screen">
      {screen === 'menu' && (
        <MainMenu 
          onStartGame={handleStartGame} 
          onStartSimulation={handleStartSimulation}
        />
      )}
      
      {screen === 'setup' && (
        <GameSetup 
          onGameCreated={handleGameCreated}
          onBack={handleBackToMenu}
        />
      )}
      
      {screen === 'game' && gameState && (
        <GameBoard onBack={handleBackToMenu} />
      )}

      {screen === 'simulation' && (
        <SimulationView onBack={handleBackToMenu} />
      )}
    </div>
  )
}

export default App

