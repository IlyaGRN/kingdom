import { useState } from 'react'
import { Holding, Player, Card, COMBAT_CARD_EFFECTS } from '../types/game'

interface CombatPrepModalProps {
  targetHolding: Holding
  defender: Player | null
  currentPlayer: Player
  cards: Record<string, Card>
  onAttack: (soldiers: number, cardIds: string[]) => void
  onCancel: () => void
}

export default function CombatPrepModal({
  targetHolding,
  defender,
  currentPlayer,
  cards,
  onAttack,
  onCancel,
}: CombatPrepModalProps) {
  const [soldiersToCommit, setSoldiersToCommit] = useState(Math.min(200, currentPlayer.soldiers))
  const [selectedCards, setSelectedCards] = useState<string[]>([])

  const minSoldiers = 200
  const maxSoldiers = currentPlayer.soldiers
  const canAttack = currentPlayer.soldiers >= minSoldiers

  // Get combat-applicable cards from player's hand
  const combatCards = currentPlayer.hand
    .map(cardId => cards[cardId])
    .filter(card => card && COMBAT_CARD_EFFECTS.includes(card.effect))

  const toggleCard = (cardId: string) => {
    setSelectedCards(prev =>
      prev.includes(cardId)
        ? prev.filter(id => id !== cardId)
        : [...prev, cardId]
    )
  }

  const handleAttack = () => {
    if (canAttack) {
      onAttack(soldiersToCommit, selectedCards)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card-parchment rounded-lg p-6 max-w-lg w-full mx-4 shadow-2xl">
        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="font-medieval text-2xl text-medieval-crimson mb-2">
            ⚔️ Prepare for Battle
          </h2>
          <p className="text-medieval-stone">
            Attacking <span className="font-bold text-medieval-bronze">{targetHolding.name}</span>
            {defender && (
              <span> owned by <span className="font-bold">{defender.name}</span></span>
            )}
          </p>
        </div>

        {/* Target info */}
        <div className="bg-parchment-100 rounded p-3 mb-4">
          <div className="flex justify-between text-sm text-medieval-stone">
            <span>💰 Gold: {targetHolding.gold_value}/turn</span>
            <span>⚔️ Soldiers: {targetHolding.soldier_value}/turn</span>
          </div>
          {targetHolding.defense_modifier !== 0 && (
            <div className="text-sm text-medieval-stone mt-1">
              🛡️ Defense Modifier: {targetHolding.defense_modifier > 0 ? '+' : ''}{targetHolding.defense_modifier}
            </div>
          )}
          {targetHolding.fortification_count > 0 && (
            <div className="text-sm text-medieval-stone mt-1">
              🏰 Fortifications: {targetHolding.fortification_count} (+{targetHolding.fortification_count * 2} defense)
            </div>
          )}
        </div>

        {/* Soldier commitment */}
        {canAttack ? (
          <div className="mb-4">
            <label className="text-sm text-medieval-stone block mb-2">
              Soldiers to commit (min 200):
            </label>
            <input
              type="range"
              min={minSoldiers}
              max={maxSoldiers}
              step={100}
              value={soldiersToCommit}
              onChange={(e) => setSoldiersToCommit(Number(e.target.value))}
              className="w-full"
            />
            <div className="text-center font-medieval text-xl text-medieval-crimson mt-2">
              {soldiersToCommit} / {maxSoldiers} soldiers
            </div>
            <div className="text-center text-xs text-medieval-stone">
              Combat bonus: +{Math.floor(soldiersToCommit / 100)}
            </div>
          </div>
        ) : (
          <div className="p-3 bg-red-50 rounded border border-red-200 text-center mb-4">
            <p className="text-red-700 font-medieval">Not Enough Soldiers</p>
            <p className="text-xs text-medieval-stone mt-1">
              Need 200 soldiers to attack (you have {currentPlayer.soldiers})
            </p>
          </div>
        )}

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

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-3 rounded bg-parchment-200 hover:bg-parchment-300 text-medieval-stone font-medieval transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleAttack}
            disabled={!canAttack}
            className={`flex-1 py-3 rounded font-medieval text-white transition-colors ${
              canAttack
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-gray-400 cursor-not-allowed'
            }`}
          >
            ⚔️ Launch Attack
          </button>
        </div>
      </div>
    </div>
  )
}

