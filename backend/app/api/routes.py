"""REST API routes for the game."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models.schemas import (
    CreateGameRequest, CreateGameResponse,
    PerformActionRequest, PerformActionResponse,
    GetValidActionsRequest, GetValidActionsResponse,
    GameState, Action, SimulationConfig
)
from app.game.state import (
    create_game, get_game, list_games, delete_game,
    assign_starting_town, start_game, calculate_prestige, get_winner
)
from app.game.engine import GameEngine

router = APIRouter()


@router.post("/games", response_model=CreateGameResponse)
async def create_new_game(request: CreateGameRequest):
    """Create a new game with the specified player configurations."""
    try:
        state = create_game(request.player_configs)
        return CreateGameResponse(game_id=state.id, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/games", response_model=list[str])
async def get_all_games():
    """List all active game IDs."""
    return list_games()


@router.get("/games/{game_id}", response_model=GameState)
async def get_game_state(game_id: str):
    """Get the current state of a game."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    return state


@router.delete("/games/{game_id}")
async def remove_game(game_id: str):
    """Delete a game."""
    if not delete_game(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    return {"status": "deleted"}


@router.post("/games/{game_id}/start")
async def start_game_endpoint(game_id: str):
    """Start a game after setup is complete."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    try:
        state = start_game(state)
        return {"status": "started", "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/games/{game_id}/assign-town")
async def assign_town(game_id: str, player_id: str, town_id: str):
    """Assign a starting town to a player during setup."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    try:
        state = assign_starting_town(state, player_id, town_id)
        return {"status": "assigned", "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/games/{game_id}/auto-assign-towns")
async def auto_assign_towns(game_id: str):
    """Auto-assign starting towns to all players."""
    from app.game.state import auto_assign_starting_towns
    
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    try:
        state = auto_assign_starting_towns(state)
        return {"status": "assigned", "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/games/{game_id}/income")
async def process_income(game_id: str):
    """Process income phase."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    engine = GameEngine(game_id)
    try:
        state = engine.process_income_phase()
        return {"status": "income_processed", "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/games/{game_id}/valid-actions/{player_id}", response_model=GetValidActionsResponse)
async def get_valid_actions(game_id: str, player_id: str):
    """Get valid actions for a player."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    engine = GameEngine(game_id)
    actions = engine.get_valid_actions(player_id)
    
    return GetValidActionsResponse(actions=actions)


@router.post("/games/{game_id}/action", response_model=PerformActionResponse)
async def perform_action(game_id: str, action: Action):
    """Perform a game action."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    engine = GameEngine(game_id)
    success, message, combat_result = engine.perform_action(action)
    
    return PerformActionResponse(
        success=success,
        message=message,
        state=engine.state,
        combat_result=combat_result,
    )


@router.get("/games/{game_id}/prestige")
async def get_prestige(game_id: str):
    """Get current prestige scores for all players."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    prestige = calculate_prestige(state)
    return {"prestige": prestige}


@router.get("/games/{game_id}/winner")
async def get_game_winner(game_id: str):
    """Get the winner if the game is over."""
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    winner = get_winner(state)
    if not winner:
        return {"winner": None, "game_over": False}
    
    return {
        "winner": winner.model_dump(),
        "game_over": True,
        "prestige": calculate_prestige(state),
    }


# ============ AI Simulation Endpoints ============

@router.post("/simulation/create")
async def create_simulation(config: SimulationConfig):
    """Create an AI-only simulation game."""
    try:
        state = create_game(config.player_configs)
        
        return {
            "game_id": state.id,
            "state": state,
            "speed_ms": config.speed_ms,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simulation/{game_id}/step")
async def simulation_step(game_id: str):
    """Execute one turn in a simulation."""
    from app.ai.manager import AIManager
    import traceback
    
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    engine = GameEngine(game_id)
    manager = AIManager()
    
    if engine.is_game_over():
        return {"status": "game_over", "state": state, "decision_log": None}
    
    # Get current player
    current_player = state.players[state.current_player_idx]
    
    # Have AI decide and perform action
    try:
        # Get valid actions from engine
        valid_actions = engine.get_valid_actions(current_player.id)
        
        # #region agent log
        import json as _json
        with open("/home/ilya/dev/kingdom/.cursor/debug.log", "a") as _f:
            _f.write(_json.dumps({"location":"routes.py:simulation_step:valid_actions","message":"Valid actions retrieved","data":{"player_id":current_player.id,"player_name":current_player.name,"action_count":len(valid_actions),"action_types":[a.action_type.value for a in valid_actions][:10]},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H2","runId":"500-debug"})+"\n")
        # #endregion
        
        if not valid_actions:
            return {"status": "no_action", "state": state, "decision_log": None}
        
        # Use AI manager to get appropriate AI player (falls back to SimpleAI if no API key)
        action, decision_log = await manager.get_ai_action(state, current_player)
        
        # #region agent log
        with open("/home/ilya/dev/kingdom/.cursor/debug.log", "a") as _f:
            _f.write(_json.dumps({"location":"routes.py:simulation_step:ai_action","message":"AI action decided","data":{"player_name":current_player.name,"action_type":action.action_type.value if action else None,"has_decision_log":decision_log is not None},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H3","runId":"500-debug"})+"\n")
        # #endregion
        
        if action:
            success, message, combat = engine.perform_action(action)
            
            # #region agent log
            with open("/home/ilya/dev/kingdom/.cursor/debug.log", "a") as _f:
                _f.write(_json.dumps({"location":"routes.py:simulation_step:action_performed","message":"Action performed","data":{"success":success,"message":message,"has_combat":combat is not None},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H4","runId":"500-debug"})+"\n")
            # #endregion
            
            return {
                "status": "action_performed",
                "action": action.model_dump(),
                "message": message,
                "state": engine.state,
                "combat_result": combat.model_dump() if combat else None,
                "decision_log": decision_log.model_dump() if decision_log else None,
            }
        else:
            return {"status": "no_action", "state": state, "decision_log": None}
    except Exception as e:
        # #region agent log
        import json as _json
        with open("/home/ilya/dev/kingdom/.cursor/debug.log", "a") as _f:
            _f.write(_json.dumps({"location":"routes.py:simulation_step:error","message":"Exception caught","data":{"error":str(e),"traceback":traceback.format_exc()},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H2,H3,H4,H5","runId":"500-debug"})+"\n")
        # #endregion
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation/{game_id}/run")
async def run_full_simulation(game_id: str, max_steps: int = 1000):
    """Run a full simulation until game over."""
    from app.ai.manager import AIManager
    
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    engine = GameEngine(game_id)
    manager = AIManager()
    
    steps = 0
    while not engine.is_game_over() and steps < max_steps:
        current_player = engine.state.players[engine.state.current_player_idx]
        
        try:
            action, _ = await manager.get_ai_action(engine.state, current_player)
            if action:
                engine.perform_action(action)
            steps += 1
        except Exception:
            break
    
    return {
        "status": "completed" if engine.is_game_over() else "max_steps_reached",
        "steps": steps,
        "state": engine.state,
        "winner": get_winner(engine.state).model_dump() if get_winner(engine.state) else None,
    }

