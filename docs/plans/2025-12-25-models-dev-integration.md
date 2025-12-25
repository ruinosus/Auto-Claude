# Models.dev Integration - Dynamic Pricing Provider

**Date:** 2025-12-25
**Addendum to:** Token Tracking & ROI System Design

---

## Overview

Integrate [models.dev](https://models.dev) API for dynamic, community-maintained LLM pricing data instead of hardcoded values in `.env`.

**Benefits:**
- ✅ **Auto-updated pricing** - Community maintains pricing, zero manual work
- ✅ **Multi-provider support** - Ready for OpenAI, Google, etc. when needed
- ✅ **Always accurate** - Pricing updated when providers change rates
- ✅ **Fallback safety** - Falls back to `.env` if API unavailable
- ✅ **Validation layer** - Compare our calculations vs. models.dev data

---

## Models.dev API Structure

### Endpoint
```bash
curl https://models.dev/api.json
```

### Response Format

```json
{
  "anthropic": {
    "id": "anthropic",
    "name": "Anthropic",
    "api": "https://api.anthropic.com/v1",
    "doc": "https://docs.anthropic.com/en/docs/about-claude/models",
    "models": {
      "claude-sonnet-4-5-20250929": {
        "id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "family": "claude-sonnet",
        "cost": {
          "input": 3.0,          // USD per 1M tokens
          "output": 15.0,         // USD per 1M tokens
          "cache_read": 0.3,      // USD per 1M tokens (90% discount)
          "cache_write": 3.75     // USD per 1M tokens (25% premium)
        },
        "limit": {
          "context": 200000,
          "output": 64000
        },
        "attachment": true,
        "reasoning": true,
        "tool_call": true,
        "knowledge": "2025-07-31"
      },
      "claude-haiku-4-5-20251001": {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku 4.5",
        "cost": {
          "input": 1.0,
          "output": 5.0,
          "cache_read": 0.1,
          "cache_write": 1.25
        },
        "limit": {
          "context": 200000,
          "output": 64000
        }
      },
      "claude-opus-4-5-20251101": {
        "id": "claude-opus-4-5-20251101",
        "name": "Claude Opus 4.5",
        "cost": {
          "input": 5.0,
          "output": 25.0,
          "cache_read": 0.5,
          "cache_write": 6.25
        },
        "limit": {
          "context": 200000,
          "output": 64000
        }
      }
    }
  }
}
```

---

## Implementation

### Module: `auto-claude/analytics/pricing_provider.py`

```python
import os
import json
import aiohttp
from typing import Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ModelPricing:
    """Pricing information for a specific model."""
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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=10) as response:
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
        if 'sonnet' in normalized:
            env_prefix = 'CLAUDE_SONNET'
        elif 'haiku' in normalized:
            env_prefix = 'CLAUDE_HAIKU'
        elif 'opus' in normalized:
            env_prefix = 'CLAUDE_OPUS'
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
        # Remove date stamps
        normalized = model_id.rsplit('-', 1)[0] if model_id.count('-') >= 3 else model_id

        # Standardize version format (claude-3-5-sonnet -> claude-sonnet-3-5)
        if normalized.startswith('claude-'):
            parts = normalized.split('-')
            if len(parts) >= 4 and parts[1].isdigit():
                # claude-3-5-sonnet -> claude-sonnet-3-5
                version = f"{parts[1]}-{parts[2]}"
                family = parts[3]
                normalized = f"claude-{family}-{version}"

        return normalized

    async def get_pricing(self, model_id: str) -> ModelPricing:
        """
        Get pricing for a specific model.

        Priority:
        1. Local cache (if fresh)
        2. models.dev API
        3. .env fallback
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
```

---

## Integration with UsageTracker

### Modified `usage_tracker.py`

```python
from auto_claude.analytics.pricing_provider import get_model_pricing

class UsageTracker:
    # ... existing code ...

    async def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int
    ) -> float:
        """Calculate cost in USD using models.dev pricing."""
        # Fetch pricing (cached or from API)
        pricing = await get_model_pricing(model)

        # Calculate costs (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing.input_price
        output_cost = (output_tokens / 1_000_000) * pricing.output_price
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.cache_read_price
        cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing.cache_write_price

        total = input_cost + output_cost + cache_read_cost + cache_write_cost

        # Log pricing source for debugging
        if pricing.last_updated < datetime.utcnow() - timedelta(hours=24):
            print(f"[UsageTracker] WARNING: Pricing for {model} is outdated (last updated: {pricing.last_updated})")

        return total
```

---

## Configuration

### Updated `.env` (Fallback Values)

```bash
# ===== PRICING PROVIDER =====

# models.dev integration (enabled by default)
USE_MODELS_DEV=true
MODELS_DEV_CACHE_TTL_HOURS=24

# Fallback pricing (used if models.dev API unavailable)
# These values should match models.dev data as of 2025-12-25
CLAUDE_SONNET_4_5_INPUT_PRICE=3.00
CLAUDE_SONNET_4_5_OUTPUT_PRICE=15.00
CLAUDE_HAIKU_4_5_INPUT_PRICE=1.00
CLAUDE_HAIKU_4_5_OUTPUT_PRICE=5.00
CLAUDE_OPUS_4_5_INPUT_PRICE=5.00
CLAUDE_OPUS_4_5_OUTPUT_PRICE=25.00

# Cache pricing (used for fallback calculations)
CACHE_READ_DISCOUNT=0.9  # 90% discount
CACHE_CREATION_MULTIPLIER=1.25  # 25% premium
```

---

## CLI Commands

### Pricing Management

```bash
# View current pricing for a model
python auto-claude/run.py --pricing claude-sonnet-4-5-20250929

# Output:
# Model: claude-sonnet-4-5-20250929
# Provider: anthropic
# Input: $3.00 / 1M tokens
# Output: $15.00 / 1M tokens
# Cache Read: $0.30 / 1M tokens (90% discount)
# Cache Write: $3.75 / 1M tokens (25% premium)
# Source: models.dev API (cached)
# Last Updated: 2025-12-25 10:30:00 UTC

# Refresh pricing cache
python auto-claude/run.py --refresh-pricing

# Output:
# Refreshing pricing cache from models.dev...
# ✓ Fetched pricing for 500+ models
# ✓ Cache updated: .auto-claude/models_dev_cache.json
# ✓ Cache valid until: 2025-12-26 10:30:00 UTC

# Compare pricing sources
python auto-claude/run.py --compare-pricing claude-sonnet-4-5

# Output:
# Comparing pricing for claude-sonnet-4-5:
#
# models.dev API:
#   Input: $3.00 / 1M tokens
#   Output: $15.00 / 1M tokens
#
# .env Fallback:
#   Input: $3.00 / 1M tokens
#   Output: $15.00 / 1M tokens
#
# Status: ✓ Pricing sources match

# List all available models
python auto-claude/run.py --list-models --provider anthropic

# Output:
# Anthropic Models (20 models):
# - claude-sonnet-4-5-20250929 ($3/$15 per 1M tokens)
# - claude-haiku-4-5-20251001 ($1/$5 per 1M tokens)
# - claude-opus-4-5-20251101 ($5/$25 per 1M tokens)
# ...
```

---

## Python API

```python
from auto_claude.analytics.pricing_provider import get_model_pricing, get_pricing_provider

# Get pricing for specific model
pricing = await get_model_pricing('claude-sonnet-4-5-20250929')

print(f"Input: ${pricing.input_price} / 1M tokens")
print(f"Output: ${pricing.output_price} / 1M tokens")
print(f"Cache Read Discount: {pricing.cache_read_discount * 100}%")

# Refresh cache manually
provider = get_pricing_provider()
await provider.refresh_cache()

# Calculate cost for specific usage
cost = (1000 / 1_000_000) * pricing.input_price + (500 / 1_000_000) * pricing.output_price
print(f"Cost for 1000 input + 500 output tokens: ${cost:.6f}")
```

---

## Benefits Summary

### 1. Zero Manual Pricing Updates
- Community maintains pricing on models.dev
- We automatically get updates
- No need to watch Anthropic pricing page

### 2. Multi-Provider Ready
- models.dev has 40+ providers (OpenAI, Google, Cohere, etc.)
- When Auto-Claude adds new LLM support, pricing is already there
- Zero additional code needed

### 3. Accurate Cost Tracking
- Always using latest pricing
- Community validates pricing changes
- Catch pricing increases immediately

### 4. Validation Layer
- Compare our calculations with models.dev data
- Alert if divergences (possible bugs)
- Confidence in cost accuracy

### 5. Graceful Degradation
- Cache lasts 24 hours (works offline)
- Falls back to .env if API unavailable
- Ultimate fallback to default Sonnet pricing
- Never breaks, always works

---

## Testing

### Unit Tests

```python
# test_pricing_provider.py

import pytest
from auto_claude.analytics.pricing_provider import ModelsPricingProvider, get_model_pricing

@pytest.mark.asyncio
async def test_fetch_from_api():
    """Test API fetching works."""
    provider = ModelsPricingProvider()
    data = await provider._fetch_from_api()

    assert data is not None
    assert 'anthropic' in data
    assert 'models' in data['anthropic']

@pytest.mark.asyncio
async def test_get_pricing_sonnet():
    """Test getting Sonnet pricing."""
    pricing = await get_model_pricing('claude-sonnet-4-5-20250929')

    assert pricing.model_id == 'claude-sonnet-4-5-20250929'
    assert pricing.provider == 'anthropic'
    assert pricing.input_price == 3.0
    assert pricing.output_price == 15.0
    assert pricing.cache_read_price == 0.3
    assert pricing.cache_write_price == 3.75

@pytest.mark.asyncio
async def test_fallback_to_env(monkeypatch):
    """Test fallback to .env when API fails."""
    # Mock API to fail
    async def mock_fetch_fail(self):
        return None

    monkeypatch.setattr(ModelsPricingProvider, '_fetch_from_api', mock_fetch_fail)

    # Set env vars
    monkeypatch.setenv('CLAUDE_SONNET_INPUT_PRICE', '3.0')
    monkeypatch.setenv('CLAUDE_SONNET_OUTPUT_PRICE', '15.0')

    pricing = await get_model_pricing('claude-sonnet-4-5-20250929')

    assert pricing.input_price == 3.0
    assert pricing.output_price == 15.0

@pytest.mark.asyncio
async def test_cache_persistence():
    """Test pricing cache persists to disk."""
    provider = ModelsPricingProvider()

    # Fetch from API (will cache)
    pricing1 = await provider.get_pricing('claude-sonnet-4-5')

    # Create new provider instance (should load from cache)
    provider2 = ModelsPricingProvider()
    assert provider2._cache is not None

    # Should return cached pricing without API call
    pricing2 = await provider2.get_pricing('claude-sonnet-4-5')

    assert pricing1.input_price == pricing2.input_price
```

---

## Migration Plan

### Phase 1: Add Provider (Week 1)
- Implement `pricing_provider.py`
- Add CLI commands
- Write tests

### Phase 2: Integrate with UsageTracker (Week 1)
- Modify `_calculate_cost()` to use provider
- Add pricing source logging
- Test end-to-end

### Phase 3: Validation (Week 2)
- Compare existing .env pricing vs. models.dev
- Alert on divergences
- Update .env to match models.dev

### Phase 4: Production (Week 2)
- Deploy with feature flag `USE_MODELS_DEV=true`
- Monitor for issues
- Full rollout

---

## Maintenance

### Monitoring
- Log pricing source (API vs. cache vs. .env)
- Alert when cache expires
- Track API failures

### Updates
- models.dev updates automatically via community
- We just fetch latest data
- Zero manual work

### Validation
- Weekly automated pricing comparison (CI job)
- Alert if models.dev pricing differs from .env by >10%
- Manual review and update .env fallback values

---

## References

- [models.dev Website](https://models.dev)
- [models.dev GitHub](https://github.com/sst/models.dev)
- [models.dev API](https://models.dev/api.json)
- [Anthropic Pricing](https://www.anthropic.com/pricing)

---

**End of Integration Document**
