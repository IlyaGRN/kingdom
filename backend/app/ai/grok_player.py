"""xAI Grok-based AI player."""
import re
from typing import Optional
from openai import AsyncOpenAI

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType


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
        valid_actions: list[Action]
    ) -> Action:
        """Choose an action using Grok."""
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions)
        
        prompt = f"""{state_text}

{actions_text}

Time to make a strategic decision in this medieval conquest game.
Evaluate each option and pick the one that gives you the best advantage.

What's your move? Reply with just the action number (1-{len(valid_actions)})."""
        
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



