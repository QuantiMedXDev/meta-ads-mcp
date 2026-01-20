# Bid Strategy Discovery Tools

## Problem Statement

When creating ad sets in Meta Ads, you may encounter error **2490487: "Bid Amount Or Bid Constraints Required For Bid Strategy"**. This error occurs when your ad account has specific bidding requirements that aren't obvious from the API.

## Solution

Two new MCP tools have been added to help discover and solve bid strategy issues:

### 1. `get_bid_strategy_info`

**Purpose:** Get information and guidance about bid strategies for a specific campaign and optimization goal.

**Use when:** You want to understand what bid strategies are commonly used and see what existing ad sets in the campaign are using.

**Parameters:**
- `campaign_id` - The campaign ID where you want to create an ad set
- `optimization_goal` - The optimization goal (e.g., 'REACH', 'LINK_CLICKS')
- `access_token` - (optional) Your Meta API access token

**Example Usage:**
```python
result = await get_bid_strategy_info(
    campaign_id="120241682238560174",
    optimization_goal="REACH",
    access_token="YOUR_TOKEN"
)
```

**What it returns:**
- Campaign details and objective
- List of existing ad sets with their bid strategies
- Guidance on common bid strategies for your optimization goal
- Recommendations based on existing ad sets

### 2. `discover_bid_strategy_requirements`

**Purpose:** Automatically test different bid strategy combinations to find what works for your account.

**Use when:** You're getting error 2490487 and need to find the exact bid configuration your account requires.

**Parameters:**
- `account_id` - Ad account ID (format: act_XXXXXXXXX)
- `campaign_id` - Campaign ID to test in
- `name` - Name for test ad sets (they'll be created as PAUSED)
- `optimization_goal` - Optimization goal (e.g., 'REACH')
- `billing_event` - Billing event (e.g., 'IMPRESSIONS')
- `daily_budget` - Daily budget in cents (e.g., 3000000 for ₹30,000)
- `targeting` - Targeting specification object
- `access_token` - (optional) Your Meta API access token

**Example Usage:**
```python
result = await discover_bid_strategy_requirements(
    account_id="act_1445720119593938",
    campaign_id="120241682238560174",
    name="Bid Strategy Test",
    optimization_goal="REACH",
    billing_event="IMPRESSIONS",
    daily_budget=3000000,
    targeting={
        "geo_locations": {"countries": ["AE"]},
        "age_min": 18,
        "age_max": 65,
        "flexible_spec": [{"interests": [{"id": "6003139266461", "name": "Real estate investing"}]}]
    },
    access_token="YOUR_TOKEN"
)
```

**What it does:**
1. Attempts to create test ad sets (as PAUSED) with different bid strategies:
   - No bid strategy (Meta default)
   - LOWEST_COST_WITHOUT_CAP
   - LOWEST_COST_WITH_BID_CAP with bid_amount
   - COST_CAP with bid_amount

2. Reports success/failure for each attempt
3. Stops when it finds a working configuration
4. Returns the working bid strategy parameters

**What it returns:**
- Test results for each bid strategy attempted
- Which strategies succeeded and which failed
- Error messages for failed attempts
- **Recommendation:** The working bid configuration to use
- Next steps if no strategy worked

**Important Notes:**
- Test ad sets are created as **PAUSED** status
- You can safely delete the test ad sets after discovery
- The tool stops testing once it finds a working strategy
- If successful, use the recommended parameters for your actual ad set creation

## Common Bid Strategies

### For REACH Optimization

Most accounts require one of these for REACH:

1. **LOWEST_COST_WITH_BID_CAP** (most common)
   ```json
   {
     "bid_strategy": "LOWEST_COST_WITH_BID_CAP",
     "bid_amount": "100000"  // ₹1,000 in paise
   }
   ```

2. **COST_CAP**
   ```json
   {
     "bid_strategy": "COST_CAP",
     "bid_amount": "100000"  // Cost per result goal
   }
   ```

### For Other Optimization Goals

Usually optional or use default:
- **LOWEST_COST_WITHOUT_CAP** - Default, no bid cap
- **LOWEST_COST_WITH_BID_CAP** - If you want to control maximum bid
- **COST_CAP** - If you want to target specific cost per result

## Workflow

1. **Start with `get_bid_strategy_info`**
   - See what existing ad sets use
   - Get general guidance
   - Understand common patterns

2. **If still getting errors, use `discover_bid_strategy_requirements`**
   - Automatically test all configurations
   - Get exact working parameters
   - Use the recommended configuration

3. **Create your actual ad set**
   - Use the discovered bid_strategy and bid_amount
   - Should work without error 2490487

## Example: Complete Workflow

```python
# Step 1: Get information
info = await get_bid_strategy_info(
    campaign_id="120241682238560174",
    optimization_goal="REACH"
)
print(info)

# Step 2: Discover requirements (if needed)
discovery = await discover_bid_strategy_requirements(
    account_id="act_1445720119593938",
    campaign_id="120241682238560174",
    name="Test Bid Discovery",
    optimization_goal="REACH",
    billing_event="IMPRESSIONS",
    daily_budget=3000000,
    targeting={
        "geo_locations": {"countries": ["AE"]},
        "age_min": 18,
        "age_max": 65
    }
)
print(discovery)

# Step 3: Use the working configuration
# From discovery result: "bid_strategy": "LOWEST_COST_WITH_BID_CAP", "bid_amount": "300000"

actual_adset = await create_adset(
    account_id="act_1445720119593938",
    campaign_id="120241682238560174",
    name="UAE Real Estate - REACH",
    optimization_goal="REACH",
    billing_event="IMPRESSIONS",
    daily_budget=3000000,
    bid_strategy="LOWEST_COST_WITH_BID_CAP",  # From discovery
    bid_amount=300000,  # From discovery
    targeting={
        "geo_locations": {"countries": ["AE"]},
        "age_min": 18,
        "age_max": 65,
        "flexible_spec": [{"interests": [{"id": "6003139266461", "name": "Real estate investing"}]}]
    }
)
```

## Troubleshooting

### If discovery finds no working strategies

This means your account has special requirements that can't be set via API:
- May require "Cost per result goal" setting in Ads Manager UI
- May require ROAS goal or other advanced bid constraints
- May need account-level settings changed by Meta support

**Solutions:**
1. Try a different campaign objective (e.g., OUTCOME_TRAFFIC instead of OUTCOME_AWARENESS)
2. Set up the ad set manually in Ads Manager UI first
3. Contact Meta support for account-specific bid requirements
4. Check if there are account-level restrictions or special ad account configurations

### Currency Conversion

Remember to convert currency to smallest unit (cents/paise):
- ₹1,000 = 100,000 paise
- $10 = 1,000 cents
- €5 = 500 cents

The `bid_amount` parameter always uses the smallest currency unit.
