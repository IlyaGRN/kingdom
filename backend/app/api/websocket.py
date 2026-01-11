"""WebSocket handlers for real-time game updates."""
import asyncio
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.game.state import get_game
from app.game.engine import GameEngine
from app.ai.manager import AIManager

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for games."""
    
    def __init__(self):
        # game_id -> set of connected websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, game_id: str):
        """Accept a new connection for a game."""
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = set()
        self.active_connections[game_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, game_id: str):
        """Remove a connection."""
        if game_id in self.active_connections:
            self.active_connections[game_id].discard(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]
    
    async def broadcast(self, game_id: str, message: dict):
        """Broadcast a message to all connections for a game."""
        if game_id in self.active_connections:
            message_text = json.dumps(message)
            disconnected = set()
            for connection in self.active_connections[game_id]:
                try:
                    await connection.send_text(message_text)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected
            for conn in disconnected:
                self.active_connections[game_id].discard(conn)


manager = ConnectionManager()


@router.websocket("/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str):
    """WebSocket endpoint for game updates."""
    state = get_game(game_id)
    if not state:
        await websocket.close(code=4004, reason="Game not found")
        return
    
    await manager.connect(websocket, game_id)
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "state",
            "data": state.model_dump(),
        })
        
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif message.get("type") == "get_state":
                state = get_game(game_id)
                if state:
                    await websocket.send_json({
                        "type": "state",
                        "data": state.model_dump(),
                    })
            
            elif message.get("type") == "action":
                # Handle game action
                from app.models.schemas import Action
                action_data = message.get("data", {})
                action = Action(**action_data)
                
                engine = GameEngine(game_id)
                success, msg, combat = engine.perform_action(action)
                
                # Broadcast update to all connected clients
                await manager.broadcast(game_id, {
                    "type": "action_result",
                    "success": success,
                    "message": msg,
                    "state": engine.state.model_dump(),
                    "combat": combat.model_dump() if combat else None,
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)


@router.websocket("/simulation/{game_id}")
async def simulation_websocket(websocket: WebSocket, game_id: str, speed_ms: int = 1000):
    """WebSocket endpoint for watching AI simulations."""
    state = get_game(game_id)
    if not state:
        await websocket.close(code=4004, reason="Game not found")
        return
    
    await manager.connect(websocket, game_id)
    engine = GameEngine(game_id)
    ai_manager = AIManager()
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "simulation_start",
            "data": state.model_dump(),
        })
        
        running = True
        
        while running and not engine.is_game_over():
            # Check for control messages (non-blocking)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.01
                )
                message = json.loads(data)
                
                if message.get("type") == "stop":
                    running = False
                    continue
                elif message.get("type") == "speed":
                    speed_ms = message.get("value", speed_ms)
            except asyncio.TimeoutError:
                pass
            
            # Get current player and have AI make a move
            current_player = engine.state.players[engine.state.current_player_idx]
            
            try:
                action = await ai_manager.get_ai_action(engine.state, current_player)
                if action:
                    success, msg, combat = engine.perform_action(action)
                    
                    # Broadcast the action
                    await manager.broadcast(game_id, {
                        "type": "simulation_step",
                        "player": current_player.name,
                        "action": action.model_dump(),
                        "message": msg,
                        "state": engine.state.model_dump(),
                        "combat": combat.model_dump() if combat else None,
                    })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
            
            # Wait before next step
            await asyncio.sleep(speed_ms / 1000)
        
        # Game over
        from app.game.state import get_winner, calculate_prestige
        winner = get_winner(engine.state)
        
        await manager.broadcast(game_id, {
            "type": "simulation_end",
            "state": engine.state.model_dump(),
            "winner": winner.model_dump() if winner else None,
            "prestige": calculate_prestige(engine.state),
        })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)




