"""OpenAI GPT-based AI player."""
import json
import re
from datetime import datetime
from typing import Optional, Tuple, TYPE_CHECKING
from openai import AsyncOpenAI

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType, AIDecisionLog, AIDecisionLogEntry

if TYPE_CHECKING:
    from app.game.logger import GameLogger


class OpenAIPlayer(AIPlayer):
    """AI player powered by OpenAI's GPT models."""
    
    DEFAULT_MODEL = "gpt-4o"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def _get_completion(self, system: str, user: str) -> str:
        """Get a completion from OpenAI."""
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
        """Choose an action using GPT."""
        action_types = [a.action_type.value for a in valid_actions]
        
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        # Format the game state and actions for the AI
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

Respond with ONLY the number of your chosen action (1-{len(valid_actions)})."""
        
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
            
            # Parse the response to get action number
            # Extract first number from response
            numbers = re.findall(r'\d+', response)
            if numbers:
                action_idx = int(numbers[0]) - 1
                if 0 <= action_idx < len(valid_actions):
                    chosen = valid_actions[action_idx]
                    # Complete the action with any missing fields
                    completed = self._complete_action(chosen, game_state, player)
                    if completed:
                        decision_log = make_log(completed, f"GPT selected action #{action_idx+1}: {response[:50]}")
                        log_ai_decision(response, completed, decision_log)
                        return completed, decision_log
                    # If action couldn't be completed, fallback to END_TURN
                    for action in valid_actions:
                        if action.action_type == ActionType.END_TURN:
                            decision_log = make_log(action, "Fallback after incomplete action")
                            log_ai_decision(response, action, decision_log)
                            return action, decision_log
            
            # Fallback: return end_turn or first valid action
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    decision_log = make_log(action, "GPT response parsing failed, defaulting to end_turn")
                    log_ai_decision(response, action, decision_log)
                    return action, decision_log
            
            fallback = valid_actions[0]
            decision_log = make_log(fallback, "All fallbacks exhausted")
            log_ai_decision(response, fallback, decision_log)
            return fallback, decision_log
            
        except Exception as e:
            error_response = f"Error: {str(e)}"
            # On any error, return a safe default action
            # Prefer end_turn if available, otherwise first action
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    decision_log = make_log(action, f"Error: {str(e)[:100]}")
                    log_ai_decision(error_response, action, decision_log)
                    return action, decision_log
            fallback = valid_actions[0]
            decision_log = make_log(fallback, f"Error fallback: {str(e)[:100]}")
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
        """Decide soldiers to commit using GPT."""
        state_text = self._format_game_state(game_state, player)
        
        # Get defender info
        defender = None
        if target.owner_id:
            defender = next((p for p in game_state.players if p.id == target.owner_id), None)
        
        defender_info = "NEUTRAL (undefended)" if not defender else f"{defender.name} with ~{defender.soldiers} soldiers"
        
        prompt = f"""{state_text}

You are attacking: {target.name}
Defender: {defender_info}
Target is fortified: {target.fortified}

You can commit between {min_soldiers} and {max_soldiers} soldiers.

COMBAT RULES:
- Strength = 2d6 + (soldiers/100) + modifiers
- Winner loses HALF their committed soldiers
- Loser loses ALL committed soldiers
- Fortifications give +2 defense

How many soldiers should you commit? Consider:
- Overwhelming force is safer but costly
- Minimal force risks losing the attack
- Your remaining soldiers after commitment

Respond with ONLY a number between {min_soldiers} and {max_soldiers}."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                soldiers = int(numbers[0])
                return max(min_soldiers, min(max_soldiers, soldiers))
            
            # Default to 60% of available soldiers
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.6)))
            
        except Exception:
            # Default to 60% of available
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.6)))
    
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list[Holding]
    ) -> str:
        """Choose a starting town using GPT."""
        towns_text = "\n".join([
            f"{i+1}. {t.name} (County {t.county}): {t.gold_value}G, {t.soldier_value*100}S"
            for i, t in enumerate(available_towns)
        ])
        
        prompt = f"""You are {player.name}, starting a new game of Machiavelli's Kingdom.

Choose your starting town. Your starting resources will be based on the town's values.

Available towns:
{towns_text}

STRATEGY TIPS:
- Higher gold helps with building and claiming titles
- More soldiers help with early expansion
- County position matters for claiming Count title later
- Consider which counties other players might target

Respond with ONLY the number of your chosen town (1-{len(available_towns)})."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                town_idx = int(numbers[0]) - 1
                if 0 <= town_idx < len(available_towns):
                    return available_towns[town_idx].id
            
            # Default to highest value town
            best = max(available_towns, key=lambda t: t.gold_value + t.soldier_value * 100)
            return best.id
            
        except Exception:
            # Default to highest value town
            best = max(available_towns, key=lambda t: t.gold_value + t.soldier_value * 100)
            return best.id



