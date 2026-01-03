"""AI Player Manager - handles AI player creation and action execution."""
from typing import Optional
from app.config import get_settings
from app.models.schemas import GameState, Player, PlayerType, Action, ActionType, HoldingType
from app.ai.base import AIPlayer
from app.ai.openai_player import OpenAIPlayer
from app.ai.anthropic_player import AnthropicPlayer
from app.ai.gemini_player import GeminiPlayer
from app.ai.grok_player import GrokPlayer
from app.game.engine import GameEngine


class AIManager:
    """Manages AI players for games."""
    
    def __init__(self):
        self.settings = get_settings()
        self._players: dict[str, AIPlayer] = {}
    
    def get_ai_player(self, player_type: PlayerType) -> Optional[AIPlayer]:
        """Get or create an AI player instance for the given type."""
        if player_type == PlayerType.HUMAN:
            return None
        
        # Cache key
        key = player_type.value
        
        if key in self._players:
            return self._players[key]
        
        # Create new AI player based on type
        ai_player: Optional[AIPlayer] = None
        
        if player_type == PlayerType.AI_OPENAI:
            if self.settings.openai_api_key:
                ai_player = OpenAIPlayer(self.settings.openai_api_key)
            else:
                # Fallback to simple AI
                ai_player = SimpleAIPlayer()
                
        elif player_type == PlayerType.AI_ANTHROPIC:
            if self.settings.anthropic_api_key:
                ai_player = AnthropicPlayer(self.settings.anthropic_api_key)
            else:
                ai_player = SimpleAIPlayer()
                
        elif player_type == PlayerType.AI_GEMINI:
            if self.settings.google_api_key:
                ai_player = GeminiPlayer(self.settings.google_api_key)
            else:
                ai_player = SimpleAIPlayer()
                
        elif player_type == PlayerType.AI_GROK:
            if self.settings.xai_api_key:
                ai_player = GrokPlayer(self.settings.xai_api_key)
            else:
                ai_player = SimpleAIPlayer()
        
        if ai_player:
            self._players[key] = ai_player
        
        return ai_player
    
    async def get_ai_action(self, state: GameState, player: Player) -> Optional[Action]:
        """Get the next action for an AI player."""
        if player.player_type == PlayerType.HUMAN:
            return None
        
        ai_player = self.get_ai_player(player.player_type)
        if not ai_player:
            # Use simple AI as ultimate fallback
            ai_player = SimpleAIPlayer()
        
        # Get valid actions from game engine
        engine = GameEngine(state.id)
        valid_actions = engine.get_valid_actions(player.id)
        
        if not valid_actions:
            return None
        
        # Have AI decide
        return await ai_player.decide_action(state, player, valid_actions)
    
    async def get_starting_town(
        self, 
        state: GameState, 
        player: Player, 
        available_towns: list
    ) -> str:
        """Get starting town choice for an AI player."""
        ai_player = self.get_ai_player(player.player_type)
        if not ai_player:
            ai_player = SimpleAIPlayer()
        
        return await ai_player.decide_starting_town(state, player, available_towns)


