"""
config/settings.py
──────────────────
Central config loaded once at startup.
All agents and tools import from here — never from os.environ directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "ollama")
    MODEL_ID: str = os.getenv("MODEL_ID", "qwen2.5:3b")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Bedrock
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

    # Ollama
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    # SigV4 / AI Platform
    AI_ROLE_ARN:    str = os.getenv("AI_ROLE_ARN", "")
    AI_EXTERNAL_ID: str = os.getenv("AI_EXTERNAL_ID", "ai-pathfinder-kyc-test")
    AI_INVOKE_URL:  str = os.getenv("AI_INVOKE_URL", "")


settings = Settings()
