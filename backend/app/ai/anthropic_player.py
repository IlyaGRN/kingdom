"""Anthropic Claude-based AI player."""
import re
from datetime import datetime
from typing import Optional, Tuple
from anthropic import AsyncAnthropic

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType, AIDecisionLog, AIDecisionLogEntry


class AnthropicPlayer(AIPlayer):
    """AI player powered by Anthropic's Claude models."""
    
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def _get_completion(self, system: str, user: str) -> str:
        """Get a completion from Anthropic."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=100,
            system=system,
            messages=[
                {"role": "user", "content": user},
            ],
        )
        return response.content[0].text.strip()
    
    async def decide_action(
        self,
        game_state: GameState,
        player: Player,
        valid_actions: list[Action]
    ) -> Tuple[Action, AIDecisionLog]:
        """Choose an action using Claude."""
        action_types = [a.action_type.value for a in valid_actions]
        
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions)
        
        prompt = f"""{state_text}

{actions_text}

BE AGGRESSIVE! Choose the BEST action. Priority order (highest to lowest):
1. attack - ATTACK enemies whenever possible! War brings victory! (requires 200+ soldiers)
2. claim_title - ALWAYS claim titles immediately (gives VP!)
3. claim_town - Capture unowned towns for 10 gold
4. play_card - Play claim cards to enable MORE ATTACKS
5. fake_claim - Fabricate claims on enemy towns to attack them! (35 gold)
6. build_fortification - Only if no attack options available
7. end_turn - Only when no aggressive moves remain
8. recruit - Only to prepare for attacks

IMPORTANT: You are a WARLORD. Attack first! Every attack weakens your enemies.
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
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                action_idx = int(numbers[0]) - 1
                if 0 <= action_idx < len(valid_actions):
                    chosen = valid_actions[action_idx]
                    completed = self._complete_action(chosen, game_state, player)
                    if completed:
                        return completed, make_log(completed, f"Claude selected #{action_idx+1}: {response[:50]}")
                    for action in valid_actions:
                        if action.action_type == ActionType.END_TURN:
                            return action, make_log(action, "Fallback after incomplete action")
            
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    return action, make_log(action, "Parse failed, defaulting to end_turn")
            fallback = valid_actions[0]
            return fallback, make_log(fallback, "All fallbacks exhausted")
            
        except Exception as e:
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    return action, make_log(action, f"Error: {str(e)[:50]}")
            fallback = valid_actions[0]
            return fallback, make_log(fallback, f"Error fallback: {str(e)[:50]}")
    
    async def decide_combat_commitment(
        self,
        game_state: GameState,
        player: Player,
        target: Holding,
        min_soldiers: int,
        max_soldiers: int
    ) -> int:
        """Decide soldiers to commit using Claude."""
        state_text = self._format_game_state(game_state, player)
        
        defender = None
        if target.owner_id:
            defender = next((p for p in game_state.players if p.id == target.owner_id), None)
        
        defender_info = "NEUTRAL" if not defender else f"{defender.name} (~{defender.soldiers}S)"
        
        prompt = f"""{state_text}

ATTACK DECISION:
Target: {target.name} (Defense: {"FORTIFIED +2" if target.fortified else "Standard"})
Defender: {defender_info}
Your available soldiers: {min_soldiers}-{max_soldiers}

Calculate the optimal commitment considering:
- Victory probability (need to exceed defender's strength)
- Loss mitigation (winner loses 50%, loser loses 100%)
- Post-battle sustainability

Respond with ONLY a number between {min_soldiers} and {max_soldiers}."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                soldiers = int(numbers[0])
                return max(min_soldiers, min(max_soldiers, soldiers))
            
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.65)))
            
        except Exception:
            return min(max_soldiers, max(min_soldiers, int(max_soldiers * 0.65)))
    
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list[Holding]
    ) -> str:
        """Choose a starting town using Claude."""
        towns_text = "\n".join([
            f"{i+1}. {t.name} (County {t.county}): {t.gold_value}G, {t.soldier_value*100}S"
            for i, t in enumerate(available_towns)
        ])
        
        prompt = f"""You are starting a new game of Machiavelli's Kingdom.

Available starting towns:
{towns_text}

Choose based on:
- Resource balance (gold for titles, soldiers for expansion)
- County positioning (2/3 towns needed for Count title)
- Strategic location on the board

Respond with ONLY the number of your chosen town (1-{len(available_towns)})."""
        
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