class SimpleAIPlayer(AIPlayer):
    """A simple rule-based AI player for when API keys aren't available.
    
    This serves as a fallback and for testing without API costs.
    """
    
    def __init__(self):
        super().__init__("", None)
    
    async def decide_action(
        self,
        game_state: GameState,
        player: Player,
        valid_actions: list[Action]
    ) -> Action:
        """Choose an action using simple heuristics."""
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        # Priority order:
        # 1. Draw card if not drawn this turn
        # 2. Play claim cards to establish claims (with valid target)
        # 3. Claim title if possible (Count/Duke/King)
        # 4. Capture unowned towns with claims (10 gold)
        # 5. Attack enemy targets with claims
        # 6. Fabricate claims if we have gold and no claims
        # 7. Build fortifications
        # 8. End turn
        
        # 1. Draw card first
        for action in valid_actions:
            if action.action_type == ActionType.DRAW_CARD:
                return action
        
        # 2. Play claim cards (need to find valid target)
        play_card_actions = [a for a in valid_actions if a.action_type == ActionType.PLAY_CARD]
        for action in play_card_actions:
            card = game_state.cards.get(action.card_id)
            if card and card.card_type.value == "claim":
                # Find a valid target for this claim card
                target = self._find_claim_target(game_state, player, card)
                if target:
                    action.target_holding_id = target.id
                    return action
            elif card and card.card_type.value == "bonus":
                # Check if we can actually play this bonus card
                if self._can_play_bonus_card(player, card):
                    return action
        
        # 3. Claim title if possible
        for action in valid_actions:
            if action.action_type == ActionType.CLAIM_TITLE:
                return action
        
        # 4. Capture unowned towns (costs 10 gold, requires claim)
        for action in valid_actions:
            if action.action_type == ActionType.CLAIM_TOWN:
                return action
        
        # 5. Attack if we have enough soldiers and a claim
        attack_actions = [a for a in valid_actions if a.action_type == ActionType.ATTACK]
        if attack_actions and player.soldiers >= 400:
            # Attack first available if we have enough force
            attack_actions[0].soldiers_count = min(player.soldiers // 2, 600)
            return attack_actions[0]
        
        # 6. Fabricate claim if we have gold (35g) but no claims
        if player.gold >= 35 and len(player.claims or []) == 0:
            for action in valid_actions:
                if action.action_type == ActionType.FAKE_CLAIM:
                    return action
        
        # 7. Build fortification if we have gold
        for action in valid_actions:
            if action.action_type == ActionType.BUILD_FORTIFICATION:
                return action
        
        # 8. End turn
        for action in valid_actions:
            if action.action_type == ActionType.END_TURN:
                return action
        
        return valid_actions[0]
    
    def _find_claim_target(self, game_state: GameState, player: Player, card) -> Optional[any]:
        """Find a valid target holding for a claim card."""
        from app.game.cards import get_card_county
        
        effect = card.effect
        
        # County claim cards (CLAIM_X, CLAIM_U, CLAIM_V, CLAIM_Q)
        if effect and effect.value in ["claim_x", "claim_u", "claim_v", "claim_q"]:
            required_county = get_card_county(card)
            # Find a town in that county we don't own and haven't claimed
            for holding in game_state.holdings:
                if (holding.holding_type == HoldingType.TOWN and 
                    holding.county == required_county and
                    holding.owner_id != player.id and
                    holding.id not in (player.claims or [])):
                    return holding
        
        # Duchy claim - find any town we don't own
        elif effect and effect.value == "duchy_claim":
            for holding in game_state.holdings:
                if (holding.holding_type == HoldingType.TOWN and
                    holding.owner_id != player.id and
                    holding.id not in (player.claims or [])):
                    return holding
        
        # Ultimate claim - find any holding we don't own
        elif effect and effect.value == "ultimate_claim":
            for holding in game_state.holdings:
                if (holding.owner_id != player.id and
                    holding.id not in (player.claims or [])):
                    return holding
        
        return None
    
    def _can_play_bonus_card(self, player: Player, card) -> bool:
        """Check if a bonus card can be successfully played."""
        from app.models.schemas import CardEffect
        
        effect = card.effect
        if not effect:
            return False
        
        # Check conditions for cards that have requirements
        if effect == CardEffect.ADVENTURER:
            return player.gold >= 25  # Requires 25 gold
        
        # These cards can always be played
        if effect in [
            CardEffect.BIG_WAR,
            CardEffect.EXCALIBUR,
            CardEffect.POISONED_ARROWS,
            CardEffect.TALENTED_COMMANDER,
            CardEffect.FORBID_MERCENARIES,
            CardEffect.ENFORCE_PEACE,
            CardEffect.VASSAL_REVOLT,
            CardEffect.DUEL,
            CardEffect.SPY,
        ]:
            return True
        
        return False  # Unknown effect, don't play
    
    async def decide_combat_commitment(
        self,
        game_state: GameState,
        player: Player,
        target,
        min_soldiers: int,
        max_soldiers: int
    ) -> int:
        """Simple heuristic for combat commitment."""
        # Commit 60% of available soldiers, but at least minimum
        commitment = int(max_soldiers * 0.6)
        return max(min_soldiers, min(max_soldiers, commitment))
    
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list
    ) -> str:
        """Choose the highest value starting town."""
        if not available_towns:
            raise ValueError("No towns available")
        
        # Pick the town with highest combined value
        best = max(
            available_towns,
            key=lambda t: t.gold_value + t.soldier_value * 100
        )
        return best.id



