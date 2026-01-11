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

  // Get icon color for a holding based on owner
  const getIconColor = (holding: Holding) => {
    if (!holding.owner_id) return 'rgba(128, 128, 128, 0.8)'
    const owner = gameState.players.find(p => p.id === holding.owner_id)
    if (!owner) return 'rgba(128, 128, 128, 0.8)'
    return owner.color
  }

  return (
    <div className="relative w-full h-full">
      {/* Board image */}
      <div className="absolute inset-0 rounded-lg overflow-hidden">
        <img 
          src="/board.png" 
          alt="Game Board" 
          className="w-full h-full object-contain"
        />
      </div>

      {/* Holdings overlay */}
      {gameState.holdings.map(holding => (
        <div
          key={holding.id}
          onClick={() => onHoldingClick(holding)}
          className={`holding-marker ${
            selectedHolding?.id === holding.id ? 'selected' : ''
          } ${isAttackable(holding.id) ? 'attackable' : ''} ${
            isClaimable(holding.id) ? 'claimable' : ''
          }`}
          style={{
            left: `${holding.position_x * 100}%`,
            top: `${holding.position_y * 100}%`,
            backgroundColor: 'rgba(30, 30, 30, 0.4)',
          }}
          title={`${holding.name}${holding.is_capitol ? ' ★ CAPITOL' : ''} | Gold: ${holding.gold_value} | Soldiers: ${holding.soldier_value}${
            holding.defense_modifier !== 0 ? ` | Defense: ${formatDefenseModifier(holding.defense_modifier)}` : ''
          }${holding.attack_modifier !== 0 ? ` | Attack: +${holding.attack_modifier}` : ''}${
            holding.is_capitol ? ' | Fortify for Count title!' : ''
          }`}
        >
          {/* Holding content */}
          <div className="absolute inset-0 flex items-center justify-center transform -rotate-45">
            {/* Crown for king's castle */}
            {holding.holding_type === 'king_castle' && (
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill={getIconColor(holding)}>
                <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm0 2h14v2H5v-2z"/>
              </svg>
            )}
            
            {/* Castle icon for county/duchy castles */}
            {(holding.holding_type === 'county_castle' || holding.holding_type === 'duchy_castle') && (
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill={getIconColor(holding)}>
                <path d="M12 2L2 12h3v8h6v-6h2v6h6v-8h3L12 2zm0 2.8L18.2 11H17v7h-3v-6H10v6H7v-7H5.8L12 4.8z"/>
              </svg>
            )}
            
            {/* Town icon and stats */}
            {holding.holding_type === 'town' && (
              <div className="flex flex-col items-center">
                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: getIconColor(holding) }} />
                {/* Capitol star indicator */}
                {holding.is_capitol && (
                  <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 text-yellow-300 text-[10px] font-bold drop-shadow-md" title="Capitol - Fortify for Count title!">
                    ★
                  </div>
                )}
              </div>
            )}
            
            {/* Fortification indicators - colored circles per player */}
            {holding.fortification_count > 0 && holding.fortifications_by_player && (
              <div className="absolute -top-1 -right-1 flex flex-wrap gap-[1px] max-w-[24px]">
                {Object.entries(holding.fortifications_by_player).map(([playerId, count]) => {
                  const fortPlayer = gameState.players.find(p => p.id === playerId)
                  const color = fortPlayer?.color ?? '#888888'
                  return Array.from({ length: count as number }).map((_, idx) => (
                    <div
                      key={`${playerId}-${idx}`}
                      className="w-[6px] h-[6px] rounded-full border border-white/50"
                      style={{ backgroundColor: color }}
                      title={`${fortPlayer?.name ?? 'Unknown'}'s fortification`}
                    />
                  ))
                })}
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

    </div>
  )
}

