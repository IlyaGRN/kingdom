import { Player, Card, Holding, getArmyCap } from '../types/game'

interface PlayerMatProps {
  player: Player
  isCurrentPlayer: boolean
  cards: Record<string, Card>
  holdings: Holding[]
  onCardClick?: (cardId: string) => void
}

interface HoldingIncome {
  name: string
  gold: number
  soldiers: number
  fortBonus: number  // Gold from fortifications on this holding
}

interface IncomeBreakdown {
  holdingDetails: HoldingIncome[]
  goldFromTitles: number
  titleDetails: string  // e.g., "King (+8)" or "Count of X, U (+4)"
  totalGold: number
  totalSoldiers: number
}

export default function PlayerMat({ player, isCurrentPlayer, cards, holdings, onCardClick }: PlayerMatProps) {
  // Determine crown based on player's title
  const getCrownForTitle = () => {
    if (player.is_king) return '/crown__king.png'
    if (player.title === 'duke') return '/crown__duke.png'
    if (player.title === 'count') return '/crown__count.png'
    return null // Baron has no crown
  }

  const crownImage = getCrownForTitle()

  const getTitleDisplay = () => {
    if (player.is_king) return 'King'
    if (player.title === 'duke') return 'Duke'
    if (player.title === 'count') return 'Count'
    return 'Baron'
  }

  const armyCap = getArmyCap(player.title, player.has_big_war_effect)
  const isOverCap = player.soldiers > armyCap

  // Calculate income breakdown with per-holding details
  const calculateIncome = (): IncomeBreakdown => {
    const holdingDetails: HoldingIncome[] = []
    let totalGold = 0
    let totalSoldiers = 0
    let goldFromTitles = 0
    let titleDetails = ''

    // Income from player's holdings
    for (const holdingId of player.holdings) {
      const holding = holdings.find(h => h.id === holdingId)
      if (holding) {
        // Fortification bonus: only from THIS PLAYER'S fortifications on THEIR OWN towns
        // +2 gold for first fort, +5 for second = +7 total for 2 forts
        const playerForts = holding.fortifications_by_player?.[player.id] ?? 0
        let fortBonus = 0
        if (playerForts >= 1) fortBonus += 2
        if (playerForts >= 2) fortBonus += 5

        holdingDetails.push({
          name: holding.name,
          gold: holding.gold_value,
          soldiers: holding.soldier_value,
          fortBonus,
        })

        totalGold += holding.gold_value + fortBonus
        totalSoldiers += holding.soldier_value
      }
    }

    // Title stipends
    if (player.is_king) {
      goldFromTitles = 8
      titleDetails = 'King (+8g)'
    } else if (player.title === 'duke') {
      goldFromTitles = 4 * player.duchies.length
      titleDetails = `Duke of ${player.duchies.join(', ')} (+${goldFromTitles}g)`
    } else if (player.title === 'count') {
      goldFromTitles = 2 * player.counties.length
      titleDetails = `Count of ${player.counties.join(', ')} (+${goldFromTitles}g)`
    }

    totalGold += goldFromTitles

    return {
      holdingDetails,
      goldFromTitles,
      titleDetails,
      totalGold,
      totalSoldiers,
    }
  }

  const income = calculateIncome()

  const getCardTypeIcon = (card: Card): string => {
    switch (card.card_type) {
      case 'personal_event': return '⚡'
      case 'global_event': return '🌍'
      case 'bonus': return '✨'
      case 'claim': return '📜'
      default: return '🃏'
    }
  }

  return (
    <div 
      className={`card-parchment rounded-lg p-2 transition-all ${
        isCurrentPlayer ? 'ring-2 ring-medieval-gold shadow-lg' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="relative flex-shrink-0">
          {/* Crown indicator based on player's title */}
          {crownImage && (
            <img 
              src={crownImage}
              alt="Crown"
              className="absolute -top-2 left-1/2 -translate-x-1/2 w-3 h-3 object-contain drop-shadow-md z-10"
              style={{ filter: 'saturate(70%)' }}
            />
          )}
          <img 
            src={player.crest}
            alt={`${player.name}'s crest`}
            className="w-7 h-7 object-contain"
          />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medieval text-sm text-medieval-bronze truncate">
            {player.name}
          </h3>
          <p className="text-[10px] text-medieval-stone truncate">
            {getTitleDisplay()}
            {player.counties.length > 0 && ` of ${player.counties.join(', ')}`}
            {player.duchies.length > 0 && ` • Duke of ${player.duchies.join(', ')}`}
          </p>
        </div>
        {isCurrentPlayer && (
          <span className="px-1.5 py-0.5 bg-medieval-gold text-white text-[10px] rounded font-medieval">
            TURN
          </span>
        )}
      </div>

      {/* Resources */}
      <div className="grid grid-cols-3 gap-1 mb-2">
        {/* Gold */}
        <div className="text-center p-1 bg-parchment-100 rounded">
          <div className="text-base font-medieval text-medieval-gold">
            {player.gold}
          </div>
          <div className="text-[9px] text-medieval-stone">Gold</div>
        </div>

        {/* Soldiers */}
        <div className={`text-center p-1 rounded ${isOverCap ? 'bg-red-100' : 'bg-parchment-100'}`}>
          <div className={`text-base font-medieval ${isOverCap ? 'text-medieval-crimson' : 'text-medieval-bronze'}`}>
            {player.soldiers}
          </div>
          <div className="text-[9px] text-medieval-stone">
            Army {isOverCap && `(${armyCap})`}
          </div>
        </div>

        {/* Prestige */}
        <div className="text-center p-1 bg-parchment-100 rounded">
          <div className="text-base font-medieval text-medieval-navy">
            {player.prestige}
          </div>
          <div className="text-[9px] text-medieval-stone">VP</div>
        </div>
      </div>

      {/* Income per turn - with hover tooltip for breakdown */}
      <div className="bg-parchment-100 rounded p-1.5 mb-2 relative group cursor-help">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-medieval-stone">Income/turn:</span>
          <span>
            <span className="font-medieval text-medieval-gold">+{income.totalGold}g</span>
            <span className="font-medieval text-medieval-bronze ml-1">+{income.totalSoldiers}s</span>
          </span>
        </div>
        {/* Hover tooltip with per-holding breakdown */}
        <div className="absolute left-0 right-0 top-full mt-1 hidden group-hover:block z-10">
          <div className="bg-gray-900 text-white text-xs rounded p-3 shadow-lg mx-1 max-h-64 overflow-y-auto">
            <div className="font-bold mb-2 text-center border-b border-gray-700 pb-1">Income Breakdown</div>
            
            {/* Per-holding breakdown */}
            {income.holdingDetails.length > 0 ? (
              <div className="mb-2">
                <div className="font-bold text-parchment-300 mb-1">Holdings:</div>
                {income.holdingDetails.map((h, idx) => (
                  <div key={idx} className="flex justify-between pl-2 py-0.5 border-b border-gray-800 last:border-0">
                    <span className="truncate mr-2">{h.name}</span>
                    <span className="whitespace-nowrap">
                      <span className="text-medieval-gold">+{h.gold + h.fortBonus}g</span>
                      {h.fortBonus > 0 && <span className="text-gray-400 text-[10px]"> (fort +{h.fortBonus})</span>}
                      <span className="text-medieval-bronze ml-1">+{h.soldiers}s</span>
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-center mb-2">No holdings</div>
            )}
            
            {/* Title income */}
            {income.goldFromTitles > 0 && (
              <div className="flex justify-between pl-2 pt-1 border-t border-gray-700">
                <span>{income.titleDetails}</span>
              </div>
            )}
            
            {/* Totals */}
            <div className="mt-2 pt-2 border-t border-gray-600">
              <div className="flex justify-between font-bold">
                <span>Total:</span>
                <span>
                  <span className="text-medieval-gold">+{income.totalGold}g</span>
                  <span className="text-medieval-bronze ml-1">+{income.totalSoldiers}s</span>
                </span>
              </div>
            </div>
            
            {/* Army cap info */}
            <div className="mt-2 pt-2 border-t border-gray-700 text-gray-400">
              <div className="flex justify-between">
                <span>Army cap:</span>
                <span>{armyCap}</span>
              </div>
              {isOverCap && (
                <div className="text-red-400 text-center mt-1">
                  ⚠️ Over cap! Excess lost at upkeep
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Holdings & Fortifications */}
      <div className="flex items-center justify-between text-[10px] mb-1 px-0.5">
        <span className="text-medieval-stone">Holdings:</span>
        <span className="font-medieval text-medieval-bronze">{player.holdings.length}</span>
      </div>
      <div className="flex items-center justify-between text-[10px] mb-1 px-0.5">
        <span className="text-medieval-stone">Forts:</span>
        <span className="font-medieval text-medieval-bronze">{player.fortifications_placed}/4</span>
      </div>

      {/* Active effects */}
      {player.active_effects && player.active_effects.length > 0 && (
        <div className="text-[10px] text-purple-700 bg-purple-50 p-1 rounded mb-1">
          ✨ {player.active_effects.join(', ')}
        </div>
      )}

      {/* Big War effect indicator */}
      {player.has_big_war_effect && (
        <div className="text-[10px] text-amber-700 bg-amber-50 p-1 rounded mb-1">
          ⚔️ Army cap doubled
        </div>
      )}

      {/* Hand (only show if current player) */}
      {isCurrentPlayer && player.hand.length > 0 && (
        <div className="mt-2 border-t border-parchment-300 pt-2">
          <h4 className="text-[10px] font-medieval text-medieval-stone mb-1">
            Hand ({player.hand.length}/7)
          </h4>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {player.hand.map(cardId => {
              const card = cards[cardId]
              if (!card) return null
              return (
                <button
                  key={cardId}
                  onClick={() => onCardClick?.(cardId)}
                  className="w-full text-left p-1.5 bg-parchment-100 rounded hover:bg-parchment-200 transition-colors"
                >
                  <div className="font-medieval text-[11px] text-medieval-bronze truncate">
                    {getCardTypeIcon(card)} {card.name}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
