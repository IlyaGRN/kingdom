"""Application configuration."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    xai_api_key: str = ""
    
    # Database
    database_url: str = "sqlite:///./kingdom.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Game Settings
    # Starting town selection mode:
    # - "random": Players get random towns (original behavior)
    # - "fixed": Players get predetermined towns (5-gold towns, one per county)
    starting_town_mode: Literal["random", "fixed"] = "fixed"
    
    # Fixed starting towns (one per county, each has 5 gold value)
    # Order: Player 1 -> Xelphane (X), Player 2 -> Ulverin (U), 
    #        Player 3 -> Vardhelm (V), Player 4 -> Quorwyn (Q)
    fixed_starting_towns: list[str] = ["xelphane", "ulverin", "vardhelm", "quorwyn"]
    
    # Card Deck Configuration - quantities per card type
    # Personal Events (instant effects)
    card_gold_5: int = 4       # Gold Chest (5) - gain 5 gold
    card_gold_10: int = 4      # Gold Chest (10) - gain 10 gold
    card_gold_15: int = 3      # Gold Chest (15) - gain 15 gold
    card_gold_25: int = 3      # Gold Chest (25) - gain 25 gold
    card_soldiers_100: int = 0 # Soldiers (100) - gain 100 soldiers
    card_soldiers_200: int = 0 # Soldiers (200) - gain 200 soldiers
    card_soldiers_300: int = 0 # Soldiers (300) - gain 300 soldiers
    card_raiders: int = 3      # Raiders - lose all income this turn
    
    # Global Events (instant effects, affect all players)
    card_crusade: int = 1      # Crusade - all players lose half gold and soldiers
    
    # Bonus Cards (player chooses when to use)
    card_big_war: int = 3           # Double army cap until next war
    card_adventurer: int = 0       # Buy 500 soldiers for 25 gold above cap
    card_excalibur: int = 3         # Roll twice, take higher
    card_poisoned_arrows: int = 3   # Halve opponent's dice
    card_forbid_mercenaries: int = 0  # No soldier purchases for one turn
    card_talented_commander: int = 4  # No soldier loss when winning
    card_vassal_revolt: int = 3     # Higher tier can attack vassals
    card_enforce_peace: int = 3     # No wars for one turn
    card_duel: int = 1              # Army-less single-dice fight
    card_spy: int = 0               # View cards or reorder deck
    
    # Claim Cards (establish claims on territories)
    card_claim_x: int = 7      # Claim on County X towns
    card_claim_u: int = 7      # Claim on County U towns
    card_claim_v: int = 7      # Claim on County V towns
    card_claim_q: int = 7      # Claim on County Q towns
    card_ultimate_claim: int = 0  # Claim any town or title
    card_duchy_claim: int = 0     # Claim any town or Duke+ title
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()



