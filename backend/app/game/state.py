"""Game state management."""
import uuid
import random
from typing import Optional
from app.models.schemas import (
    GameState, Player, PlayerType, TitleType, GamePhase,
    Holding, HoldingType, Card, Army, CardType, CardEffect
)
from app.game.board import create_board, get_towns_in_county
from app.game.cards import create_deck, shuffle_deck, is_instant_card


# In-memory game storage
_games: dict[str, GameState] = {}


def auto_draw_card(state: GameState, player: Player) -> Optional[str]:
    """Auto-draw a card for a player at the beginning of their turn.
    
    Returns the name of the drawn card, or None if deck is empty.
    Handles instant cards (applied immediately) and regular cards (added to hand).
    """
    try:
        if not state.deck:
            # Reshuffle discard pile if needed
            if state.discard_pile:
                state.deck = state.discard_pile.copy()
                random.shuffle(state.deck)
                state.discard_pile = []
            else:
                return None  # No cards available
        
        card_id = state.deck.pop(0)
        card = state.cards.get(card_id)
        
        if not card:
            return None
        
        # Check if instant card (personal/global events)
        if is_instant_card(card):
            # Apply instant effect
            _apply_instant_card_effect(state, player, card)
            state.discard_pile.append(card_id)
            return f"{card.name} (instant effect applied)"
        
        # Non-instant cards go to hand
        player.hand.append(card_id)
        state.card_drawn_this_turn = True
        
        return card.name
    except Exception as e:
        # #region agent log
        import json as _json
        import traceback
        with open("/home/ilya/dev/kingdom/.cursor/debug.log", "a") as _f:
            _f.write(_json.dumps({"location":"state.py:auto_draw_card:error","message":"Exception in auto_draw_card","data":{"error":str(e),"traceback":traceback.format_exc(),"player_id":player.id},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H1","runId":"500-debug"})+"\n")
        # #endregion
        raise


def _apply_instant_card_effect(state: GameState, player: Player, card: Card) -> None:
    """Apply effects of instant cards (personal/global events)."""
    if card.card_type == CardType.PERSONAL_EVENT:
        # Gold cards
        if card.effect == CardEffect.GOLD_5:
            player.gold += 5
        elif card.effect == CardEffect.GOLD_10:
            player.gold += 10
        elif card.effect == CardEffect.GOLD_15:
            player.gold += 15
        elif card.effect == CardEffect.GOLD_25:
            player.gold += 25
        # Soldier cards
        elif card.effect == CardEffect.SOLDIERS_100:
            player.soldiers = min(player.soldiers + 100, player.army_cap)
        elif card.effect == CardEffect.SOLDIERS_200:
            player.soldiers = min(player.soldiers + 200, player.army_cap)
        elif card.effect == CardEffect.SOLDIERS_300:
            player.soldiers = min(player.soldiers + 300, player.army_cap)
        # Raiders - lose current turn income (handled at draw time, just mark it)
        elif card.effect == CardEffect.RAIDERS:
            # Raiders effect: lose income this turn - simplified, just reduce gold
            income = calculate_income(state)
            player_income = income.get(player.id, {"gold": 0})
            player.gold = max(0, player.gold - player_income["gold"])
    
    elif card.card_type == CardType.GLOBAL_EVENT:
        if card.effect == CardEffect.CRUSADE:
            # All players lose half gold and soldiers
            for p in state.players:
                p.gold = p.gold // 2
                p.soldiers = p.soldiers // 2


def create_game(player_configs: list[dict]) -> GameState:
    """Create a new game with the given player configurations.
    
    Args:
        player_configs: List of dicts with keys: name, player_type, color
    
    Returns:
        New GameState
    """
    player_count = len(player_configs)
    if player_count < 4 or player_count > 6:
        raise ValueError("Game requires 4-6 players")
    
    game_id = str(uuid.uuid4())
    
    # Create board
    holdings = create_board()
    
    # Create deck
    cards = create_deck()
    cards_dict = {c.id: c for c in cards}
    deck = shuffle_deck(cards)
    
    # Create players
    players = []
    colors = ["#8B0000", "#00008B", "#006400", "#4B0082", "#8B4513", "#2F4F4F"]
    
    for i, config in enumerate(player_configs):
        player_type = PlayerType(config.get("player_type", "human"))
        player = Player(
            id=str(uuid.uuid4()),
            name=config.get("name", f"Player {i + 1}"),
            player_type=player_type,
            color=config.get("color", colors[i]),
        )
        players.append(player)
    
    # Create initial game state (no round limit - game ends at 18 VP)
    state = GameState(
        id=game_id,
        player_count=player_count,
        victory_threshold=18,
        current_round=1,
        current_player_idx=0,
        phase=GamePhase.SETUP,
        players=players,
        holdings=holdings,
        deck=deck,
        cards=cards_dict,
    )
    
    # Store game
    _games[game_id] = state
    
    return state


def get_game(game_id: str) -> Optional[GameState]:
    """Get a game by ID."""
    state = _games.get(game_id)
    if state:
        # Update prestige values on players so frontend sees current totals
        update_player_prestige(state)
    return state


def update_player_prestige(state: GameState) -> None:
    """Update the prestige field on each player with their calculated total.
    
    This ensures the frontend sees the correct prestige values.
    """
    for player in state.players:
        vp = 0  # Start from 0, calculate everything
        
        # 1 VP per town
        vp += len([h for h in state.holdings 
                   if h.owner_id == player.id and h.holding_type == HoldingType.TOWN])
        
        # 2 VP per county
        vp += 2 * len(player.counties)
        
        # 4 VP per duchy
        vp += 4 * len(player.duchies)
        
        # 6 VP for being king
        if player.is_king:
            vp += 6
        
        player.prestige = vp


def save_game(state: GameState) -> None:
    """Save/update a game state."""
    _games[state.id] = state


def delete_game(game_id: str) -> bool:
    """Delete a game."""
    if game_id in _games:
        del _games[game_id]
        return True
    return False


def list_games() -> list[str]:
    """List all game IDs."""
    return list(_games.keys())


def assign_starting_town(state: GameState, player_id: str, town_id: str) -> GameState:
    """Assign a starting town to a player during setup.
    
    Args:
        state: Current game state
        player_id: ID of the player
        town_id: ID of the town to claim
    
    Returns:
        Updated game state
    """
    # Find player
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    # Find holding
    holding = next((h for h in state.holdings if h.id == town_id), None)
    if not holding:
        raise ValueError(f"Holding {town_id} not found")
    
    # Check it's a town and unowned
    if holding.holding_type != HoldingType.TOWN:
        raise ValueError("Can only start with a town")
    if holding.owner_id:
        raise ValueError("Town already claimed")
    
    # Assign town to player
    holding.owner_id = player_id
    player.holdings.append(town_id)
    
    # Give starting resources from the town (soldier_value is actual soldiers now)
    player.gold = holding.gold_value
    player.soldiers = holding.soldier_value
    
    # Update holdings list in state
    for i, h in enumerate(state.holdings):
        if h.id == town_id:
            state.holdings[i] = holding
            break
    
    # Update players list in state
    for i, p in enumerate(state.players):
        if p.id == player_id:
            state.players[i] = player
            break
    
    save_game(state)
    return state


def auto_assign_starting_towns(state: GameState) -> GameState:
    """Auto-assign starting towns to all players.
    
    Distributes towns evenly across counties so players start spread out.
    """
    import random
    
    if state.phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase")
    
    # Get all unclaimed towns
    unclaimed_towns = [
        h for h in state.holdings 
        if h.holding_type == HoldingType.TOWN and h.owner_id is None
    ]
    
    # Shuffle for randomness
    random.shuffle(unclaimed_towns)
    
    # Assign one town per player
    for player in state.players:
        if player.holdings:
            continue  # Already has a town
        
        if not unclaimed_towns:
            raise ValueError("Not enough towns for all players")
        
        town = unclaimed_towns.pop(0)
        town.owner_id = player.id
        player.holdings.append(town.id)
        
        # Players start with nothing - they gain resources from income phase
        player.gold = 0
        player.soldiers = 0
        player.hand = []  # No starting cards
        
        # Update holding in state
        for i, h in enumerate(state.holdings):
            if h.id == town.id:
                state.holdings[i] = town
                break
    
    save_game(state)
    return state


def start_game(state: GameState) -> GameState:
    """Start the game after setup is complete."""
    if state.phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase")
    
    # Verify all players have a starting town
    for player in state.players:
        if not player.holdings:
            raise ValueError(f"Player {player.name} has no starting town")
    
    # Move to income phase
    state.phase = GamePhase.INCOME
    save_game(state)
    return state


def calculate_income(state: GameState) -> dict[str, dict]:
    """Calculate income for all players.
    
    Returns:
        Dict mapping player_id to {gold: int, soldiers: int}
    """
    income = {}
    
    for player in state.players:
        gold = 0
        soldiers = 0
        
        # Income from holdings
        for holding_id in player.holdings:
            holding = next((h for h in state.holdings if h.id == holding_id), None)
            if holding:
                gold += holding.gold_value
                soldiers += holding.soldier_value  # Now actual soldiers (100, 200, etc.)
                
                # Fortification bonus: +2 gold per fortification, +5 for second
                if holding.fortification_count >= 1:
                    gold += 2
                if holding.fortification_count >= 2:
                    gold += 5  # Total +7 for 2 fortifications
        
        # Title stipends
        if player.title == TitleType.COUNT:
            gold += 2 * len(player.counties)
        elif player.title == TitleType.DUKE:
            gold += 4 * len(player.duchies)
        elif player.is_king:
            gold += 8
        
        income[player.id] = {"gold": gold, "soldiers": soldiers}
    
    return income


def apply_income(state: GameState) -> GameState:
    """Apply income to all players and move to player turn phase."""
    if state.phase != GamePhase.INCOME:
        raise ValueError("Not in income phase")
    
    income = calculate_income(state)
    
    for player in state.players:
        player_income = income.get(player.id, {"gold": 0, "soldiers": 0})
        player.gold += player_income["gold"]
        player.soldiers += player_income["soldiers"]
        # Cap soldiers at army capacity (excess lost)
        player.soldiers = min(player.soldiers, player.army_cap)
    
    # Move to player turn phase
    state.phase = GamePhase.PLAYER_TURN
    state.current_player_idx = 0
    state.card_drawn_this_turn = True  # Will be set by auto-draw
    state.war_fought_this_turn = False
    
    # Clear global turn effects
    state.forbid_mercenaries_active = False
    state.enforce_peace_active = False
    
    # Auto-draw card for first player at start of round
    first_player = state.players[0]
    auto_draw_card(state, first_player)
    
    save_game(state)
    return state


def next_player_turn(state: GameState) -> GameState:
    """Advance to the next player's turn."""
    state.current_player_idx += 1
    
    # Check if all players have taken their turn
    if state.current_player_idx >= len(state.players):
        # Move to upkeep, then next round
        state.phase = GamePhase.UPKEEP
        state = process_upkeep(state)
    else:
        # Reset for next player (unlimited actions - no counter needed)
        state.card_drawn_this_turn = True  # Will be set by auto-draw
        state.war_fought_this_turn = False
        
        # Auto-draw card for the new current player
        current_player = state.players[state.current_player_idx]
        auto_draw_card(state, current_player)
    
    save_game(state)
    return state


def process_upkeep(state: GameState) -> GameState:
    """Process end-of-round upkeep."""
    # Cap soldiers at army capacity (no hoarding above cap)
    for player in state.players:
        player.soldiers = min(player.soldiers, player.army_cap)
    
    # Award prestige to current king
    for player in state.players:
        if player.is_king:
            player.prestige += 2
    
    # Check for victory (18 VP threshold)
    prestige = calculate_prestige(state)
    for player in state.players:
        if prestige[player.id] >= state.victory_threshold:
            state.phase = GamePhase.GAME_OVER
            save_game(state)
            return state
    
    # Advance round (no round limit - game continues until victory)
    state.current_round += 1
    
    # Start new round with income phase
    state.phase = GamePhase.INCOME
    state.current_player_idx = 0
    
    save_game(state)
    return state


def check_victory(state: GameState) -> Optional[Player]:
    """Check if any player has won (reached victory threshold).
    
    Returns the winning player or None.
    """
    prestige = calculate_prestige(state)
    for player in state.players:
        if prestige[player.id] >= state.victory_threshold:
            return player
    return None


def get_player_holdings(state: GameState, player_id: str) -> list[Holding]:
    """Get all holdings owned by a player."""
    return [h for h in state.holdings if h.owner_id == player_id]


def count_player_towns(state: GameState, player_id: str) -> int:
    """Count how many towns a player owns."""
    return len([
        h for h in state.holdings 
        if h.owner_id == player_id and h.holding_type == HoldingType.TOWN
    ])


def count_towns_in_county(state: GameState, player_id: str, county: str) -> int:
    """Count how many towns a player owns in a county."""
    county_towns = get_towns_in_county(county)
    player_towns = [h.id for h in state.holdings if h.owner_id == player_id and h.id in county_towns]
    return len(player_towns)


def can_claim_count(state: GameState, player_id: str, county: str) -> bool:
    """Check if a player can claim Count of a county."""
    # Need 2/3 towns in the county
    return count_towns_in_county(state, player_id, county) >= 2


def can_claim_duke(state: GameState, player_id: str, duchy: str) -> bool:
    """Check if a player can claim Duke of a duchy."""
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        return False
    
    # Need Count in one county + 1 town in the other
    if duchy == "XU":
        counties = ["X", "U"]
    elif duchy == "QV":
        counties = ["Q", "V"]
    else:
        return False
    
    # Check if player is Count in either county
    is_count_0 = counties[0] in player.counties
    is_count_1 = counties[1] in player.counties
    
    if is_count_0:
        # Need at least 1 town in the other county
        return count_towns_in_county(state, player_id, counties[1]) >= 1
    elif is_count_1:
        return count_towns_in_county(state, player_id, counties[0]) >= 1
    
    return False


def has_town_in_duchy(state: GameState, player_id: str, duchy: str) -> bool:
    """Check if player owns any town in the specified duchy."""
    # Counties in each duchy
    duchy_counties = {
        "XU": ["X", "U"],
        "QV": ["Q", "V"]
    }
    counties = duchy_counties.get(duchy, [])
    
    for holding in state.holdings:
        if holding.owner_id == player_id and holding.holding_type == HoldingType.TOWN:
            if holding.county in counties:
                return True
    return False


def can_claim_king(state: GameState, player_id: str) -> bool:
    """Check if a player can claim King.
    
    Requirement: Duke in one duchy + own a town in the other duchy.
    """
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        return False
    
    # Need at least one duchy
    if len(player.duchies) == 0:
        return False
    
    # If player has both duchies, they can claim king
    if len(player.duchies) >= 2:
        return True
    
    # Check for a TOWN in the other duchy (not a Count title)
    if "XU" in player.duchies:
        # Need a town in QV duchy
        return has_town_in_duchy(state, player_id, "QV")
    elif "QV" in player.duchies:
        # Need a town in XU duchy
        return has_town_in_duchy(state, player_id, "XU")
    
    return False
    
    return False


def calculate_prestige(state: GameState) -> dict[str, int]:
    """Calculate current prestige for all players.
    
    Prestige is calculated from scratch based on current holdings/titles:
    - 1 VP per town
    - 2 VP per county
    - 4 VP per duchy
    - 6 VP for being king
    """
    prestige = {}
    
    for player in state.players:
        vp = 0  # Calculate from scratch, not from player.prestige
        
        # 1 VP per town
        vp += len([h for h in state.holdings 
                   if h.owner_id == player.id and h.holding_type == HoldingType.TOWN])
        
        # 2 VP per county
        vp += 2 * len(player.counties)
        
        # 4 VP per duchy
        vp += 4 * len(player.duchies)
        
        # 6 VP for being king
        if player.is_king:
            vp += 6
        
        prestige[player.id] = vp
    
    return prestige


def get_winner(state: GameState) -> Optional[Player]:
    """Determine the winner if game is over."""
    if state.phase != GamePhase.GAME_OVER:
        return None
    
    prestige = calculate_prestige(state)
    
    # Sort players by prestige, then tier, then gold, then soldiers
    def sort_key(p: Player):
        tier_order = {TitleType.BARON: 0, TitleType.COUNT: 1, 
                      TitleType.DUKE: 2, TitleType.KING: 3}
        return (
            -prestige[p.id],  # Higher is better
            -tier_order[p.title],  # Higher tier wins ties
            -p.gold,  # More gold wins
            -p.soldiers  # More soldiers wins
        )
    
    sorted_players = sorted(state.players, key=sort_key)
    return sorted_players[0] if sorted_players else None
