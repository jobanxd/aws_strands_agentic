"""
core/model_factory.py
────────────────────────
Returns the correct Strands model object based on MODEL_PROVIDER in .env.
Add a new provider here without touching any agent code.
"""

from src.core.settings import settings


def get_model():
    """
    Factory that returns the configured Strands model provider.
    Agents call this instead of hardcoding a provider.
    """
    provider = settings.MODEL_PROVIDER.lower()

    if provider == "bedrock":
        from strands.models import BedrockModel
        return BedrockModel(
            model_id=settings.MODEL_ID,
            region_name=settings.AWS_REGION,
            max_tokens=settings.MAX_TOKENS,
        )

    elif provider == "ollama":
        from strands.models.ollama import OllamaModel
        return OllamaModel(
            host=settings.OLLAMA_HOST,
            model_id=settings.MODEL_ID,
        )

    elif provider == "sigv4":
        from src.core.sigv4_model import SigV4Model
        return SigV4Model(
            model_id=settings.MODEL_ID,
            invoke_url=settings.AI_INVOKE_URL,
            region=settings.AWS_REGION,
        )

    else:
        raise ValueError(
            f"Unknown MODEL_PROVIDER '{provider}'. "
            "Choose: bedrock | ollama | sigv4"
        )
