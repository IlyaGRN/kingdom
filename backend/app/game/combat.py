"""Combat resolution system."""
import random
from typing import Optional
from app.models.schemas import (
    GameState, CombatResult, Action, ActionType, 
    TitleType, HoldingType, CardEffect
)
from app.game.state import save_game


def roll_dice() -> int:
    """Roll 2d6."""
    return random.randint(1, 6) + random.randint(1, 6)


def roll_dice_with_excalibur() -> tuple[int, int]:
    """Roll 2d6 twice (for Excalibur effect) and return both rolls."""
    roll1 = roll_dice()
    roll2 = roll_dice()
    return roll1, roll2


def calculate_defense_bonus(state: GameState, holding_id: str) -> int:
    """Calculate defense bonuses for a holding."""
    holding = next((h for h in state.holdings if h.id == holding_id), None)
    if not holding:
        return 0
    
    bonus = 0
    
    # Town base defense
    if holding.holding_type == HoldingType.TOWN:
        bonus += 1
    elif holding.holding_type == HoldingType.COUNTY_CASTLE:
        bonus += 2
    elif holding.holding_type == HoldingType.DUCHY_CASTLE:
        bonus += 3
    elif holding.holding_type == HoldingType.KING_CASTLE:
        bonus += 4
    
    # Fortification bonus: +1 per fortification, +2 for second fortification
    if holding.fortification_count >= 1:
        bonus += 1
    if holding.fortification_count >= 2:
        bonus += 2  # Total +3 for 2 forts
    if holding.fortification_count >= 3:
        bonus += 2  # Total +5 for 3 forts
    
    # Town-specific defense modifier (e.g., Velthar +2, Quindara -2)
    bonus += holding.defense_modifier
    
    return bonus


def calculate_attack_bonus(state: GameState, source_holding_id: str | None) -> int:
    """Calculate attack bonuses from the source holding."""
    if not source_holding_id:
        return 0
    
    holding = next((h for h in state.holdings if h.id == source_holding_id), None)
    if not holding:
        return 0
    
    # Town-specific attack modifier (e.g., Umbrith +1 when attacking)
    return holding.attack_modifier


def calculate_title_combat_bonus(state: GameState, player_id: str, holding_id: str, is_defending: bool) -> int:
    """Calculate title-based combat bonuses."""
    player = next((p for p in state.players if p.id == player_id), None)
    holding = next((h for h in state.holdings if h.id == holding_id), None)
    
    if not player or not holding:
        return 0
    
    bonus = 0
    
    # Count gets +1 defense in their county (only when defending)
    if is_defending and player.title in [TitleType.COUNT, TitleType.DUKE, TitleType.KING]:
        if holding.county and holding.county in player.counties:
            bonus += 1
    
    # Duke gets combat bonus in their duchy
    if player.title in [TitleType.DUKE, TitleType.KING]:
        if holding.duchy and holding.duchy in player.duchies:
            bonus += 1
    
    return bonus


