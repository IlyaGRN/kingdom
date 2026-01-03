import { useGameStore } from '../store/gameStore'
import { Holding } from '../types/game'

interface BoardProps {
  onHoldingClick: (holding: Holding) => void
}

export default function Board({ onHoldingClick }: BoardProps) {
  const { gameState, selectedHolding, validActions } = useGameStore()

  if (!gameState) return null

  // Check if a holding is a valid attack target
  const isAttackable = (holdingId: string) => {
    return validActions.some(
      a => a.action_type === 'attack' && a.target_holding_id === holdingId
    )
  }

  // Check if a holding can be claimed (unowned town with valid claim)
  const isClaimable = (holdingId: string) => {
    return validActions.some(
      a => a.action_type === 'claim_town' && a.target_holding_id === holdingId
    )
  }

  // Format defense modifier for display
  const formatDefenseModifier = (modifier: number) => {
    if (modifier === 0) return ''
    return modifier > 0 ? `+${modifier}` : `${modifier}`
  }

  // Get owner color for a holding
  const getOwnerColor = (holding: Holding) => {
    if (!holding.owner_id) return 'bg-gray-400/50'
    const owner = gameState.players.find(p => p.id === holding.owner_id)
    if (!owner) return 'bg-gray-400/50'
    return '' // Will use inline style
  }

  const getOwnerStyle = (holding: Holding) => {
    if (!holding.owner_id) return { backgroundColor: 'rgba(128, 128, 128, 0.5)' }
    const owner = gameState.players.find(p => p.id === holding.owner_id)
    if (!owner) return { backgroundColor: 'rgba(128, 128, 128, 0.5)' }
    return { backgroundColor: owner.color }
  }

  return (
    <div className="relative w-full h-full">
      {/* Board image - you'll replace this with your actual board image */}
      <div className="absolute inset-0 bg-gradient-to-br from-parchment-200 via-parchment-300 to-parchment-400 rounded-lg">
        {/* Placeholder board pattern */}
        <svg className="w-full h-full opacity-20" viewBox="0 0 100 100">
          <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#8b5a2b" strokeWidth="0.5"/>
          </pattern>
          <rect width="100" height="100" fill="url(#grid)" />
        </svg>
      </div>

      {/* Holdings overlay */}
      {gameState.holdings.map(holding => (
        <div
          key={holding.id}
          onClick={() => onHoldingClick(holding)}
          className={`holding-marker ${getOwnerColor(holding)} ${
            selectedHolding?.id === holding.id ? 'selected' : ''
          } ${isAttackable(holding.id) ? 'attackable' : ''} ${
            isClaimable(holding.id) ? 'claimable' : ''
          }`}
          style={{
            left: `${holding.position_x * 100}%`,
            top: `${holding.position_y * 100}%`,
            ...getOwnerStyle(holding),
          }}
          title={`${holding.name} | Gold: ${holding.gold_value} | Soldiers: ${holding.soldier_value}${
            holding.defense_modifier !== 0 ? ` | Defense: ${formatDefenseModifier(holding.defense_modifier)}` : ''
          }${holding.attack_modifier !== 0 ? ` | Attack: +${holding.attack_modifier}` : ''}`}
        >
          {/* Holding content */}
          <div className="absolute inset-0 flex items-center justify-center transform -rotate-45">
            {/* Crown for king's castle */}
            {holding.holding_type === 'king_castle' && (
              <svg className="w-6 h-6 text-yellow-300" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm0 2h14v2H5v-2z"/>
              </svg>
            )}
            
            {/* Castle icon for county/duchy castles */}
            {(holding.holding_type === 'county_castle' || holding.holding_type === 'duchy_castle') && (
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 12h3v8h6v-6h2v6h6v-8h3L12 2zm0 2.8L18.2 11H17v7h-3v-6H10v6H7v-7H5.8L12 4.8z"/>
              </svg>
            )}
            
            {/* Town icon and stats */}
            {holding.holding_type === 'town' && (
              <div className="flex flex-col items-center">
                <div className="w-3 h-3 bg-white rounded-sm" />
              </div>
            )}
            
            {/* Fortification indicator (show count) */}
            {holding.fortification_count > 0 && (
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-yellow-400 rounded-full border border-yellow-600 flex items-center justify-center text-[8px] font-bold text-yellow-900">
                {holding.fortification_count}
              </div>
            )}
          </div>
          
          {/* Town stats overlay - shown below the marker for towns */}
          {holding.holding_type === 'town' && (
            <div className="absolute -bottom-5 left-1/2 transform -translate-x-1/2 flex gap-1 text-[9px] font-mono whitespace-nowrap bg-black/70 text-white px-1 rounded">
              <span className="text-yellow-400" title="Gold income">{holding.gold_value}g</span>
              <span className="text-red-400" title="Soldier income">{holding.soldier_value}s</span>
              {holding.defense_modifier !== 0 && (
                <span className={holding.defense_modifier > 0 ? 'text-green-400' : 'text-orange-400'} title="Defense modifier">
                  {formatDefenseModifier(holding.defense_modifier)}d
                </span>
              )}
              {holding.attack_modifier !== 0 && (
                <span className="text-purple-400" title="Attack modifier">+{holding.attack_modifier}a</span>
              )}
            </div>
          )}
        </div>
      ))}

      {/* Board labels */}
      <div className="absolute top-4 left-4 text-parchment-900 font-medieval text-lg opacity-50">
        County U
      </div>
      <div className="absolute top-4 right-4 text-parchment-900 font-medieval text-lg opacity-50">
        County V
      </div>
      <div className="absolute bottom-4 left-4 text-parchment-900 font-medieval text-lg opacity-50">
        County X
      </div>
      <div className="absolute bottom-4 right-4 text-parchment-900 font-medieval text-lg opacity-50">
        County Q
      </div>
      <div className="absolute top-1/2 left-1/4 text-parchment-900 font-medieval text-sm opacity-40 transform -translate-y-1/2">
        Duchy XU
      </div>
      <div className="absolute top-1/2 right-1/4 text-parchment-900 font-medieval text-sm opacity-40 transform -translate-y-1/2">
        Duchy QV
      </div>
    </div>
  )
}

