"""
Dynamic LLM pricing provider using models.dev API.

Provides accurate, community-maintained pricing data for all LLM providers
with local caching and graceful fallback to .env configuration.
"""

import os
import json
from typing import Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

# Optional aiohttp import - pricing will use fallback if not available
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False


@dataclass
class ModelPricing:
    """Pricing information for a specific LLM model."""

    model_id: str
    provider: str
    input_price: float  # USD per 1M tokens
    output_price: float  # USD per 1M tokens
    cache_read_price: float  # USD per 1M tokens
    cache_write_price: float  # USD per 1M tokens
    context_limit: int
    output_limit: int
    last_updated: datetime

    @property
    def cache_read_discount(self) -> float:
        """Calculate cache read discount percentage."""
        if self.input_price == 0:
            return 0.0
        return 1.0 - (self.cache_read_price / self.input_price)

    @property
    def cache_write_multiplier(self) -> float:
        """Calculate cache write premium multiplier."""
        if self.input_price == 0:
            return 1.0
        return self.cache_write_price / self.input_price


class ModelsPricingProvider:
    """
    Fetch pricing from models.dev API with local caching and .env fallback.

    Strategy:
    1. Check local cache (24h TTL)
    2. Fetch from models.dev API
    3. Fallback to .env if API unavailable
    4. Cache successful API responses
    """

    API_URL = "https://models.dev/api.json"
    CACHE_FILE = ".auto-claude/models_dev_cache.json"
    CACHE_TTL = timedelta(hours=24)

    def __init__(self):
        self.cache_path = Path(self.CACHE_FILE)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Optional[Dict] = None
        self._load_cache()

    def _load_cache(self):
        """Load pricing cache from disk."""
        if not self.cache_path.exists():
            return

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            # Check if cache is expired
            cached_at = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
            if datetime.utcnow() - cached_at < self.CACHE_TTL:
                self._cache = data.get('data')
        except Exception as e:
            print(f"[ModelsPricingProvider] Cache load failed: {e}")

    def _save_cache(self, data: Dict):
        """Save pricing data to cache."""
        try:
            cache_data = {
                'cached_at': datetime.utcnow().isoformat(),
                'data': data
            }
            with open(self.cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            self._cache = data
        except Exception as e:
            print(f"[ModelsPricingProvider] Cache save failed: {e}")

    async def _fetch_from_api(self) -> Optional[Dict]:
        """Fetch pricing data from models.dev API."""
        if not AIOHTTP_AVAILABLE:
            # aiohttp not installed, skip API fetch
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._save_cache(data)
                        return data
        except Exception as e:
            print(f"[ModelsPricingProvider] API fetch failed: {e}")

        return None

    def _get_env_pricing(self, model_id: str) -> Optional[ModelPricing]:
        """Fallback to .env pricing configuration."""
        # Normalize model ID (claude-sonnet-4-5-20250929 -> claude-sonnet-4-5)
        normalized = self._normalize_model_id(model_id)

        # Map to env var prefix
        env_prefix = None
        if 'sonnet' in normalized.lower():
            env_prefix = 'CLAUDE_SONNET_4_5'
        elif 'haiku' in normalized.lower():
            env_prefix = 'CLAUDE_HAIKU_4_5'
        elif 'opus' in normalized.lower():
            env_prefix = 'CLAUDE_OPUS_4_5'
        else:
            return None

        # Read from .env
        input_price = float(os.getenv(f'{env_prefix}_INPUT_PRICE', 0))
        output_price = float(os.getenv(f'{env_prefix}_OUTPUT_PRICE', 0))
        cache_read_discount = float(os.getenv('CACHE_READ_DISCOUNT', 0.9))
        cache_write_multiplier = float(os.getenv('CACHE_CREATION_MULTIPLIER', 1.25))

        if input_price == 0 or output_price == 0:
            return None

        return ModelPricing(
            model_id=model_id,
            provider='anthropic',
            input_price=input_price,
            output_price=output_price,
            cache_read_price=input_price * cache_read_discount,
            cache_write_price=input_price * cache_write_multiplier,
            context_limit=200000,  # Default
            output_limit=64000,    # Default
            last_updated=datetime.utcnow()
        )

    def _normalize_model_id(self, model_id: str) -> str:
        """
        Normalize model ID for matching.

        Examples:
        - claude-sonnet-4-5-20250929 -> claude-sonnet-4-5
        - claude-3-5-sonnet-20241022 -> claude-sonnet-3-5
        """
        # Remove date stamps (8 digits at end)
        parts = model_id.split('-')
        if len(parts) > 0 and parts[-1].isdigit() and len(parts[-1]) == 8:
            normalized = '-'.join(parts[:-1])
        else:
            normalized = model_id

        return normalized

    async def get_pricing(self, model_id: str) -> ModelPricing:
        """
        Get pricing for a specific model.

        Priority:
        1. Local cache (if fresh)
        2. models.dev API
        3. .env fallback
        4. Default Sonnet pricing (ultimate fallback)
        """
        # 1. Try cache
        if self._cache:
            pricing = self._extract_pricing_from_data(self._cache, model_id)
            if pricing:
                return pricing

        # 2. Try API
        api_data = await self._fetch_from_api()
        if api_data:
            pricing = self._extract_pricing_from_data(api_data, model_id)
            if pricing:
                return pricing

        # 3. Fallback to .env
        env_pricing = self._get_env_pricing(model_id)
        if env_pricing:
            print(f"[ModelsPricingProvider] Using .env pricing for {model_id}")
            return env_pricing

        # 4. Ultimate fallback (use default Sonnet pricing)
        print(f"[ModelsPricingProvider] WARNING: No pricing found for {model_id}, using default Sonnet pricing")
        return ModelPricing(
            model_id=model_id,
            provider='anthropic',
            input_price=3.0,
            output_price=15.0,
            cache_read_price=0.3,
            cache_write_price=3.75,
            context_limit=200000,
            output_limit=64000,
            last_updated=datetime.utcnow()
        )

    def _extract_pricing_from_data(
        self,
        data: Dict,
        model_id: str
    ) -> Optional[ModelPricing]:
        """Extract pricing for specific model from models.dev data."""
        # Try exact match first
        for provider_id, provider_data in data.items():
            if not isinstance(provider_data, dict):
                continue

            models = provider_data.get('models', {})
            if model_id in models:
                return self._parse_model_data(
                    model_id,
                    provider_id,
                    models[model_id]
                )

        # Try normalized match
        normalized = self._normalize_model_id(model_id)
        for provider_id, provider_data in data.items():
            if not isinstance(provider_data, dict):
                continue

            models = provider_data.get('models', {})
            for model_data_id, model_data in models.items():
                if self._normalize_model_id(model_data_id) == normalized:
                    return self._parse_model_data(
                        model_id,
                        provider_id,
                        model_data
                    )

        return None

    def _parse_model_data(
        self,
        model_id: str,
        provider: str,
        model_data: Dict
    ) -> ModelPricing:
        """Parse models.dev model data into ModelPricing."""
        cost = model_data.get('cost', {})
        limit = model_data.get('limit', {})

        return ModelPricing(
            model_id=model_id,
            provider=provider,
            input_price=cost.get('input', 0.0),
            output_price=cost.get('output', 0.0),
            cache_read_price=cost.get('cache_read', 0.0),
            cache_write_price=cost.get('cache_write', 0.0),
            context_limit=limit.get('context', 200000),
            output_limit=limit.get('output', 64000),
            last_updated=datetime.utcnow()
        )

    async def refresh_cache(self):
        """Force refresh cache from API."""
        print("[ModelsPricingProvider] Refreshing pricing cache...")
        await self._fetch_from_api()


# Singleton instance
_pricing_provider: Optional[ModelsPricingProvider] = None


def get_pricing_provider() -> ModelsPricingProvider:
    """Get global pricing provider instance."""
    global _pricing_provider
    if _pricing_provider is None:
        _pricing_provider = ModelsPricingProvider()
    return _pricing_provider


async def get_model_pricing(model_id: str) -> ModelPricing:
    """Convenience function to get model pricing."""
    provider = get_pricing_provider()
    return await provider.get_pricing(model_id)
