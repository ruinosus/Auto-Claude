"""
Model Configuration Utilities
==============================

Shared utilities for reading and parsing model configuration from environment variables.
Used by both commit_message.py and merge resolver.
"""

import logging
import os

from phase_config import resolve_model_id

logger = logging.getLogger(__name__)

# Default model shorthand for utility operations (commit messages, merge resolution)
# Use resolve_model_id() at runtime to get the correct model ID (supports Azure Foundry)
DEFAULT_UTILITY_MODEL_SHORT = "haiku"


def get_utility_model_config(
    default_model: str | None = None,
) -> tuple[str, int | None]:
    """
    Get utility model configuration from environment variables.

    Reads UTILITY_MODEL_ID and UTILITY_THINKING_BUDGET from environment,
    with sensible defaults and validation.

    Args:
        default_model: Default model ID to use if UTILITY_MODEL_ID not set.
                      If None, uses resolve_model_id("haiku") for Azure Foundry support.

    Returns:
        Tuple of (model_id, thinking_budget) where thinking_budget is None
        if extended thinking is disabled, or an int representing token budget
    """
    # Resolve default model at runtime to support Azure Foundry deployment names
    resolved_default = default_model if default_model else resolve_model_id(DEFAULT_UTILITY_MODEL_SHORT)
    model = os.environ.get("UTILITY_MODEL_ID", resolved_default)
    thinking_budget_str = os.environ.get("UTILITY_THINKING_BUDGET", "")

    # Parse thinking budget: empty string = disabled (None), number = budget tokens
    # Note: 0 is treated as "disable thinking" (same as None) since 0 tokens is meaningless
    thinking_budget: int | None
    if not thinking_budget_str:
        # Empty string means "none" level - disable extended thinking
        thinking_budget = None
    else:
        try:
            parsed_budget = int(thinking_budget_str)
            # Validate positive values - 0 or negative are invalid
            # 0 would mean "thinking enabled but 0 tokens" which is meaningless
            if parsed_budget <= 0:
                if parsed_budget == 0:
                    # Zero means disable thinking (same as empty string)
                    logger.debug(
                        "UTILITY_THINKING_BUDGET=0 interpreted as 'disable thinking'"
                    )
                    thinking_budget = None
                else:
                    logger.warning(
                        f"Negative UTILITY_THINKING_BUDGET value '{thinking_budget_str}' not allowed, using default 1024"
                    )
                    thinking_budget = 1024
            else:
                thinking_budget = parsed_budget
        except ValueError:
            logger.warning(
                f"Invalid UTILITY_THINKING_BUDGET value '{thinking_budget_str}', using default 1024"
            )
            thinking_budget = 1024

    return model, thinking_budget
