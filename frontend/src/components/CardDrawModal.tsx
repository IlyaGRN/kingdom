import { DrawnCardInfo, Card } from '../types/game'

interface CardDrawModalProps {
  drawnCard: DrawnCardInfo
  card?: Card  // Full card info if available
  onClose: () => void
}

export default function CardDrawModal({ drawnCard, card, onClose }: CardDrawModalProps) {
  // Determine display text based on whether card is hidden
  const isHidden = drawnCard.is_hidden
  const displayName = isHidden ? 'a hidden card' : drawnCard.card_name
  const isCurrentPlayerDraw = !isHidden  // Only show details if not hidden
  
  // Card type styling
  const getCardTypeStyle = () => {
    if (isHidden) return 'bg-gray-600'
    switch (drawnCard.card_type) {
      case 'personal_event': return 'bg-blue-600'
      case 'global_event': return 'bg-red-600'
      case 'bonus': return 'bg-purple-600'
      case 'claim': return 'bg-amber-600'
      default: return 'bg-gray-600'
    }
  }

  const getCardTypeIcon = () => {
    if (isHidden) return '🎴'
    switch (drawnCard.card_type) {
      case 'personal_event': return '⚡'
      case 'global_event': return '🌍'
      case 'bonus': return '✨'
      case 'claim': return '📜'
      default: return '🃏'
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div 
        className="bg-parchment-100 rounded-lg shadow-2xl max-w-md w-full mx-4 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`${getCardTypeStyle()} px-6 py-4 text-white text-center`}>
          <div className="text-4xl mb-2">{getCardTypeIcon()}</div>
          <h2 className="font-medieval text-xl">
            {drawnCard.player_name} drew {displayName}
            {drawnCard.is_instant && !isHidden && (
              <span className="block text-sm opacity-80 mt-1">
                (Instant effect applied!)
              </span>
            )}
          </h2>
        </div>
        
        {/* Card details - only show if not hidden */}
        {isCurrentPlayerDraw && card && (
          <div className="p-6">
            <div className="text-center mb-4">
              <h3 className="font-medieval text-2xl text-medieval-bronze mb-2">
                {card.name}
              </h3>
              <p className="text-medieval-stone text-sm">
                {card.description}
              </p>
            </div>
            
            <div className="text-center text-xs text-medieval-stone/70 uppercase tracking-wide">
              {drawnCard.card_type.replace('_', ' ')}
            </div>
          </div>
        )}
        
        {/* Hidden card message */}
        {isHidden && (
          <div className="p-6 text-center">
            <p className="text-medieval-stone">
              This card is kept secret until played.
            </p>
          </div>
        )}
        
        {/* Close button */}
        <div className="px-6 pb-6 text-center">
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


