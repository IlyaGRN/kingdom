import { useState } from 'react'
import { Holding, Player, Card, PendingCombat, COMBAT_CARD_EFFECTS } from '../types/game'

interface DefenseModalProps {
  pendingCombat: PendingCombat
  targetHolding: Holding
  attacker: Player
  defender: Player
  cards: Record<string, Card>
  holdings: Holding[]
  onDefend: (soldiers: number, cardIds: string[]) => void
}

export default function DefenseModal({
  pendingCombat,
  targetHolding,
  attacker,
  defender,
  cards,
  holdings,
  onDefend,
}: DefenseModalProps) {
  const [soldiersToCommit, setSoldiersToCommit] = useState(defender.soldiers)
  const [selectedCards, setSelectedCards] = useState<string[]>([])

  const maxSoldiers = defender.soldiers

  // Get combat-applicable cards from defender's hand
  const combatCards = defender.hand
    .map(cardId => cards[cardId])
    .filter(card => card && COMBAT_CARD_EFFECTS.includes(card.effect))

  // Get attacker's card names for display
  const attackerCardNames = pendingCombat.attacker_cards
    .map(cardId => cards[cardId]?.name)
    .filter(Boolean)

  // Get source holding for attack bonus display
  const sourceHolding = pendingCombat.source_holding_id 
    ? holdings.find(h => h.id === pendingCombat.source_holding_id) 
    : null
  
  // Calculate attack bonus: attack_modifier + fortification bonus
  const fortCount = sourceHolding?.fortification_count || 0
  const fortAttackBonus = (fortCount >= 1 ? 1 : 0) + (fortCount >= 2 ? 2 : 0) + (fortCount >= 3 ? 2 : 0)
  const attackBonus = (sourceHolding?.attack_modifier || 0) + fortAttackBonus

  const toggleCard = (cardId: string) => {
    setSelectedCards(prev =>
      prev.includes(cardId)
        ? prev.filter(id => id !== cardId)
        : [...prev, cardId]
    )
  }

  const handleDefend = () => {
    onDefend(soldiersToCommit, selectedCards)
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card-parchment rounded-lg p-6 max-w-lg w-full mx-4 shadow-2xl border-4 border-red-600">
        {/* Header */}
        <div className="text-center mb-4">
          <h2 className="font-medieval text-2xl text-medieval-crimson mb-3">
            🛡️ Under Attack!
          </h2>
          
          {/* Combatants with crests */}
          <div className="flex items-center justify-center gap-4">
            {/* Attacker */}
            <div className="flex items-center gap-2">
              <img 
                src={attacker.crest} 
                alt={attacker.name}
                className="w-10 h-10 object-contain"
              />
              <span className="font-medieval text-red-600">{attacker.name}</span>
            </div>
            
            <span className="text-2xl font-medieval text-medieval-stone">→</span>
            
            {/* Defender (you) */}
            <div className="flex items-center gap-2">
              <img 
                src={defender.crest} 
                alt={defender.name}
                className="w-10 h-10 object-contain"
              />
              <span className="font-medieval text-medieval-bronze">{defender.name}</span>
            </div>
          </div>
          
          <p className="text-sm text-medieval-stone mt-2">
            Target: <span className="font-bold text-medieval-bronze">{targetHolding.name}</span>
          </p>
        </div>

        {/* Attacker info */}
        <div className="bg-red-50 rounded p-3 mb-4 border border-red-200">
          <h3 className="font-medieval text-sm text-red-700 mb-2">Enemy Forces:</h3>
          <div className="text-sm text-medieval-stone">
            <div>⚔️ Soldiers committed: <span className="font-bold">{pendingCombat.attacker_soldiers}</span></div>
            {attackBonus > 0 && (
              <div>🏹 Attack bonus ({sourceHolding?.name}): +{attackBonus}</div>
            )}
            {attackerCardNames.length > 0 && (
              <div className="mt-1">
                ✨ Using cards: {attackerCardNames.join(', ')}
              </div>
            )}
          </div>
        </div>

        {/* Your holding info */}
        <div className="bg-parchment-100 rounded p-3 mb-4">
          <h3 className="font-medieval text-sm text-medieval-stone mb-2">Your Defense:</h3>
          <div className="text-sm text-medieval-stone">
            <div>🛡️ Base defense bonus: +{1 + targetHolding.defense_modifier}</div>
            {targetHolding.fortification_count > 0 && (
              <div>🏰 Fortification bonus: +{(targetHolding.fortification_count >= 1 ? 1 : 0) + (targetHolding.fortification_count >= 2 ? 2 : 0) + (targetHolding.fortification_count >= 3 ? 2 : 0)}</div>
            )}
          </div>
        </div>

        {/* Soldier commitment */}
        <div className="mb-4">
          <label className="text-sm text-medieval-stone block mb-2">
            Soldiers to commit for defense:
          </label>
          <input
            type="range"
            min={0}
            max={maxSoldiers}
            step={100}
            value={soldiersToCommit}
            onChange={(e) => setSoldiersToCommit(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-center font-medieval text-xl text-medieval-bronze mt-2">
            {soldiersToCommit} / {maxSoldiers} soldiers
          </div>
          {soldiersToCommit === 0 && (
            <div className="text-center text-xs text-yellow-600 mt-1">
              ⚠️ No soldiers = minimal defense (dice + bonuses only)
            </div>
          )}
        </div>

        {/* Combat cards selection */}
        {combatCards.length > 0 && (
          <div className="mb-4">
            <label className="text-sm text-medieval-stone block mb-2">
              Combat Cards (optional):
            </label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {combatCards.map(card => (
                <label
                  key={card.id}
                  className={`flex items-center p-2 rounded cursor-pointer transition-colors ${
                    selectedCards.includes(card.id)
                      ? 'bg-purple-100 border border-purple-300'
                      : 'bg-parchment-100 hover:bg-parchment-200'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedCards.includes(card.id)}
                    onChange={() => toggleCard(card.id)}
                    className="mr-3"
                  />
                  <div>
                    <span className="font-medieval text-sm text-medieval-bronze">
                      ✨ {card.name}
                    </span>
                    <p className="text-xs text-medieval-stone">{card.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Defend button */}
        <button
          onClick={handleDefend}
          className="w-full py-3 rounded bg-blue-600 hover:bg-blue-700 text-white font-medieval text-lg transition-colors"
        >
          🛡️ Defend!
        </button>
      </div>
    </div>
  )
}

