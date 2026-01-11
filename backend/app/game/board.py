"""Board topology and holding definitions."""
import json
from pathlib import Path
from app.models.schemas import Holding, HoldingType


def _load_positions() -> dict[str, dict[str, float]]:
    """Load holding positions from config file."""
    config_path = Path(__file__).parent.parent / "config" / "holding_positions.json"
    with open(config_path) as f:
        config = json.load(f)
    return config["holdings"]


def create_board() -> list[Holding]:
    """Create the game board with all holdings.
    
    Positions are loaded from config/holding_positions.json for easy adjustment.
    """
    positions = _load_positions()
    holdings = []
    
    def pos(holding_id: str) -> tuple[float, float]:
        """Get position for a holding from config."""
        p = positions[holding_id]
        return p["x"], p["y"]
    
    # ============ County X (Bottom Left Quadrant) ============
    holdings.extend([
        Holding(
            id="xandoria",
            name="Xandoria",
            holding_type=HoldingType.TOWN,
            county="X",
            duchy="XU",
            gold_value=1,
            soldier_value=400,
            defense_modifier=2,  # +2 dice when defending
            position_x=pos("xandoria")[0],
            position_y=pos("xandoria")[1],
        ),
        Holding(
            id="xelphane",
            name="Xelphane",
            holding_type=HoldingType.TOWN,
            county="X",
            duchy="XU",
            gold_value=5,
            soldier_value=200,
            defense_modifier=0,
            position_x=pos("xelphane")[0],
            position_y=pos("xelphane")[1],
        ),
        Holding(
            id="xythera",
            name="Xythera",
            holding_type=HoldingType.TOWN,
            county="X",
            duchy="XU",
            gold_value=3,
            soldier_value=300,
            defense_modifier=1,  # +1 dice when defending
            is_capitol=True,  # Capitol of County X
            position_x=pos("xythera")[0],
            position_y=pos("xythera")[1],
        ),
        Holding(
            id="x_castle",
            name="Castle X",
            holding_type=HoldingType.COUNTY_CASTLE,
            county="X",
            duchy="XU",
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,
            position_x=pos("x_castle")[0],
            position_y=pos("x_castle")[1],
        ),
    ])
    
    # ============ County U (Top Left Quadrant) ============
    holdings.extend([
        Holding(
            id="ulverin",
            name="Ulverin",
            holding_type=HoldingType.TOWN,
            county="U",
            duchy="XU",
            gold_value=5,
            soldier_value=200,
            defense_modifier=0,
            position_x=pos("ulverin")[0],
            position_y=pos("ulverin")[1],
        ),
        Holding(
            id="uldorwyn",
            name="Uldorwyn",
            holding_type=HoldingType.TOWN,
            county="U",
            duchy="XU",
            gold_value=4,
            soldier_value=300,
            defense_modifier=0,
            position_x=pos("uldorwyn")[0],
            position_y=pos("uldorwyn")[1],
        ),
        Holding(
            id="umbrith",
            name="Umbrith",
            holding_type=HoldingType.TOWN,
            county="U",
            duchy="XU",
            gold_value=2,
            soldier_value=400,
            defense_modifier=0,
            attack_modifier=1,  # +1 dice when attacking FROM this town
            is_capitol=True,  # Capitol of County U
            position_x=pos("umbrith")[0],
            position_y=pos("umbrith")[1],
        ),
        Holding(
            id="u_castle",
            name="Castle U",
            holding_type=HoldingType.COUNTY_CASTLE,
            county="U",
            duchy="XU",
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,
            position_x=pos("u_castle")[0],
            position_y=pos("u_castle")[1],
        ),
    ])
    
    # ============ County V (Top Right Quadrant) ============
    holdings.extend([
        Holding(
            id="valoria",
            name="Valoria",
            holding_type=HoldingType.TOWN,
            county="V",
            duchy="QV",
            gold_value=3,
            soldier_value=300,
            defense_modifier=1,  # +1 dice when defending
            is_capitol=True,  # Capitol of County V
            position_x=pos("valoria")[0],
            position_y=pos("valoria")[1],
        ),
        Holding(
            id="vardhelm",
            name="Vardhelm",
            holding_type=HoldingType.TOWN,
            county="V",
            duchy="QV",
            gold_value=5,
            soldier_value=200,
            defense_modifier=0,
            position_x=pos("vardhelm")[0],
            position_y=pos("vardhelm")[1],
        ),
        Holding(
            id="velthar",
            name="Velthar",
            holding_type=HoldingType.TOWN,
            county="V",
            duchy="QV",
            gold_value=1,
            soldier_value=500,
            defense_modifier=2,  # +2 dice when defending
            position_x=pos("velthar")[0],
            position_y=pos("velthar")[1],
        ),
        Holding(
            id="v_castle",
            name="Castle V",
            holding_type=HoldingType.COUNTY_CASTLE,
            county="V",
            duchy="QV",
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,
            position_x=pos("v_castle")[0],
            position_y=pos("v_castle")[1],
        ),
    ])
    
    # ============ County Q (Bottom Right Quadrant) ============
    holdings.extend([
        Holding(
            id="quindara",
            name="Quindara",
            holding_type=HoldingType.TOWN,
            county="Q",
            duchy="QV",
            gold_value=10,
            soldier_value=100,
            defense_modifier=-2,  # -2 dice when defending (weak walls)
            is_capitol=True,  # Capitol of County Q
            position_x=pos("quindara")[0],
            position_y=pos("quindara")[1],
        ),
        Holding(
            id="qyrelis",
            name="Qyrelis",
            holding_type=HoldingType.TOWN,
            county="Q",
            duchy="QV",
            gold_value=4,
            soldier_value=300,
            defense_modifier=0,
            position_x=pos("qyrelis")[0],
            position_y=pos("qyrelis")[1],
        ),
        Holding(
            id="quorwyn",
            name="Quorwyn",
            holding_type=HoldingType.TOWN,
            county="Q",
            duchy="QV",
            gold_value=5,
            soldier_value=200,
            defense_modifier=0,
            position_x=pos("quorwyn")[0],
            position_y=pos("quorwyn")[1],
        ),
        Holding(
            id="q_castle",
            name="Castle Q",
            holding_type=HoldingType.COUNTY_CASTLE,
            county="Q",
            duchy="QV",
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,
            position_x=pos("q_castle")[0],
            position_y=pos("q_castle")[1],
        ),
    ])
    
    # ============ Duchy Castles ============
    holdings.extend([
        Holding(
            id="xu_castle",
            name="Duchy Castle XU",
            holding_type=HoldingType.DUCHY_CASTLE,
            duchy="XU",
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,
            position_x=pos("xu_castle")[0],
            position_y=pos("xu_castle")[1],
        ),
        Holding(
            id="qv_castle",
            name="Duchy Castle QV",
            holding_type=HoldingType.DUCHY_CASTLE,
            duchy="QV",
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,
            position_x=pos("qv_castle")[0],
            position_y=pos("qv_castle")[1],
        ),
    ])
    
    # ============ King's Castle (Center) ============
    holdings.append(
        Holding(
            id="king_castle",
            name="King's Castle",
            holding_type=HoldingType.KING_CASTLE,
            gold_value=0,
            soldier_value=0,
            defense_modifier=0,  # King wins ties when defending
            position_x=pos("king_castle")[0],
            position_y=pos("king_castle")[1],
        )
    )
    
    return holdings


