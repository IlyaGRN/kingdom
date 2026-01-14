/**
 * Visual configuration for the game board and holdings
 */

export const visualConfig = {
  // Board image settings
  board: {
    // Saturation filter percentage (0-200, 100 = normal)
    saturation: 75,
  },

  // Possible player colors (hex format)
  playerColors: [
    '#D10303',  // Red
    '#066B1B',  // Teal
    '#e9c46a',  // Gold
    '#9b59b6',  // Purple
    '#3498db',  // Blue
    '#e67e22',  // Orange
    '#1abc9c',  // Emerald
    '#e91e63',  // Pink
  ],

  // Diamond/holding marker settings
  holdings: {
    // Transparency for occupied holding backgrounds (0.0 - 1.0)
    occupiedTransparency: 0.3,
    
    // Transparency for unoccupied holding backgrounds (0.0 - 1.0)
    unoccupiedTransparency: 0.4,
    
    // Background color for unoccupied holdings (RGB values)
    unoccupiedColor: {
      r: 128,
      g: 128,
      b: 128,
    },
    
    // Icon color for unoccupied holdings
    unoccupiedIconColor: 'rgba(128, 128, 128, 0.8)',
    
    // Border width for occupied holdings (in pixels)
    borderWidth: 3,
  },

  // Crest image settings
  crests: {
    // Show colored box as fallback if crest image is missing
    showFallbackColor: true,
    
    // Available crests for selection
    available: [
      { id: 'player_0', path: '/crest_player_0.png', label: 'Player 1' },
      { id: 'player_1', path: '/crest_player_1.png', label: 'Player 2' },
      { id: 'openai', path: '/crest_openai.png', label: 'OpenAI' },
      { id: 'anthropic', path: '/crest_anthropic.png', label: 'Anthropic' },
      { id: 'gemini', path: '/crest_gemini.png', label: 'Gemini' },
      { id: 'grok', path: '/crest_grok.png', label: 'Grok' },
    ],
    
    // Default crest mapping by player type
    defaultByType: {
      human: '/crest_player_0.png',
      ai_openai: '/crest_openai.png',
      ai_anthropic: '/crest_anthropic.png',
      ai_gemini: '/crest_gemini.png',
      ai_grok: '/crest_grok.png',
    } as Record<string, string>,
  },
}

// Helper to get RGBA string for unoccupied holdings
export function getUnoccupiedBackgroundColor(): string {
  const { r, g, b } = visualConfig.holdings.unoccupiedColor
  return `rgba(${r}, ${g}, ${b}, ${visualConfig.holdings.unoccupiedTransparency})`
}

// Helper to convert hex color to RGBA with configured transparency
export function hexToRgba(hex: string, isOccupied: boolean = true): string {
  const transparency = isOccupied 
    ? visualConfig.holdings.occupiedTransparency 
    : visualConfig.holdings.unoccupiedTransparency
  
  const cleanHex = hex.replace('#', '')
  const r = parseInt(cleanHex.substring(0, 2), 16)
  const g = parseInt(cleanHex.substring(2, 4), 16)
  const b = parseInt(cleanHex.substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${transparency})`
}

// Helper to get the default crest for a player type
export function getDefaultCrest(playerType: string, humanIndex: number = 0): string {
  if (playerType === 'human') {
    return `/crest_player_${humanIndex}.png`
  }
  return visualConfig.crests.defaultByType[playerType] || '/crest_player_0.png'
}

