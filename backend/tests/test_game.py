"""Tests for core game logic."""
import pytest
from app.game.state import create_game, get_game, assign_starting_town, start_game
from app.game.board import create_board, get_adjacent_holdings, get_towns_in_county
from app.game.cards import create_deck
from app.game.engine import GameEngine
from app.models.schemas import ActionType, GamePhase, HoldingType


class TestBoardTopology:
    """Test board structure and adjacency."""
    
    def test_create_board_has_correct_holdings(self):
        """Board should have all required holdings."""
        board = create_board()
        
        # 12 towns + 4 county castles + 2 duchy castles + 1 king castle = 19
        assert len(board) == 19
        
        towns = [h for h in board if h.holding_type == HoldingType.TOWN]
        assert len(towns) == 12
        
        county_castles = [h for h in board if h.holding_type == HoldingType.COUNTY_CASTLE]
        assert len(county_castles) == 4
        
        duchy_castles = [h for h in board if h.holding_type == HoldingType.DUCHY_CASTLE]
        assert len(duchy_castles) == 2
        
        king_castle = [h for h in board if h.holding_type == HoldingType.KING_CASTLE]
        assert len(king_castle) == 1
    
    def test_county_towns(self):
        """Each county should have 3 towns."""
        for county in ["X", "U", "V", "Q"]:
            towns = get_towns_in_county(county)
            assert len(towns) == 3
    
    def test_adjacency_is_symmetric(self):
        """If A is adjacent to B, then B should be adjacent to A."""
        for holding_id in ["x_town_1", "u_castle", "king_castle"]:
            adjacent = get_adjacent_holdings(holding_id)
            for adj_id in adjacent:
                assert holding_id in get_adjacent_holdings(adj_id)
    
    def test_king_castle_connected_to_duchy_castles(self):
        """King's castle should connect to both duchy castles."""
        adjacent = get_adjacent_holdings("king_castle")
        assert "xu_castle" in adjacent
        assert "qv_castle" in adjacent


class TestCardDeck:
    """Test card deck creation."""
    
    def test_deck_has_35_cards(self):
        """Deck should have exactly 35 cards."""
        deck = create_deck()
        assert len(deck) == 35
    
    def test_deck_has_town_claims(self):
        """Deck should have 8 town claims."""
        deck = create_deck()
        town_claims = [c for c in deck if c.card_type.value == "town_claim"]
        assert len(town_claims) == 8
    
    def test_deck_has_treasure_hoards(self):
        """Deck should have 3 treasure hoard cards."""
        deck = create_deck()
        treasures = [c for c in deck if c.name == "Treasure Hoard"]
        assert len(treasures) == 3


class TestGameCreation:
    """Test game creation and setup."""
    
    def test_create_game_with_4_players(self):
        """Should create a game with 4 players."""
        configs = [
            {"name": "Player 1", "player_type": "human", "color": "#FF0000"},
            {"name": "Player 2", "player_type": "ai_openai", "color": "#00FF00"},
            {"name": "Player 3", "player_type": "ai_anthropic", "color": "#0000FF"},
            {"name": "Player 4", "player_type": "ai_gemini", "color": "#FFFF00"},
        ]
        
        state = create_game(configs)
        
        assert state.player_count == 4
        assert state.max_rounds == 10
        assert len(state.players) == 4
        assert state.phase == GamePhase.SETUP
    
    def test_create_game_with_6_players(self):
        """6 player game should have 12 rounds."""
        configs = [{"name": f"P{i}", "player_type": "human", "color": f"#{i}00000"} 
                   for i in range(6)]
        
        state = create_game(configs)
        
        assert state.player_count == 6
        assert state.max_rounds == 12
    
    def test_invalid_player_count_raises(self):
        """Should reject games with fewer than 4 or more than 6 players."""
        with pytest.raises(ValueError):
            create_game([{"name": "P1", "player_type": "human", "color": "#000"}])
        
        with pytest.raises(ValueError):
            configs = [{"name": f"P{i}", "player_type": "human", "color": "#000"} 
                       for i in range(7)]
            create_game(configs)
    
    def test_players_get_starting_hands(self):
        """Each player should receive 3 starting cards."""
        configs = [{"name": f"P{i}", "player_type": "human", "color": f"#{i}00000"} 
                   for i in range(4)]
        
        state = create_game(configs)
        
        for player in state.players:
            assert len(player.hand) == 3


class TestGameEngine:
    """Test game engine actions."""
    
    @pytest.fixture
    def setup_game(self):
        """Create a started game for testing."""
        configs = [
            {"name": "Human", "player_type": "human", "color": "#FF0000"},
            {"name": "AI 1", "player_type": "ai_openai", "color": "#00FF00"},
            {"name": "AI 2", "player_type": "ai_anthropic", "color": "#0000FF"},
            {"name": "AI 3", "player_type": "ai_gemini", "color": "#FFFF00"},
        ]
        
        state = create_game(configs)
        
        # Assign starting towns
        towns = ["x_town_1", "u_town_1", "v_town_1", "q_town_1"]
        for i, player in enumerate(state.players):
            assign_starting_town(state, player.id, towns[i])
        
        # Start the game
        state = start_game(state)
        
        return state
    
    def test_game_starts_in_income_phase(self, setup_game):
        """Game should start in income phase after setup."""
        assert setup_game.phase == GamePhase.INCOME
    
    def test_get_valid_actions(self, setup_game):
        """Engine should return valid actions for current player."""
        # First process income to move to player turn phase
        from app.game.state import apply_income
        state = apply_income(setup_game)
        
        engine = GameEngine(state.id)
        current_player = state.players[0]
        
        actions = engine.get_valid_actions(current_player.id)
        
        assert len(actions) > 0
        
        # Should have draw_card action
        action_types = [a.action_type for a in actions]
        assert ActionType.DRAW_CARD in action_types
        assert ActionType.END_TURN in action_types
    
    def test_draw_card_action(self, setup_game):
        """Player should be able to draw a card."""
        from app.game.state import apply_income
        from app.models.schemas import Action
        
        state = apply_income(setup_game)
        engine = GameEngine(state.id)
        current_player = state.players[0]
        
        initial_hand_size = len(current_player.hand)
        
        action = Action(
            action_type=ActionType.DRAW_CARD,
            player_id=current_player.id,
        )
        
        success, message, _ = engine.perform_action(action)
        
        assert success
        assert len(engine.state.players[0].hand) == initial_hand_size + 1
        assert engine.state.card_drawn_this_turn


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



