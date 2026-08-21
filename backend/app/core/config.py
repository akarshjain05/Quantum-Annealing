from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NostroQ"
    APP_TAGLINE: str = "Quantum-Ready Liquidity Intelligence for Cross-Border Corridors"
    ENV: str = "development"

    # Auth
    SECRET_KEY: str = "dev-only-secret-CHANGE-ME-before-any-real-deployment"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # Database - defaults to SQLite for zero-friction local/demo use.
    # Point DATABASE_URL at Postgres for production, e.g.:
    #   postgresql+psycopg2://nostroq:nostroq@localhost:5432/nostroq
    DATABASE_URL: str = "sqlite:///./nostroq.db"

    # Optional LLM enhancement for the agent's natural-language phrasing.
    # The agent is fully functional with NONE of these set (see app/agent/orchestrator.py) -
    # tool selection, retrieval, and explanation are deterministic and template-driven.
    LLM_PROVIDER: Optional[str] = None  # "anthropic" | "openai" | "gemini" | None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    DEMO_MODE: bool = True
    RANDOM_SEED: int = 42

    # Version tags recorded on every optimization run for reproducibility (spec §34)
    MODEL_VERSION: str = "0.1.0"
    QUBO_VERSION: str = "1.0.0"
    FORECAST_VERSION: str = "1.0.0"
    KNOWLEDGE_VERSION: str = "1.0.0"
    AGENT_VERSION: str = "0.1.0"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
