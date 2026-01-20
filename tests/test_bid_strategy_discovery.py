"""Test bid strategy discovery tools."""

import pytest
import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from meta_ads_mcp.core.adsets import get_bid_strategy_info, discover_bid_strategy_requirements


@pytest.mark.asyncio
async def test_get_bid_strategy_info():
    """Test getting bid strategy information for a campaign."""
    # Use environment variable for token or skip if not available
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        pytest.skip("META_ACCESS_TOKEN not set")
    
    # Test with a real campaign
    campaign_id = os.getenv("TEST_CAMPAIGN_ID", "120241682238560174")
    
    result = await get_bid_strategy_info(
        campaign_id=campaign_id,
        optimization_goal="REACH",
        access_token=token
    )
    
    # Parse JSON result
    data = json.loads(result)
    
    # Verify structure
    assert "campaign" in data
    assert "requested_optimization_goal" in data
    assert "bid_strategy_guidance" in data
    
    # Verify campaign info
    assert data["campaign"]["id"] == campaign_id
    assert "name" in data["campaign"]
    
    # Verify guidance for REACH
    if data["requested_optimization_goal"] == "REACH":
        assert "common_issue" in data["bid_strategy_guidance"]
        assert "possible_solutions" in data["bid_strategy_guidance"]
    
    print("✅ get_bid_strategy_info test passed")
    print(json.dumps(data, indent=2))


@pytest.mark.asyncio
async def test_discover_bid_strategy_requirements_dry_run():
    """Test bid strategy discovery logic without actually creating ad sets."""
    # This is a dry-run test that verifies the tool structure
    # We don't actually run it to avoid creating test ad sets
    
    # Just verify the function exists and has correct signature
    import inspect
    sig = inspect.signature(discover_bid_strategy_requirements)
    params = sig.parameters
    
    assert "account_id" in params
    assert "campaign_id" in params
    assert "name" in params
    assert "optimization_goal" in params
    assert "billing_event" in params
    assert "daily_budget" in params
    assert "targeting" in params
    assert "access_token" in params
    
    print("✅ discover_bid_strategy_requirements structure test passed")


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_TESTS"),
    reason="Set RUN_LIVE_TESTS=1 to run live API tests that create ad sets"
)
@pytest.mark.asyncio
async def test_discover_bid_strategy_live():
    """Live test of bid strategy discovery (only runs if RUN_LIVE_TESTS=1)."""
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        pytest.skip("META_ACCESS_TOKEN not set")
    
    account_id = os.getenv("TEST_ACCOUNT_ID", "act_1445720119593938")
    campaign_id = os.getenv("TEST_CAMPAIGN_ID", "120241682238560174")
    
    result = await discover_bid_strategy_requirements(
        account_id=account_id,
        campaign_id=campaign_id,
        name="Bid Strategy Discovery Test",
        optimization_goal="REACH",
        billing_event="IMPRESSIONS",
        daily_budget=3000000,  # ₹30,000
        targeting={
            "geo_locations": {"countries": ["AE"]},
            "age_min": 18,
            "age_max": 65
        },
        access_token=token
    )
    
    # Parse result
    data = json.loads(result)
    
    # Verify structure
    assert "account_id" in data
    assert "campaign_id" in data
    assert "test_results" in data
    assert "summary" in data
    
    # Should have attempted at least one test
    assert len(data["test_results"]) > 0
    
    # Each test should have required fields
    for test in data["test_results"]:
        assert "test_number" in test
        assert "description" in test
        assert "status" in test
    
    print("✅ Live bid strategy discovery test passed")
    print(json.dumps(data, indent=2))
    
    # If any test succeeded, print the recommendation
    if data["summary"].get("successful_strategies"):
        print("\n🎉 Found working bid strategy!")
        if "recommendation" in data:
            print(json.dumps(data["recommendation"], indent=2))


if __name__ == "__main__":
    # Run tests
    import asyncio
    
    print("Testing get_bid_strategy_info...")
    asyncio.run(test_get_bid_strategy_info())
    
    print("\nTesting discover_bid_strategy_requirements structure...")
    asyncio.run(test_discover_bid_strategy_requirements_dry_run())
    
    print("\nAll tests passed! ✅")
    print("\nTo run live discovery test, set:")
    print("  export META_ACCESS_TOKEN=your_token")
    print("  export RUN_LIVE_TESTS=1")
    print("  pytest tests/test_bid_strategy_discovery.py::test_discover_bid_strategy_live")
