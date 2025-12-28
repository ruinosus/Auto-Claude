"""
Cross-Encoder / Reranker Provider
==================================

Cross-encoder/reranker for improved search quality.
Supports multiple providers: Azure OpenAI, OpenAI, Ollama, Google.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from graphiti_config import GraphitiConfig

logger = logging.getLogger(__name__)


def create_cross_encoder(
    config: "GraphitiConfig", llm_client: Any = None
) -> Any | None:
    """
    Create a cross-encoder/reranker for improved search quality.

    Args:
        config: GraphitiConfig with provider settings
        llm_client: Optional LLM client for reranking (required for some providers)

    Returns:
        Cross-encoder instance, or None if not available
    """
    provider = config.llm_provider

    if provider == "azure_openai":
        return _create_azure_openai_cross_encoder(config)
    elif provider == "openai":
        return _create_openai_cross_encoder(config)
    elif provider == "ollama":
        return _create_ollama_cross_encoder(config, llm_client)
    elif provider == "google":
        return _create_google_cross_encoder(config)
    else:
        # For other providers (anthropic, openrouter), return None
        # graphiti-core will handle this gracefully
        logger.debug(f"No cross-encoder available for provider: {provider}")
        return None


def _create_azure_openai_cross_encoder(config: "GraphitiConfig") -> Any | None:
    """Create Azure OpenAI cross-encoder/reranker."""
    try:
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )
        from openai import AsyncOpenAI
    except ImportError:
        logger.debug("Azure OpenAI cross-encoder not available (missing packages)")
        return None

    if not config.azure_openai_api_key or not config.azure_openai_base_url:
        logger.warning("Azure OpenAI cross-encoder requires API key and base URL")
        return None

    try:
        # Create Azure client using OpenAI-compatible endpoint
        # Azure OpenAI v1 API: base_url should end with /openai/v1/
        base_url = config.azure_openai_base_url.rstrip("/")
        if not base_url.endswith("/openai/v1"):
            base_url = f"{base_url}/openai/v1/"

        azure_client = AsyncOpenAI(
            base_url=base_url,
            api_key=config.azure_openai_api_key,
        )

        # Pass the Azure client directly - OpenAIRerankerClient accepts AsyncOpenAI
        return OpenAIRerankerClient(client=azure_client)

    except Exception as e:
        logger.warning(f"Could not create Azure OpenAI cross-encoder: {e}")
        return None


def _create_openai_cross_encoder(config: "GraphitiConfig") -> Any | None:
    """Create OpenAI cross-encoder/reranker."""
    try:
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )
        from graphiti_core.llm_client.config import LLMConfig
    except ImportError:
        logger.debug("OpenAI cross-encoder not available (missing packages)")
        return None

    if not config.openai_api_key:
        logger.warning("OpenAI cross-encoder requires OPENAI_API_KEY")
        return None

    try:
        llm_config = LLMConfig(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )
        return OpenAIRerankerClient(config=llm_config)

    except Exception as e:
        logger.warning(f"Could not create OpenAI cross-encoder: {e}")
        return None


def _create_ollama_cross_encoder(
    config: "GraphitiConfig", llm_client: Any = None
) -> Any | None:
    """Create Ollama cross-encoder/reranker."""
    if llm_client is None:
        logger.debug("Ollama cross-encoder requires llm_client")
        return None

    try:
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )
        from graphiti_core.llm_client.config import LLMConfig
    except ImportError:
        logger.debug("Ollama cross-encoder not available (missing packages)")
        return None

    try:
        # Create LLM config for reranker
        base_url = config.ollama_base_url
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        llm_config = LLMConfig(
            api_key="ollama",
            model=config.ollama_llm_model,
            base_url=base_url,
        )

        return OpenAIRerankerClient(client=llm_client, config=llm_config)

    except Exception as e:
        logger.warning(f"Could not create Ollama cross-encoder: {e}")
        return None


def _create_google_cross_encoder(config: "GraphitiConfig") -> Any | None:
    """Create Google Gemini cross-encoder/reranker."""
    try:
        from graphiti_core.cross_encoder.gemini_reranker_client import (
            GeminiRerankerClient,
        )
        from graphiti_core.llm_client.config import LLMConfig
    except ImportError:
        logger.debug("Google cross-encoder not available (missing packages)")
        return None

    if not config.google_api_key:
        logger.warning("Google cross-encoder requires GOOGLE_API_KEY")
        return None

    try:
        llm_config = LLMConfig(
            api_key=config.google_api_key,
            model=config.google_llm_model,
        )
        return GeminiRerankerClient(config=llm_config)

    except Exception as e:
        logger.warning(f"Could not create Google cross-encoder: {e}")
        return None
