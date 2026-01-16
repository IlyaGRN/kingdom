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


def calculate_defense_bonus(state: GameState, holding_id: str, defender_id: str | None = None) -> int:
    """Calculate defense bonuses for a holding.
    
    Args:
        state: Current game state
        holding_id: ID of the holding being defended
        defender_id: ID of the defending player (for player-specific fortification bonus)
    """
    holding = next((h for h in state.holdings if h.id == holding_id), None)
    if not holding:
        return 0
    
    bonus = 0
    
    # Town base defense - castles have no base defense bonus
    if holding.holding_type == HoldingType.TOWN:
        bonus += 1
    
    # Fortification bonus: based on THIS PLAYER'S fortifications on the holding
    # +1 for first, +2 for second = +3 total for 2 forts
    if defender_id:
        player_forts = holding.fortifications_by_player.get(defender_id, 0)
    else:
        player_forts = 0
    
    if player_forts >= 1:
        bonus += 1
    if player_forts >= 2:
        bonus += 2  # Total +3 for 2 forts
    
    # Town-specific defense modifier (e.g., Velthar +2, Quindara -2)
    bonus += holding.defense_modifier
    
    return bonus


def calculate_attack_bonus(state: GameState, source_holding_id: str | None, attacker_id: str | None = None) -> int:
    """Calculate attack bonuses from the source holding.
    
    Includes:
    - Holding's attack_modifier (e.g., Umbrith +1)
    - Fortification bonus when attacking FROM a fortified holding (player's own forts only)
    
    Args:
        state: Current game state
        source_holding_id: ID of the holding the attack originates from
        attacker_id: ID of the attacking player (for player-specific fortification bonus)
    """
    if not source_holding_id:
        return 0
    
    holding = next((h for h in state.holdings if h.id == source_holding_id), None)
    if not holding:
        return 0
    
    bonus = 0
    
    # Town-specific attack modifier (e.g., Umbrith +1 when attacking)
    bonus += holding.attack_modifier
    
    # Fortification bonus when attacking FROM this holding (player's own forts only)
    # Same formula as defense: +1 for first, +2 for second
    if attacker_id:
        player_forts = holding.fortifications_by_player.get(attacker_id, 0)
    else:
        player_forts = 0
    
    if player_forts >= 1:
        bonus += 1
    if player_forts >= 2:
        bonus += 2  # Total +3 for 2 forts
    
    return bonus


def calculate_title_combat_bonus(state: GameState, player_id: str, holding_id: str, is_defending: bool) -> int:
    """Calculate title-based combat bonuses.
    
    NOTE: Title combat bonuses have been removed per game rules update.
    Counts, Dukes, and Kings no longer get military bonuses in combat.
    This function is kept for API compatibility but always returns 0.
    """
    return 0


