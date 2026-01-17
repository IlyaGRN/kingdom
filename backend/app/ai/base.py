"""Abstract base class for AI players."""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from app.models.schemas import GameState, Player, Action, Holding, ActionType, CardType, HoldingType

if TYPE_CHECKING:
    from app.game.logger import GameLogger


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
        valid_actions: list[Action],
        logger: Optional["GameLogger"] = None
    ) -> Action:
        """Given the current game state and valid actions, choose one.
        
        Args:
            game_state: Current state of the game
            player: The player this AI is controlling
            valid_actions: List of actions the player can take
            logger: Optional game logger for recording AI decisions
            
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
                holding_info = self._format_holding_details(holding)
                lines.append(f"  - {holding_info}")
        
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
        
        lines.append("\n=== All Holdings on Board ===")
        # Group holdings by county for clarity
        for county in ["X", "U", "V", "Q"]:
            lines.append(f"\n  County {county}:")
            county_holdings = [h for h in game_state.holdings if h.county == county]
            for holding in county_holdings:
                owner = "NEUTRAL"
                if holding.owner_id:
                    owner_player = next((p for p in game_state.players if p.id == holding.owner_id), None)
                    owner = owner_player.name if owner_player else "Unknown"
                holding_info = self._format_holding_details(holding, owner)
                lines.append(f"    {holding_info}")
        
        # Duchy and King castles
        lines.append("\n  Duchy Castles:")
        for holding in game_state.holdings:
            if holding.holding_type == HoldingType.DUCHY_CASTLE:
                owner = "NEUTRAL"
                if holding.owner_id:
                    owner_player = next((p for p in game_state.players if p.id == holding.owner_id), None)
                    owner = owner_player.name if owner_player else "Unknown"
                lines.append(f"    {holding.name} (id={holding.id}): Owner={owner}, Duchy={holding.duchy}")
        
        lines.append("\n  King's Castle:")
        for holding in game_state.holdings:
            if holding.holding_type == HoldingType.KING_CASTLE:
                owner = "NEUTRAL"
                if holding.owner_id:
                    owner_player = next((p for p in game_state.players if p.id == holding.owner_id), None)
                    owner = owner_player.name if owner_player else "Unknown"
                lines.append(f"    {holding.name} (id={holding.id}): Owner={owner}")
        
        lines.append(f"\n=== Your Hand ({len(player.hand)} cards) ===")
        for card_id in player.hand:
            card = game_state.cards.get(card_id)
            if card:
                lines.append(f"  - {card.name} (id={card_id}): {card.description}")
        
        return "\n".join(lines)
    
    def _format_holding_details(self, holding: Holding, owner: Optional[str] = None) -> str:
        """Format a holding with detailed information."""
        # Holding type
        type_labels = {
            HoldingType.TOWN: "Town",
            HoldingType.COUNTY_CASTLE: "County Castle",
            HoldingType.DUCHY_CASTLE: "Duchy Castle",
            HoldingType.KING_CASTLE: "King's Castle",
        }
        type_label = type_labels.get(holding.holding_type, "Unknown")
        
        parts = [f"{holding.name} (id={holding.id})"]
        parts.append(f"Type={type_label}")
        
        if owner:
            parts.append(f"Owner={owner}")
        
        # Resources
        if holding.gold_value > 0 or holding.soldier_value > 0:
            parts.append(f"Income={holding.gold_value}G/{holding.soldier_value}S")
        
        # Bonuses
        bonuses = []
        if holding.fortification_count > 0:
            bonuses.append(f"FORT x{holding.fortification_count} (+{holding.fortification_count * 2} def)")
        if holding.defense_modifier > 0:
            bonuses.append(f"+{holding.defense_modifier} defense")
        if holding.attack_modifier > 0:
            bonuses.append(f"+{holding.attack_modifier} attack")
        if holding.is_capitol:
            bonuses.append("CAPITOL")
        
        if bonuses:
            parts.append(f"[{', '.join(bonuses)}]")
        
        return ", ".join(parts)
    
    def _format_valid_actions(self, actions: list[Action], game_state: GameState, player: Player) -> str:
        """Format valid actions as a string for the AI prompt, including claim targets."""
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
                card = game_state.cards.get(action.card_id)
                if card:
                    action_desc += f" [{card.name}]"
                    # For claim cards, show available targets
                    if card.card_type == CardType.CLAIM:
                        targets = self._get_valid_claim_targets(game_state, player, card)
                        if targets:
                            action_desc += "\n      CLAIMABLE TARGETS:"
                            for t in targets:
                                owner = "NEUTRAL"
                                if t.owner_id:
                                    owner_player = next((p for p in game_state.players if p.id == t.owner_id), None)
                                    owner = owner_player.name if owner_player else "Unknown"
                                target_info = self._format_holding_details(t, owner)
                                action_desc += f"\n        - {target_info}"
            lines.append(action_desc)
        
        return "\n".join(lines)
    
    def _get_valid_claim_targets(self, game_state: GameState, player: Player, card) -> list[Holding]:
        """Get all valid targets for a claim card.
        
        Returns a list of holdings that can be claimed with this card.
        """
        from app.models.schemas import CardEffect
        
        effect = card.effect
        targets = []
        
        # County claim cards (CLAIM_X, CLAIM_U, CLAIM_V, CLAIM_Q)
        if effect in [CardEffect.CLAIM_X, CardEffect.CLAIM_U, CardEffect.CLAIM_V, CardEffect.CLAIM_Q]:
            effect_str = effect.value if hasattr(effect, 'value') else str(effect)
            target_county = effect_str.replace("claim_", "").upper()
            
            # Find all holdings in the target county that we don't own and haven't claimed
            for holding in game_state.holdings:
                if holding.county == target_county and holding.owner_id != player.id:
                    if holding.id not in (player.claims or []):
                        # County claim cards work on towns and county castles
                        if holding.holding_type in [HoldingType.TOWN, HoldingType.COUNTY_CASTLE]:
                            targets.append(holding)
        
        # Duchy claim - can claim any town or Duke+ title
        elif effect == CardEffect.DUCHY_CLAIM:
            for holding in game_state.holdings:
                if holding.owner_id != player.id and holding.id not in (player.claims or []):
                    if holding.holding_type in [HoldingType.TOWN, HoldingType.DUCHY_CASTLE, HoldingType.KING_CASTLE]:
                        targets.append(holding)
        
        # Ultimate claim - can claim anything
        elif effect == CardEffect.ULTIMATE_CLAIM:
            for holding in game_state.holdings:
                if holding.owner_id != player.id and holding.id not in (player.claims or []):
                    targets.append(holding)
        
        return targets
    
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
    
    def _parse_ai_response(self, response: str) -> tuple[Optional[int], Optional[str], Optional[int], str]:
        """Parse the structured AI response.
        
        Expected format:
        ACTION: [number]
        TARGET: [holding_id or "none"]
        SOLDIERS: [number or "none"] (for attack actions)
        REASON: [explanation]
        
        Returns:
            Tuple of (action_number, target_id, soldiers_count, reason)
            action_number is 1-indexed, or None if not found
            target_id is the holding ID, or None if "none" or not found
            soldiers_count is the number of soldiers to commit, or None
            reason is the explanation text
        """
        import re
        
        action_num = None
        target_id = None
        soldiers_count = None
        reason = ""
        
        # Parse ACTION line
        action_match = re.search(r'ACTION:\s*(\d+)', response, re.IGNORECASE)
        if action_match:
            action_num = int(action_match.group(1))
        else:
            # Fallback: try to find any number at the start
            numbers = re.findall(r'\d+', response)
            if numbers:
                action_num = int(numbers[0])
        
        # Parse TARGET line
        target_match = re.search(r'TARGET:\s*(\S+)', response, re.IGNORECASE)
        if target_match:
            target_value = target_match.group(1).strip().lower()
            if target_value != "none" and target_value != "n/a":
                target_id = target_value
        
        # Parse SOLDIERS line
        soldiers_match = re.search(r'SOLDIERS:\s*(\d+)', response, re.IGNORECASE)
        if soldiers_match:
            soldiers_count = int(soldiers_match.group(1))
        
        # Parse REASON line - capture everything after REASON:
        reason_match = re.search(r'REASON:\s*(.+?)(?:\n|$)', response, re.IGNORECASE | re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            # Use entire response as reason if format not followed
            reason = response.strip()[:200]
        
        return action_num, target_id, soldiers_count, reason
    
    def _complete_action(
        self, 
        action: Action, 
        game_state: GameState, 
        player: Player,
        target_id: Optional[str] = None,
        soldiers_count: Optional[int] = None
    ) -> Optional[Action]:
        """Complete an action with missing fields.
        
        Some actions (like PLAY_CARD for claim cards) require additional fields
        that are not populated by get_valid_actions(). This method fills them in.
        
        Args:
            action: The action to complete
            game_state: Current game state
            player: The player taking the action
            target_id: Optional target holding ID from AI response
            soldiers_count: Optional soldier count from AI response (for attacks)
        
        Returns None if the action cannot be completed (e.g., no valid target).
        """
        if action.action_type == ActionType.PLAY_CARD:
            card = game_state.cards.get(action.card_id)
            if card and card.card_type == CardType.CLAIM:
                # Claim cards require a target_holding_id
                if not action.target_holding_id:
                    # First, try to use the target_id from AI response
                    if target_id:
                        # Validate that the target is valid for this claim card
                        valid_targets = self._get_valid_claim_targets(game_state, player, card)
                        valid_target_ids = [t.id for t in valid_targets]
                        if target_id in valid_target_ids:
                            action.target_holding_id = target_id
                            return action
                    
                    # Fallback: auto-select first valid target
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
            if soldiers_count and soldiers_count >= 200:
                # Use AI-specified soldier count
                rounded_count = (soldiers_count // 100) * 100
                rounded_count = min(rounded_count, player.soldiers)  # Can't exceed available
                rounded_count = max(200, rounded_count)  # Ensure minimum 200
                action.soldiers_count = rounded_count
            elif not action.soldiers_count or action.soldiers_count < 200:
                # Fallback: commit 50% of soldiers
                raw_count = min(player.soldiers // 2, max(200, player.soldiers))
                rounded_count = (raw_count // 100) * 100
                rounded_count = max(200, rounded_count)
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

GAME STRUCTURE:
- 4 counties (X, U, V, Q), each with 3 towns and 1 county castle
- 2 duchies: XU (counties X+U) and QV (counties Q+V)
- 1 King's Castle in the center

=== TITLE PROGRESSION - YOUR PATH TO VICTORY ===
Titles give MASSIVE VP bonuses. Pursue them aggressively!

SCORING:
- Town = 1 VP
- Count title = +2 VP (total: 3 VP for town + county castle)
- Duke title = +4 VP (controls 2 counties!)
- King title = +6 VP (GAME WINNING!)

HOW TO BECOME COUNT (Choose ONE path):
  Path A: Own 2 of 3 towns in a county → pay 25 Gold for County Castle
  Path B (FASTER!): Own a CAPITOL with 1+ fortification → pay 25 Gold for County Castle
  CAPITOLS: X=Xythera, U=Umbrith, V=Valoria, Q=Quindara

HOW TO BECOME DUKE:
  Be Count in BOTH counties of a duchy (XU or QV) → pay 50 Gold for Duchy Castle

HOW TO BECOME KING:
  Be Duke + own any town in the OTHER duchy → pay 75 Gold for King's Castle

=== CLAIMS - THE FOUNDATION OF CONQUEST ===
CRITICAL: You CANNOT attack or capture ANY territory without a valid claim!

How to get claims:
1. Play claim cards from your hand (claim_x, claim_u, claim_v, claim_q)
2. Fabricate claims: 35 Gold, TOWNS ONLY (cannot fabricate on castles!)

With a claim you can:
- Capture UNOWNED town: pay 10 Gold (claim_town action)
- Attack ENEMY territory: commit 200+ soldiers

NO CLAIMS = NO EXPANSION. If you have no claims, getting claims is your TOP priority!

COMBAT:
- Must commit at least 200 soldiers
- Strength = 2d6 + (soldiers/100) + modifiers
- Winner loses HALF committed soldiers, loser loses ALL
- Defender wins ties
- Fortifications give +2 defense per fortification

=== STRATEGIC PRIORITY ORDER ===

1. claim_title - ALWAYS claim titles when available! They give huge VP!
   Count=+2VP, Duke=+4VP, King=+6VP. This is how you WIN.

2. IF YOU HAVE CLAIMS:
   - attack - Attack enemy territories to expand!
   - claim_town - Capture unowned towns for 10 gold

3. IF YOU HAVE NO CLAIMS (this blocks all expansion!):
   - play_card - Play claim cards IMMEDIATELY to enable conquest
   - fake_claim - Fabricate claims (35 Gold) on enemy towns - DO THIS!
   Getting claims is URGENT - you cannot expand without them!

4. build_fortification - Fortify your CAPITOL! This unlocks Count title fast!
   Only need 1 fort on capitol to qualify for Count (vs conquering 2 towns)

5. recruit - Get soldiers if below 300 for attacking

6. end_turn - Only when no productive actions remain

MINDSET: Titles win games! Focus on becoming Count → Duke → King. 
Claims enable everything - if you can't attack, get claims FIRST!

CARD TYPES:
- Claim cards (claim_x, claim_u, claim_v, claim_q): Use to enable attacks on that county!
- Bonus cards: Big War (double army cap), Adventurer (buy 500 soldiers for 25g), Excalibur (roll twice), etc.
- Personal/Global events: Applied automatically when drawn

RESPONSE FORMAT (IMPORTANT):
You must respond in this EXACT format:
ACTION: [number]
TARGET: [holding_id or "none"]
SOLDIERS: [number or "none"] (REQUIRED for attack actions)
REASON: [brief explanation of your choice]

Example responses:
ACTION: 3
TARGET: none
SOLDIERS: none
REASON: Claiming Count title to gain 2 VP and solidify control of County X.

ACTION: 5
TARGET: xythera
SOLDIERS: none
REASON: Playing claim card on Xythera because it's a CAPITOL - fortifying it later gives easy Count title.

ACTION: 2
TARGET: none
SOLDIERS: 400
REASON: Attacking enemy town with 400 soldiers - enough to win but preserving reserves.

For claim cards (play_card), you MUST specify which holding to target from the CLAIMABLE TARGETS list shown.
For attack actions, you MUST specify SOLDIERS (minimum 200, in multiples of 100). Consider:
- More soldiers = higher chance of winning
- Winner loses 50% of committed soldiers, loser loses 100%
- Don't overcommit if you need reserves for future battles
For other actions, use "none" for both TARGET and SOLDIERS."""



