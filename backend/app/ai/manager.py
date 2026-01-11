"""AI Player Manager - handles AI player creation and action execution."""
from typing import Optional, Tuple
from datetime import datetime
from app.config import get_settings
from app.models.schemas import (
    GameState, Player, PlayerType, Action, ActionType, HoldingType,
    AIDecisionLog, AIDecisionLogEntry
)
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
    
    async def get_ai_action(self, state: GameState, player: Player) -> Tuple[Optional[Action], Optional[AIDecisionLog]]:
        """Get the next action for an AI player, along with decision log."""
        import time
        
        if player.player_type == PlayerType.HUMAN:
            return None, None
        
        ai_player = self.get_ai_player(player.player_type)
        
        if not ai_player:
            # Use simple AI as ultimate fallback
            ai_player = SimpleAIPlayer()
        
        # Get valid actions from game engine
        engine = GameEngine(state.id)
        valid_actions = engine.get_valid_actions(player.id)
        
        if not valid_actions:
            return None, None
        
        # Have AI decide - SimpleAIPlayer returns (action, log), others just return action
        result = await ai_player.decide_action(state, player, valid_actions)
        
        if isinstance(result, tuple):
            return result
        else:
            # Legacy AI players that don't return logs
            return result, None
    
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
    ) -> Tuple[Action, AIDecisionLog]:
        """Choose an action using simple heuristics, with full decision logging."""
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        # Build list of available action types for the log
        action_types = list(set(a.action_type.value for a in valid_actions))
        considered: list[AIDecisionLogEntry] = []
        chosen_action: Optional[Action] = None
        chosen_reason = ""
        
        # AGGRESSIVE Priority order (cards are auto-drawn at turn start):
        # 1. ATTACK enemy targets with claims - WAR FIRST!
        # 2. Claim title if possible (Count/Duke/King)
        # 3. Capture unowned towns with claims (10 gold)
        # 4. Play claim cards to establish claims (with valid target) - enables more attacks!
        # 5. Fabricate claims if we have gold - enables more attacks!
        # 6. Build fortifications (only if nothing to attack)
        # 7. End turn
        
        # 1. ATTACK FIRST - We are aggressive warlords!
        if not chosen_action:
            attack_actions = [a for a in valid_actions if a.action_type == ActionType.ATTACK]
            if attack_actions and player.soldiers >= 200:
                # Sort by weakest target first (prefer attacking towns with fewer fortifications)
                chosen_action = attack_actions[0]
                # Commit 70% of soldiers for aggressive attacks (minimum 300), rounded down to 100s
                raw_soldiers = max(300, int(player.soldiers * 0.7))
                rounded_soldiers = (raw_soldiers // 100) * 100  # Round down to nearest 100
                chosen_action.soldiers_count = rounded_soldiers
                chosen_reason = f"ATTACKING {chosen_action.target_holding_id} with {chosen_action.soldiers_count} soldiers! War is the path to victory!"
                considered.append(AIDecisionLogEntry(action="attack", status="chosen", reason=chosen_reason))
            elif attack_actions:
                considered.append(AIDecisionLogEntry(action="attack", status="skipped", reason=f"Have claims but not enough soldiers (have {player.soldiers}, need 200+)"))
            else:
                considered.append(AIDecisionLogEntry(action="attack", status="unavailable", reason="No valid attack targets (need claim on enemy territory)"))
        
        # 2. Claim title if possible (gives VP immediately)
        if not chosen_action:
            title_actions = [a for a in valid_actions if a.action_type == ActionType.CLAIM_TITLE]
            if title_actions:
                chosen_action = title_actions[0]
                target_id = chosen_action.target_holding_id
                chosen_reason = f"Claiming title at {target_id} (prerequisites met, have enough gold)"
                considered.append(AIDecisionLogEntry(action="claim_title", status="chosen", reason=chosen_reason))
            else:
                considered.append(AIDecisionLogEntry(action="claim_title", status="unavailable", reason="Prerequisites not met or not enough gold (Count: 2 towns OR fortified capitol + 25g, Duke: 2 counties + 50g, King: 1 duchy + town in other duchy + 75g)"))
        
        # 3. Capture unowned towns (costs 10 gold, requires claim)
        if not chosen_action:
            claim_town_actions = [a for a in valid_actions if a.action_type == ActionType.CLAIM_TOWN]
            if claim_town_actions:
                chosen_action = claim_town_actions[0]
                chosen_reason = f"Capturing unowned town {chosen_action.target_holding_id} for 10 gold (have valid claim)"
                considered.append(AIDecisionLogEntry(action="claim_town", status="chosen", reason=chosen_reason))
            else:
                considered.append(AIDecisionLogEntry(action="claim_town", status="unavailable", reason="No unowned towns with valid claims, or not enough gold (10g)"))
        
        # 4. Play claim cards (to enable more attacks!)
        if not chosen_action:
            play_card_actions = [a for a in valid_actions if a.action_type == ActionType.PLAY_CARD]
            if play_card_actions:
                for action in play_card_actions:
                    card = game_state.cards.get(action.card_id)
                    if card and card.card_type.value == "claim":
                        target = self._find_claim_target(game_state, player, card)
                        if target:
                            action.target_holding_id = target.id
                            chosen_action = action
                            chosen_reason = f"Playing claim card '{card.name}' targeting {target.name} to enable future attacks!"
                            considered.append(AIDecisionLogEntry(action="play_card", status="chosen", reason=chosen_reason))
                            break
                        else:
                            considered.append(AIDecisionLogEntry(action="play_card", status="skipped", reason=f"Claim card '{card.name}' has no valid target (already own all towns in that county)"))
                    elif card and card.card_type.value == "bonus":
                        if self._can_play_bonus_card(player, card):
                            chosen_action = action
                            chosen_reason = f"Playing bonus card '{card.name}'"
                            considered.append(AIDecisionLogEntry(action="play_card", status="chosen", reason=chosen_reason))
                            break
                        else:
                            considered.append(AIDecisionLogEntry(action="play_card", status="skipped", reason=f"Bonus card '{card.name}' requirements not met (e.g., not enough gold)"))
                if not chosen_action and play_card_actions:
                    considered.append(AIDecisionLogEntry(action="play_card", status="skipped", reason="No playable cards with valid targets"))
            else:
                if ActionType.PLAY_CARD.value in action_types:
                    considered.append(AIDecisionLogEntry(action="play_card", status="skipped", reason="No cards in hand"))
        
        # 5. Fabricate claims aggressively - enables attacks!
        if not chosen_action:
            fake_claim_actions = [a for a in valid_actions if a.action_type == ActionType.FAKE_CLAIM]
            # Be aggressive - fabricate claims even if we have some, as long as we have gold
            if fake_claim_actions and player.gold >= 35:
                chosen_action = fake_claim_actions[0]
                chosen_reason = f"Fabricating claim on {chosen_action.target_holding_id} for 35 gold to enable future attack!"
                considered.append(AIDecisionLogEntry(action="fake_claim", status="chosen", reason=chosen_reason))
            elif fake_claim_actions:
                considered.append(AIDecisionLogEntry(action="fake_claim", status="skipped", reason=f"Not enough gold ({player.gold}/35)"))
            else:
                considered.append(AIDecisionLogEntry(action="fake_claim", status="unavailable", reason="No targets available for fake claims"))
        
        # 6. Build fortification only if nothing to attack
        if not chosen_action:
            fort_actions = [a for a in valid_actions if a.action_type == ActionType.BUILD_FORTIFICATION]
            if fort_actions:
                chosen_action = fort_actions[0]
                chosen_reason = f"Building fortification at {chosen_action.target_holding_id} for 10 gold (no attack options)"
                considered.append(AIDecisionLogEntry(action="build_fortification", status="chosen", reason=chosen_reason))
            else:
                considered.append(AIDecisionLogEntry(action="build_fortification", status="unavailable", reason="No valid locations or not enough gold (10g)"))
        
        # 7. End turn
        if not chosen_action:
            end_actions = [a for a in valid_actions if a.action_type == ActionType.END_TURN]
            if end_actions:
                chosen_action = end_actions[0]
                chosen_reason = "Ending turn (no other beneficial actions available)"
                considered.append(AIDecisionLogEntry(action="end_turn", status="chosen", reason=chosen_reason))
        
        # Fallback
        if not chosen_action:
            chosen_action = valid_actions[0]
            chosen_reason = f"Fallback: selecting first available action ({chosen_action.action_type.value})"
        
        # Build the decision log
        decision_log = AIDecisionLog(
            player_name=player.name,
            timestamp=datetime.now().isoformat(),
            valid_actions=action_types,
            considered=considered,
            chosen_action=chosen_action.action_type.value,
            reason=chosen_reason
        )
        
        return chosen_action, decision_log
    
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



