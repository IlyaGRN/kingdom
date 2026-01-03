// Game type definitions matching backend schemas

export type TitleType = 'baron' | 'count' | 'duke' | 'king'

export type HoldingType = 'town' | 'county_castle' | 'duchy_castle' | 'king_castle'

export type ActionType = 
  | 'move' 
  | 'recruit' 
  | 'build_fortification' 
  | 'relocate_fortification'  // Move fort when all 4 placed
  | 'claim_title' 
  | 'claim_town'  // 10 gold to capture unowned town with valid claim
  | 'attack' 
  | 'fake_claim'  // 35 gold to fabricate a claim
  | 'play_card' 
  | 'draw_card' 
  | 'end_turn'

export type CardType = 
  | 'personal_event'  // Instant effect on drawing player
  | 'global_event'    // Instant effect on all players
  | 'bonus'           // Player chooses when to use
  | 'claim'           // Claim cards for territories

export type CardEffect = 
  // Personal Events
  | 'gold_5'
  | 'gold_10'
  | 'gold_15'
  | 'gold_25'
  | 'raiders'
  // Global Events
  | 'crusade'
  // Bonus Cards
  | 'big_war'
  | 'adventurer'
  | 'excalibur'
  | 'poisoned_arrows'
  | 'forbid_mercenaries'
  | 'talented_commander'
  | 'vassal_revolt'
  | 'enforce_peace'
  | 'duel'
  | 'spy'
  // Claims
  | 'claim_x'
  | 'claim_u'
  | 'claim_v'
  | 'claim_q'
  | 'ultimate_claim'
  | 'duchy_claim'

export type PlayerType = 
  | 'human' 
  | 'ai_openai' 
  | 'ai_anthropic' 
  | 'ai_gemini' 
  | 'ai_grok'

export type GamePhase = 
  | 'setup' 
  | 'income' 
  | 'player_turn' 
  | 'combat' 
  | 'upkeep' 
  | 'game_over'

export interface Holding {
  id: string
  name: string
  holding_type: HoldingType
  county: string | null
  duchy: string | null
  gold_value: number
  soldier_value: number  // Actual soldiers (100, 200, etc.)
  owner_id: string | null
  fortification_count: number  // 0-3
  defense_modifier: number  // Dice modifier for defense
  attack_modifier: number   // Dice modifier for attacking (Umbrith)
  fortifications_by_player: Record<string, number>  // Track who placed forts
  position_x: number
  position_y: number
}

export interface Card {
  id: string
  name: string
  card_type: CardType
  effect: CardEffect
  description: string
  target_county: string | null  // For county claim cards
  effect_value: number | null   // For gold cards
}

export interface Player {
  id: string
  name: string
  player_type: PlayerType
  color: string
  gold: number
  soldiers: number
  title: TitleType
  counties: string[]
  duchies: string[]
  is_king: boolean
  holdings: string[]
  hand: string[]
  prestige: number
  fortifications_placed: number  // Max 4 per player
  claims: string[]               // Territory IDs player has valid claims on
  active_effects: CardEffect[]   // Combat effects ready to use
  has_big_war_effect: boolean    // Doubled army cap until next war
}

export interface Action {
  action_type: ActionType
  player_id: string
  target_holding_id?: string
  source_holding_id?: string
  soldiers_count?: number
  card_id?: string
  target_player_id?: string
  target_county?: string  // For claims
}

export interface CombatResult {
  attacker_id: string
  defender_id: string | null
  target_holding_id: string
  attacker_strength: number
  defender_strength: number
  attacker_roll: number
  defender_roll: number
  attacker_soldiers_committed: number
  defender_soldiers_committed: number
  attacker_won: boolean
  attacker_losses: number
  defender_losses: number
  attacker_effects: CardEffect[]
  defender_effects: CardEffect[]
}

export interface GameState {
  id: string
  player_count: number
  victory_threshold: number  // 18 VP to win
  current_round: number
  current_player_idx: number
  phase: GamePhase
  card_drawn_this_turn: boolean
  war_fought_this_turn: boolean
  forbid_mercenaries_active: boolean
  enforce_peace_active: boolean
  players: Player[]
  holdings: Holding[]
  deck: string[]
  discard_pile: string[]
  cards: Record<string, Card>
  action_log: Action[]
  combat_log: CombatResult[]
}

export interface PlayerConfig {
  name: string
  player_type: PlayerType
  color: string
}

export const PLAYER_COLORS = [
  '#DC2626', // Bright Red
  '#2563EB', // Bright Blue
  '#16A34A', // Bright Green
  '#9333EA', // Purple
  '#EA580C', // Orange
  '#0891B2', // Cyan
]

export const AI_TYPES: { value: PlayerType; label: string }[] = [
  { value: 'human', label: 'Human Player' },
  { value: 'ai_openai', label: 'AI (OpenAI GPT-4)' },
  { value: 'ai_anthropic', label: 'AI (Anthropic Claude)' },
  { value: 'ai_gemini', label: 'AI (Google Gemini)' },
  { value: 'ai_grok', label: 'AI (xAI Grok)' },
]

// Helper: Get army cap for a title
export function getArmyCap(title: TitleType, hasBigWarEffect: boolean = false): number {
  const caps: Record<TitleType, number> = {
    baron: 500,
    count: 800,
    duke: 1200,
    king: 2000,
  }
  const base = caps[title]
  return hasBigWarEffect ? base * 2 : base
}
