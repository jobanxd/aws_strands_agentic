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

    elif provider == "aiplatform":
        from src.core.aiplatform_model import AIPlatformModel
        return AIPlatformModel(
            endpoint=settings.AI_PLATFORM_ENDPOINT,
            tenant_id=settings.TENANT_ID,
        )

    else:
        raise ValueError(
            f"Unknown MODEL_PROVIDER '{provider}'. "
            "Choose: bedrock | ollama | sigv4"
        )
