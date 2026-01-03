"""OpenAI GPT-based AI player."""
import json
import re
from typing import Optional
from openai import AsyncOpenAI

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType


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
        valid_actions: list[Action]
    ) -> Action:
        """Choose an action using GPT."""
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        # Format the game state and actions for the AI
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions)
        
        prompt = f"""{state_text}

{actions_text}

Based on the current game state, choose the best action to maximize your chances of winning.
Consider:
- Your current position and resources
- Expansion opportunities
- Defensive needs
- Title claim prerequisites
- Other players' positions

Respond with ONLY the number of your chosen action (1-{len(valid_actions)})."""
        
        try:
            response = await self._get_completion(self._get_system_prompt(), prompt)
            
            # Parse the response to get action number
            # Extract first number from response
            numbers = re.findall(r'\d+', response)
            if numbers:
                action_idx = int(numbers[0]) - 1
                if 0 <= action_idx < len(valid_actions):
                    return valid_actions[action_idx]
            
            # Fallback: return first valid action (often draw card or end turn)
            return valid_actions[0]
            
        except Exception as e:
            # On any error, return a safe default action
            # Prefer end_turn if available, otherwise first action
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