# Board adjacency map - which holdings connect to which
ADJACENCY: dict[str, list[str]] = {
    # County X (Bottom Left) - all towns connect to county castle
    "xandoria": ["xelphane", "xythera", "x_castle"],
    "xelphane": ["xandoria", "xythera", "x_castle"],
    "xythera": ["xandoria", "xelphane", "x_castle"],
    "x_castle": ["xandoria", "xelphane", "xythera", "xu_castle"],
    
    # County U (Top Left) - all towns connect to county castle
    "ulverin": ["uldorwyn", "umbrith", "u_castle"],
    "uldorwyn": ["ulverin", "umbrith", "u_castle"],
    "umbrith": ["ulverin", "uldorwyn", "u_castle"],
    "u_castle": ["ulverin", "uldorwyn", "umbrith", "xu_castle"],
    
    # County V (Top Right) - all towns connect to county castle
    "valoria": ["vardhelm", "velthar", "v_castle"],
    "vardhelm": ["valoria", "velthar", "v_castle"],
    "velthar": ["valoria", "vardhelm", "v_castle"],
    "v_castle": ["valoria", "vardhelm", "velthar", "qv_castle"],
    
    # County Q (Bottom Right) - all towns connect to county castle
    "quindara": ["qyrelis", "quorwyn", "q_castle"],
    "qyrelis": ["quindara", "quorwyn", "q_castle"],
    "quorwyn": ["quindara", "qyrelis", "q_castle"],
    "q_castle": ["quindara", "qyrelis", "quorwyn", "qv_castle"],
    
    # Duchy Castles connect to their county castles and king
    "xu_castle": ["x_castle", "u_castle", "king_castle"],
    "qv_castle": ["v_castle", "q_castle", "king_castle"],
    
    # King's Castle connects to both duchy castles
    "king_castle": ["xu_castle", "qv_castle"],
}


