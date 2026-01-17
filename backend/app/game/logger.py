"""Game logging system for detailed game event tracking."""
import json
import os
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from app.config import get_settings


# Module-level storage for active game loggers
_game_loggers: dict[str, "GameLogger"] = {}


def get_logger(game_id: str) -> Optional["GameLogger"]:
    """Get an existing logger for a game."""
    return _game_loggers.get(game_id)


def create_logger(game_id: str) -> Optional["GameLogger"]:
    """Create a new logger for a game if logging is enabled."""
    settings = get_settings()
    if not settings.game_logging_enabled:
        return None
    
    logger = GameLogger(game_id, settings.game_logs_directory)
    _game_loggers[game_id] = logger
    return logger


def remove_logger(game_id: str) -> None:
    """Remove a logger when game is finished or deleted."""
    if game_id in _game_loggers:
        _game_loggers[game_id].close()
        del _game_loggers[game_id]


class GameLogger:
    """Logger for recording detailed game events to a JSON file."""
    
    def __init__(self, game_id: str, logs_directory: str):
        """Initialize the game logger.
        
        Args:
            game_id: Unique identifier for the game
            logs_directory: Directory path for log files
        """
        self.game_id = game_id
        self.logs_directory = Path(logs_directory)
        self.entries: list[dict] = []
        self._closed = False
        
        # Create logs directory if it doesn't exist
        self.logs_directory.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"game_{game_id[:8]}_{timestamp}.json"
        self.log_path = self.logs_directory / self.log_filename
    
    def _create_entry(
        self,
        event_type: str,
        round_num: Optional[int] = None,
        player_id: Optional[str] = None,
        player_name: Optional[str] = None,
        data: Optional[dict] = None
    ) -> dict:
        """Create a log entry with common fields."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
        }
        if round_num is not None:
            entry["round"] = round_num
        if player_id is not None:
            entry["player_id"] = player_id
        if player_name is not None:
            entry["player_name"] = player_name
        if data is not None:
            entry["data"] = data
        return entry
    
    def _write_entry(self, entry: dict) -> None:
        """Add entry to the log and write to file."""
        if self._closed:
            return
        
        self.entries.append(entry)
        self._save_to_file()
    
    def _save_to_file(self) -> None:
        """Save all entries to the log file."""
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "game_id": self.game_id,
                    "log_file": self.log_filename,
                    "entries": self.entries
                }, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            # Don't crash the game if logging fails
            print(f"Warning: Failed to write game log: {e}")
    
    def close(self) -> None:
        """Close the logger and finalize the log file."""
        if not self._closed:
            self._save_to_file()
            self._closed = True
    
    # ============ Game Lifecycle Events ============
    
    def log_game_start(
        self,
        player_configs: list[dict],
        players: list[Any],
        settings_snapshot: dict
    ) -> None:
        """Log game initialization."""
        player_data = []
        for p in players:
            player_data.append({
                "id": p.id,
                "name": p.name,
                "player_type": p.player_type.value if hasattr(p.player_type, 'value') else str(p.player_type),
                "color": p.color,
            })
        
        entry = self._create_entry(
            event_type="game_start",
            data={
                "player_configs": player_configs,
                "players": player_data,
                "settings": settings_snapshot,
            }
        )
        self._write_entry(entry)
    
    def log_game_end(
        self,
        round_num: int,
        winner_id: Optional[str],
        winner_name: Optional[str],
        final_standings: list[dict]
    ) -> None:
        """Log game completion."""
        entry = self._create_entry(
            event_type="game_end",
            round_num=round_num,
            data={
                "winner_id": winner_id,
                "winner_name": winner_name,
                "final_standings": final_standings,
            }
        )
        self._write_entry(entry)
        self.close()
    
    # ============ Turn Events ============
    
    def log_turn_start(
        self,
        round_num: int,
        player_id: str,
        player_name: str,
        player_state: dict
    ) -> None:
        """Log the start of a player's turn."""
        entry = self._create_entry(
            event_type="turn_start",
            round_num=round_num,
            player_id=player_id,
            player_name=player_name,
            data={
                "player_state": player_state,
            }
        )
        self._write_entry(entry)
    
    def log_turn_end(
        self,
        round_num: int,
        player_id: str,
        player_name: str,
        player_state: dict
    ) -> None:
        """Log the end of a player's turn."""
        entry = self._create_entry(
            event_type="turn_end",
            round_num=round_num,
            player_id=player_id,
            player_name=player_name,
            data={
                "player_state": player_state,
            }
        )
        self._write_entry(entry)
    
    def log_income_phase(
        self,
        round_num: int,
        income_details: dict[str, dict]
    ) -> None:
        """Log income phase details for all players."""
        entry = self._create_entry(
            event_type="income_phase",
            round_num=round_num,
            data={
                "income_by_player": income_details,
            }
        )
        self._write_entry(entry)
    
    # ============ Card Events ============
    
    def log_card_draw(
        self,
        round_num: int,
        player_id: str,
        player_name: str,
        card_id: str,
        card_name: str,
        card_type: str,
        is_instant: bool,
        effect_applied: Optional[str] = None
    ) -> None:
        """Log a card draw event."""
        entry = self._create_entry(
            event_type="card_draw",
            round_num=round_num,
            player_id=player_id,
            player_name=player_name,
            data={
                "card_id": card_id,
                "card_name": card_name,
                "card_type": card_type,
                "is_instant": is_instant,
                "effect_applied": effect_applied,
            }
        )
        self._write_entry(entry)
    
    # ============ Action Events ============
    
    def log_action(
        self,
        round_num: int,
        player_id: str,
        player_name: str,
        action_type: str,
        action_details: dict,
        success: bool,
        result_message: str
    ) -> None:
        """Log a game action."""
        entry = self._create_entry(
            event_type="action",
            round_num=round_num,
            player_id=player_id,
            player_name=player_name,
            data={
                "action_type": action_type,
                "action_details": action_details,
                "success": success,
                "result_message": result_message,
            }
        )
        self._write_entry(entry)
    
    # ============ Combat Events ============
    
    def log_combat(
        self,
        round_num: int,
        attacker_id: str,
        attacker_name: str,
        defender_id: Optional[str],
        defender_name: Optional[str],
        target_holding_id: str,
        target_holding_name: str,
        combat_details: dict
    ) -> None:
        """Log a combat event with full details."""
        entry = self._create_entry(
            event_type="combat",
            round_num=round_num,
            data={
                "attacker_id": attacker_id,
                "attacker_name": attacker_name,
                "defender_id": defender_id,
                "defender_name": defender_name,
                "target_holding_id": target_holding_id,
                "target_holding_name": target_holding_name,
                "combat_details": combat_details,
            }
        )
        self._write_entry(entry)
    
    # ============ AI Events ============
    
    def log_ai_decision(
        self,
        round_num: int,
        player_id: str,
        player_name: str,
        player_type: str,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        parsed_action: str,
        action_details: dict,
        decision_log: Optional[dict] = None
    ) -> None:
        """Log an AI decision with full prompt/response details."""
        entry = self._create_entry(
            event_type="ai_decision",
            round_num=round_num,
            player_id=player_id,
            player_name=player_name,
            data={
                "player_type": player_type,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_response": raw_response,
                "parsed_action": parsed_action,
                "action_details": action_details,
                "decision_log": decision_log,
            }
        )
        self._write_entry(entry)
    
    def log_ai_combat_decision(
        self,
        round_num: int,
        player_id: str,
        player_name: str,
        player_type: str,
        decision_type: str,  # "attack_commitment" or "defense"
        prompt: str,
        response: str,
        soldiers_committed: int
    ) -> None:
        """Log an AI combat decision (soldier commitment)."""
        entry = self._create_entry(
            event_type="ai_combat_decision",
            round_num=round_num,
            player_id=player_id,
            player_name=player_name,
            data={
                "player_type": player_type,
                "decision_type": decision_type,
                "prompt": prompt,
                "response": response,
                "soldiers_committed": soldiers_committed,
            }
        )
        self._write_entry(entry)
    
    # ============ Utility Methods ============
    
    def get_player_state_snapshot(self, player: Any) -> dict:
        """Create a snapshot of player state for logging."""
        return {
            "gold": player.gold,
            "soldiers": player.soldiers,
            "prestige": player.prestige,
            "title": player.title.value if hasattr(player.title, 'value') else str(player.title),
            "holdings": list(player.holdings),
            "counties": list(player.counties),
            "duchies": list(player.duchies),
            "is_king": player.is_king,
            "hand_size": len(player.hand),
            "claims": list(player.claims),
            "army_cap": player.army_cap,
        }
    
    def get_action_details(self, action: Any) -> dict:
        """Extract action details for logging."""
        details = {
            "action_type": action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type),
        }
        if action.target_holding_id:
            details["target_holding_id"] = action.target_holding_id
        if action.source_holding_id:
            details["source_holding_id"] = action.source_holding_id
        if action.soldiers_count is not None:
            details["soldiers_count"] = action.soldiers_count
        if action.card_id:
            details["card_id"] = action.card_id
        if action.target_player_id:
            details["target_player_id"] = action.target_player_id
        if action.attack_cards:
            details["attack_cards"] = list(action.attack_cards)
        if action.defense_cards:
            details["defense_cards"] = list(action.defense_cards)
        return details
