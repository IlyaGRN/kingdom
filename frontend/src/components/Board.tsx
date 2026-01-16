import { useGameStore } from '../store/gameStore'
import { Holding } from '../types/game'
import { visualConfig, getUnoccupiedBackgroundColor, hexToRgba } from '../config/visualConfig'

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
    if (!holding.owner_id) return visualConfig.holdings.unoccupiedIconColor
    const owner = gameState.players.find(p => p.id === holding.owner_id)
    if (!owner) return visualConfig.holdings.unoccupiedIconColor
    return owner.color
  }

  // Get transparent background color based on owner's color
  const getBackgroundColor = (holding: Holding) => {
    if (!holding.owner_id) return getUnoccupiedBackgroundColor()
    const owner = gameState.players.find(p => p.id === holding.owner_id)
    if (!owner) return getUnoccupiedBackgroundColor()
    return hexToRgba(owner.color, true)
  }

  // Get crest image path for a holding's owner
  const getOwnerCrest = (holding: Holding): string | null => {
    if (!holding.owner_id) return null
    const owner = gameState.players.find(p => p.id === holding.owner_id)
    return owner?.crest || null
  }

  // Get crown image path for castle holdings
  const getCrownImage = (holdingType: string): string | null => {
    switch (holdingType) {
      case 'king_castle': return '/crown__king.png'
      case 'county_castle': return '/crown__count.png'
      case 'duchy_castle': return '/crown__duke.png'
      default: return null
    }
  }

  return (
    <div className="relative w-full h-full">
      {/* Board image */}
      <div className="absolute inset-0 rounded-lg overflow-hidden">
        <img 
          src="/board.png" 
          alt="Game Board" 
          className="w-full h-full object-contain"
          style={{ filter: `saturate(${visualConfig.board.saturation}%)` }}
        />
      </div>

      {/* County labels in corners */}
      <div className="absolute top-6 left-6">
        <span className="absolute font-medieval text-3xl text-black font-bold" style={{textShadow: '0 0 8px black, 0 0 16px black, 0 0 24px black'}}>U</span>
        <span className="absolute font-medieval text-2xl text-amber-100 blur-[1px]">U</span>
        <span className="relative font-medieval text-2xl text-amber-50 drop-shadow-lg font-bold">U</span>
      </div>
      <div className="absolute top-6 right-6">
        <span className="absolute font-medieval text-3xl text-black font-bold" style={{textShadow: '0 0 8px black, 0 0 16px black, 0 0 24px black'}}>V</span>
        <span className="absolute font-medieval text-2xl text-amber-100 blur-[1px]">V</span>
        <span className="relative font-medieval text-2xl text-amber-50 drop-shadow-lg font-bold">V</span>
      </div>
      <div className="absolute bottom-6 left-6">
        <span className="absolute font-medieval text-3xl text-black font-bold" style={{textShadow: '0 0 8px black, 0 0 16px black, 0 0 24px black'}}>X</span>
        <span className="absolute font-medieval text-2xl text-amber-100 blur-[1px]">X</span>
        <span className="relative font-medieval text-2xl text-amber-50 drop-shadow-lg font-bold">X</span>
      </div>
      <div className="absolute bottom-6 right-6">
        <span className="absolute font-medieval text-3xl text-black font-bold" style={{textShadow: '0 0 8px black, 0 0 16px black, 0 0 24px black'}}>Q</span>
        <span className="absolute font-medieval text-2xl text-amber-100 blur-[1px]">Q</span>
        <span className="relative font-medieval text-2xl text-amber-50 drop-shadow-lg font-bold">Q</span>
      </div>

      {/* Duchy labels on middle sides */}
      <div className="absolute top-1/2 left-10 -translate-y-1/2">
        <span className="absolute font-medieval text-base text-black font-bold" style={{textShadow: '0 0 5px black, 0 0 10px black'}}>XU</span>
        <span className="absolute font-medieval text-sm text-amber-100 blur-[1px]">XU</span>
        <span className="relative font-medieval text-sm text-amber-50 drop-shadow-lg font-bold">XU</span>
      </div>
      <div className="absolute top-1/2 right-10 -translate-y-1/2">
        <span className="absolute font-medieval text-base text-black font-bold" style={{textShadow: '0 0 5px black, 0 0 10px black'}}>QV</span>
        <span className="absolute font-medieval text-sm text-amber-100 blur-[1px]">QV</span>
        <span className="relative font-medieval text-sm text-amber-50 drop-shadow-lg font-bold">QV</span>
      </div>

      {/* Holdings overlay */}
      {gameState.holdings.map(holding => {
        const ownerCrest = getOwnerCrest(holding)
        const isOccupied = !!holding.owner_id && !!ownerCrest
        
        return (
          <div
            key={holding.id}
            onClick={() => onHoldingClick(holding)}
            className={`absolute cursor-pointer transition-all duration-200 -translate-x-1/2 -translate-y-1/2 hover:scale-110 hover:z-20 ${
              selectedHolding?.id === holding.id ? 'z-20 ring-2 ring-yellow-400' : 'z-10'
            } ${isAttackable(holding.id) ? 'animate-pulse' : ''} ${
              isClaimable(holding.id) ? 'ring-2 ring-green-400 ring-offset-1' : ''
            } ${!isOccupied ? 'holding-marker hover:brightness-125' : ''} ${
              !isOccupied && holding.holding_type === 'king_castle' ? 'hover:shadow-[0_0_20px_8px_rgba(251,191,36,0.6)]' : ''
            }`}
            style={{
              left: `${holding.position_x * 100}%`,
              top: `${holding.position_y * 100}%`,
              ...(isOccupied ? {} : {
                backgroundColor: getBackgroundColor(holding),
              }),
            }}
            title={`${holding.name}${holding.is_capitol ? ' ★ CAPITOL' : ''} | Gold: ${holding.gold_value} | Soldiers: ${holding.soldier_value}${
              holding.defense_modifier !== 0 ? ` | Defense: ${formatDefenseModifier(holding.defense_modifier)}` : ''
            }${holding.attack_modifier !== 0 ? ` | Attack: +${holding.attack_modifier}` : ''}${
              holding.is_capitol ? ' | Fortify for Count title!' : ''
            }`}
          >
            {/* Occupied holding - just show crest at diamond size */}
            {isOccupied && (
              <div className="relative">
                {/* Blurred circle background */}
                <div className="absolute inset-0 w-16 h-16 -translate-x-3 -translate-y-4 rounded-full bg-black/10 backdrop-blur-[2px] border-[3px] border-amber-400/85" />
                {/* Crown for castle holdings (70% saturation when occupied) */}
                {getCrownImage(holding.holding_type) && (
                  <img 
                    src={getCrownImage(holding.holding_type)!}
                    alt="Crown"
                    className={`absolute left-1/2 -translate-x-1/2 object-contain z-10 ${
                      holding.holding_type === 'county_castle' ? 'w-5 h-5 -top-4' : 'w-6 h-6 -top-5'
                    }`}
                    style={{ filter: 'saturate(70%)' }}
                  />
                )}
                <img 
                  src={ownerCrest} 
                  alt="Crest" 
                  className="relative w-10 h-10 object-contain drop-shadow-lg"
                />
                {/* Capitol star indicator (only show if not a castle with crown) */}
                {holding.is_capitol && !getCrownImage(holding.holding_type) && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 text-yellow-300 text-xs font-bold drop-shadow-md">
                    ★
                  </div>
                )}
                {/* Fortification indicators */}
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
            )}
            
            {/* Unoccupied holding - show rectangle with icon */}
            {!isOccupied && (
              <div className="absolute inset-0 flex items-center justify-center">
                {/* Crown images for castle holdings (grayscale when unoccupied) */}
                {getCrownImage(holding.holding_type) && (
                  <img 
                    src={getCrownImage(holding.holding_type)!}
                    alt="Crown"
                    className={holding.holding_type === 'county_castle' ? 'w-7 h-7 object-contain' : 'w-8 h-8 object-contain'}
                    style={{ filter: 'saturate(0)' }}
                  />
                )}
                
                {/* Town icon */}
                {holding.holding_type === 'town' && (
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: getIconColor(holding) }} />
                    {holding.is_capitol && (
                      <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 text-yellow-300 text-[10px] font-bold drop-shadow-md" title="Capitol - Fortify for Count title!">
                        ★
                      </div>
                    )}
                  </div>
                )}
                
                {/* Fortification indicators for unoccupied */}
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
            )}
            
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
        )
      })}

    </div>
  )
}

