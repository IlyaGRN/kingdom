"""Abstract base class for AI players."""
from abc import ABC, abstractmethod
from typing import Optional
from app.models.schemas import GameState, Player, Action, Holding


class AIPlayer(ABC):
    """Abstract base class for AI players.
    
    Each AI provider (OpenAI, Anthropic, Gemini, Grok) implements this interface
    to provide decision-making capabilities for the game.
    """
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """Initialize the AI player.
        
        Args:
            api_key: API key for the provider
            model: Optional model name override
        """
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def decide_action(
        self, 
        game_state: GameState, 
        player: Player,
        valid_actions: list[Action]
    ) -> Action:
        """Given the current game state and valid actions, choose one.
        
        Args:
            game_state: Current state of the game
            player: The player this AI is controlling
            valid_actions: List of actions the player can take
            
        Returns:
            The chosen action
        """
        pass
    
    @abstractmethod
    async def decide_combat_commitment(
        self, 
        game_state: GameState, 
        player: Player,
        target: Holding,
        min_soldiers: int,
        max_soldiers: int
    ) -> int:
        """Decide how many soldiers to commit to an attack.
        
        Args:
            game_state: Current state of the game
            player: The player making the attack
            target: The holding being attacked
            min_soldiers: Minimum soldiers required (200)
            max_soldiers: Maximum soldiers available
            
        Returns:
            Number of soldiers to commit
        """
        pass
    
    @abstractmethod
    async def decide_starting_town(
        self,
        game_state: GameState,
        player: Player,
        available_towns: list[Holding]
    ) -> str:
        """Choose a starting town during setup.
        
        Args:
            game_state: Current state of the game
            player: The player choosing
            available_towns: List of unclaimed towns
            
        Returns:
            ID of the chosen town
        """
        pass
    
    def _format_game_state(self, game_state: GameState, player: Player) -> str:
        """Format game state as a string for the AI prompt.
        
        Args:
            game_state: Current game state
            player: The player's perspective
            
        Returns:
            Formatted string describing the game state
        """
        lines = [
            f"=== Machiavelli's Kingdom - Round {game_state.current_round} (Victory: {game_state.victory_threshold} VP) ===",
            "",
            f"You are: {player.name} ({player.title.value})",
            f"Your Resources: {player.gold} Gold, {player.soldiers} Soldiers",
            f"Your Prestige: {player.prestige} VP",
            f"Army Cap: {player.army_cap}",
            "",
            "=== Your Holdings ===",
        ]
        
        for holding_id in player.holdings:
            holding = next((h for h in game_state.holdings if h.id == holding_id), None)
            if holding:
                fort = f" [FORT x{holding.fortification_count}]" if holding.fortification_count > 0 else ""
                lines.append(f"  - {holding.name}: {holding.gold_value}G, {holding.soldier_value}S{fort}")
        
        if player.counties:
            lines.append(f"\nCounties held: {', '.join(player.counties)}")
        if player.duchies:
            lines.append(f"Duchies held: {', '.join(player.duchies)}")
        if player.is_king:
            lines.append("YOU ARE THE KING!")
        
        lines.append("\n=== Other Players ===")
        for p in game_state.players:
            if p.id != player.id:
                title = "KING" if p.is_king else p.title.value.upper()
                lines.append(f"  {p.name} ({title}): {len(p.holdings)} holdings, ~{p.soldiers}S, {p.prestige}VP")
        
        lines.append("\n=== Board State ===")
        for holding in game_state.holdings:
            owner = "NEUTRAL"
            if holding.owner_id:
                owner_player = next((p for p in game_state.players if p.id == holding.owner_id), None)
                owner = owner_player.name if owner_player else "Unknown"
            fort = f" [FORT x{holding.fortification_count}]" if holding.fortification_count > 0 else ""
            lines.append(f"  {holding.name}: Owner={owner}{fort}")
        
        lines.append(f"\n=== Your Hand ({len(player.hand)} cards) ===")
        for card_id in player.hand:
            card = game_state.cards.get(card_id)
            if card:
                lines.append(f"  - {card.name}: {card.description}")
        
        return "\n".join(lines)
    
    def _format_valid_actions(self, actions: list[Action]) -> str:
        """Format valid actions as a string for the AI prompt."""
        lines = ["=== Valid Actions ==="]
        
        for i, action in enumerate(actions):
            action_desc = f"{i+1}. {action.action_type.value}"
            if action.target_holding_id:
                action_desc += f" -> {action.target_holding_id}"
            if action.source_holding_id:
                action_desc += f" (from {action.source_holding_id})"
            if action.target_player_id:
                action_desc += f" with player {action.target_player_id}"
            if action.card_id:
                action_desc += f" card {action.card_id}"
            lines.append(action_desc)
        
        return "\n".join(lines)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI."""
        return """You are an AI playing Machiavelli's Kingdom, a medieval strategy board game.

OBJECTIVE: First to reach 18 Prestige Points (VP) wins!

SCORING:
- Town = 1 VP
- County = +2 VP
- Duchy = +4 VP  
- King = +6 VP
- Each round survived as King = +2 VP bonus

TITLES (require prerequisites and gold):
- Count: Own 2/3 towns in a county. Cost: 25 Gold. Bonus: +2 Gold/round, +1 defense in county.
- Duke: Be Count in 2 counties of same duchy. Cost: 50 Gold. Bonus: +4 Gold/round.
- King: Be Duke in one duchy + own a town in other duchy. Cost: 75 Gold. Bonus: +8 Gold/round.

CLAIMS:
- You need a valid claim to attack any territory
- Play claim cards to establish claims on towns
- Fabricate claims costs 35 Gold
- Capture unowned towns with a claim for 10 Gold

COMBAT:
- Commit at least 200 soldiers
- Strength = 2d6 + (soldiers/100) + modifiers
- Winner loses half soldiers, loser loses all
- Defender wins ties

STRATEGY TIPS:
- Draw cards automatically each turn - play claim cards wisely
- Build fortifications (+2 Gold income, +defense) on key holdings
- Prioritize claiming titles for VP and income bonuses
- Managing army cap is important (excess soldiers lost)

Always respond with just the NUMBER of your chosen action. Nothing else."""



