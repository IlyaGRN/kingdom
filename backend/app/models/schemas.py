"""Pydantic models for game state and API requests/responses."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ============ Enums ============

class TitleType(str, Enum):
    """Title hierarchy levels."""
    BARON = "baron"
    COUNT = "count"
    DUKE = "duke"
    KING = "king"


class HoldingType(str, Enum):
    """Types of holdings on the board."""
    TOWN = "town"
    COUNTY_CASTLE = "county_castle"
    DUCHY_CASTLE = "duchy_castle"
    KING_CASTLE = "king_castle"


class ActionType(str, Enum):
    """Available player actions."""
    MOVE = "move"
    RECRUIT = "recruit"
    BUILD_FORTIFICATION = "build_fortification"
    RELOCATE_FORTIFICATION = "relocate_fortification"  # Move fort when all 4 placed
    CLAIM_TITLE = "claim_title"
    CLAIM_TOWN = "claim_town"  # 10 gold to capture unowned town with valid claim
    ATTACK = "attack"
    DEFEND = "defend"  # Human defender responds to attack
    PLAY_CARD = "play_card"
    DRAW_CARD = "draw_card"
    FAKE_CLAIM = "fake_claim"  # 35 gold to fabricate a claim
    END_TURN = "end_turn"


class CardType(str, Enum):
    """Types of cards in the deck."""
    PERSONAL_EVENT = "personal_event"  # Instant effect on drawing player
    GLOBAL_EVENT = "global_event"  # Instant effect on all players
    BONUS = "bonus"  # Player chooses when to use
    CLAIM = "claim"  # Claim cards for territories


class CardEffect(str, Enum):
    """Specific card effects for gameplay mechanics."""
    # Personal Events - Gold
    GOLD_5 = "gold_5"
    GOLD_10 = "gold_10"
    GOLD_15 = "gold_15"
    GOLD_25 = "gold_25"
    # Personal Events - Soldiers
    SOLDIERS_100 = "soldiers_100"
    SOLDIERS_200 = "soldiers_200"
    SOLDIERS_300 = "soldiers_300"
    RAIDERS = "raiders"  # Lose all income this turn
    
    # Global Events
    CRUSADE = "crusade"  # All lose half gold and soldiers
    
    # Bonus Cards
    BIG_WAR = "big_war"  # Double army cap until next war
    ADVENTURER = "adventurer"  # Buy 500 soldiers for 25 gold above cap
    EXCALIBUR = "excalibur"  # Roll twice, take higher
    POISONED_ARROWS = "poisoned_arrows"  # Halve opponent's dice
    FORBID_MERCENARIES = "forbid_mercenaries"  # No soldier purchases for one turn
    TALENTED_COMMANDER = "talented_commander"  # No soldier loss when winning
    VASSAL_REVOLT = "vassal_revolt"  # Higher tier can attack vassals
    ENFORCE_PEACE = "enforce_peace"  # No wars for one turn
    DUEL = "duel"  # Army-less single-dice fight
    SPY = "spy"  # View cards or reorder deck
    
    # Claims
    CLAIM_X = "claim_x"
    CLAIM_U = "claim_u"
    CLAIM_V = "claim_v"
    CLAIM_Q = "claim_q"
    ULTIMATE_CLAIM = "ultimate_claim"  # Any town or title
    DUCHY_CLAIM = "duchy_claim"  # Any town or Duke+ title


class EdictType(str, Enum):
    """King's edict options."""
    TAX = "tax"  # +3 Gold
    DRAFT = "draft"  # +200 soldiers
    JUSTICE = "justice"  # Target discards 1 card


class PlayerType(str, Enum):
    """Type of player controller."""
    HUMAN = "human"
    AI_OPENAI = "ai_openai"
    AI_ANTHROPIC = "ai_anthropic"
    AI_GEMINI = "ai_gemini"
    AI_GROK = "ai_grok"


class GamePhase(str, Enum):
    """Current phase of the game."""
    SETUP = "setup"
    INCOME = "income"
    PLAYER_TURN = "player_turn"
    COMBAT = "combat"
    UPKEEP = "upkeep"
    GAME_OVER = "game_over"


