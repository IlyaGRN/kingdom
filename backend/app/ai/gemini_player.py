"""Google Gemini-based AI player."""
import re
from datetime import datetime
from typing import Optional, Tuple, TYPE_CHECKING
import google.generativeai as genai

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType, AIDecisionLog, AIDecisionLogEntry

if TYPE_CHECKING:
    from app.game.logger import GameLogger


class GeminiPlayer(AIPlayer):
    """AI player powered by Google's Gemini models."""
    
    DEFAULT_MODEL = "gemini-1.5-pro"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(self.model)
    
    async def _get_completion(self, system: str, user: str) -> str:
        """Get a completion from Gemini."""
        # Gemini uses a combined prompt approach
        full_prompt = f"{system}\n\n{user}"
        
        response = await self.model_instance.generate_content_async(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=300,
            ),
        )
        return response.text.strip()
    
    async def decide_action(
        self,
        game_state: GameState,
        player: Player,
        valid_actions: list[Action],
        logger: Optional["GameLogger"] = None
    ) -> Tuple[Action, AIDecisionLog]:
        """Choose an action using Gemini."""
        action_types = [a.action_type.value for a in valid_actions]
        
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions, game_state, player)
        
        system_prompt = self._get_system_prompt()
        user_prompt = f"""{state_text}

{actions_text}

You have {player.soldiers} soldiers available. Minimum 200 required for attacks.

Choose your action wisely!
- For claim cards (play_card): specify TARGET from CLAIMABLE TARGETS list
- For attacks: specify SOLDIERS to commit (200-{player.soldiers}, multiples of 100)

Respond in this format:
ACTION: [number 1-{len(valid_actions)}]
TARGET: [holding_id or "none"]
SOLDIERS: [number for attacks, or "none"]
REASON: [your strategic reasoning]"""
        
        def make_log(action: Action, reason: str) -> AIDecisionLog:
            return AIDecisionLog(
                player_name=player.name,
                timestamp=datetime.now().isoformat(),
                valid_actions=action_types,
                considered=[AIDecisionLogEntry(action=action.action_type.value, status="chosen", reason=reason)],
                chosen_action=action.action_type.value,
                reason=reason
            )
        
        def log_ai_decision(response: str, chosen_action: Action, decision_log: AIDecisionLog):
            """Log the AI decision if logger is available."""
            if logger:
                action_details = logger.get_action_details(chosen_action)
                logger.log_ai_decision(
                    round_num=game_state.current_round,
                    player_id=player.id,
                    player_name=player.name,
                    player_type=player.player_type.value,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    raw_response=response,
                    parsed_action=chosen_action.action_type.value,
                    action_details=action_details,
                    decision_log=decision_log.model_dump() if decision_log else None
                )
        
        try:
            response = await self._get_completion(system_prompt, user_prompt)
            
            # Parse the structured response
            action_num, target_id, soldiers_count, reason = self._parse_ai_response(response)
            
            if action_num is not None:
                action_idx = action_num - 1
                if 0 <= action_idx < len(valid_actions):
                    chosen = valid_actions[action_idx]
                    completed = self._complete_action(chosen, game_state, player, target_id, soldiers_count)
                    if completed:
                        decision_log = make_log(completed, reason or f"Gemini selected #{action_num}")
                        log_ai_decision(response, completed, decision_log)
                        return completed, decision_log
                    for action in valid_actions:
                        if action.action_type == ActionType.END_TURN:
                            decision_log = make_log(action, "Fallback after incomplete action")
                            log_ai_decision(response, action, decision_log)
                            return action, decision_log
            
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    decision_log = make_log(action, "Parse failed, defaulting to end_turn")
                    log_ai_decision(response, action, decision_log)
                    return action, decision_log
            fallback = valid_actions[0]
            decision_log = make_log(fallback, "All fallbacks exhausted")
            log_ai_decision(response, fallback, decision_log)
            return fallback, decision_log
            
        except Exception as e:
            error_response = f"Error: {str(e)}"
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    decision_log = make_log(action, f"Error: {str(e)[:50]}")
                    log_ai_decision(error_response, action, decision_log)
                    return action, decision_log
            fallback = valid_actions[0]
            decision_log = make_log(fallback, f"Error fallback: {str(e)[:50]}")
            log_ai_decision(error_response, fallback, decision_log)
            return fallback, decision_log
    
    async def decide_combat_commitment(
        self,
        game_state: GameState,
        player: Player,
        target: Holding,
        min_soldiers: int,
        max_soldiers: int
    ) -> int:
        """Decide soldiers to commit using Gemini."""
        state_text = self._format_game_state(game_state, player)
        
        defender = None
        if target.owner_id:
            defender = next((p for p in game_state.players if p.id == target.owner_id), None)
        
        defender_info = "Undefended" if not defender else f"Defended by {defender.name}"
        
        prompt = f"""{state_text}

COMBAT DECISION REQUIRED:
Attacking: {target.name}
Status: {defender_info}, {"Fortified" if target.fortified else "Unfortified"}
Available: {min_soldiers} to {max_soldiers} soldiers

Remember:
- Combat uses 2d6 + (soldiers/100) + bonuses
- Winners lose 50% of committed troops
- Losers lose everything

Choose your troop commitment wisely.
Respond with ONLY a number between {min_soldiers} and {max_soldiers}."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                soldiers = int(numbers[0])
                return max(min_soldiers, min(max_soldiers, soldiers))
            
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.55)))
            
        except Exception:
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.55)))
    
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list[Holding]
    ) -> str:
        """Choose a starting town using Gemini."""
        towns_text = "\n".join([
            f"{i+1}. {t.name} in County {t.county}: {t.gold_value} gold, {t.soldier_value*100} soldiers"
            for i, t in enumerate(available_towns)
        ])
        
        prompt = f"""New game of Machiavelli's Kingdom starting!

You must choose a starting town. Your choice determines initial resources.

Available options:
{towns_text}

Consider starting resources and strategic county positioning.
Respond with ONLY the number of your choice (1-{len(available_towns)})."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                town_idx = int(numbers[0]) - 1
                if 0 <= town_idx < len(available_towns):
                    return available_towns[town_idx].id
            
            best = max(available_towns, key=lambda t: t.gold_value + t.soldier_value * 100)
            return best.id
            
        except Exception:
            best = max(available_towns, key=lambda t: t.gold_value + t.soldier_value * 100)
            return best.id



