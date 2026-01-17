"""xAI Grok-based AI player."""
import re
from datetime import datetime
from typing import Optional, Tuple, TYPE_CHECKING
from openai import AsyncOpenAI

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType, AIDecisionLog, AIDecisionLogEntry

if TYPE_CHECKING:
    from app.game.logger import GameLogger


class GrokPlayer(AIPlayer):
    """AI player powered by xAI's Grok models.
    
    Note: Grok uses an OpenAI-compatible API endpoint.
    """
    
    DEFAULT_MODEL = "grok-beta"
    BASE_URL = "https://api.x.ai/v1"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
        )
    
    async def _get_completion(self, system: str, user: str) -> str:
        """Get a completion from Grok."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    
    async def decide_action(
        self,
        game_state: GameState,
        player: Player,
        valid_actions: list[Action],
        logger: Optional["GameLogger"] = None
    ) -> Tuple[Action, AIDecisionLog]:
        """Choose an action using Grok."""
        action_types = [a.action_type.value for a in valid_actions]
        
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions)
        
        system_prompt = self._get_system_prompt()
        user_prompt = f"""{state_text}

{actions_text}

BE AGGRESSIVE! Choose the BEST action. Priority order (highest to lowest):
1. attack - ATTACK enemies whenever possible! War brings victory! (requires 200+ soldiers)
2. claim_title - ALWAYS claim titles immediately (gives VP!)
3. claim_town - Capture unowned towns for 10 gold
4. play_card - Play claim cards to enable MORE ATTACKS
5. fake_claim - Fabricate claims on enemy towns to attack them! (35 gold)
6. build_fortification - FORTIFY YOUR CAPITOL FIRST! (X=Xythera, U=Umbrith, V=Valoria, Q=Quindara)
   - A fortified Capitol (1 fort) lets you become Count without 2 towns!
7. end_turn - Only when no aggressive moves remain
8. recruit - Only to prepare for attacks

IMPORTANT: You are a WARLORD. Attack first! Fortify your Capitol for a fast path to Count title!
If you can attack, DO IT. Expansion through conquest is the path to victory!

Reply with just the action number (1-{len(valid_actions)})."""
        
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
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                action_idx = int(numbers[0]) - 1
                if 0 <= action_idx < len(valid_actions):
                    chosen = valid_actions[action_idx]
                    completed = self._complete_action(chosen, game_state, player)
                    if completed:
                        decision_log = make_log(completed, f"Grok selected #{action_idx+1}: {response[:50]}")
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
        """Decide soldiers to commit using Grok."""
        state_text = self._format_game_state(game_state, player)
        
        defender = None
        if target.owner_id:
            defender = next((p for p in game_state.players if p.id == target.owner_id), None)
        
        defender_info = "No defender" if not defender else f"{defender.name} waiting"
        fort_status = "fortified (tough nut to crack)" if target.fortified else "open"
        
        prompt = f"""{state_text}

Battle time! You're attacking {target.name}.
The target is {fort_status}.
Defender situation: {defender_info}

You've got {min_soldiers} to {max_soldiers} soldiers ready.
Remember: win = lose half your troops, lose = lose them all.

How many soldiers are you sending in? Just give me a number."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                soldiers = int(numbers[0])
                return max(min_soldiers, min(max_soldiers, soldiers))
            
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.7)))
            
        except Exception:
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.7)))
    
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list[Holding]
    ) -> str:
        """Choose a starting town using Grok."""
        towns_text = "\n".join([
            f"{i+1}. {t.name} (County {t.county}) - {t.gold_value}G/{t.soldier_value*100}S"
            for i, t in enumerate(available_towns)
        ])
        
        prompt = f"""Fresh game! Pick your starting territory.

Your options:
{towns_text}

The town you pick gives you starting gold and soldiers.
Think about what kind of start you want - rich or military?

Pick a number (1-{len(available_towns)})."""
        
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



