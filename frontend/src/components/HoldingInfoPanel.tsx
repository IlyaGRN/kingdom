import { Holding, HoldingType, Player } from '../types/game'
import { visualConfig } from '../config/visualConfig'

interface HoldingInfoPanelProps {
  holding: Holding
  players: Player[]
}

/**
 * Get the cover image path for a holding based on its ID and type
 */
function getHoldingCoverPath(holdingId: string, holdingType: HoldingType): string {
  if (holdingType === 'town') {
    return `/holding_covers/${holdingId}.png`
  }
  if (holdingType === 'county_castle') {
    // x_castle -> castle_county_x
    const letter = holdingId.replace('_castle', '')
    return `/holding_covers/castle_county_${letter}.png`
  }
  if (holdingType === 'duchy_castle') {
    // xu_castle -> castle_duchy_xu
    const letters = holdingId.replace('_castle', '')
    return `/holding_covers/castle_duchy_${letters}.png`
  }
  if (holdingType === 'king_castle') {
    return `/holding_covers/castle_king.png`
  }
  return ''
}

/**
 * Format defense/attack modifier for display
 */
function formatModifier(value: number): string {
  if (value === 0) return ''
  return value > 0 ? `+${value}` : `${value}`
}

/**
 * Get the vertical position for a holding's cover image
 */
function getCoverVerticalPosition(holdingId: string): string {
  const position = visualConfig.holdingCovers.verticalPosition[holdingId] 
    ?? visualConfig.holdingCovers.defaultPosition
  return `center ${position}%`
}

export default function HoldingInfoPanel({ holding, players }: HoldingInfoPanelProps) {
  const coverPath = getHoldingCoverPath(holding.id, holding.holding_type)
  
  // Get the owner of this holding
  const owner = holding.owner_id 
    ? players.find(p => p.id === holding.owner_id) 
    : null

  // Build list of fort slots (always 3)
  // Each slot contains the player who placed that fortification, or null if empty
  const fortSlots: (Player | null)[] = [null, null, null]
  let slotIndex = 0
  Object.entries(holding.fortifications_by_player || {}).forEach(([playerId, count]) => {
    const player = players.find(p => p.id === playerId)
    for (let i = 0; i < (count as number) && slotIndex < 3; i++) {
      fortSlots[slotIndex++] = player || null
    }
  })

  // Determine holding type label
  const getTypeLabel = (): string => {
    switch (holding.holding_type) {
      case 'town': return 'Town'
      case 'county_castle': return 'County Castle'
      case 'duchy_castle': return 'Duchy Castle'
      case 'king_castle': return 'King\'s Castle'
      default: return 'Holding'
    }
  }

  return (
    <div className="mb-4 rounded-lg overflow-hidden bg-parchment-200 border border-parchment-400 shadow-md">
      {/* Cover image with name overlay */}
      <div className="relative">
        <img 
          src={coverPath} 
          alt={holding.name}
          className="w-full h-36 object-cover"
          style={{ objectPosition: getCoverVerticalPosition(holding.id) }}
          onError={(e) => {
            // Fallback if image doesn't exist
            e.currentTarget.style.display = 'none'
          }}
        />
        {/* Gradient overlay for text readability */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
        
        {/* Holding name and type */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <h3 className="font-medieval text-lg text-white drop-shadow-lg">
            {holding.name}
            {holding.is_capitol && (
              <span className="ml-2 text-yellow-300" title="Capitol - Fortify for Count title!">★</span>
            )}
          </h3>
          <p className="text-xs text-parchment-200 drop-shadow">
            {getTypeLabel()}
            {holding.county && ` • County ${holding.county}`}
            {holding.duchy && ` • Duchy ${holding.duchy}`}
          </p>
        </div>

        {/* Owner badge (top-right) */}
        {owner && (
          <div 
            className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded bg-black/50 backdrop-blur-sm"
          >
            <img 
              src={owner.crest} 
              alt={owner.name} 
              className="w-5 h-5 object-contain"
            />
            <span className="text-xs text-white font-medium">{owner.name}</span>
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="px-3 py-2 flex items-center justify-around bg-parchment-100 border-b border-parchment-300">
        {/* Gold */}
        <div className="flex items-center gap-1" title="Gold income per turn">
          <span className="text-yellow-600 text-sm">💰</span>
          <span className="text-sm font-medium text-medieval-stone">{holding.gold_value}</span>
        </div>

        {/* Soldiers */}
        <div className="flex items-center gap-1" title="Soldier recruitment per turn">
          <span className="text-red-600 text-sm">⚔️</span>
          <span className="text-sm font-medium text-medieval-stone">{holding.soldier_value}</span>
        </div>

        {/* Defense modifier (only show if non-zero) */}
        {holding.defense_modifier !== 0 && (
          <div 
            className="flex items-center gap-1" 
            title={`Defense modifier: ${formatModifier(holding.defense_modifier)}`}
          >
            <span className="text-blue-600 text-sm">🛡️</span>
            <span className={`text-sm font-medium ${holding.defense_modifier > 0 ? 'text-green-600' : 'text-orange-600'}`}>
              {formatModifier(holding.defense_modifier)}
            </span>
          </div>
        )}

        {/* Attack modifier (only show if non-zero) */}
        {holding.attack_modifier !== 0 && (
          <div 
            className="flex items-center gap-1" 
            title={`Attack modifier: +${holding.attack_modifier}`}
          >
            <span className="text-purple-600 text-sm">🗡️</span>
            <span className="text-sm font-medium text-purple-600">
              +{holding.attack_modifier}
            </span>
          </div>
        )}
      </div>

      {/* Fortifications section */}
      <div className="px-3 py-2">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-medieval-stone uppercase tracking-wide">
            Fortifications
          </span>
          <span className="text-xs text-medieval-stone/70">
            {holding.fortification_count}/3
          </span>
        </div>
        
        {/* Three fortification slots */}
        <div className="flex items-center justify-center gap-3">
          {fortSlots.map((player, idx) => (
            <div
              key={idx}
              className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
                player 
                  ? 'bg-parchment-50 shadow-inner' 
                  : 'border-2 border-dashed border-parchment-400/50 bg-parchment-100/50'
              }`}
              style={player ? { borderWidth: 2, borderStyle: 'solid', borderColor: player.color } : undefined}
              title={player ? `${player.name}'s fortification` : 'Empty slot'}
            >
              {player ? (
                <img 
                  src={player.crest} 
                  alt={player.name}
                  className="w-7 h-7 object-contain"
                />
              ) : (
                <span className="text-parchment-400 text-lg">🏰</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
