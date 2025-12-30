# tests/test_datasets.py
import pytest
from unittest.mock import MagicMock, patch


def test_dataset_item_creation():
    """Test creating a dataset item."""
    from analytics.datasets import DatasetItem, create_dataset_item

    item = create_dataset_item(
        input_data={"spec": "Add login feature"},
        expected_output={"files_changed": ["auth.py", "login.tsx"]},
        metadata={"complexity": "standard"},
    )

    assert item.input_data == {"spec": "Add login feature"}
    assert item.expected_output == {"files_changed": ["auth.py", "login.tsx"]}
    assert item.metadata["complexity"] == "standard"


def test_dataset_creation():
    """Test creating a dataset."""
    from analytics.datasets import Dataset, create_dataset

    dataset = create_dataset(
        name="spec_quality_baseline",
        description="Reference specs for testing prompt changes",
        items=[],
    )

    assert dataset.name == "spec_quality_baseline"
    assert dataset.description == "Reference specs for testing prompt changes"
    assert len(dataset.items) == 0


def test_add_item_to_dataset():
    """Test adding items to a dataset."""
    from analytics.datasets import create_dataset, create_dataset_item, add_item_to_dataset

    dataset = create_dataset("test_dataset", "Test")

    item = create_dataset_item(
        input_data={"prompt": "test"},
        expected_output={"response": "ok"},
    )

    updated = add_item_to_dataset(dataset, item)
    assert len(updated.items) == 1


def test_default_datasets():
    """Test that default datasets are defined."""
    from analytics.datasets import DEFAULT_DATASETS

    assert "spec_quality" in DEFAULT_DATASETS
    assert "qa_scenarios" in DEFAULT_DATASETS
    assert "merge_conflicts" in DEFAULT_DATASETS


def test_export_dataset_to_langfuse_format():
    """Test exporting dataset to Langfuse format."""
    from analytics.datasets import (
        create_dataset,
        create_dataset_item,
        add_item_to_dataset,
        export_to_langfuse_format,
    )

    dataset = create_dataset("test", "Test dataset")
    item = create_dataset_item(
        input_data={"spec": "test"},
        expected_output={"result": "ok"},
    )
    dataset = add_item_to_dataset(dataset, item)

    exported = export_to_langfuse_format(dataset)

    assert exported["name"] == "test"
    assert len(exported["items"]) == 1
    assert "input" in exported["items"][0]
    assert "expectedOutput" in exported["items"][0]
