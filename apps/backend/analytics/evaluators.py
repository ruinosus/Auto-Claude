"""
LLM-as-a-Judge Evaluators for Langfuse
======================================

Provides configuration and management for LLM-based evaluation of
agent outputs. Uses Langfuse's LLM-as-a-Judge capability.

Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class EvaluatorConfig:
    """Configuration for an LLM-as-a-Judge evaluator."""
    name: str
    model: str = "claude-haiku-4-5"
    criteria: List[str] = field(default_factory=list)
    output_type: Literal["numeric", "categorical", "boolean"] = "numeric"
    scale_min: int = 1
    scale_max: int = 10
    description: str = ""
    prompt_template: Optional[str] = None


def create_evaluator_config(
    name: str,
    model: str = "claude-haiku-4-5",
    criteria: Optional[List[str]] = None,
    output_type: str = "numeric",
    scale_min: int = 1,
    scale_max: int = 10,
    description: str = "",
    prompt_template: Optional[str] = None,
) -> EvaluatorConfig:
    """Create an evaluator configuration."""
    return EvaluatorConfig(
        name=name,
        model=model,
        criteria=criteria or [],
        output_type=output_type,
        scale_min=scale_min,
        scale_max=scale_max,
        description=description,
        prompt_template=prompt_template,
    )


# =============================================================================
# Evaluator Registry
# =============================================================================

_evaluator_registry: Dict[str, Dict[str, Any]] = {}


def register_evaluator(name: str, config: Dict[str, Any]) -> None:
    """Register an evaluator configuration."""
    _evaluator_registry[name] = config
    logger.debug(f"Registered evaluator: {name}")


def get_evaluator(name: str) -> Optional[Dict[str, Any]]:
    """Get an evaluator configuration by name."""
    return _evaluator_registry.get(name)


def list_evaluators() -> List[str]:
    """List all registered evaluator names."""
    return list(_evaluator_registry.keys())


def clear_evaluators() -> None:
    """Clear all registered evaluators."""
    _evaluator_registry.clear()


# =============================================================================
# Default Evaluators
# =============================================================================

DEFAULT_EVALUATORS = {
    "code_quality": {
        "name": "code_quality",
        "model": "claude-haiku-4-5",
        "description": "Evaluates overall code quality",
        "criteria": [
            "Does the code follow project conventions and style guides?",
            "Is the code readable and well-structured?",
            "Are there adequate comments where needed?",
            "Is the code DRY (no unnecessary duplication)?",
        ],
        "output_type": "numeric",
        "scale_min": 1,
        "scale_max": 10,
    },
    "spec_completeness": {
        "name": "spec_completeness",
        "model": "claude-haiku-4-5",
        "description": "Evaluates how completely the spec was implemented",
        "criteria": [
            "Are all acceptance criteria addressed?",
            "Is the implementation complete, not partial?",
            "Are edge cases handled?",
            "Does it match the user's intent?",
        ],
        "output_type": "numeric",
        "scale_min": 1,
        "scale_max": 10,
    },
    "security_review": {
        "name": "security_review",
        "model": "claude-haiku-4-5",
        "description": "Evaluates security of the implementation",
        "criteria": [
            "Are there any potential injection vulnerabilities (SQL, command, etc.)?",
            "Is user input properly validated and sanitized?",
            "Are secrets and credentials handled securely?",
            "Are there any obvious security anti-patterns?",
        ],
        "output_type": "categorical",
        "categories": ["secure", "minor_issues", "major_issues"],
    },
    "test_coverage": {
        "name": "test_coverage",
        "model": "claude-haiku-4-5",
        "description": "Evaluates test coverage and quality",
        "criteria": [
            "Are the main code paths tested?",
            "Are edge cases covered?",
            "Are tests meaningful (not just for coverage)?",
            "Do tests verify behavior, not implementation?",
        ],
        "output_type": "numeric",
        "scale_min": 1,
        "scale_max": 10,
    },
}

# Register default evaluators
for name, config in DEFAULT_EVALUATORS.items():
    register_evaluator(name, config)


# =============================================================================
# Evaluation Execution
# =============================================================================

def run_evaluation(
    evaluator_name: str,
    trace_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run an evaluation on content.

    Note: This is a placeholder. Full implementation requires Langfuse
    to be properly configured with LLM-as-a-Judge capability.

    Args:
        evaluator_name: Name of the evaluator to use
        trace_id: Langfuse trace ID to attach score to
        content: Content to evaluate
        metadata: Optional additional metadata

    Returns:
        Evaluation result dictionary
    """
    evaluator = get_evaluator(evaluator_name)
    if not evaluator:
        return {"error": f"Evaluator not found: {evaluator_name}"}

    # Check if Langfuse is available
    try:
        from analytics.langfuse_integration import get_langfuse_client, is_langfuse_ready

        if not is_langfuse_ready():
            return {
                "error": "Langfuse not initialized",
                "evaluator": evaluator_name,
                "trace_id": trace_id,
            }

        client = get_langfuse_client()
        if not client:
            return {"error": "Langfuse client not available"}

        # TODO: Implement actual LLM-as-a-Judge evaluation via Langfuse API
        # This requires Langfuse to have evaluators configured in the UI
        # Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

        logger.info(f"Would run evaluator '{evaluator_name}' on trace {trace_id}")
        return {
            "evaluator": evaluator_name,
            "trace_id": trace_id,
            "status": "pending",
            "note": "Evaluation queued. Configure evaluators in Langfuse UI.",
        }

    except ImportError:
        return {
            "error": "Langfuse integration not available",
            "evaluator": evaluator_name,
        }


def get_evaluator_prompt(evaluator_name: str, content: str) -> Optional[str]:
    """
    Generate the evaluation prompt for an evaluator.

    Args:
        evaluator_name: Name of the evaluator
        content: Content to evaluate

    Returns:
        Evaluation prompt string, or None if evaluator not found
    """
    evaluator = get_evaluator(evaluator_name)
    if not evaluator:
        return None

    criteria = evaluator.get("criteria", [])
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    output_type = evaluator.get("output_type", "numeric")
    if output_type == "numeric":
        scale_min = evaluator.get("scale_min", 1)
        scale_max = evaluator.get("scale_max", 10)
        score_instruction = f"Provide a score from {scale_min} to {scale_max}."
    elif output_type == "categorical":
        categories = evaluator.get("categories", ["good", "bad"])
        score_instruction = f"Classify as one of: {', '.join(categories)}."
    else:
        score_instruction = "Respond with true or false."

    prompt = f"""Evaluate the following content based on these criteria:

{criteria_text}

{score_instruction}

Content to evaluate:
---
{content}
---

Provide your evaluation with a brief justification."""

    return prompt