def get_adjacent_holdings(holding_id: str) -> list[str]:
    """Get IDs of holdings adjacent to the given holding."""
    return ADJACENCY.get(holding_id, [])


def get_holdings_in_county(county: str) -> list[str]:
    """Get all holding IDs in a county (including castle)."""
    county_holdings = {
        "X": ["xandoria", "xelphane", "xythera", "x_castle"],
        "U": ["ulverin", "uldorwyn", "umbrith", "u_castle"],
        "V": ["valoria", "vardhelm", "velthar", "v_castle"],
        "Q": ["quindara", "qyrelis", "quorwyn", "q_castle"],
    }
    return county_holdings.get(county, [])


def get_towns_in_county(county: str) -> list[str]:
    """Get town IDs in a county (excluding castle)."""
    towns = {
        "X": ["xandoria", "xelphane", "xythera"],
        "U": ["ulverin", "uldorwyn", "umbrith"],
        "V": ["valoria", "vardhelm", "velthar"],
        "Q": ["quindara", "qyrelis", "quorwyn"],
    }
    return towns.get(county, [])


def get_holdings_in_duchy(duchy: str) -> list[str]:
    """Get all holding IDs in a duchy."""
    duchy_holdings = {
        "XU": ["xandoria", "xelphane", "xythera", "x_castle",
               "ulverin", "uldorwyn", "umbrith", "u_castle", "xu_castle"],
        "QV": ["valoria", "vardhelm", "velthar", "v_castle",
               "quindara", "qyrelis", "quorwyn", "q_castle", "qv_castle"],
    }
    return duchy_holdings.get(duchy, [])


def get_county_castle(county: str) -> str:
    """Get the castle ID for a county."""
    return f"{county.lower()}_castle"


def get_duchy_castle(duchy: str) -> str:
    """Get the duchy castle ID."""
    return f"{duchy.lower()}_castle"


def get_counties_in_duchy(duchy: str) -> list[str]:
    """Get counties that make up a duchy."""
    duchy_counties = {
        "XU": ["X", "U"],
        "QV": ["Q", "V"],
    }
    return duchy_counties.get(duchy, [])


def get_all_towns() -> list[str]:
    """Get all town IDs on the board."""
    return [
        "xandoria", "xelphane", "xythera",
        "ulverin", "uldorwyn", "umbrith",
        "valoria", "vardhelm", "velthar",
        "quindara", "qyrelis", "quorwyn",
    ]


def get_town_county(town_id: str) -> str | None:
    """Get the county a town belongs to."""
    for county in ["X", "U", "V", "Q"]:
        if town_id in get_towns_in_county(county):
            return county
    return None


# Capitol towns for each county
CAPITOLS: dict[str, str] = {
    "X": "xythera",
    "U": "umbrith",
    "V": "valoria",
    "Q": "quindara",
}


def get_capitol_for_county(county: str) -> str | None:
    """Get the capitol town ID for a county."""
    return CAPITOLS.get(county)
