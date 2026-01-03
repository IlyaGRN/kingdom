interface MainMenuProps {
  onStartGame: () => void
  onStartSimulation: () => void
}

export default function MainMenu({ onStartGame, onStartSimulation }: MainMenuProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      {/* Decorative background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-0 w-96 h-96 bg-medieval-gold/5 rounded-full blur-3xl transform -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-medieval-crimson/5 rounded-full blur-3xl transform translate-x-1/2 translate-y-1/2" />
      </div>

      {/* Main content */}
      <div className="relative z-10 text-center">
        {/* Crown icon */}
        <div className="mb-6">
          <svg 
            className="w-24 h-24 mx-auto text-medieval-gold crown-pulse" 
            viewBox="0 0 24 24" 
            fill="currentColor"
          >
            <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm0 2h14v2H5v-2z"/>
          </svg>
        </div>

        {/* Title */}
        <h1 className="font-medieval text-6xl md:text-7xl text-parchment-100 mb-2 tracking-wider">
          Machiavelli's
        </h1>
        <h2 className="font-medieval text-5xl md:text-6xl text-medieval-gold mb-4 tracking-widest">
          KINGDOM
        </h2>
        
        {/* Subtitle */}
        <p className="text-parchment-300 text-xl mb-12 font-body italic">
          A Medieval Strategy Board Game
        </p>

        {/* Decorative divider */}
        <div className="flex items-center justify-center gap-4 mb-12">
          <div className="h-px w-24 bg-gradient-to-r from-transparent to-medieval-gold/50" />
          <div className="w-3 h-3 rotate-45 border border-medieval-gold/50" />
          <div className="h-px w-24 bg-gradient-to-l from-transparent to-medieval-gold/50" />
        </div>

        {/* Menu buttons */}
        <div className="flex flex-col gap-4 items-center">
          <button
            onClick={onStartGame}
            className="btn-medieval text-xl px-12 py-4 min-w-[280px] rounded"
          >
            New Game
          </button>
          
          <button
            onClick={onStartSimulation}
            className="btn-medieval text-xl px-12 py-4 min-w-[280px] rounded"
          >
            AI Simulation
          </button>

          <button
            disabled
            className="btn-medieval text-xl px-12 py-4 min-w-[280px] rounded opacity-50 cursor-not-allowed"
            title="Coming in Stage 2"
          >
            Multiplayer (Coming Soon)
          </button>
        </div>

        {/* Game info */}
        <div className="mt-16 text-parchment-400 text-sm">
          <p>4-6 Players • 90-120 minutes</p>
          <p className="mt-1">Conquer towns, claim titles, seize the crown</p>
        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-4 text-parchment-500 text-xs">
        Version 1.0 • Rules V2
      </div>
    </div>
  )
}



