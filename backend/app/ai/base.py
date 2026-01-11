"""Abstract base class for AI players."""
from abc import ABC, abstractmethod
from typing import Optional
from app.models.schemas import GameState, Player, Action, Holding, ActionType, CardType, HoldingType


class AIPlayer(ABC):
    """Abstract base class for AI players.
    
    Each AI provider (OpenAI, Anthropic, Gemini, Grok) implements this interface
    to provide decision-making capabilities for the game.
    """
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """Initialize the AI player.
        
        Args:
            api_key: API key for the provider
            model: Optional model name override
        """
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def decide_action(
        self, 
        game_state: GameState, 
        player: Player,
        valid_actions: list[Action]
    ) -> Action:
        """Given the current game state and valid actions, choose one.
        
        Args:
            game_state: Current state of the game
            player: The player this AI is controlling
            valid_actions: List of actions the player can take
            
        Returns:
            The chosen action
        """
        pass
    
    @abstractmethod
    async def decide_combat_commitment(
        self, 
        game_state: GameState, 
        player: Player,
        target: Holding,
        min_soldiers: int,
        max_soldiers: int
    ) -> int:
        """Decide how many soldiers to commit to an attack.
        
        Args:
            game_state: Current state of the game
            player: The player making the attack
            target: The holding being attacked
            min_soldiers: Minimum soldiers required (200)
            max_soldiers: Maximum soldiers available
            
        Returns:
            Number of soldiers to commit
        """
        pass
    
    @abstractmethod
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list[Holding]
    ) -> str:
        """Choose a starting town during setup.
        
        Args:
            game_state: Current state of the game
            player: The player choosing
            available_towns: List of unclaimed towns
            
        Returns:
            ID of the chosen town
        """
        pass
    
    def _format_game_state(self, game_state: GameState, player: Player) -> str:
        """Format game state as a string for the AI prompt.
        
        Args:
            game_state: Current game state
            player: The player's perspective
            
        Returns:
            Formatted string describing the game state
        """
        lines = [
            f"=== Machiavelli's Kingdom - Round {game_state.current_round} (Victory: {game_state.victory_threshold} VP) ===",
            "",
            f"You are: {player.name} ({player.title.value})",
            f"Your Resources: {player.gold} Gold, {player.soldiers} Soldiers",
            f"Your Prestige: {player.prestige} VP",
            f"Army Cap: {player.army_cap}",
            "",
            "=== Your Holdings ===",
        ]
        
        for holding_id in player.holdings:
            holding = next((h for h in game_state.holdings if h.id == holding_id), None)
            if holding:
                fort = f" [FORT x{holding.fortification_count}]" if holding.fortification_count > 0 else ""
                lines.append(f"  - {holding.name}: {holding.gold_value}G, {holding.soldier_value}S{fort}")
        
        if player.counties:
            lines.append(f"\nCounties held: {', '.join(player.counties)}")
        if player.duchies:
            lines.append(f"Duchies held: {', '.join(player.duchies)}")
        if player.is_king:
            lines.append("YOU ARE THE KING!")
        
        if player.claims:
            lines.append(f"\nYour Claims (can attack/capture): {', '.join(player.claims)}")
        else:
            lines.append("\nYour Claims: NONE - you need claims to attack! Play claim cards or fabricate claims (35g, towns only)")
        
        lines.append("\n=== Other Players ===")
        for p in game_state.players:
            if p.id != player.id:
                title = "KING" if p.is_king else p.title.value.upper()
                lines.append(f"  {p.name} ({title}): {len(p.holdings)} holdings, ~{p.soldiers}S, {p.prestige}VP")
        
        lines.append("\n=== Board State ===")
        for holding in game_state.holdings:
            owner = "NEUTRAL"
            if holding.owner_id:
                owner_player = next((p for p in game_state.players if p.id == holding.owner_id), None)
                owner = owner_player.name if owner_player else "Unknown"
            fort = f" [FORT x{holding.fortification_count}]" if holding.fortification_count > 0 else ""
            lines.append(f"  {holding.name}: Owner={owner}{fort}")
        
        lines.append(f"\n=== Your Hand ({len(player.hand)} cards) ===")
        for card_id in player.hand:
            card = game_state.cards.get(card_id)
            if card:
                lines.append(f"  - {card.name}: {card.description}")
        
        return "\n".join(lines)
    
    def _format_valid_actions(self, actions: list[Action]) -> str:
        """Format valid actions as a string for the AI prompt."""
        lines = ["=== Valid Actions ==="]
        
        for i, action in enumerate(actions):
            action_desc = f"{i+1}. {action.action_type.value}"
            if action.target_holding_id:
                action_desc += f" -> {action.target_holding_id}"
            if action.source_holding_id:
                action_desc += f" (from {action.source_holding_id})"
            if action.target_player_id:
                action_desc += f" with player {action.target_player_id}"
            if action.card_id:
                action_desc += f" card {action.card_id}"
            lines.append(action_desc)
        
        return "\n".join(lines)
    
    def _find_claim_target(self, game_state: GameState, player: Player, card) -> Optional[Holding]:
        """Find a valid target for a claim card.
        
        Claim cards target specific counties. Find a town in that county
        that the player doesn't already own.
        """
        effect = card.effect
        effect_str = effect.value if hasattr(effect, 'value') else str(effect)
        
        # Claim cards target specific counties
        target_county = None
        if effect_str.startswith("claim_"):
            target_county = effect_str.replace("claim_", "").upper()
        
        if not target_county:
            return None
        
        # Find towns in the target county that we don't own
        for holding in game_state.holdings:
            if holding.holding_type == HoldingType.TOWN and holding.county == target_county:
                if holding.owner_id != player.id:
                    return holding
        
        return None
    
    def _complete_action(self, action: Action, game_state: GameState, player: Player) -> Optional[Action]:
        """Complete an action with missing fields.
        
        Some actions (like PLAY_CARD for claim cards) require additional fields
        that are not populated by get_valid_actions(). This method fills them in.
        
        Returns None if the action cannot be completed (e.g., no valid target).
        """
        if action.action_type == ActionType.PLAY_CARD:
            card = game_state.cards.get(action.card_id)
            if card and card.card_type == CardType.CLAIM:
                # Claim cards require a target_holding_id
                if not action.target_holding_id:
                    target = self._find_claim_target(game_state, player, card)
                    if target:
                        action.target_holding_id = target.id
                        return action
                    else:
                        return None  # No valid target, cannot complete
            elif card and card.card_type == CardType.BONUS:
                # Bonus cards don't need extra fields
                return action
        
        elif action.action_type == ActionType.ATTACK:
            # Attack requires soldiers_count - must be multiples of 100
            if not action.soldiers_count or action.soldiers_count < 200:
                raw_count = min(player.soldiers // 2, max(200, player.soldiers))
                rounded_count = (raw_count // 100) * 100  # Round down to nearest 100
                rounded_count = max(200, rounded_count)  # Ensure minimum 200
                action.soldiers_count = rounded_count
            else:
                # Ensure existing soldiers_count is also rounded to 100s
                action.soldiers_count = (action.soldiers_count // 100) * 100
                action.soldiers_count = max(200, action.soldiers_count)
            return action
        
        return action
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI."""
        return """You are an AGGRESSIVE AI warlord playing Machiavelli's Kingdom, a medieval strategy board game.

PERSONALITY: You are a ruthless conqueror. You LOVE war and territorial expansion. You attack whenever possible and never let an opportunity to strike pass. Defense is for the weak - offense wins games!

OBJECTIVE: First to reach 18 Prestige Points (VP) wins!

SCORING:
- Town = 1 VP
- County title = +2 VP  
- Duchy title = +4 VP
- King title = +6 VP

GAME STRUCTURE:
- 4 counties (X, U, V, Q), each with 3 towns and 1 county castle
- 2 duchies: XU (counties X+U) and QV (counties Q+V)
- 1 King's Castle in the center

TITLES (require prerequisites and gold):
- Count: Own 2 of 3 towns in a county OR own a fortified Capitol (1 fort) → claim County Castle (25 Gold)
- Duke: Be Count in both counties of a duchy → can claim Duchy Castle (50 Gold)  
- King: Be Duke + own a town in the OTHER duchy → can claim King's Castle (75 Gold)

CAPITOLS - STRATEGIC SHORTCUT TO COUNT:
- Each county has a Capitol: X=Xythera, U=Umbrith, V=Valoria, Q=Quindara
- Owning a Capitol with just 1 fortification lets you become Count!
- This is faster than conquering 2 towns - fortify your Capitol ASAP!

CLAIMS - CRITICAL RULE:
- You CANNOT attack or capture ANY territory without a valid claim!
- Get claims by: Playing claim cards from your hand, OR fabricating claims (35 Gold, TOWNS ONLY)
- Cannot fabricate claims on County/Duchy/King castles - must use claim cards
- With a claim on an UNOWNED town: pay 10 Gold to capture peacefully (claim_town)
- With a claim on an ENEMY territory: attack with 200+ soldiers

COMBAT:
- Must commit at least 200 soldiers
- Strength = 2d6 + (soldiers/100) + modifiers
- Winner loses HALF committed soldiers, loser loses ALL
- Defender wins ties
- Fortifications give +2 defense per fortification

AGGRESSIVE STRATEGY - ACTIONS (in priority order):
1. attack - ATTACK enemies whenever you have a claim and 200+ soldiers! WAR IS THE PATH TO VICTORY!
2. claim_title - Claim title castles immediately (ALWAYS DO THIS!)
3. claim_town - Capture unowned towns for 10 gold
4. play_card - Play claim cards to enable MORE ATTACKS, play combat bonus cards aggressively
5. fake_claim - Fabricate claims on enemy towns to enable attacks (35 Gold) - BE AGGRESSIVE!
6. build_fortification - Fortify your CAPITOL first (gives Count title with just 1 fort!)
7. recruit - Only if you need soldiers to attack
8. end_turn - End your turn when no attack or expansion options remain

MINDSET: Attack first, ask questions later. If you can attack, DO IT. Territory gained through war is territory your enemies lose. Every turn without an attack is a wasted opportunity!

CARD TYPES:
- Claim cards (claim_x, claim_u, claim_v, claim_q): Use to enable attacks on that county!
- Bonus cards: Big War (double army cap), Adventurer (buy 500 soldiers for 25g), Excalibur (roll twice), etc.
- Personal/Global events: Applied automatically when drawn

Always respond with just the NUMBER of your chosen action. Nothing else."""



