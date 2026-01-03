import { useState } from 'react'
import { Holding, Player } from '../types/game'

interface ClaimActionModalProps {
  holding: Holding
  currentPlayer: Player
  onCapture: () => void
  onAttack: (soldiers: number) => void
  onClose: () => void
}

export default function ClaimActionModal({
  holding,
  currentPlayer,
  onCapture,
  onAttack,
  onClose,
}: ClaimActionModalProps) {
  const [soldiersToCommit, setSoldiersToCommit] = useState(200)
  
  const isUnowned = holding.owner_id === null
  const canAffordCapture = currentPlayer.gold >= 10
  const canAttack = currentPlayer.soldiers >= 200
  
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card-parchment rounded-lg p-6 max-w-md w-full mx-4 shadow-2xl">
        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="font-medieval text-2xl text-medieval-bronze mb-2">
            Claim Established!
          </h2>
          <p className="text-medieval-stone">
            You have a valid claim on <span className="font-bold text-medieval-bronze">{holding.name}</span>
          </p>
        </div>
        
        {/* Holding info */}
        <div className="bg-parchment-100 rounded p-3 mb-4">
          <div className="flex justify-between text-sm text-medieval-stone">
            <span>💰 Gold: {holding.gold_value}/turn</span>
            <span>⚔️ Soldiers: {holding.soldier_value}/turn</span>
          </div>
          {holding.defense_modifier !== 0 && (
            <div className="text-sm text-medieval-stone mt-1">
              🛡️ Defense Modifier: {holding.defense_modifier > 0 ? '+' : ''}{holding.defense_modifier}
            </div>
          )}
        </div>
        
        {isUnowned ? (
          /* Unowned town - offer capture for 10 gold */
          <div className="space-y-4">
            {canAffordCapture ? (
              <button
                onClick={onCapture}
                className="w-full py-3 rounded bg-green-600 hover:bg-green-700 text-white font-medieval text-lg transition-colors"
              >
                💰 Capture for 10 Gold
              </button>
            ) : (
              <div className="p-3 bg-yellow-50 rounded border border-yellow-200 text-center">
                <p className="text-yellow-700 font-medieval">
                  Not Enough Gold
                </p>
                <p className="text-xs text-medieval-stone mt-1">
                  Need 10 gold to capture (you have {currentPlayer.gold})
                </p>
              </div>
            )}
          </div>
        ) : (
          /* Owned by enemy - offer attack */
          <div className="space-y-4">
            {canAttack ? (
              <>
                <div>
                  <label className="text-sm text-medieval-stone block mb-2">
                    Soldiers to commit (min 200):
                  </label>
                  <input
                    type="range"
                    min={200}
                    max={currentPlayer.soldiers}
                    step={100}
                    value={soldiersToCommit}
                    onChange={(e) => setSoldiersToCommit(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="text-center font-medieval text-xl text-medieval-crimson mt-2">
                    {soldiersToCommit} soldiers
                  </div>
                </div>
                
                <button
                  onClick={() => onAttack(soldiersToCommit)}
                  className="w-full py-3 rounded bg-red-600 hover:bg-red-700 text-white font-medieval text-lg transition-colors"
                >
                  ⚔️ Launch Attack
                </button>
              </>
            ) : (
              <div className="p-3 bg-yellow-50 rounded border border-yellow-200 text-center">
                <p className="text-yellow-700 font-medieval">
                  Not Enough Soldiers
                </p>
                <p className="text-xs text-medieval-stone mt-1">
                  Need 200 soldiers to attack (you have {currentPlayer.soldiers})
                </p>
              </div>
            )}
          </div>
        )}
        
        {/* Close button */}
        <button
          onClick={onClose}
          className="w-full mt-4 py-2 rounded bg-parchment-200 hover:bg-parchment-300 text-medieval-stone font-medieval transition-colors"
        >
          Maybe Later
        </button>
      </div>
    </div>
  )
}


