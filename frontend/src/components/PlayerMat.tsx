import { Player, Card, Holding, getArmyCap } from '../types/game'

interface PlayerMatProps {
  player: Player
  isCurrentPlayer: boolean
  cards: Record<string, Card>
  holdings: Holding[]
  onCardClick?: (cardId: string) => void
}

interface IncomeBreakdown {
  goldFromHoldings: number
  soldiersFromHoldings: number
  goldFromFortifications: number
  goldFromTitles: number
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

  // Calculate income breakdown
  const calculateIncome = (): IncomeBreakdown => {
    let goldFromHoldings = 0
    let soldiersFromHoldings = 0
    let goldFromFortifications = 0
    let goldFromTitles = 0

    // Income from player's holdings
    for (const holdingId of player.holdings) {
      const holding = holdings.find(h => h.id === holdingId)
      if (holding) {
        goldFromHoldings += holding.gold_value
        soldiersFromHoldings += holding.soldier_value

        // Fortification bonus: +2 gold per first fort, +5 for second
        if (holding.fortification_count >= 1) {
          goldFromFortifications += 2
        }
        if (holding.fortification_count >= 2) {
          goldFromFortifications += 5
        }
      }
    }

    // Title stipends
    if (player.is_king) {
      goldFromTitles = 8
    } else if (player.title === 'duke') {
      goldFromTitles = 4 * player.duchies.length
    } else if (player.title === 'count') {
      goldFromTitles = 2 * player.counties.length
    }

    return {
      goldFromHoldings,
      soldiersFromHoldings,
      goldFromFortifications,
      goldFromTitles,
      totalGold: goldFromHoldings + goldFromFortifications + goldFromTitles,
      totalSoldiers: soldiersFromHoldings,
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
        <div 
          className="w-10 h-10 rounded-full border-2 border-parchment-400 flex items-center justify-center"
          style={{ backgroundColor: player.color }}
        >
          {player.is_king && (
            <svg className="w-6 h-6 text-yellow-300" viewBox="0 0 24 24" fill="currentColor">
              <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5z"/>
            </svg>
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

      {/* Income per turn */}
      <div className="bg-parchment-100 rounded p-2 mb-3">
        <div className="text-xs font-medieval text-medieval-stone mb-1">Income per turn:</div>
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
        {/* Breakdown (collapsed by default, show on hover) */}
        <div className="mt-1 pt-1 border-t border-parchment-300 text-xs text-medieval-stone">
          <div className="flex justify-between">
            <span>From holdings:</span>
            <span>+{income.goldFromHoldings}g / +{income.soldiersFromHoldings}s</span>
          </div>
          {income.goldFromFortifications > 0 && (
            <div className="flex justify-between">
              <span>From fortifications:</span>
              <span>+{income.goldFromFortifications}g</span>
            </div>
          )}
          {income.goldFromTitles > 0 && (
            <div className="flex justify-between">
              <span>From titles:</span>
              <span>+{income.goldFromTitles}g</span>
            </div>
          )}
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
