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
        # 1. Draw card if not drawn
        # 2. Claim title if possible
        # 3. Attack weak targets
        # 4. Build fortifications
        # 5. Form alliance
        # 6. End turn
        
        for action in valid_actions:
            if action.action_type == ActionType.DRAW_CARD:
                return action
        
        for action in valid_actions:
            if action.action_type == ActionType.CLAIM_TITLE:
                return action
        
        # Attack if we have enough soldiers and a good target
        attack_actions = [a for a in valid_actions if a.action_type == ActionType.ATTACK]
        if attack_actions and player.soldiers >= 400:
            # Prefer attacking neutral or weak targets
            for action in attack_actions:
                target = next(
                    (h for h in game_state.holdings if h.id == action.target_holding_id), 
                    None
                )
                if target and not target.owner_id:  # Neutral
                    action.soldiers_count = min(player.soldiers, 400)
                    return action
            
            # Attack first available if we have overwhelming force
            if player.soldiers >= 600:
                attack_actions[0].soldiers_count = min(player.soldiers // 2, 600)
                return attack_actions[0]
        
        # Build fortification if we have gold
        for action in valid_actions:
            if action.action_type == ActionType.BUILD_FORTIFICATION:
                return action
        
        # Form alliance if available
        for action in valid_actions:
            if action.action_type == ActionType.FORM_ALLIANCE:
                return action
        
        # End turn
        for action in valid_actions:
            if action.action_type == ActionType.END_TURN:
                return action
        
        return valid_actions[0]
    
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

