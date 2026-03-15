# Portfolio Analysis System - Dual Strategy Tracker

Monitor two Bittensor investment portfolios hourly and produce comparative analysis.

## Wallets
- **bf_roi_pot**: `5C5FwRHVfsUUwW65SEAvh7dt7X9NKSLBEvwW1Prd15bUESvz` (concentrated, active management, 25-30%+ monthly ROI target)
- **jpot2**: `5EvwoiVLL7uWL6gdA5eqFjScWUPDewBtd9VPaApiWx1Tx6cd` (diversified ~90 subnets, Investing88 strategy)

## Each Step: Check STATE.md for Timing

Read STATE.md to determine what action to take. It tracks: `last_snapshot_time`, `last_comparison_time`, `last_full_analysis_time`.

---

### Hourly Snapshots (if >55 min since last_snapshot_time)

For EACH wallet address:

1. `mcp__taostats__GetAccountLatest(address=WALLET_ADDRESS)` -> save the `.data[0]` result
2. `mcp__taostats__GetStakeBalance(coldkey=WALLET_ADDRESS, limit=100, order="balance_as_tao_desc")`
   - If pagination shows more pages, fetch page=2, etc. until all positions retrieved
   - Concatenate all `.data` arrays
3. `mcp__taostats__GetLatestSubnetPool(limit=100, order="netuid_asc")` (fetch once, shared)
   - Fetch page=2 if needed for full coverage

4. Save snapshots using Python:
```python
import json, sys
sys.path.insert(0, '.')
from strategies.snapshots import save_snapshot

# Call save_snapshot for each wallet with the collected data
path = save_snapshot(
    wallet_key="bf_roi_pot",  # or "jpot2"
    account_data=account_data,   # .data[0] from GetAccountLatest
    stakes=stakes_list,           # combined .data from GetStakeBalance
    subnet_pools=pool_list,       # .data from GetLatestSubnetPool
)
print(f"Saved: {path}")
```

5. Update STATE.md: set `last_snapshot_time` to current UTC ISO timestamp

---

### 6-Hour Comparison (if >5.5 hours since last_comparison_time)

```python
sys.path.insert(0, '.')
from strategies.compare import compare
print(compare('24h'))
```

Send output to operator via Telegram. Update STATE.md `last_comparison_time`.

---

### Daily Full Analysis (if >23 hours since last_full_analysis_time)

```python
sys.path.insert(0, '.')
from strategies.compare import weekly_summary
print(weekly_summary())
```

Also run rotation candidate analysis for BF ROI POT:
```python
from strategies.bf_roi_pot import score_rotation_candidates
# Pass current_netuids (from latest snapshot) and subnet_pools data
candidates = score_rotation_candidates(current_netuids, subnet_pools)
for c in candidates[:5]:
    print(f"SN{c['netuid']}: score={c['score']:.3f}, 24h={c['price_change_24h']:+.1f}%, liq={c['liquidity']:.0f}")
```

Send combined report to operator. Update STATE.md `last_full_analysis_time`.

---

### On Operator Request (INBOX.md)

If INBOX.md contains a request, run the appropriate analysis:
- "compare" / "comparison" -> `compare('24h')`
- "bf analysis" / "roi pot" -> `bf_roi_pot.format_analysis()`
- "88 analysis" / "jpot" -> `investing88.format_analysis()`
- "weekly" / "full report" -> `weekly_summary()`
- "rotation" / "candidates" -> `score_rotation_candidates()`
- "snapshot" -> force immediate snapshot for both wallets
