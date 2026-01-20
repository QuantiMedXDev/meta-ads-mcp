# Bid Strategy Discovery Feature - Implementation Summary

## Overview

Added two new MCP tools to solve the common error **2490487: "Bid Amount Or Bid Constraints Required For Bid Strategy"** when creating ad sets in Meta Ads API.

## Problem Solved

When creating ad sets with certain optimization goals (especially REACH), Meta's API may require specific bid constraints that vary by account configuration. The error message doesn't tell you which bid_strategy or bid_amount to use, making it difficult to create ad sets programmatically.

## Solution

Two new tools that work together to discover and apply the correct bid configuration:

### 1. `get_bid_strategy_info`
**Location:** `meta_ads_mcp/core/adsets.py`

**Purpose:** Provide information and guidance about bid strategies

**What it does:**
- Retrieves campaign details and objective
- Lists existing ad sets and their bid configurations
- Provides guidance specific to the optimization goal
- Recommends matching existing ad set configurations

**When to use:** Before creating an ad set to understand common patterns

### 2. `discover_bid_strategy_requirements`
**Location:** `meta_ads_mcp/core/adsets.py`

**Purpose:** Automatically find the correct bid configuration

**What it does:**
- Tests multiple bid strategy combinations:
  1. No bid strategy (Meta default)
  2. LOWEST_COST_WITHOUT_CAP
  3. LOWEST_COST_WITH_BID_CAP with bid_amount
  4. COST_CAP with bid_amount
- Creates test ad sets (PAUSED) to see what works
- Stops when it finds a working configuration
- Returns detailed results and recommendations

**When to use:** When getting error 2490487 and need to find exact requirements

## Files Added/Modified

### New Files
1. **`BID_STRATEGY_DISCOVERY.md`** - Complete user guide
2. **`tests/test_bid_strategy_discovery.py`** - Test suite
3. **`examples/bid_strategy_discovery.py`** - Interactive example script

### Modified Files
1. **`meta_ads_mcp/core/adsets.py`** - Added two new tool functions
2. **`README.md`** - Added documentation for new tools

## Code Changes

### Added to `adsets.py` (2 new functions):

```python
@mcp_server.tool()
@meta_api_tool
async def get_bid_strategy_info(
    campaign_id: str,
    optimization_goal: str,
    access_token: Optional[str] = None
) -> str:
    """Get bid strategy information and guidance"""
    # ... implementation

@mcp_server.tool()
@meta_api_tool
async def discover_bid_strategy_requirements(
    account_id: str,
    campaign_id: str,
    name: str,
    optimization_goal: str,
    billing_event: str,
    daily_budget: int,
    targeting: Dict[str, Any],
    access_token: Optional[str] = None
) -> str:
    """Discover correct bid strategy by testing combinations"""
    # ... implementation
```

## Usage Examples

### Quick Info Check
```python
from meta_ads_mcp.core.adsets import get_bid_strategy_info

result = await get_bid_strategy_info(
    campaign_id="120241682238560174",
    optimization_goal="REACH",
    access_token="YOUR_TOKEN"
)
```

### Full Discovery
```python
from meta_ads_mcp.core.adsets import discover_bid_strategy_requirements

result = await discover_bid_strategy_requirements(
    account_id="act_1445720119593938",
    campaign_id="120241682238560174",
    name="Test Bid Discovery",
    optimization_goal="REACH",
    billing_event="IMPRESSIONS",
    daily_budget=3000000,
    targeting={"geo_locations": {"countries": ["AE"]}, "age_min": 18, "age_max": 65},
    access_token="YOUR_TOKEN"
)
# Returns working bid_strategy and bid_amount
```

### Using MCP Client (Claude, Cursor, etc.)
```
User: "I'm getting error 2490487 when creating a REACH ad set. Can you help me find the right bid strategy?"

AI: "I'll use the discover_bid_strategy_requirements tool to find what works..."
    [Calls tool with campaign and targeting info]
    "Found it! Your account requires LOWEST_COST_WITH_BID_CAP with bid_amount: 300000"
```

## Testing

### Run Tests
```bash
# Unit tests (no API calls)
pytest tests/test_bid_strategy_discovery.py::test_discover_bid_strategy_requirements_dry_run

# Live test (requires token)
export META_ACCESS_TOKEN=your_token
export RUN_LIVE_TESTS=1
pytest tests/test_bid_strategy_discovery.py::test_discover_bid_strategy_live
```

### Run Example
```bash
cd meta-ads-mcp
export META_ACCESS_TOKEN=your_token
python examples/bid_strategy_discovery.py
```

## Benefits

1. **Solves Common Error** - Automatically resolves error 2490487
2. **Saves Time** - No manual trial-and-error in Ads Manager
3. **Account-Specific** - Discovers requirements specific to your account
4. **Educational** - Shows what different bid strategies do
5. **Safe** - Creates test ad sets as PAUSED (can be deleted)
6. **AI-Friendly** - Works seamlessly with AI agents via MCP

## Technical Details

### API Endpoints Used
- `GET /{campaign_id}` - Get campaign details
- `GET /{campaign_id}/adsets` - Get existing ad sets
- `POST /{account_id}/adsets` - Create test ad sets

### Error Handling
- Catches and reports specific Meta API errors
- Provides helpful next steps when nothing works
- Includes account-level restriction detection

### Return Format
All tools return JSON with:
- Structured data about bid strategies
- Success/failure status for each test
- Detailed error messages
- Actionable recommendations
- Links to related documentation

## Future Enhancements

Potential improvements:
1. Cache discovered bid strategies per account/objective
2. Support for more bid constraints (ROAS, cost_per_result_goal)
3. Integration with account settings API
4. Historical tracking of successful configurations
5. Smart defaults based on campaign objective

## Documentation

- **User Guide:** `BID_STRATEGY_DISCOVERY.md`
- **API Docs:** Updated in `README.md`
- **Code Examples:** `examples/bid_strategy_discovery.py`
- **Tests:** `tests/test_bid_strategy_discovery.py`

## Deployment

No special deployment needed:
1. Changes are in existing Python module
2. MCP server automatically picks up new @mcp_server.tool() decorators
3. Tools immediately available to all MCP clients

## Support

For questions or issues:
- See `BID_STRATEGY_DISCOVERY.md` for detailed guide
- Check `examples/bid_strategy_discovery.py` for usage patterns
- Review test cases in `tests/test_bid_strategy_discovery.py`
- Discord: https://discord.gg/YzMwQ8zrjr
- Email: info@pipeboard.co
