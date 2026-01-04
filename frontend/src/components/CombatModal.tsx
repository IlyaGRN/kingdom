import { CombatResult, Player, Holding } from '../types/game'

interface CombatModalProps {
  combat: CombatResult
  players: Player[]
  holdings: Holding[]
  onClose: () => void
}

export default function CombatModal({ combat, players, holdings, onClose }: CombatModalProps) {
  const attacker = players.find(p => p.id === combat.attacker_id)
  const defender = combat.defender_id ? players.find(p => p.id === combat.defender_id) : null
  const holding = holdings.find(h => h.id === combat.target_holding_id)

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="card-parchment rounded-lg p-8 max-w-lg w-full mx-4 combat-flash">
        <h2 className="font-medieval text-2xl text-center text-medieval-crimson mb-6">
          ⚔️ Battle for {holding?.name} ⚔️
        </h2>

        {/* Combatants */}
        <div className="flex items-center justify-between mb-6">
          {/* Attacker */}
          <div className="text-center flex-1">
            <div 
              className="w-16 h-16 rounded-full mx-auto mb-2 flex items-center justify-center border-4"
              style={{ 
                backgroundColor: attacker?.color,
                borderColor: combat.attacker_won ? '#c9a227' : 'transparent'
              }}
            >
              <span className="text-white text-2xl">⚔️</span>
            </div>
            <h3 className="font-medieval text-lg text-medieval-bronze">
              {attacker?.name}
            </h3>
            <p className="text-sm text-medieval-stone">Attacker</p>
          </div>

          {/* VS */}
          <div className="text-4xl font-medieval text-medieval-stone px-4">
            VS
          </div>

          {/* Defender */}
          <div className="text-center flex-1">
            <div 
              className="w-16 h-16 rounded-full mx-auto mb-2 flex items-center justify-center border-4"
              style={{ 
                backgroundColor: defender?.color || '#666',
                borderColor: !combat.attacker_won ? '#c9a227' : 'transparent'
              }}
            >
              <span className="text-white text-2xl">🛡️</span>
            </div>
            <h3 className="font-medieval text-lg text-medieval-bronze">
              {defender?.name || 'Neutral'}
            </h3>
            <p className="text-sm text-medieval-stone">Defender</p>
          </div>
        </div>

        {/* Combat stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Attacker stats */}
          <div className="bg-parchment-100 rounded p-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm text-medieval-stone">🎲 Dice Roll:</span>
              <span className="font-medieval text-medieval-bronze">{combat.attacker_roll}</span>
            </div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm text-medieval-stone">⚔️ Soldiers ({combat.attacker_soldiers_committed}):</span>
              <span className="font-medieval text-medieval-bronze">+{combat.attacker_soldiers_bonus}</span>
            </div>
            {combat.attacker_attack_bonus > 0 && (
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-medieval-stone">🏹 Attack Bonus:</span>
                <span className="font-medieval text-green-600">+{combat.attacker_attack_bonus}</span>
              </div>
            )}
            {combat.attacker_title_bonus > 0 && (
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-medieval-stone">👑 Title Bonus:</span>
                <span className="font-medieval text-green-600">+{combat.attacker_title_bonus}</span>
              </div>
            )}
            <div className="flex justify-between items-center border-t border-parchment-300 pt-2 mt-2">
              <span className="text-sm font-bold text-medieval-stone">Total:</span>
              <span className="font-medieval text-xl text-medieval-gold">{combat.attacker_strength}</span>
            </div>
          </div>

          {/* Defender stats */}
          <div className="bg-parchment-100 rounded p-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm text-medieval-stone">🎲 Dice Roll:</span>
              <span className="font-medieval text-medieval-bronze">{combat.defender_roll}</span>
            </div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm text-medieval-stone">🛡️ Soldiers ({combat.defender_soldiers_committed}):</span>
              <span className="font-medieval text-medieval-bronze">+{combat.defender_soldiers_bonus}</span>
            </div>
            {combat.defender_defense_bonus > 0 && (
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-medieval-stone">🏰 Defense Bonus:</span>
                <span className="font-medieval text-green-600">+{combat.defender_defense_bonus}</span>
              </div>
            )}
            {combat.defender_title_bonus > 0 && (
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-medieval-stone">👑 Title Bonus:</span>
                <span className="font-medieval text-green-600">+{combat.defender_title_bonus}</span>
              </div>
            )}
            <div className="flex justify-between items-center border-t border-parchment-300 pt-2 mt-2">
              <span className="text-sm font-bold text-medieval-stone">Total:</span>
              <span className="font-medieval text-xl text-medieval-gold">{combat.defender_strength}</span>
            </div>
          </div>
        </div>

        {/* Result */}
        <div className={`text-center p-4 rounded mb-6 ${
          combat.attacker_won ? 'bg-green-100' : 'bg-red-100'
        }`}>
          <h3 className="font-medieval text-2xl mb-2">
            {combat.attacker_won ? (
              <span className="text-green-700">⚔️ Victory! ⚔️</span>
            ) : (
              <span className="text-red-700">🛡️ Repelled! 🛡️</span>
            )}
          </h3>
          <p className="text-medieval-stone">
            {combat.attacker_won 
              ? `${attacker?.name} conquers ${holding?.name}!`
              : `${defender?.name || 'The defenders'} hold their ground!`
            }
          </p>
        </div>

        {/* Casualties */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="text-center">
            <span className="text-sm text-medieval-stone">Attacker Losses:</span>
            <p className="font-medieval text-xl text-medieval-crimson">
              -{combat.attacker_losses} ⚔️
            </p>
          </div>
          <div className="text-center">
            <span className="text-sm text-medieval-stone">Defender Losses:</span>
            <p className="font-medieval text-xl text-medieval-crimson">
              -{combat.defender_losses} 🛡️
            </p>
          </div>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="btn-medieval w-full py-3 rounded text-lg"
        >
          Continue
        </button>
      </div>
    </div>
  )
}



