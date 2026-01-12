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
      className={`card-parchment rounded-lg p-4 transition-all ${
        isCurrentPlayer ? 'ring-2 ring-medieval-gold shadow-lg' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-shrink-0">
          <img 
            src={player.crest}
            alt={`${player.name}'s crest`}
            className="w-10 h-10 object-contain"
          />
          {player.is_king && (
            <div className="absolute -top-1 -right-1">
              <svg className="w-4 h-4 text-yellow-400 drop-shadow-md" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5z"/>
              </svg>
            </div>
          )}
        </div>
        <div className="flex-1">
          <h3 className="font-medieval text-lg text-medieval-bronze">
            {player.name}
          </h3>
          <p className="text-sm text-medieval-stone">
            {getTitleDisplay()}
            {player.counties.length > 0 && ` of ${player.counties.join(', ')}`}
            {player.duchies.length > 0 && ` • Duke of ${player.duchies.join(', ')}`}
          </p>
        </div>
        {isCurrentPlayer && (
          <span className="px-2 py-1 bg-medieval-gold text-white text-xs rounded font-medieval">
            YOUR TURN
          </span>
        )}
      </div>

      {/* Resources */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {/* Gold */}
        <div className="text-center p-2 bg-parchment-100 rounded">
          <div className="text-2xl font-medieval text-medieval-gold">
            {player.gold}
          </div>
          <div className="text-xs text-medieval-stone">Gold</div>
        </div>

        {/* Soldiers */}
        <div className={`text-center p-2 rounded ${isOverCap ? 'bg-red-100' : 'bg-parchment-100'}`}>
          <div className={`text-2xl font-medieval ${isOverCap ? 'text-medieval-crimson' : 'text-medieval-bronze'}`}>
            {player.soldiers}
          </div>
          <div className="text-xs text-medieval-stone">
            Soldiers {isOverCap && `(cap: ${armyCap})`}
          </div>
        </div>

        {/* Prestige */}
        <div className="text-center p-2 bg-parchment-100 rounded">
          <div className="text-2xl font-medieval text-medieval-navy">
            {player.prestige}
          </div>
          <div className="text-xs text-medieval-stone">VP</div>
        </div>
      </div>

      {/* Income per turn - with hover tooltip for breakdown */}
      <div className="bg-parchment-100 rounded p-2 mb-3 relative group cursor-help">
        <div className="text-xs font-medieval text-medieval-stone mb-1">
          Income per turn: <span className="text-medieval-stone/50">(hover for details)</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between">
            <span className="text-medieval-stone">💰 Gold:</span>
            <span className="font-medieval text-medieval-gold">+{income.totalGold}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-medieval-stone">⚔️ Soldiers:</span>
            <span className="font-medieval text-medieval-bronze">+{income.totalSoldiers}</span>
          </div>
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
      <div className="flex items-center justify-between text-sm mb-3 px-1">
        <span className="text-medieval-stone">Holdings:</span>
        <span className="font-medieval text-medieval-bronze">{player.holdings.length}</span>
      </div>
      <div className="flex items-center justify-between text-sm mb-3 px-1">
        <span className="text-medieval-stone">Fortifications:</span>
        <span className="font-medieval text-medieval-bronze">{player.fortifications_placed}/4</span>
      </div>

      {/* Active effects */}
      {player.active_effects && player.active_effects.length > 0 && (
        <div className="text-sm text-purple-700 bg-purple-50 p-2 rounded mb-3">
          ✨ Active: {player.active_effects.join(', ')}
        </div>
      )}

      {/* Big War effect indicator */}
      {player.has_big_war_effect && (
        <div className="text-sm text-amber-700 bg-amber-50 p-2 rounded mb-3">
          ⚔️ Big War: Army cap doubled!
        </div>
      )}

      {/* Hand (only show if current player) */}
      {isCurrentPlayer && player.hand.length > 0 && (
        <div className="mt-4 border-t border-parchment-300 pt-3">
          <h4 className="text-sm font-medieval text-medieval-stone mb-2">
            Your Hand ({player.hand.length}/7)
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {player.hand.map(cardId => {
              const card = cards[cardId]
              if (!card) return null
              return (
                <button
                  key={cardId}
                  onClick={() => onCardClick?.(cardId)}
                  className="w-full text-left p-2 bg-parchment-100 rounded hover:bg-parchment-200 transition-colors"
                >
                  <div className="font-medieval text-sm text-medieval-bronze">
                    {getCardTypeIcon(card)} {card.name}
                  </div>
                  <div className="text-xs text-medieval-stone truncate">
                    {card.description}
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