def resolve_combat(
    state: GameState,
    attacker_id: str,
    target_holding_id: str,
    attacker_soldiers: int,
    source_holding_id: str | None = None,
) -> CombatResult:
    """Resolve a combat between attacker and defender.
    
    Combat Formula:
    Battle Strength = 2d6 + Modifiers + (Committed Soldiers ÷ 100)
    
    Args:
        state: Current game state
        attacker_id: ID of attacking player
        target_holding_id: ID of holding being attacked
        attacker_soldiers: Number of soldiers committed by attacker
        source_holding_id: ID of holding attack originates from (for attack modifiers)
    
    Returns:
        CombatResult with outcome
    """
    attacker = next((p for p in state.players if p.id == attacker_id), None)
    holding = next((h for h in state.holdings if h.id == target_holding_id), None)
    
    if not attacker or not holding:
        raise ValueError("Invalid attacker or target")
    
    if attacker_soldiers < 200:
        raise ValueError("Must commit at least 200 soldiers")
    
    if attacker_soldiers > attacker.soldiers:
        raise ValueError("Not enough soldiers")
    
    # Get defender
    defender_id = holding.owner_id
    defender = next((p for p in state.players if p.id == defender_id), None) if defender_id else None
    
    # Calculate defender's committed soldiers
    defender_soldiers = 0
    if defender:
        defender_soldiers = min(defender.soldiers, attacker_soldiers)
    
    # Check for card effects
    attacker_effects = attacker.active_effects.copy() if attacker else []
    defender_effects = defender.active_effects.copy() if defender else []
    
    # Check for Duel effect (army-less fight)
    is_duel = CardEffect.DUEL in attacker_effects
    if is_duel:
        attacker_soldiers = 0
        defender_soldiers = 0
    
    # Roll dice with potential Excalibur effect
    if CardEffect.EXCALIBUR in attacker_effects:
        roll1, roll2 = roll_dice_with_excalibur()
        attacker_roll = max(roll1, roll2)
    else:
        attacker_roll = roll_dice()
    
    if defender and CardEffect.EXCALIBUR in defender_effects:
        roll1, roll2 = roll_dice_with_excalibur()
        defender_roll = max(roll1, roll2)
    else:
        defender_roll = roll_dice()
    
    # Apply Poisoned Arrows effect (halve opponent's dice)
    if CardEffect.POISONED_ARROWS in attacker_effects:
        defender_roll = defender_roll // 2
    if defender and CardEffect.POISONED_ARROWS in defender_effects:
        attacker_roll = attacker_roll // 2
    
    # Calculate attacker strength
    attacker_strength = (
        attacker_roll +
        (attacker_soldiers // 100) +
        calculate_attack_bonus(state, source_holding_id) +
        calculate_title_combat_bonus(state, attacker_id, target_holding_id, is_defending=False)
    )
    
    # Calculate defender strength
    defender_strength = (
        defender_roll +
        (defender_soldiers // 100) +
        calculate_defense_bonus(state, target_holding_id)
    )
    if defender:
        defender_strength += calculate_title_combat_bonus(state, defender_id, target_holding_id, is_defending=True)
    
    # Determine winner (defender wins ties, except King defending King's Castle)
    attacker_won = attacker_strength > defender_strength
    
    # Special: King wins ties when defending King's Castle
    if defender and defender.is_king and holding.id == "king_castle":
        if attacker_strength == defender_strength:
            attacker_won = False
    
    # Calculate losses
    if attacker_won:
        # Check for Talented Commander (no losses on victory)
        if CardEffect.TALENTED_COMMANDER in attacker_effects:
            attacker_losses = 0
        else:
            attacker_losses = attacker_soldiers // 2  # Winner loses half
        defender_losses = defender_soldiers  # Loser loses all
    else:
        attacker_losses = attacker_soldiers  # Loser loses all
        # Check for Talented Commander for defender
        if defender and CardEffect.TALENTED_COMMANDER in defender_effects:
            defender_losses = 0
        else:
            defender_losses = defender_soldiers // 2 if defender else 0
    
    result = CombatResult(
        attacker_id=attacker_id,
        defender_id=defender_id,
        target_holding_id=target_holding_id,
        attacker_strength=attacker_strength,
        defender_strength=defender_strength,
        attacker_roll=attacker_roll,
        defender_roll=defender_roll,
        attacker_soldiers_committed=attacker_soldiers,
        defender_soldiers_committed=defender_soldiers,
        attacker_won=attacker_won,
        attacker_losses=attacker_losses,
        defender_losses=defender_losses,
        attacker_effects=attacker_effects,
        defender_effects=defender_effects,
    )
    
    return result


def apply_combat_result(state: GameState, result: CombatResult) -> GameState:
    """Apply combat result to game state."""
    attacker = next((p for p in state.players if p.id == result.attacker_id), None)
    defender = next((p for p in state.players if p.id == result.defender_id), None) if result.defender_id else None
    holding = next((h for h in state.holdings if h.id == result.target_holding_id), None)
    
    if not attacker or not holding:
        return state
    
    # Apply losses
    attacker.soldiers = max(0, attacker.soldiers - result.attacker_losses)
    if defender:
        defender.soldiers = max(0, defender.soldiers - result.defender_losses)
    
    # Clear used combat effects from both players
    for effect in [CardEffect.EXCALIBUR, CardEffect.POISONED_ARROWS, 
                   CardEffect.TALENTED_COMMANDER, CardEffect.DUEL]:
        if effect in attacker.active_effects:
            attacker.active_effects.remove(effect)
        if defender and effect in defender.active_effects:
            defender.active_effects.remove(effect)
    
    # Transfer holding if attacker won
    if result.attacker_won:
        # Remove from defender's holdings
        if defender and result.target_holding_id in defender.holdings:
            defender.holdings.remove(result.target_holding_id)
        
        # Add to attacker's holdings
        holding.owner_id = result.attacker_id
        if result.target_holding_id not in attacker.holdings:
            attacker.holdings.append(result.target_holding_id)
    
    # Log combat
    state.combat_log.append(result)
    
    save_game(state)
    return state
