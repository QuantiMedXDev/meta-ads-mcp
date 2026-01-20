#!/usr/bin/env python3
"""
Example: Using Bid Strategy Discovery Tools

This script demonstrates how to use the new bid strategy discovery tools
to solve error 2490487: "Bid Amount Or Bid Constraints Required For Bid Strategy"
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from meta_ads_mcp.core.adsets import (
    get_bid_strategy_info,
    discover_bid_strategy_requirements,
    create_adset
)


async def example_workflow():
    """Complete workflow for discovering and using bid strategies."""
    
    # Configuration
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        print("❌ Please set META_ACCESS_TOKEN environment variable")
        print("   export META_ACCESS_TOKEN=your_long_lived_token")
        return
    
    account_id = "act_1445720119593938"
    campaign_id = "120241682238560174"
    
    print("=" * 60)
    print("Bid Strategy Discovery Workflow")
    print("=" * 60)
    
    # Step 1: Get bid strategy information
    print("\n📊 Step 1: Getting bid strategy information...")
    print("-" * 60)
    
    info_result = await get_bid_strategy_info(
        campaign_id=campaign_id,
        optimization_goal="REACH",
        access_token=token
    )
    
    info_data = json.loads(info_result)
    print(f"Campaign: {info_data['campaign']['name']}")
    print(f"Objective: {info_data['campaign']['objective']}")
    
    if info_data.get("existing_adsets_in_campaign"):
        print("\nExisting ad sets in campaign:")
        for adset in info_data["existing_adsets_in_campaign"]:
            print(f"  - {adset['name']}")
            print(f"    Bid Strategy: {adset.get('bid_strategy', 'Not set')}")
            print(f"    Bid Amount: {adset.get('bid_amount', 'Not set')}")
    else:
        print("\n⚠️  No existing ad sets found in campaign")
    
    print("\n💡 Bid Strategy Guidance:")
    if "bid_strategy_guidance" in info_data:
        guidance = info_data["bid_strategy_guidance"]
        if "common_issue" in guidance:
            print(f"  Issue: {guidance['common_issue']}")
        if "recommendation" in guidance:
            print(f"  Recommendation: {guidance['recommendation']}")
    
    # Step 2: Discover bid strategy requirements
    print("\n" + "=" * 60)
    print("🔍 Step 2: Discovering bid strategy requirements...")
    print("-" * 60)
    print("This will create test ad sets (PAUSED) to find what works.")
    
    confirm = input("\nProceed with discovery? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Discovery cancelled")
        return
    
    discovery_result = await discover_bid_strategy_requirements(
        account_id=account_id,
        campaign_id=campaign_id,
        name="TEST - Bid Discovery",
        optimization_goal="REACH",
        billing_event="IMPRESSIONS",
        daily_budget=3000000,  # ₹30,000 in paise
        targeting={
            "geo_locations": {"countries": ["AE"]},
            "age_min": 18,
            "age_max": 65,
            "flexible_spec": [{
                "interests": [{"id": "6003139266461", "name": "Real estate investing"}]
            }]
        },
        access_token=token
    )
    
    discovery_data = json.loads(discovery_result)
    
    print("\n📝 Test Results:")
    for test in discovery_data["test_results"]:
        status_emoji = "✅" if test["status"] == "success" else "❌"
        print(f"\n{status_emoji} Test {test['test_number']}: {test['description']}")
        print(f"   Status: {test['status']}")
        
        if test["status"] == "success":
            print(f"   Created Ad Set: {test['created_adset']['id']}")
            print(f"   Note: {test['created_adset']['note']}")
        elif "error" in test:
            print(f"   Error: {test['error'].get('message', 'Unknown error')}")
    
    # Step 3: Use the working configuration
    print("\n" + "=" * 60)
    print("🎯 Step 3: Using discovered bid strategy")
    print("-" * 60)
    
    if discovery_data["summary"].get("successful_strategies"):
        print(f"\n✅ Found working strategy: {discovery_data['summary']['successful_strategies'][0]}")
        
        if "recommendation" in discovery_data:
            rec = discovery_data["recommendation"]
            print("\n💡 Recommended Configuration:")
            print(json.dumps(rec["working_configuration"], indent=2))
            
            # Ask if user wants to create actual ad set
            print("\nCreate actual ad set with this configuration?")
            confirm = input("(y/n): ")
            
            if confirm.lower() == 'y':
                actual_name = input("Enter ad set name: ")
                
                # Build create_adset params with discovered config
                create_params = {
                    "account_id": account_id,
                    "campaign_id": campaign_id,
                    "name": actual_name,
                    "optimization_goal": "REACH",
                    "billing_event": "IMPRESSIONS",
                    "daily_budget": 3000000,
                    "status": "PAUSED",
                    "targeting": {
                        "geo_locations": {"countries": ["AE"]},
                        "age_min": 18,
                        "age_max": 65,
                        "flexible_spec": [{
                            "interests": [{"id": "6003139266461", "name": "Real estate investing"}]
                        }]
                    },
                    "access_token": token
                }
                
                # Add discovered bid configuration
                create_params.update(rec["working_configuration"])
                
                print("\nCreating ad set...")
                create_result = await create_adset(**create_params)
                create_data = json.loads(create_result)
                
                if "error" in create_data:
                    print(f"❌ Failed to create ad set: {create_data['error']}")
                else:
                    print(f"✅ Successfully created ad set!")
                    print(f"   ID: {create_data.get('id')}")
                    print(f"   Name: {actual_name}")
                    print(f"\n🎉 Ad set created successfully with discovered bid strategy!")
    else:
        print("\n❌ No working bid strategy found")
        print("\nNext steps:")
        for step in discovery_data.get("next_steps", []):
            print(f"  - {step}")
    
    print("\n" + "=" * 60)
    print("Workflow complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║        Meta Ads MCP - Bid Strategy Discovery Example        ║
╚══════════════════════════════════════════════════════════════╝

This example demonstrates how to:
1. Get bid strategy information for a campaign
2. Automatically discover what bid constraints your account requires  
3. Create an ad set using the discovered configuration

Environment Variables Required:
  META_ACCESS_TOKEN - Your Meta API long-lived access token

    """)
    
    asyncio.run(example_workflow())
