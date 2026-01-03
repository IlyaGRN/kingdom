"""Core game engine - orchestrates game flow and action processing."""
from typing import Optional
from app.models.schemas import (
    GameState, Action, ActionType, GamePhase, TitleType,
    CombatResult, EdictType, HoldingType, CardType, CardEffect
)
from app.game.state import (
    get_game, save_game, next_player_turn, apply_income,
    can_claim_count, can_claim_duke, can_claim_king,
    get_player_holdings, count_player_towns, calculate_prestige,
    check_victory
)
from app.game.combat import resolve_combat, apply_combat_result
from app.game.board import (
    get_adjacent_holdings, get_county_castle, get_duchy_castle,
    get_towns_in_county, get_all_towns
)
from app.game.cards import is_instant_card, is_bonus_card, is_claim_card, get_card_county


class GameEngine:
    """Main game engine for processing actions and managing game flow."""
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self._state: Optional[GameState] = None
    
    @property
    def state(self) -> GameState:
        """Get current game state."""
        if self._state is None:
            self._state = get_game(self.game_id)
        if self._state is None:
            raise ValueError(f"Game {self.game_id} not found")
        return self._state
    
    def refresh_state(self) -> GameState:
        """Reload state from storage."""
        self._state = get_game(self.game_id)
        return self.state
    
    def get_valid_actions(self, player_id: str) -> list[Action]:
        """Get all valid actions for a player."""
        state = self.state
        player = next((p for p in state.players if p.id == player_id), None)
        
        if not player:
            return []
        
        # Check if it's this player's turn
        if state.current_player_idx >= len(state.players):
            return []
        if state.players[state.current_player_idx].id != player_id:
            return []
        
        if state.phase != GamePhase.PLAYER_TURN:
            return []
        
        actions = []
        player_holdings = [h for h in state.holdings if h.owner_id == player_id]
        player_town_count = count_player_towns(state, player_id)
        
        # Draw card (once per turn, NOT available if player has > 4 towns)
        if not state.card_drawn_this_turn and state.deck and player_town_count <= 4:
            actions.append(Action(
                action_type=ActionType.DRAW_CARD,
                player_id=player_id,
            ))
        
        # All these actions are available (unlimited actions per turn)
        
        # Move - can move armies between adjacent holdings
        for holding in player_holdings:
            adjacent = get_adjacent_holdings(holding.id)
            for adj_id in adjacent:
                adj_holding = next((h for h in state.holdings if h.id == adj_id), None)
                # Can move to own holdings
                if adj_holding and adj_holding.owner_id == player_id:
                    actions.append(Action(
                        action_type=ActionType.MOVE,
                        player_id=player_id,
                        source_holding_id=holding.id,
                        target_holding_id=adj_id,
                    ))
        
        # Recruit - move soldiers from holdings to pool
        if player_holdings:
            actions.append(Action(
                action_type=ActionType.RECRUIT,
                player_id=player_id,
            ))
        
        # Build fortification (costs 10 gold, max 2 per player, max 3 per town)
        if player.gold >= 10 and player.fortifications_placed < 2:
            for holding in state.holdings:
                if holding.holding_type == HoldingType.TOWN:
                    if holding.fortification_count < 3:
                        # Can build on own holdings or others' holdings
                        actions.append(Action(
                            action_type=ActionType.BUILD_FORTIFICATION,
                            player_id=player_id,
                            target_holding_id=holding.id,
                        ))
        
        # Claim titles
        self._add_title_claim_actions(actions, player, state)
        
        # Attack (need at least 200 soldiers, one war per turn)
        if player.soldiers >= 200 and not state.war_fought_this_turn:
            if not state.enforce_peace_active:  # Enforce Peace card blocks wars
                self._add_attack_actions(actions, player, state)
        
        # Fake Claim (costs 35 gold for any unowned town)
        if player.gold >= 35:
            for holding in state.holdings:
                if holding.holding_type == HoldingType.TOWN and holding.owner_id is None:
                    actions.append(Action(
                        action_type=ActionType.FAKE_CLAIM,
                        player_id=player_id,
                        target_holding_id=holding.id,
                    ))
        
        # Play cards from hand
        for card_id in player.hand:
            card = state.cards.get(card_id)
            if card and not is_instant_card(card):  # Only non-instant cards can be played from hand
                actions.append(Action(
                    action_type=ActionType.PLAY_CARD,
                    player_id=player_id,
                    card_id=card_id,
                ))
        
        # End turn is always available
        actions.append(Action(
            action_type=ActionType.END_TURN,
            player_id=player_id,
        ))
        
        return actions
    
    def _add_title_claim_actions(self, actions: list[Action], player, state: GameState):
        """Add title claiming actions if prerequisites are met."""
        # Claim Count
        for county in ["X", "U", "V", "Q"]:
            if county not in player.counties and can_claim_count(state, player.id, county):
                # Check if castle is already claimed by someone else
                castle_id = get_county_castle(county)
                castle = next((h for h in state.holdings if h.id == castle_id), None)
                if castle and castle.owner_id is None:  # Not taken yet
                    if player.gold >= 25:
                        actions.append(Action(
                            action_type=ActionType.CLAIM_TITLE,
                            player_id=player.id,
                            target_holding_id=castle_id,
                        ))
        
        # Claim Duke
        for duchy in ["XU", "QV"]:
            if duchy not in player.duchies and can_claim_duke(state, player.id, duchy):
                castle_id = get_duchy_castle(duchy)
                castle = next((h for h in state.holdings if h.id == castle_id), None)
                if castle and castle.owner_id is None:
                    if player.gold >= 50:
                        actions.append(Action(
                            action_type=ActionType.CLAIM_TITLE,
                            player_id=player.id,
                            target_holding_id=castle_id,
                        ))
        
        # Claim King
        if not player.is_king and can_claim_king(state, player.id):
            king_castle = next((h for h in state.holdings if h.id == "king_castle"), None)
            if king_castle and king_castle.owner_id is None:
                if player.gold >= 75:
                    actions.append(Action(
                        action_type=ActionType.CLAIM_TITLE,
                        player_id=player.id,
                        target_holding_id="king_castle",
                    ))
    
    def _add_attack_actions(self, actions: list[Action], player, state: GameState):
        """Add attack actions for reachable enemy holdings."""
        player_holdings = [h.id for h in state.holdings if h.owner_id == player.id]
        
        for holding_id in player_holdings:
            adjacent = get_adjacent_holdings(holding_id)
            for adj_id in adjacent:
                adj_holding = next((h for h in state.holdings if h.id == adj_id), None)
                if adj_holding and adj_holding.owner_id != player.id:
                    # Can attack if not owned by player
                    actions.append(Action(
                        action_type=ActionType.ATTACK,
                        player_id=player.id,
                        source_holding_id=holding_id,
                        target_holding_id=adj_id,
                    ))
    
    def perform_action(self, action: Action) -> tuple[bool, str, Optional[CombatResult]]:
        """Perform a game action.
        
        Returns:
            Tuple of (success, message, combat_result)
        """
        state = self.state
        
        # Validate it's the player's turn
        if state.phase != GamePhase.PLAYER_TURN:
            return False, "Not in player turn phase", None
        
        current_player = state.players[state.current_player_idx]
        if current_player.id != action.player_id:
            return False, "Not your turn", None
        
        # Process action based on type
        handlers = {
            ActionType.DRAW_CARD: self._handle_draw_card,
            ActionType.MOVE: self._handle_move,
            ActionType.RECRUIT: self._handle_recruit,
            ActionType.BUILD_FORTIFICATION: self._handle_build_fortification,
            ActionType.CLAIM_TITLE: self._handle_claim_title,
            ActionType.ATTACK: self._handle_attack,
            ActionType.FAKE_CLAIM: self._handle_fake_claim,
            ActionType.PLAY_CARD: self._handle_play_card,
            ActionType.END_TURN: self._handle_end_turn,
        }
        
        handler = handlers.get(action.action_type)
        if not handler:
            return False, f"Unknown action type: {action.action_type}", None
        
        result = handler(action)
        
        # Check for victory after each action
        winner = check_victory(self.state)
        if winner:
            self.state.phase = GamePhase.GAME_OVER
            save_game(self.state)
        
        return result
    
    def _handle_draw_card(self, action: Action) -> tuple[bool, str, None]:
        """Handle drawing a card."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        
        if state.card_drawn_this_turn:
            return False, "Already drew a card this turn", None
        
        # Check town restriction
        if count_player_towns(state, player.id) > 4:
            return False, "Cannot draw cards while holding more than 4 towns", None
        
        if not state.deck:
            # Reshuffle discard pile
            if state.discard_pile:
                import random
                state.deck = state.discard_pile.copy()
                random.shuffle(state.deck)
                state.discard_pile = []
            else:
                return False, "No cards available", None
        
        card_id = state.deck.pop(0)
        card = state.cards.get(card_id)
        
        # Handle instant cards (personal and global events)
        if card and is_instant_card(card):
            result_msg = self._apply_instant_card(player, card, state)
            state.discard_pile.append(card_id)
            state.card_drawn_this_turn = True
            state.action_log.append(action)
            save_game(state)
            return True, result_msg, None
        
        # Non-instant cards go to hand
        player.hand.append(card_id)
        state.card_drawn_this_turn = True
        state.action_log.append(action)
        save_game(state)
        
        return True, f"Drew {card.name if card else 'card'}", None
    
    def _apply_instant_card(self, player, card, state: GameState) -> str:
        """Apply effects of instant cards (personal/global events)."""
        if card.card_type == CardType.PERSONAL_EVENT:
            if card.effect in [CardEffect.GOLD_5, CardEffect.GOLD_10, 
                              CardEffect.GOLD_15, CardEffect.GOLD_25]:
                gold_amount = card.effect_value or 0
                player.gold += gold_amount
                return f"Gained {gold_amount} gold from {card.name}!"
            
            elif card.effect == CardEffect.RAIDERS:
                # Lose all income collected this turn
                # For simplicity, we'll just notify (income was already applied)
                return f"Raiders attacked! (Effect pending implementation)"
        
        elif card.card_type == CardType.GLOBAL_EVENT:
            if card.effect == CardEffect.CRUSADE:
                # All players lose half gold and soldiers
                for p in state.players:
                    p.gold = p.gold // 2
                    p.soldiers = p.soldiers // 2
                return "Crusade! All players lost half their gold and soldiers!"
        
        return f"Drew {card.name}"
    
    def _handle_move(self, action: Action) -> tuple[bool, str, None]:
        """Handle moving soldiers between holdings."""
        state = self.state
        
        # Validate source and target
        source = next((h for h in state.holdings if h.id == action.source_holding_id), None)
        target = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if not source or not target:
            return False, "Invalid holdings", None
        
        if source.owner_id != action.player_id:
            return False, "You don't own the source holding", None
        
        if target.owner_id != action.player_id:
            return False, "Target is not your holding (use attack instead)", None
        
        # Check adjacency
        if action.target_holding_id not in get_adjacent_holdings(action.source_holding_id):
            return False, "Holdings are not adjacent", None
        
        state.action_log.append(action)
        save_game(state)
        
        return True, "Moved successfully", None
    
    def _handle_recruit(self, action: Action) -> tuple[bool, str, None]:
        """Handle recruiting soldiers."""
        state = self.state
        
        # Check if mercenaries are forbidden
        if state.forbid_mercenaries_active:
            return False, "Mercenaries are forbidden this turn", None
        
        state.action_log.append(action)
        save_game(state)
        
        return True, "Soldiers recruited", None
    
    def _handle_build_fortification(self, action: Action) -> tuple[bool, str, None]:
        """Handle building a fortification."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        holding = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if player.gold < 10:
            return False, "Not enough gold (need 10)", None
        
        if player.fortifications_placed >= 2:
            return False, "Maximum fortifications placed (2)", None
        
        if holding.fortification_count >= 3:
            return False, "Maximum fortifications on this holding (3)", None
        
        player.gold -= 10
        holding.fortification_count += 1
        player.fortifications_placed += 1
        
        # Track who placed the fortification
        if player.id not in holding.fortifications_by_player:
            holding.fortifications_by_player[player.id] = 0
        holding.fortifications_by_player[player.id] += 1
        
        state.action_log.append(action)
        save_game(state)
        
        return True, "Fortification built", None
    
    def _handle_claim_title(self, action: Action) -> tuple[bool, str, None]:
        """Handle claiming a title."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        
        target_id = action.target_holding_id
        holding = next((h for h in state.holdings if h.id == target_id), None)
        
        if not holding:
            return False, "Holding not found", None
        
        # Determine what title is being claimed
        if holding.holding_type == HoldingType.COUNTY_CASTLE:
            county = target_id[0].upper()
            if not can_claim_count(state, player.id, county):
                return False, "Prerequisites not met for Count", None
            if player.gold < 25:
                return False, "Not enough gold (need 25)", None
            
            player.gold -= 25
            player.counties.append(county)
            holding.owner_id = player.id
            if player.title == TitleType.BARON:
                player.title = TitleType.COUNT
            
            state.action_log.append(action)
            save_game(state)
            return True, f"Claimed Count of {county}", None
            
        elif holding.holding_type == HoldingType.DUCHY_CASTLE:
            duchy = target_id[:2].upper()
            if not can_claim_duke(state, player.id, duchy):
                return False, "Prerequisites not met for Duke", None
            if player.gold < 50:
                return False, "Not enough gold (need 50)", None
            
            player.gold -= 50
            player.duchies.append(duchy)
            holding.owner_id = player.id
            player.title = TitleType.DUKE
            
            state.action_log.append(action)
            save_game(state)
            return True, f"Claimed Duke of {duchy}", None
            
        elif holding.holding_type == HoldingType.KING_CASTLE:
            if not can_claim_king(state, player.id):
                return False, "Prerequisites not met for King", None
            if player.gold < 75:
                return False, "Not enough gold (need 75)", None
            
            # Remove king status from current king
            for p in state.players:
                if p.is_king:
                    p.is_king = False
                    p.title = TitleType.DUKE if p.duchies else (
                        TitleType.COUNT if p.counties else TitleType.BARON
                    )
            
            player.gold -= 75
            player.is_king = True
            player.title = TitleType.KING
            holding.owner_id = player.id
            player.prestige += 6  # Bonus for claiming king
            
            state.action_log.append(action)
            save_game(state)
            return True, "Claimed the Crown!", None
        
        return False, "Invalid title claim", None
    
    def _handle_fake_claim(self, action: Action) -> tuple[bool, str, None]:
        """Handle fabricating a claim on a town (35 gold)."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        holding = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if player.gold < 35:
            return False, "Not enough gold (need 35)", None
        
        if not holding or holding.holding_type != HoldingType.TOWN:
            return False, "Can only fake claim towns", None
        
        if holding.owner_id is not None:
            return False, "Town is already owned", None
        
        player.gold -= 35
        holding.owner_id = player.id
        player.holdings.append(holding.id)
        
        state.action_log.append(action)
        save_game(state)
        
        return True, f"Fabricated claim on {holding.name}", None
    
    def _handle_attack(self, action: Action) -> tuple[bool, str, Optional[CombatResult]]:
        """Handle attacking a holding."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        
        if state.war_fought_this_turn:
            return False, "Already fought a war this turn", None
        
        if state.enforce_peace_active:
            return False, "Wars are forbidden this turn", None
        
        soldiers = action.soldiers_count or 200  # Default to minimum
        
        if player.soldiers < soldiers:
            return False, "Not enough soldiers", None
        
        if soldiers < 200:
            return False, "Must commit at least 200 soldiers", None
        
        # Resolve combat
        result = resolve_combat(
            state,
            action.player_id,
            action.target_holding_id,
            soldiers,
        )
        
        # Apply result
        state = apply_combat_result(state, result)
        
        # Clear Big War effect if player used it in combat
        if player.has_big_war_effect:
            player.has_big_war_effect = False
        
        state.war_fought_this_turn = True
        state.action_log.append(action)
        save_game(state)
        self._state = state
        
        return True, "Combat resolved", result
    
    def _handle_play_card(self, action: Action) -> tuple[bool, str, None]:
        """Handle playing a card from hand."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        
        if action.card_id not in player.hand:
            return False, "Card not in hand", None
        
        card = state.cards.get(action.card_id)
        if not card:
            return False, "Card not found", None
        
        # Process based on card type
        if card.card_type == CardType.BONUS:
            result = self._play_bonus_card(player, card, action, state)
        elif card.card_type == CardType.CLAIM:
            result = self._play_claim_card(player, card, action, state)
        else:
            return False, "Cannot play this card type", None
        
        if result[0]:  # Success
            player.hand.remove(action.card_id)
            state.discard_pile.append(action.card_id)
            state.action_log.append(action)
            save_game(state)
        
        return result
    
    def _play_bonus_card(self, player, card, action: Action, state: GameState) -> tuple[bool, str, None]:
        """Play a bonus card."""
        effect = card.effect
        
        if effect == CardEffect.BIG_WAR:
            player.has_big_war_effect = True
            return True, "Big War activated! Army cap doubled until next war.", None
        
        elif effect == CardEffect.ADVENTURER:
            if player.gold < 25:
                return False, "Not enough gold (need 25)", None
            player.gold -= 25
            player.soldiers += 500
            return True, "Hired 500 adventurer soldiers!", None
        
        elif effect == CardEffect.EXCALIBUR:
            player.active_effects.append(CardEffect.EXCALIBUR)
            return True, "Excalibur ready! Roll twice in next combat.", None
        
        elif effect == CardEffect.POISONED_ARROWS:
            player.active_effects.append(CardEffect.POISONED_ARROWS)
            return True, "Poisoned arrows prepared! Enemy dice halved in next combat.", None
        
        elif effect == CardEffect.TALENTED_COMMANDER:
            player.active_effects.append(CardEffect.TALENTED_COMMANDER)
            return True, "Commander ready! No soldier loss on victory.", None
        
        elif effect == CardEffect.FORBID_MERCENARIES:
            state.forbid_mercenaries_active = True
            return True, "Mercenaries forbidden for this turn!", None
        
        elif effect == CardEffect.ENFORCE_PEACE:
            state.enforce_peace_active = True
            return True, "Peace enforced! No wars this turn.", None
        
        elif effect == CardEffect.VASSAL_REVOLT:
            player.active_effects.append(CardEffect.VASSAL_REVOLT)
            return True, "Vassal revolt prepared!", None
        
        elif effect == CardEffect.DUEL:
            player.active_effects.append(CardEffect.DUEL)
            return True, "Duel challenge ready!", None
        
        elif effect == CardEffect.SPY:
            # Simplified: just reveal top 3 cards of deck
            if len(state.deck) >= 3:
                top_cards = [state.cards.get(cid) for cid in state.deck[:3]]
                names = [c.name for c in top_cards if c]
                return True, f"Spy reveals next 3 cards: {', '.join(names)}", None
            return True, "Spy found nothing.", None
        
        return False, "Unknown bonus card effect", None
    
    def _play_claim_card(self, player, card, action: Action, state: GameState) -> tuple[bool, str, None]:
        """Play a claim card to take a town."""
        effect = card.effect
        target_id = action.target_holding_id
        
        if not target_id:
            return False, "Must specify a target holding", None
        
        holding = next((h for h in state.holdings if h.id == target_id), None)
        if not holding:
            return False, "Holding not found", None
        
        # Validate claim based on card type
        if effect in [CardEffect.CLAIM_X, CardEffect.CLAIM_U, CardEffect.CLAIM_V, CardEffect.CLAIM_Q]:
            required_county = get_card_county(card)
            if holding.county != required_county:
                return False, f"This claim only works in County {required_county}", None
            if holding.holding_type != HoldingType.TOWN:
                return False, "Can only claim towns", None
            if holding.owner_id is not None:
                return False, "Town is already owned", None
        
        elif effect == CardEffect.DUCHY_CLAIM:
            # Can claim any town or Duke+ title
            if holding.holding_type not in [HoldingType.TOWN, HoldingType.DUCHY_CASTLE, HoldingType.KING_CASTLE]:
                return False, "Invalid target for Duchy Claim", None
            if holding.owner_id is not None:
                return False, "Target is already owned", None
        
        elif effect == CardEffect.ULTIMATE_CLAIM:
            # Can claim anything
            if holding.owner_id is not None:
                return False, "Target is already owned", None
        
        else:
            return False, "Unknown claim type", None
        
        # Apply the claim
        holding.owner_id = player.id
        if holding.holding_type == HoldingType.TOWN:
            player.holdings.append(holding.id)
        
        return True, f"Claimed {holding.name}!", None
    
    def _handle_end_turn(self, action: Action) -> tuple[bool, str, None]:
        """Handle ending the turn."""
        state = self.state
        
        # Discard to hand limit (7 cards)
        player = next((p for p in state.players if p.id == action.player_id), None)
        while len(player.hand) > 7:
            discarded = player.hand.pop()
            state.discard_pile.append(discarded)
        
        # Clear player's active effects at end of turn
        player.active_effects = []
        
        state.action_log.append(action)
        next_player_turn(state)
        self._state = None  # Force refresh
        
        return True, "Turn ended", None
    
    def process_income_phase(self) -> GameState:
        """Process income phase for all players."""
        return apply_income(self.state)
    
    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return self.state.phase == GamePhase.GAME_OVER
