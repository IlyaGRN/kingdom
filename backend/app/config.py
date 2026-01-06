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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()