def resolve_combat(
    state: GameState,
    attacker_id: str,
    target_holding_id: str,
    attacker_soldiers: int,
    source_holding_id: str | None = None,
    attacker_cards: list[str] | None = None,
    defender_cards: list[str] | None = None,
    defender_soldiers_override: int | None = None,
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
        attacker_cards: Card IDs the attacker is using in this combat
        defender_cards: Card IDs the defender is using in this combat
        defender_soldiers_override: Override for defender's soldier commitment
    
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
    if defender_soldiers_override is not None:
        defender_soldiers = min(defender_soldiers_override, defender.soldiers if defender else 0)
    elif defender:
        defender_soldiers = min(defender.soldiers, attacker_soldiers)
    else:
        defender_soldiers = 0
    
    # Build card effects from selected cards
    attacker_effects: list[CardEffect] = []
    defender_effects: list[CardEffect] = []
    
    combat_card_effects = {CardEffect.EXCALIBUR, CardEffect.POISONED_ARROWS,
                           CardEffect.TALENTED_COMMANDER, CardEffect.DUEL}
    
    if attacker_cards:
        for card_id in attacker_cards:
            card = state.cards.get(card_id)
            if card and card.effect in combat_card_effects:
                attacker_effects.append(card.effect)
    
    if defender_cards:
        for card_id in defender_cards:
            card = state.cards.get(card_id)
            if card and card.effect in combat_card_effects:
                defender_effects.append(card.effect)
    
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
    atk_soldiers_bonus = attacker_soldiers // 100
    atk_attack_bonus = calculate_attack_bonus(state, source_holding_id, attacker_id)
    
    # Add bonus from attacker's fortifications on the TARGET holding
    # (If attacker has forts on the town they're attacking, they get bonus)
    attacker_forts_on_target = holding.fortifications_by_player.get(attacker_id, 0)
    if attacker_forts_on_target >= 1:
        atk_attack_bonus += 1
    if attacker_forts_on_target >= 2:
        atk_attack_bonus += 2  # Total +3 for 2 forts
    
    atk_title_bonus = calculate_title_combat_bonus(state, attacker_id, target_holding_id, is_defending=False)
    attacker_strength = attacker_roll + atk_soldiers_bonus + atk_attack_bonus + atk_title_bonus
    
    # Calculate defender strength
    def_soldiers_bonus = defender_soldiers // 100
    def_defense_bonus = calculate_defense_bonus(state, target_holding_id, defender_id)
    def_title_bonus = calculate_title_combat_bonus(state, defender_id, target_holding_id, is_defending=True) if defender else 0
    defender_strength = defender_roll + def_soldiers_bonus + def_defense_bonus + def_title_bonus
    
    # Determine winner (defender wins ties, except King defending King's Castle)
    attacker_won = attacker_strength > defender_strength
    
    # Special: King wins ties when defending King's Castle
    if defender and defender.is_king and holding.id == "king_castle":
        if attacker_strength == defender_strength:
            attacker_won = False
    
    # Calculate losses - winner keeps soldiers rounded DOWN to nearest 100
    # Example: 300 committed, win -> remaining = 100 (half=150, round down to 100)
    if attacker_won:
        # Check for Talented Commander (no losses on victory)
        if CardEffect.TALENTED_COMMANDER in attacker_effects:
            attacker_losses = 0
        else:
            # Winner keeps half, rounded down to nearest 100
            remaining = (attacker_soldiers // 2 // 100) * 100  # Half, then round down to 100
            attacker_losses = attacker_soldiers - remaining
        defender_losses = defender_soldiers  # Loser loses all
    else:
        attacker_losses = attacker_soldiers  # Loser loses all
        # Check for Talented Commander for defender
        if defender and CardEffect.TALENTED_COMMANDER in defender_effects:
            defender_losses = 0
        else:
            # Winner keeps half, rounded down to nearest 100
            if defender:
                remaining = (defender_soldiers // 2 // 100) * 100
                defender_losses = defender_soldiers - remaining
            else:
                defender_losses = 0
    
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
        # Bonus breakdowns
        attacker_soldiers_bonus=atk_soldiers_bonus,
        attacker_attack_bonus=atk_attack_bonus,
        attacker_title_bonus=atk_title_bonus,
        defender_soldiers_bonus=def_soldiers_bonus,
        defender_defense_bonus=def_defense_bonus,
        defender_title_bonus=def_title_bonus,
        # Result
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
        
        # Handle title transfer for castles
        if holding.holding_type == HoldingType.COUNTY_CASTLE:
            county = result.target_holding_id[0].upper()  # e.g., "x_castle" -> "X"
            # Remove county from defender
            if defender and county in defender.counties:
                defender.counties.remove(county)
                # Downgrade defender's title if needed
                if not defender.counties and not defender.duchies and not defender.is_king:
                    defender.title = TitleType.BARON
            # Add county to attacker
            if county not in attacker.counties:
                attacker.counties.append(county)
            if attacker.title == TitleType.BARON:
                attacker.title = TitleType.COUNT
                
        elif holding.holding_type == HoldingType.DUCHY_CASTLE:
            duchy = result.target_holding_id[:2].upper()  # e.g., "xu_castle" -> "XU"
            # Remove duchy from defender
            if defender and duchy in defender.duchies:
                defender.duchies.remove(duchy)
                # Downgrade defender's title if needed
                if not defender.duchies and not defender.is_king:
                    defender.title = TitleType.COUNT if defender.counties else TitleType.BARON
            # Add duchy to attacker
            if duchy not in attacker.duchies:
                attacker.duchies.append(duchy)
            if attacker.title in [TitleType.BARON, TitleType.COUNT]:
                attacker.title = TitleType.DUKE
                
        elif holding.holding_type == HoldingType.KING_CASTLE:
            # Remove king status from defender
            if defender and defender.is_king:
                defender.is_king = False
                defender.title = TitleType.DUKE if defender.duchies else (
                    TitleType.COUNT if defender.counties else TitleType.BARON
                )
            # Make attacker king
            attacker.is_king = True
            attacker.title = TitleType.KING
            # Note: 6 VP for being king is calculated dynamically in calculate_prestige
    
    # Remove all fortifications from the town after combat
    if holding.holding_type == HoldingType.TOWN and holding.fortification_count > 0:
        # Decrement each player's fortifications_placed count
        for player_id, fort_count in holding.fortifications_by_player.items():
            player = next((p for p in state.players if p.id == player_id), None)
            if player:
                player.fortifications_placed = max(0, player.fortifications_placed - fort_count)
        
        # Clear fortifications from the holding
        holding.fortification_count = 0
        holding.fortifications_by_player = {}
    
    # Log combat
    state.combat_log.append(result)
    
    save_game(state)
    return state