# ============ Game Objects ============

class Holding(BaseModel):
    """A holding on the board (town or castle)."""
    id: str
    name: str
    holding_type: HoldingType
    county: Optional[str] = None  # X, U, V, Q
    duchy: Optional[str] = None  # XU, QV
    gold_value: int = Field(ge=0)
    soldier_value: int = Field(ge=0)  # Actual soldiers (100, 200, 300, etc.)
    owner_id: Optional[str] = None
    fortification_count: int = Field(default=0, ge=0, le=3)  # Max 3 per town
    defense_modifier: int = Field(default=0)  # Dice modifier for defense
    attack_modifier: int = Field(default=0)  # Dice modifier for attacking (Umbrith)
    is_capitol: bool = False  # County capitol - fortifying gives claim to Count title
    
    # Track who placed fortifications (player_id -> count)
    fortifications_by_player: dict[str, int] = Field(default_factory=dict)
    
    # Board position for frontend rendering
    position_x: float = 0.0
    position_y: float = 0.0


class Card(BaseModel):
    """A card in the game."""
    id: str
    name: str
    card_type: CardType
    effect: CardEffect
    description: str
    target_county: Optional[str] = None  # For county claim cards (X, U, V, Q)
    effect_value: Optional[int] = None  # For gold cards


class Player(BaseModel):
    """A player in the game."""
    id: str
    name: str
    player_type: PlayerType
    color: str
    
    # Resources
    gold: int = Field(default=0, ge=0)
    soldiers: int = Field(default=0, ge=0)
    
    # Titles
    title: TitleType = TitleType.BARON
    counties: list[str] = Field(default_factory=list)  # County IDs held
    duchies: list[str] = Field(default_factory=list)  # Duchy IDs held
    is_king: bool = False
    
    # Holdings
    holdings: list[str] = Field(default_factory=list)  # Holding IDs owned
    
    # Hand
    hand: list[str] = Field(default_factory=list)  # Card IDs in hand
    
    # Victory points
    prestige: int = Field(default=0, ge=0)
    
    # Fortification tracking (max 4 per player across board)
    fortifications_placed: int = Field(default=0, ge=0, le=4)
    
    # Claims - town/territory IDs that this player has valid claims on
    claims: list[str] = Field(default_factory=list)
    
    # Active effects (card effects currently active)
    active_effects: list[CardEffect] = Field(default_factory=list)
    
    # Big War effect - doubled army cap until next war
    has_big_war_effect: bool = False
    
    @property
    def army_cap(self) -> int:
        """Maximum soldiers before supply costs apply."""
        caps = {
            TitleType.BARON: 500,
            TitleType.COUNT: 800,
            TitleType.DUKE: 1200,
            TitleType.KING: 2000,
        }
        base_cap = caps[self.title]
        if self.has_big_war_effect:
            return base_cap * 2
        return base_cap


class Army(BaseModel):
    """An army on the board."""
    id: str
    owner_id: str
    soldiers: int = Field(ge=0)
    location: str  # Holding ID
    can_move: bool = True


# ============ Actions ============

class Action(BaseModel):
    """A game action."""
    action_type: ActionType
    player_id: str
    
    # Optional parameters based on action type
    target_holding_id: Optional[str] = None
    source_holding_id: Optional[str] = None
    soldiers_count: Optional[int] = None
    card_id: Optional[str] = None
    target_player_id: Optional[str] = None
    edict: Optional[EdictType] = None
    target_county: Optional[str] = None  # For claims
    
    # Combat card selection
    attack_cards: list[str] = Field(default_factory=list)  # Card IDs to use when attacking
    defense_cards: list[str] = Field(default_factory=list)  # Card IDs to use when defending


class CombatResult(BaseModel):
    """Result of a combat."""
    attacker_id: str
    defender_id: Optional[str]
    target_holding_id: str
    
    attacker_strength: int
    defender_strength: int
    attacker_roll: int
    defender_roll: int
    
    attacker_soldiers_committed: int
    defender_soldiers_committed: int
    
    # Bonus breakdowns for UI display
    attacker_soldiers_bonus: int = 0
    attacker_attack_bonus: int = 0
    attacker_title_bonus: int = 0
    defender_soldiers_bonus: int = 0
    defender_defense_bonus: int = 0
    defender_title_bonus: int = 0
    
    attacker_won: bool
    attacker_losses: int
    defender_losses: int
    
    # Card effects used
    attacker_effects: list[CardEffect] = Field(default_factory=list)
    defender_effects: list[CardEffect] = Field(default_factory=list)


