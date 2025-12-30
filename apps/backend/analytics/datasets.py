"""
Dataset Management for Langfuse Experiments
============================================

Provides tools for creating and managing datasets for A/B testing
and prompt experiments via Langfuse.

Reference: https://langfuse.com/docs/datasets/prompt-experiments
"""

import logging
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DatasetItem:
    """A single item in a dataset."""
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Dataset:
    """A collection of dataset items for experiments."""
    name: str
    description: str = ""
    items: List[DatasetItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


def create_dataset_item(
    input_data: Dict[str, Any],
    expected_output: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None,
) -> DatasetItem:
    """Create a new dataset item."""
    return DatasetItem(
        input_data=input_data,
        expected_output=expected_output,
        metadata=metadata or {},
        id=id,
    )


def create_dataset(
    name: str,
    description: str = "",
    items: Optional[List[DatasetItem]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dataset:
    """Create a new dataset."""
    return Dataset(
        name=name,
        description=description,
        items=items or [],
        metadata=metadata or {},
    )


def add_item_to_dataset(dataset: Dataset, item: DatasetItem) -> Dataset:
    """Add an item to a dataset and return the updated dataset."""
    dataset.items.append(item)
    return dataset


# =============================================================================
# Default Datasets for Auto-Claude
# =============================================================================

DEFAULT_DATASETS = {
    "spec_quality": {
        "name": "spec_quality",
        "description": "Reference specs for testing spec writer prompt changes",
        "items": [
            {
                "input": {
                    "task": "Add user authentication with email/password",
                    "context": "React + Node.js app with PostgreSQL",
                },
                "expected_output": {
                    "has_acceptance_criteria": True,
                    "has_technical_requirements": True,
                    "has_test_plan": True,
                    "clarity_score_min": 8,
                },
            },
            {
                "input": {
                    "task": "Fix bug: login button doesn't work on mobile",
                    "context": "React Native app",
                },
                "expected_output": {
                    "identifies_root_cause": True,
                    "has_reproduction_steps": True,
                    "is_scoped": True,
                },
            },
        ],
    },
    "qa_scenarios": {
        "name": "qa_scenarios",
        "description": "QA reviewer test scenarios for validation testing",
        "items": [
            {
                "input": {
                    "code_diff": "def validate_email(email): return '@' in email",
                    "spec_requirement": "Email validation using RFC 5322 standard",
                },
                "expected_output": {
                    "should_reject": True,
                    "reason": "Insufficient email validation",
                },
            },
            {
                "input": {
                    "code_diff": "# Added comprehensive tests\ndef test_login(): ...",
                    "spec_requirement": "Add unit tests for login",
                },
                "expected_output": {
                    "should_approve": True,
                },
            },
        ],
    },
    "merge_conflicts": {
        "name": "merge_conflicts",
        "description": "Merge conflict scenarios for AI resolver testing",
        "items": [
            {
                "input": {
                    "ours": "const MAX_RETRIES = 3;",
                    "theirs": "const MAX_RETRIES = 5;",
                    "base": "const MAX_RETRIES = 3;",
                },
                "expected_output": {
                    "resolution": "theirs",
                    "reasoning": "Take newer value",
                },
            },
        ],
    },
}


# =============================================================================
# Langfuse Integration
# =============================================================================

def export_to_langfuse_format(dataset: Dataset) -> Dict[str, Any]:
    """
    Export a dataset to Langfuse API format.

    Args:
        dataset: Dataset to export

    Returns:
        Dictionary in Langfuse dataset format
    """
    return {
        "name": dataset.name,
        "description": dataset.description,
        "metadata": dataset.metadata,
        "items": [
            {
                "input": item.input_data,
                "expectedOutput": item.expected_output,
                "metadata": item.metadata,
            }
            for item in dataset.items
        ],
    }


def upload_dataset_to_langfuse(dataset: Dataset) -> Optional[str]:
    """
    Upload a dataset to Langfuse.

    Args:
        dataset: Dataset to upload

    Returns:
        Dataset ID if successful, None otherwise
    """
    try:
        from analytics.langfuse_integration import get_langfuse_client, is_langfuse_ready

        if not is_langfuse_ready():
            logger.warning("Langfuse not initialized, cannot upload dataset")
            return None

        client = get_langfuse_client()
        if not client:
            return None

        # Create dataset in Langfuse
        langfuse_dataset = client.create_dataset(
            name=dataset.name,
            description=dataset.description,
            metadata=dataset.metadata,
        )

        # Add items
        for item in dataset.items:
            client.create_dataset_item(
                dataset_name=dataset.name,
                input=item.input_data,
                expected_output=item.expected_output,
                metadata=item.metadata,
            )

        logger.info(f"Uploaded dataset '{dataset.name}' with {len(dataset.items)} items")
        return langfuse_dataset.id

    except ImportError:
        logger.warning("Langfuse integration not available")
        return None
    except Exception as e:
        logger.error(f"Failed to upload dataset: {e}")
        return None


def load_dataset_from_file(path: Path) -> Optional[Dataset]:
    """
    Load a dataset from a JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Dataset object, or None if loading failed
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = [
            create_dataset_item(
                input_data=item.get("input", {}),
                expected_output=item.get("expectedOutput") or item.get("expected_output"),
                metadata=item.get("metadata", {}),
            )
            for item in data.get("items", [])
        ]

        return create_dataset(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            items=items,
            metadata=data.get("metadata", {}),
        )

    except Exception as e:
        logger.error(f"Failed to load dataset from {path}: {e}")
        return None


def save_dataset_to_file(dataset: Dataset, path: Path) -> bool:
    """
    Save a dataset to a JSON file.

    Args:
        dataset: Dataset to save
        path: Path to save to

    Returns:
        True if successful
    """
    try:
        data = export_to_langfuse_format(dataset)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved dataset '{dataset.name}' to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save dataset: {e}")
        return False
