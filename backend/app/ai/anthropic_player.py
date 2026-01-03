"""Anthropic Claude-based AI player."""
import re
from typing import Optional
from anthropic import AsyncAnthropic

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType


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
    ) -> Action:
        """Choose an action using Claude."""
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions)
        
        prompt = f"""{state_text}

{actions_text}

Analyze the game state carefully and choose the optimal action.
Think about:
- Immediate tactical advantages
- Long-term strategic positioning
- Resource management
- Opponent threats

Respond with ONLY the number of your chosen action (1-{len(valid_actions)})."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            numbers = re.findall(r'\d+', response)
            if numbers:
                action_idx = int(numbers[0]) - 1
                if 0 <= action_idx < len(valid_actions):
                    return valid_actions[action_idx]
            
            return valid_actions[0]
            
        except Exception:
            for action in valid_actions:
                if action.action_type == ActionType.END_TURN:
                    return action
            return valid_actions[0]
    
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



