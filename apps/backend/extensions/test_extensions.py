#!/usr/bin/env python3
"""
Extensions Integration Test
===========================

Tests the expanded extensions layer with:
- Value engine
- Artifact storage
- Artifact capture
- ROI calculation
- Session tracking

Run: python extensions/test_extensions.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up test environment
os.environ["EXTENSIONS_ENABLED"] = "true"
os.environ["LANGFUSE_ENABLED"] = "false"  # Don't need Langfuse for this test


def test_value_engine():
    """Test value engine calculations."""
    print("\n=== Testing Value Engine ===")

    from extensions.analytics.value_engine import (
        get_artifact_value,
        ValueAttribution,
        ARTIFACT_VALUES,
    )

    # Test diagram value
    value = get_artifact_value("diagram", "coder")
    print(f"  Diagram (coder): ${value['adjusted_value_usd']:.2f} ({value['dimension']})")
    assert value["adjusted_value_usd"] > 0
    assert value["dimension"] == "knowledge"

    # Test security finding
    value = get_artifact_value("security_finding", "qa_reviewer")
    print(f"  Security Finding (qa_reviewer): ${value['adjusted_value_usd']:.2f}")
    assert value["adjusted_value_usd"] > 100  # High value

    # Test unknown type
    value = get_artifact_value("unknown_type", "unknown")
    print(f"  Unknown type: ${value['adjusted_value_usd']:.2f}")
    assert value["adjusted_value_usd"] > 0

    # Test value attribution
    attribution = ValueAttribution()
    attribution.add_artifact(get_artifact_value("diagram", "coder"))
    attribution.add_artifact(get_artifact_value("gotcha_identified", "coder"))
    print(f"  Total attribution: ${attribution.total_value:.2f}")
    assert attribution.artifact_count == 2

    print("  [PASS] Value engine working correctly")


def test_storage():
    """Test artifact storage wrapper (delegates to main storage)."""
    print("\n=== Testing Artifact Storage Wrapper ===")

    from extensions.analytics.storage import (
        save_artifact,
        load_artifact,
        list_artifacts,
        get_artifacts_summary,
        _check_main_storage,
    )

    # Use temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Check if main storage is available
        main_available = _check_main_storage()
        print(f"  Main storage available: {main_available}")

        if main_available:
            # Test with main storage delegation
            artifact = save_artifact(
                artifact_type="diagram",
                content="graph TD\n  A --> B\n  B --> C",
                description="Test diagram",
                value_usd=127.50,
                trace_id="test-trace-123",
                spec_id="001",
                agent_type="coder",
                project_dir=tmpdir,
                format="mermaid",
            )

            assert artifact is not None
            print(f"  Saved artifact via main storage: {artifact['id']}")
            assert artifact["content"] == "graph TD\n  A --> B\n  B --> C"

            # Load artifact
            loaded = load_artifact(artifact["id"], project_dir=tmpdir)
            assert loaded is not None
            print(f"  Loaded artifact: {loaded['id']}")
            assert loaded["content"] == artifact["content"]

            # List artifacts
            artifacts = list_artifacts(project_dir=tmpdir)
            print(f"  Listed {len(artifacts)} artifacts")
            assert len(artifacts) >= 1

            # Get summary
            summary = get_artifacts_summary(project_dir=tmpdir)
            print(f"  Summary: {summary['total_artifacts']} artifacts, ${summary['total_value_usd']:.2f}")
            assert summary["total_artifacts"] >= 1
        else:
            # Main storage not available, test fallback behavior
            artifact = save_artifact(
                artifact_type="diagram",
                content="graph TD\n  A --> B",
                description="Test",
                value_usd=100.0,
                project_dir=tmpdir,
            )
            # Should return None when main storage unavailable
            assert artifact is None
            print("  Main storage unavailable, fallback behavior confirmed")

    print("  [PASS] Artifact storage wrapper working correctly")


def test_artifact_capture():
    """Test artifact capture from MCP tools (no-duplicate mode)."""
    print("\n=== Testing Artifact Capture ===")

    from extensions.analytics.artifact_capture import (
        capture_from_mcp_tool_result,
        capture_from_tool_result,
        ARTIFACT_TOOLS,
    )

    # Use temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test EXPLICIT mode - MCP tool result WITH artifact_id (already saved)
        # When artifact_id is present, the MCP tool already saved it
        # So we should NOT save again, just return info for tracking
        tool_result_with_id = {
            "artifact_id": "art-001",
            "artifact_type": "diagram",
            "content": "graph TD\n  User --> API\n  API --> DB",
            "description": "Architecture diagram",
            "format": "mermaid",
            "value_usd": 150.0,
        }

        result = capture_from_mcp_tool_result(
            tool_name="mcp__auto-claude__create_diagram",
            tool_result=tool_result_with_id,
            agent_type="coder",
            trace_id="test-trace",
            project_dir=tmpdir,
        )

        assert result is not None
        print(f"  Result from MCP tool (already saved): {result['id']}")
        assert result["type"] == "diagram"
        assert result.get("already_saved") == True  # Flag indicating no duplicate save
        assert result["id"] == "art-001"  # Original ID preserved

        # Test EXPLICIT mode - MCP tool result WITHOUT artifact_id (needs save)
        # This is a fallback case for tools that don't save
        tool_result_no_id = {
            "artifact_type": "pattern_discovered",
            "content": "Always use dependency injection for services",
            "description": "DI pattern",
        }

        artifacts, attribution = capture_from_tool_result(
            tool_name="mcp__auto-claude__create_artifact",
            tool_result=tool_result_no_id,
            agent_type="planner",
            project_dir=tmpdir,
        )

        # This will either:
        # - Save via main storage (if available) and return artifact
        # - Return empty list (if main storage unavailable)
        print(f"  Captured {len(artifacts)} artifacts via main function")
        # Note: result depends on whether main storage is available

        # Test non-artifact tool (should return empty)
        artifacts_empty, _ = capture_from_tool_result(
            tool_name="mcp__auto-claude__get_build_progress",
            tool_result={"status": "running"},
            agent_type="coder",
            project_dir=tmpdir,
        )
        assert len(artifacts_empty) == 0
        print("  Non-artifact tool correctly skipped")

    print("  [PASS] Artifact capture working correctly")


def test_roi_calculator():
    """Test ROI calculation."""
    print("\n=== Testing ROI Calculator ===")

    from extensions.analytics.roi_calculator import (
        calculate_session_roi,
        calculate_artifact_roi,
        get_token_cost,
        ROIResult,
    )
    from extensions.analytics.storage import save_artifact

    # Use temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some artifacts
        save_artifact(
            artifact_type="diagram",
            content="graph TD\n  A --> B",
            description="Test",
            value_usd=150.0,
            trace_id="roi-test",
            project_dir=tmpdir,
        )
        save_artifact(
            artifact_type="security_finding",
            content="SQL injection vulnerability found",
            description="Security",
            value_usd=200.0,
            trace_id="roi-test",
            project_dir=tmpdir,
        )

        # Calculate ROI
        token_usage = {
            "model": "claude-sonnet-4-5",
            "input_tokens": 10000,
            "output_tokens": 2000,
        }

        result = calculate_session_roi(
            trace_id="roi-test",
            project_dir=tmpdir,
            token_usage=token_usage,
        )

        print(f"  ROI: {result.roi_percentage:.1f}%")
        print(f"  Total Value: ${result.total_value_usd:.2f}")
        print(f"  Total Cost: ${result.total_cost_usd:.4f}")
        print(f"  Net Value: ${result.net_value_usd:.2f}")

        assert result.roi_percentage > 0
        assert result.total_value_usd > 0
        assert result.total_cost_usd > 0

        # Test token cost calculation
        cost = get_token_cost("claude-opus-4-5", 100000, 10000)
        print(f"  Opus 100k/10k tokens cost: ${cost:.4f}")
        assert cost > 0

    print("  [PASS] ROI calculator working correctly")


def test_session_tracker():
    """Test session tracking."""
    print("\n=== Testing Session Tracker ===")

    from extensions.analytics.session_tracker import (
        start_session,
        end_session,
        get_current_session,
        track_token_usage,
        track_tool_start,
        track_tool_end,
        track_artifact,
    )

    # Start session
    session = start_session(
        agent_type="coder",
        trace_id="session-test",
        spec_id="001",
    )

    assert session is not None
    print(f"  Started session: {session.agent_type}")

    # Track some activity
    track_token_usage("claude-sonnet-4-5", 5000, 1000)
    track_token_usage("claude-sonnet-4-5", 3000, 500)
    print(f"  Tracked tokens: {session.total_tokens}")

    # Track tool calls
    tool_call = track_tool_start("Read")
    assert tool_call is not None
    track_tool_end(tool_call, success=True)
    print(f"  Tracked {session.tool_call_count} tool calls")

    # Track artifact
    track_artifact("diagram", 150.0)
    print(f"  Tracked {session.artifact_count} artifacts")

    # End session
    final = end_session("completed")
    assert final is not None
    print(f"  Session duration: {final.duration_seconds:.2f}s")

    # Verify no current session
    assert get_current_session() is None

    print("  [PASS] Session tracker working correctly")


def test_hooks_integration():
    """Test hooks integration."""
    print("\n=== Testing Hooks Integration ===")

    from extensions.patches.hooks import (
        register_hooks,
        get_tracking_hooks,
        set_hook_context,
        clear_hook_context,
        start_tracked_session,
        end_tracked_session,
    )

    # Check hooks available (may fail without SDK)
    hooks_ok = register_hooks()
    print(f"  Hooks registered: {hooks_ok}")

    # Set hook context
    set_hook_context(
        trace_id="hook-test",
        spec_id="001",
        agent_type="coder",
    )
    print("  Hook context set")

    # Clear context
    clear_hook_context()
    print("  Hook context cleared")

    print("  [PASS] Hooks integration working correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Extensions Layer Integration Test")
    print("=" * 60)

    try:
        test_value_engine()
        test_storage()
        test_artifact_capture()
        test_roi_calculator()
        test_session_tracker()
        test_hooks_integration()

        print("\n" + "=" * 60)
        print(" ALL TESTS PASSED")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
