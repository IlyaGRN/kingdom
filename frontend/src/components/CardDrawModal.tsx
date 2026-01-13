import { DrawnCardInfo, Card } from '../types/game'

interface CardDrawModalProps {
  drawnCard: DrawnCardInfo
  card?: Card  // Full card info if available
  onClose: () => void
}

// Map card effects to image filenames
const getCardImagePath = (effect: string): string => {
  const effectToImage: Record<string, string> = {
    // Gold cards
    'gold_5': 'card__gold_chest.png',
    'gold_10': 'card__gold_chest.png',
    'gold_15': 'card__gold_chest.png',
    'gold_25': 'card__gold_chest.png',
    // Soldier cards
    'soldiers_100': 'card__mercenaries.png',
    'soldiers_200': 'card__mercenaries.png',
    'soldiers_300': 'card__mercenaries.png',
    // Events
    'raiders': 'card__raiders.png',
    'crusade': 'card__crusade.png',
    // Bonus cards
    'big_war': 'card__big_war.png',
    'adventurer': 'card__mercenaries.png',
    'excalibur': 'card__excalibur.png',
    'poisoned_arrows': 'card__poisoned_arrowes.png',
    'forbid_mercenaries': 'card__mercenaries_forbidden.png',
    'talented_commander': 'card__talented_commander.png',
    'vassal_revolt': 'card__vassal_revolt.png',
    'enforce_peace': 'card__enforce_peace.png',
    'duel': 'card__duel.png',
    'spy': 'card__spy.png',
    // Claim cards
    'claim_x': 'card__claim_x.png',
    'claim_u': 'card__claim_u.png',
    'claim_v': 'card__claim_v.png',
    'claim_q': 'card__claim_q.png',
    'ultimate_claim': 'card__ultimate_claim.png',
    'duchy_claim': 'card__ultimate_claim.png',
  }
  return effectToImage[effect] || ''
}

export default function CardDrawModal({ drawnCard, card, onClose }: CardDrawModalProps) {
  // Determine display text based on whether card is hidden
  const isHidden = drawnCard.is_hidden
  const isCurrentPlayerDraw = !isHidden  // Only show details if not hidden
  
  // Get card image path
  const cardImagePath = card?.effect ? getCardImagePath(card.effect) : ''

  return (
    <div 
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div 
        className="flex flex-col items-center max-w-sm w-full mx-4"
        onClick={e => e.stopPropagation()}
      >
        {/* Header - who drew */}
        <div className="bg-medieval-navy/90 px-6 py-2 rounded-t-lg text-white text-center w-full">
          <h2 className="font-medieval text-lg">
            {drawnCard.player_name} drew a card
            {drawnCard.is_instant && !isHidden && (
              <span className="block text-xs opacity-80">
                (Instant effect applied!)
              </span>
            )}
          </h2>
        </div>
        
        {/* Card image - only show if not hidden */}
        {isCurrentPlayerDraw && cardImagePath && (
          <div className="bg-parchment-100 p-4 w-full flex justify-center">
            <img 
              src={`/${cardImagePath}`}
              alt={card?.name || 'Card'}
              className="max-h-64 w-auto object-contain rounded-lg shadow-lg"
            />
          </div>
        )}
        
        {/* Card details - only show if not hidden */}
        {isCurrentPlayerDraw && card && (
          <div className="bg-parchment-100 px-6 pb-2 w-full text-center">
            <h3 className="font-medieval text-xl text-medieval-bronze">
              {card.name}
            </h3>
            <p className="text-medieval-stone text-sm mt-1">
              {card.description}
            </p>
          </div>
        )}
        
        {/* Hidden card message */}
        {isHidden && (
          <div className="bg-parchment-100 p-6 w-full text-center">
            <div className="text-6xl mb-4">🎴</div>
            <p className="text-medieval-stone">
              This card is kept secret until played.
            </p>
          </div>
        )}
        
        {/* Close button */}
        <div className="bg-parchment-100 px-6 pb-4 pt-2 rounded-b-lg w-full text-center">
          <button
            onClick={onClose}
            className="px-8 py-2 bg-medieval-bronze hover:bg-medieval-bronze/90 text-white rounded font-medieval transition-colors"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}


