"""
Application settings — loaded from environment / .env file.

See: docs/architecture/LLD_pipeline.md § 8
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- LLM (Anthropic Claude) ---
    anthropic_api_key: str = ""          # or set ANTHROPIC_API_KEY in env
    llm_model: str = "claude-haiku-4-5"  # Haiku for prototype speed/cost
    llm_temperature: float = 0.7
    llm_max_retries: int = 3

    # --- Blaxel ---
    use_blaxel: bool = False             # set True when Blaxel is configured
    blaxel_workspace: str = ""
    blaxel_api_key: str = ""
    blaxel_region: str = "us-pdx-1"

    # --- Pipeline Config ---
    num_analyst_agents: int = 5
    num_negotiation_rounds: int = 10
    num_decision_makers: int = 3
    top_k_recommendations: int = 3

    class Config:
        env_file = "backend/.env"
        extra = "ignore"


settings = Settings()