# ============ AI Decision Log ============

class AIDecisionLogEntry(BaseModel):
    """A single action consideration in the AI decision process."""
    action: str
    status: str  # "chosen", "skipped", "unavailable"
    reason: str


class AIDecisionLog(BaseModel):
    """Full log of an AI decision for one action."""
    player_name: str
    timestamp: str
    valid_actions: list[str]  # e.g., ["draw_card", "play_card", "end_turn"]
    considered: list[AIDecisionLogEntry]
    chosen_action: str
    reason: str


# ============ Pending Combat ============

class PendingCombat(BaseModel):
    """Combat waiting for human defender response."""
    attacker_id: str
    defender_id: str
    target_holding_id: str
    attacker_soldiers: int
    attacker_cards: list[str] = Field(default_factory=list)  # Card IDs attacker is using
    source_holding_id: str | None = None  # Where attacker is attacking from (for attack bonus)


# ============ Game State ============

class DrawnCardInfo(BaseModel):
    """Information about a drawn card for display purposes."""
    card_id: str
    card_name: str
    card_type: str
    player_id: str
    player_name: str
    is_instant: bool = False
    is_hidden: bool = False  # True if should show "hidden card" (e.g. AI bonus cards)


class GameState(BaseModel):
    """Complete game state."""
    id: str
    
    # Game configuration
    player_count: int = Field(ge=4, le=6)
    victory_threshold: int = Field(default=18)  # Game ends when someone reaches this
    
    # Current state
    current_round: int = Field(default=1, ge=1)
    current_player_idx: int = Field(default=0, ge=0)
    phase: GamePhase = GamePhase.SETUP
    card_drawn_this_turn: bool = False
    war_fought_this_turn: bool = False  # Only one war per turn
    
    # Last drawn card (for popup display)
    last_drawn_card: Optional[DrawnCardInfo] = None
    
    # Global effects active this turn
    forbid_mercenaries_active: bool = False
    enforce_peace_active: bool = False
    
    # Game objects
    players: list[Player] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)
    armies: list[Army] = Field(default_factory=list)
    
    # Deck
    deck: list[str] = Field(default_factory=list)  # Card IDs
    discard_pile: list[str] = Field(default_factory=list)
    
    # All cards (lookup)
    cards: dict[str, Card] = Field(default_factory=dict)
    
    # History
    action_log: list[Action] = Field(default_factory=list)
    combat_log: list[CombatResult] = Field(default_factory=list)
    
    # Pending combat (waiting for human defender response)
    pending_combat: Optional[PendingCombat] = None
    
    @property
    def current_player(self) -> Optional[Player]:
        """Get the current player."""
        if 0 <= self.current_player_idx < len(self.players):
            return self.players[self.current_player_idx]
        return None


# ============ API Requests/Responses ============

class CreateGameRequest(BaseModel):
    """Request to create a new game."""
    player_configs: list[dict]  # [{name, player_type, color}, ...]


class CreateGameResponse(BaseModel):
    """Response after creating a game."""
    game_id: str
    state: GameState


class PerformActionRequest(BaseModel):
    """Request to perform an action."""
    game_id: str
    action: Action


class PerformActionResponse(BaseModel):
    """Response after performing an action."""
    success: bool
    message: str
    state: GameState
    combat_result: Optional[CombatResult] = None


class GetValidActionsRequest(BaseModel):
    """Request to get valid actions for a player."""
    game_id: str
    player_id: str


class GetValidActionsResponse(BaseModel):
    """Response with valid actions."""
    actions: list[Action]


class SimulationConfig(BaseModel):
    """Configuration for AI simulation mode."""
    player_configs: list[dict]  # AI player configurations
    speed_ms: int = Field(default=1000, ge=100)  # Delay between turns
