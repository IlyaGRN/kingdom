"""Core game engine - orchestrates game flow and action processing."""
from typing import Optional
from app.models.schemas import (
    GameState, Action, ActionType, GamePhase, TitleType,
    CombatResult, EdictType, HoldingType, CardType, CardEffect,
    PendingCombat, PlayerType
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
from app.game.logger import get_logger


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
        
        # Cards are now auto-drawn at the beginning of each turn
        # No manual draw action needed
        
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
        
        # Build fortification (costs 10 gold, max 4 per player total, max 2 per player per town, max 3 per town)
        if player.gold >= 10 and player.fortifications_placed < 4:
            for holding in state.holdings:
                if holding.holding_type == HoldingType.TOWN:
                    if holding.fortification_count < 3:
                        # Check max 2 per player on this town
                        player_forts_here = holding.fortifications_by_player.get(player_id, 0)
                        if player_forts_here < 2:
                            actions.append(Action(
                                action_type=ActionType.BUILD_FORTIFICATION,
                                player_id=player_id,
                                target_holding_id=holding.id,
                            ))
        
        # Relocate fortification (costs 10 gold, available when player has at least one fortification)
        if player.gold >= 10:
            for source in state.holdings:
                player_forts_here = source.fortifications_by_player.get(player_id, 0)
                if player_forts_here > 0:
                    for target in state.holdings:
                        if target.id != source.id and target.holding_type == HoldingType.TOWN:
                            if target.fortification_count < 3:
                                target_player_forts = target.fortifications_by_player.get(player_id, 0)
                                if target_player_forts < 2:
                                    actions.append(Action(
                                        action_type=ActionType.RELOCATE_FORTIFICATION,
                                        player_id=player_id,
                                        source_holding_id=source.id,
                                        target_holding_id=target.id,
                                    ))
        
        # Claim titles
        self._add_title_claim_actions(actions, player, state)
        
        # Attack (need at least 200 soldiers, one war per turn)
        if player.soldiers >= 200 and not state.war_fought_this_turn:
            if not state.enforce_peace_active:  # Enforce Peace card blocks wars
                self._add_attack_actions(actions, player, state)
        
        # Claim Town (10 gold to peacefully capture unowned town with valid claim)
        if player.gold >= 10:
            for holding in state.holdings:
                if (holding.holding_type == HoldingType.TOWN and 
                    holding.owner_id is None and 
                    holding.id in player.claims):
                    actions.append(Action(
                        action_type=ActionType.CLAIM_TOWN,
                        player_id=player_id,
                        target_holding_id=holding.id,
                    ))
        
        # Fake Claim (costs 35 gold to fabricate a claim on a town only)
        # Cannot fabricate claims on County, Duchy, or King castles
        if player.gold >= 35:
            for holding in state.holdings:
                # Can only fabricate claim on TOWNS, not castles
                if holding.holding_type == HoldingType.TOWN and holding.id not in player.claims:
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
                castle_id = get_county_castle(county)
                castle = next((h for h in state.holdings if h.id == castle_id), None)
                if castle and castle.owner_id is None:
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
        """Add attack actions for holdings the player can attack.
        
        Attack requires a valid claim on the target territory.
        Player can attack ANY holding they have a claim on (not just adjacent).
        
        IMPORTANT: Cannot attack vassals (holdings in your domain) without VASSAL_REVOLT card.
        """
        player_holdings = [h.id for h in state.holdings if h.owner_id == player.id]
        added_targets = set()  # Track to avoid duplicates
        
        # First, add attacks for adjacent holdings (if player has claim)
        # Only attack holdings owned by OTHER players (not unowned, not own)
        for holding_id in player_holdings:
            adjacent = get_adjacent_holdings(holding_id)
            for adj_id in adjacent:
                adj_holding = next((h for h in state.holdings if h.id == adj_id), None)
                # Must be owned by another player (not unowned, not own)
                if adj_holding and adj_holding.owner_id is not None and adj_holding.owner_id != player.id:
                    has_claim = self._has_valid_claim(player, adj_holding)
                    can_attack = self._can_attack_holding(player, adj_holding)
                    if has_claim and can_attack and adj_id not in added_targets:
                        actions.append(Action(
                            action_type=ActionType.ATTACK,
                            player_id=player.id,
                            source_holding_id=holding_id,
                            target_holding_id=adj_id,
                        ))
                        added_targets.add(adj_id)
        
        # Second, add attacks for ANY holding the player has a direct claim on
        # But only if the holding is OWNED by someone else (can't attack unowned)
        for claim_id in player.claims:
            if claim_id in added_targets:
                continue
            claim_holding = next((h for h in state.holdings if h.id == claim_id), None)
            # Must be owned by another player (not unowned, not own)
            if claim_holding and claim_holding.owner_id is not None and claim_holding.owner_id != player.id:
                # Check vassal protection
                if not self._can_attack_holding(player, claim_holding):
                    continue
                # Use any player holding as source (they're "projecting power")
                source_holding = player_holdings[0] if player_holdings else None
                if source_holding:
                    actions.append(Action(
                        action_type=ActionType.ATTACK,
                        player_id=player.id,
                        source_holding_id=source_holding,
                        target_holding_id=claim_id,
                    ))
                    added_targets.add(claim_id)
    
    def _has_valid_claim(self, player, holding) -> bool:
        """Check if player has a valid claim on a holding.
        
        Claims come from:
        - Played claim cards (stored in player.claims list)
        - Fabricated claims (also in player.claims list)
        - AUTOMATIC: Meeting Count/Duke/King prerequisites gives a claim on that castle
        
        IMPORTANT: Without any claims, you cannot attack anyone!
        """
        # FIRST: Check for automatic claims based on title prerequisites
        # If player meets Count prerequisites for a county, they have a claim on that county castle
        if holding.holding_type == HoldingType.COUNTY_CASTLE and holding.county:
            if can_claim_count(self.state, player.id, holding.county):
                return True
        
        # If player meets Duke prerequisites for a duchy, they have a claim on that duchy castle
        if holding.holding_type == HoldingType.DUCHY_CASTLE and holding.duchy:
            if can_claim_duke(self.state, player.id, holding.duchy):
                return True
        
        # If player meets King prerequisites, they have a claim on the king castle
        if holding.id == "king_castle":
            if can_claim_king(self.state, player.id):
                return True
        
        # If player has no explicit claims at all, return False for non-castle holdings
        if not player.claims or len(player.claims) == 0:
            return False
        
        # Check if holding ID is in player's claims list
        if holding.id in player.claims:
            return True
        
        # Check if player has a claim for the holding's county (for towns)
        county_claim_key = f"county_{holding.county}"
        if holding.county and county_claim_key in player.claims:
            return True
        
        # Check for "all" claims (ultimate/duchy)
        if "all" in player.claims:
            return True
        
        return False
    
    def _is_holding_in_domain(self, player, holding) -> bool:
        """Check if a holding is within the player's domain (making its owner a vassal).
        
        Vassal relationships:
        - Count of county X: all holdings in county X are in their domain
        - Duke of duchy XU: all holdings in counties X and U are in their domain
        - King: all holdings in the realm are in their domain
        
        A player cannot attack holdings in their domain without VASSAL_REVOLT card.
        """
        # King controls the entire realm
        if player.is_king:
            return True
        
        # Duke controls their duchy (both counties)
        for duchy in player.duchies:
            duchy_counties = []
            if duchy == "XU":
                duchy_counties = ["X", "U"]
            elif duchy == "QV":
                duchy_counties = ["Q", "V"]
            
            if holding.county in duchy_counties:
                return True
            if holding.duchy == duchy:
                return True
        
        # Count controls their county
        if holding.county in player.counties:
            return True
        
        return False
    
    def _can_attack_holding(self, player, holding) -> bool:
        """Check if player can attack a holding, considering vassal protection.
        
        Returns False if:
        - The holding is in the player's domain (vassal) AND
        - The player doesn't have VASSAL_REVOLT active
        """
        # If holding is in player's domain, need Vassal Revolt to attack
        is_in_domain = self._is_holding_in_domain(player, holding)
        if is_in_domain:
            if CardEffect.VASSAL_REVOLT not in player.active_effects:
                return False
        
        return True
    
    def _consume_claim(self, player, holding) -> None:
        """Remove the claim used for attack/capture."""
        # Remove specific holding claim first
        if holding.id in player.claims:
            player.claims.remove(holding.id)
            return
        
        # Remove county claim
        if holding.county and f"county_{holding.county}" in player.claims:
            player.claims.remove(f"county_{holding.county}")
            return
        
        # Remove universal claim last
        if "all" in player.claims:
            player.claims.remove("all")
    
    def perform_action(self, action: Action) -> tuple[bool, str, Optional[CombatResult]]:
        """Perform a game action.
        
        Returns:
            Tuple of (success, message, combat_result)
        """
        state = self.state
        
        # Special case: DEFEND action is allowed during COMBAT phase
        if action.action_type == ActionType.DEFEND:
            if state.phase != GamePhase.COMBAT:
                return False, "No combat to defend", None
            # Defender validation is done in _handle_defend
            return self._handle_defend(action)
        
        # Validate it's the player's turn for all other actions
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
            ActionType.RELOCATE_FORTIFICATION: self._handle_relocate_fortification,
            ActionType.CLAIM_TITLE: self._handle_claim_title,
            ActionType.CLAIM_TOWN: self._handle_claim_town,
            ActionType.ATTACK: self._handle_attack,
            ActionType.DEFEND: self._handle_defend,
            ActionType.FAKE_CLAIM: self._handle_fake_claim,
            ActionType.PLAY_CARD: self._handle_play_card,
            ActionType.END_TURN: self._handle_end_turn,
        }
        
        handler = handlers.get(action.action_type)
        if not handler:
            return False, f"Unknown action type: {action.action_type}", None
        
        result = handler(action)
        
        # Log the action
        logger = get_logger(self.game_id)
        if logger:
            player = next((p for p in self.state.players if p.id == action.player_id), None)
            player_name = player.name if player else "Unknown"
            
            action_details = logger.get_action_details(action)
            logger.log_action(
                round_num=self.state.current_round,
                player_id=action.player_id,
                player_name=player_name,
                action_type=action.action_type.value,
                action_details=action_details,
                success=result[0],
                result_message=result[1]
            )
        
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
                # All players lose half gold and soldiers (soldiers rounded down to 100)
                for p in state.players:
                    p.gold = p.gold // 2
                    p.soldiers = (p.soldiers // 2 // 100) * 100  # Half, then round down to 100
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
        """Handle building a fortification.
        
        Rules:
        - Max 4 per player total
        - Max 2 per player per town
        - Max 3 per town total
        """
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        holding = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if player.gold < 10:
            return False, "Not enough gold (need 10)", None
        
        if player.fortifications_placed >= 4:
            return False, "Maximum fortifications placed (4)", None
        
        if holding.holding_type != HoldingType.TOWN:
            return False, "Can only fortify towns", None
        
        if holding.fortification_count >= 3:
            return False, "Maximum fortifications on this town (3)", None
        
        # Check max 2 per player on this town
        player_forts_here = holding.fortifications_by_player.get(player.id, 0)
        if player_forts_here >= 2:
            return False, "You already have 2 fortifications on this town", None
        
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
            # Note: 6 VP for being king is calculated dynamically in calculate_prestige
            
            state.action_log.append(action)
            save_game(state)
            return True, "Claimed the Crown!", None
        
        return False, "Invalid title claim", None
    
    def _handle_fake_claim(self, action: Action) -> tuple[bool, str, None]:
        """Handle fabricating a claim on a town (35 gold).
        
        This establishes a claim that allows attacking or capturing the territory.
        Does not immediately take the territory.
        Cannot fabricate claims on County, Duchy, or King castles.
        """
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        holding = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if player.gold < 35:
            return False, "Not enough gold (need 35)", None
        
        if not holding:
            return False, "Holding not found", None
        
        # Cannot fabricate claims on castles - only towns
        if holding.holding_type != HoldingType.TOWN:
            return False, "Cannot fabricate claims on castles. Only towns can be targeted.", None
        
        # Check if player already has a claim on this holding
        if holding.id in player.claims:
            return False, "You already have a claim on this territory", None
        
        player.gold -= 35
        player.claims.append(holding.id)
        
        state.action_log.append(action)
        save_game(state)
        
        return True, f"Fabricated claim on {holding.name}! You can now attack or capture it.", None
    
    def _handle_claim_town(self, action: Action) -> tuple[bool, str, None]:
        """Handle peacefully capturing an unowned town with a valid claim (10 gold)."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        holding = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if player.gold < 10:
            return False, "Not enough gold (need 10)", None
        
        if not holding:
            return False, "Holding not found", None
        
        if holding.holding_type != HoldingType.TOWN:
            return False, "Can only claim towns this way", None
        
        if holding.owner_id is not None:
            return False, "Town is occupied - you must attack to take it", None
        
        # Must have a valid claim
        if holding.id not in player.claims:
            return False, "You need a valid claim to capture this town", None
        
        # Consume the claim
        player.claims.remove(holding.id)
        
        # Capture the town
        player.gold -= 10
        holding.owner_id = player.id
        player.holdings.append(holding.id)
        
        state.action_log.append(action)
        save_game(state)
        
        return True, f"Captured {holding.name}!", None
    
    def _handle_relocate_fortification(self, action: Action) -> tuple[bool, str, None]:
        """Handle relocating a fortification (costs 10 gold)."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        
        source = next((h for h in state.holdings if h.id == action.source_holding_id), None)
        target = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if not source or not target:
            return False, "Invalid holdings", None
        
        # Check player has enough gold
        if player.gold < 10:
            return False, "Not enough gold (need 10)", None
        
        # Check source has player's fortification
        if player.id not in source.fortifications_by_player or source.fortifications_by_player[player.id] <= 0:
            return False, "No fortification to move from this holding", None
        
        # Check target can receive fortification
        if target.holding_type != HoldingType.TOWN:
            return False, "Can only fortify towns", None
        
        if target.fortification_count >= 3:
            return False, "Target already has maximum fortifications", None
        
        # Check player's limit on target (max 2 per player per town)
        player_forts_on_target = target.fortifications_by_player.get(player.id, 0)
        if player_forts_on_target >= 2:
            return False, "You already have 2 fortifications on this town", None
        
        # Charge gold
        player.gold -= 10
        
        # Relocate the fortification
        source.fortifications_by_player[player.id] -= 1
        source.fortification_count -= 1
        
        if player.id not in target.fortifications_by_player:
            target.fortifications_by_player[player.id] = 0
        target.fortifications_by_player[player.id] += 1
        target.fortification_count += 1
        
        state.action_log.append(action)
        save_game(state)
        
        return True, f"Relocated fortification from {source.name} to {target.name} (10 gold)", None
    
    def _handle_attack(self, action: Action) -> tuple[bool, str, Optional[CombatResult]]:
        """Handle attacking a holding.
        
        Requires a valid claim on the target territory.
        If defender is human, creates pending_combat for their response.
        """
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        target = next((h for h in state.holdings if h.id == action.target_holding_id), None)
        
        if not target:
            return False, "Target holding not found", None
        
        if state.war_fought_this_turn:
            return False, "Already fought a war this turn", None
        
        if state.enforce_peace_active:
            return False, "Wars are forbidden this turn", None
        
        # Validate claim
        if not self._has_valid_claim(player, target):
            return False, "You need a valid claim to attack this territory", None
        
        # Check vassal protection - cannot attack holdings in your domain without Vassal Revolt
        if not self._can_attack_holding(player, target):
            return False, "Cannot attack your vassals! Use Vassal Revolt card first.", None
        
        soldiers = action.soldiers_count or 200  # Default to minimum
        # Enforce soldiers must be multiples of 100
        soldiers = (soldiers // 100) * 100
        soldiers = max(200, soldiers)  # Minimum 200
        
        if player.soldiers < soldiers:
            return False, "Not enough soldiers", None
        
        if soldiers < 200:
            return False, "Must commit at least 200 soldiers", None
        
        # Get defender
        defender = next((p for p in state.players if p.id == target.owner_id), None)
        
        # Check if defender is human - if so, create pending combat
        if defender and defender.player_type == PlayerType.HUMAN:
            state.pending_combat = PendingCombat(
                attacker_id=action.player_id,
                defender_id=defender.id,
                target_holding_id=action.target_holding_id,
                attacker_soldiers=soldiers,
                attacker_cards=action.attack_cards or [],
                source_holding_id=action.source_holding_id,
            )
            # Change phase to COMBAT to pause game until human responds
            state.phase = GamePhase.COMBAT
            state.action_log.append(action)
            save_game(state)
            return True, "Awaiting defender response", None
        
        # Defender is AI or unowned - resolve combat immediately
        # For AI defender, let them select cards and decide soldier commitment
        defender_cards: list[str] = []
        defender_soldiers = 0
        if defender and defender.player_type != PlayerType.HUMAN:
            defender_cards = self._ai_select_combat_cards(defender)
            # AI decides how many soldiers to commit based on situation
            defender_soldiers = self._ai_calculate_defender_commitment(
                defender, soldiers, target
            )
        
        # Consume the claim (regardless of combat outcome)
        self._consume_claim(player, target)
        
        # Resolve combat with card selections
        result = resolve_combat(
            state,
            action.player_id,
            action.target_holding_id,
            soldiers,
            source_holding_id=action.source_holding_id,
            attacker_cards=action.attack_cards or [],
            defender_cards=defender_cards,
            defender_soldiers_override=defender_soldiers if defender else None,
        )
        
        # Apply result
        state = apply_combat_result(state, result)
        
        # Log the combat
        logger = get_logger(self.game_id)
        if logger:
            defender_name = defender.name if defender else "Neutral"
            combat_details = {
                "attacker_soldiers_committed": result.attacker_soldiers_committed,
                "defender_soldiers_committed": result.defender_soldiers_committed,
                "attacker_roll": result.attacker_roll,
                "defender_roll": result.defender_roll,
                "attacker_strength": result.attacker_strength,
                "defender_strength": result.defender_strength,
                "attacker_won": result.attacker_won,
                "attacker_losses": result.attacker_losses,
                "defender_losses": result.defender_losses,
                "attacker_cards_used": action.attack_cards or [],
                "defender_cards_used": defender_cards,
            }
            logger.log_combat(
                round_num=state.current_round,
                attacker_id=action.player_id,
                attacker_name=player.name,
                defender_id=defender.id if defender else None,
                defender_name=defender_name,
                target_holding_id=action.target_holding_id,
                target_holding_name=target.name,
                combat_details=combat_details
            )
        
        # Discard used combat cards
        self._discard_combat_cards(player, action.attack_cards or [])
        if defender:
            self._discard_combat_cards(defender, defender_cards)
        
        # Clear Big War effect if player used it in combat
        if player.has_big_war_effect:
            player.has_big_war_effect = False
        
        state.war_fought_this_turn = True
        state.action_log.append(action)
        save_game(state)
        self._state = state
        
        return True, "Combat resolved", result
    
    def _ai_select_combat_cards(self, player) -> list[str]:
        """AI selects which combat cards to use from hand."""
        combat_effects = {CardEffect.EXCALIBUR, CardEffect.POISONED_ARROWS, 
                          CardEffect.TALENTED_COMMANDER, CardEffect.DUEL}
        selected = []
        state = self.state
        for card_id in player.hand:
            card = state.cards.get(card_id)
            if card and card.card_type == CardType.BONUS and card.effect in combat_effects:
                selected.append(card_id)
        return selected
    
    def _ai_calculate_defender_commitment(
        self, 
        defender, 
        attacker_soldiers: int,
        target_holding
    ) -> int:
        """AI calculates how many soldiers to commit for defense.
        
        Strategy:
        - If we have fortifications, we have an advantage - commit less
        - If attacker is committing heavily, we need to match
        - Always keep some reserves if possible
        - Commit enough to have a good chance of winning
        
        Combat formula: Strength = 2d6 + (soldiers/100) + modifiers
        """
        if defender.soldiers == 0:
            return 0
        
        # Calculate our defensive advantage
        fort_bonus = target_holding.fortification_count * 2 if target_holding else 0
        defense_bonus = target_holding.defense_modifier if target_holding else 0
        total_defense_bonus = fort_bonus + defense_bonus
        
        # Attacker's soldier bonus
        attacker_bonus = attacker_soldiers // 100
        
        # We need to match or exceed attacker strength
        # Base dice average is 7 (2d6)
        # We want: our_soldiers/100 + our_bonuses >= attacker_soldiers/100
        # So: our_soldiers >= (attacker_bonus - total_defense_bonus) * 100
        
        # Calculate minimum soldiers needed to match attacker
        min_needed = max(0, (attacker_bonus - total_defense_bonus) * 100)
        
        # Add buffer for dice variance (about 200 extra for safety)
        recommended = min_needed + 200
        
        # But also consider committing proportionally to threat
        # If attacker is committing a lot, we might need to match more aggressively
        proportional = int(attacker_soldiers * 0.8)  # Match 80% of attacker
        
        # Take the higher of the two strategies
        target_commitment = max(recommended, proportional)
        
        # Round to nearest 100
        target_commitment = (target_commitment // 100) * 100
        
        # Cap at available soldiers
        target_commitment = min(target_commitment, defender.soldiers)
        
        # If we'd commit more than 80% of our army, just commit all
        # (no point keeping tiny reserves)
        if target_commitment >= defender.soldiers * 0.8:
            target_commitment = defender.soldiers
        
        # Minimum commitment (if we have any soldiers, commit at least some)
        if defender.soldiers > 0 and target_commitment == 0:
            target_commitment = min(200, defender.soldiers)
        
        return target_commitment
    
    def _discard_combat_cards(self, player, card_ids: list[str]) -> None:
        """Remove combat cards from player's hand and add to discard."""
        state = self.state
        for card_id in card_ids:
            if card_id in player.hand:
                player.hand.remove(card_id)
                state.discard_pile.append(card_id)
    
    def _handle_defend(self, action: Action) -> tuple[bool, str, Optional[CombatResult]]:
        """Handle human defender's response to an attack."""
        state = self.state
        
        if not state.pending_combat:
            return False, "No pending combat to defend", None
        
        pending = state.pending_combat
        
        if action.player_id != pending.defender_id:
            return False, "You are not the defender in this combat", None
        
        defender = next((p for p in state.players if p.id == pending.defender_id), None)
        attacker = next((p for p in state.players if p.id == pending.attacker_id), None)
        target = next((h for h in state.holdings if h.id == pending.target_holding_id), None)
        
        if not defender or not attacker or not target:
            return False, "Invalid combat state", None
        
        # Get defender's soldier commitment (defaults to all available)
        defender_soldiers = action.soldiers_count if action.soldiers_count is not None else defender.soldiers
        defender_soldiers = max(0, min(defender_soldiers, defender.soldiers))
        
        # Consume attacker's claim
        self._consume_claim(attacker, target)
        
        # Resolve combat with both sides' card selections
        result = resolve_combat(
            state,
            pending.attacker_id,
            pending.target_holding_id,
            pending.attacker_soldiers,
            source_holding_id=pending.source_holding_id,
            attacker_cards=pending.attacker_cards,
            defender_cards=action.defense_cards or [],
            defender_soldiers_override=defender_soldiers,
        )
        
        # Apply result
        state = apply_combat_result(state, result)
        
        # Log the combat
        logger = get_logger(self.game_id)
        if logger:
            combat_details = {
                "attacker_soldiers_committed": result.attacker_soldiers_committed,
                "defender_soldiers_committed": result.defender_soldiers_committed,
                "attacker_roll": result.attacker_roll,
                "defender_roll": result.defender_roll,
                "attacker_strength": result.attacker_strength,
                "defender_strength": result.defender_strength,
                "attacker_won": result.attacker_won,
                "attacker_losses": result.attacker_losses,
                "defender_losses": result.defender_losses,
                "attacker_cards_used": pending.attacker_cards,
                "defender_cards_used": action.defense_cards or [],
            }
            logger.log_combat(
                round_num=state.current_round,
                attacker_id=pending.attacker_id,
                attacker_name=attacker.name,
                defender_id=defender.id,
                defender_name=defender.name,
                target_holding_id=pending.target_holding_id,
                target_holding_name=target.name,
                combat_details=combat_details
            )
        
        # Discard used combat cards
        self._discard_combat_cards(attacker, pending.attacker_cards)
        self._discard_combat_cards(defender, action.defense_cards or [])
        
        # Clear Big War effect if attacker used it
        if attacker.has_big_war_effect:
            attacker.has_big_war_effect = False
        
        # Clear pending combat and restore player turn phase
        state.pending_combat = None
        state.phase = GamePhase.PLAYER_TURN
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
            # Cap soldiers at army capacity
            player.soldiers = min(player.soldiers, player.army_cap)
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
        """Play a claim card to establish a claim on a territory.
        
        Claims allow the player to:
        - Attack a territory (if occupied by another player)
        - Capture an unowned territory for 10 gold (via CLAIM_TOWN action)
        """
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
            # County claim cards can target TOWNS or the COUNTY CASTLE
            if holding.holding_type not in [HoldingType.TOWN, HoldingType.COUNTY_CASTLE]:
                return False, "County claim cards only work on towns or county castles", None
        
        elif effect == CardEffect.DUCHY_CLAIM:
            # Can claim any town or Duke+ title
            if holding.holding_type not in [HoldingType.TOWN, HoldingType.DUCHY_CASTLE, HoldingType.KING_CASTLE]:
                return False, "Invalid target for Duchy Claim", None
        
        elif effect == CardEffect.ULTIMATE_CLAIM:
            # Can claim anything - no restrictions
            pass
        
        else:
            return False, "Unknown claim type", None
        
        # Add the claim to player's claims list
        if holding.id not in player.claims:
            player.claims.append(holding.id)
        
        return True, f"Established claim on {holding.name}! You can now attack or capture it.", None
    
    def _handle_end_turn(self, action: Action) -> tuple[bool, str, None]:
        """Handle ending the turn."""
        state = self.state
        player = next((p for p in state.players if p.id == action.player_id), None)
        
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
