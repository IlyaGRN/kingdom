"""Google Gemini-based AI player."""
import re
from typing import Optional
import google.generativeai as genai

from app.ai.base import AIPlayer
from app.models.schemas import GameState, Player, Action, Holding, ActionType


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
                max_output_tokens=100,
            ),
        )
        return response.text.strip()
    
    async def decide_action(
        self,
        game_state: GameState,
        player: Player,
        valid_actions: list[Action]
    ) -> Action:
        """Choose an action using Gemini."""
        if not valid_actions:
            raise ValueError("No valid actions available")
        
        state_text = self._format_game_state(game_state, player)
        actions_text = self._format_valid_actions(valid_actions)
        
        prompt = f"""{state_text}

{actions_text}

As a strategic AI, analyze this medieval kingdom game state.
Select the action that best:
- Advances your position toward victory
- Manages risk appropriately
- Sets up future opportunities

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



