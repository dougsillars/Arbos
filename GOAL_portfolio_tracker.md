# Dual Trusted Stake Strategy Tracker

Monitor and analyze two competing Trusted Stake investment strategies. Fully AI managed with human execution. Compare performance to determine best client offering.

## Strategy 1: AI Managed (Diversified, Low Volatility)
- **Wallet**: `5EvwoiVLL7uWL6gdA5eqFjScWUPDewBtd9VPaApiWx1Tx6cd`
- **wallet_key**: `ai_managed`
- **Target**: 15-20% ROI per month (GOAL >20%)
- **Approach**: Big spread of subnets, low volatility, steadily growing equity curve
- **Based on**: SN88 / Investing88 methodology with AI-tuned parameters
- **Rebalance**: Every 1-3 days to optimise for ROI
- **Key focus**: Handle large amounts of TAO with lower risk & volatility, great returns

## Strategy 2: BF ROI POT (Concentrated, Aggressive)
- **Wallet**: `5GmSL6ioeTuybuK8Jhk34mvnQc5gowYArAShgeRhQK1QewUr`
- **wallet_key**: `bf_roi_pot`
- **Target**: 25-30%+ ROI per month
- **Approach**: Fewer subnets, active daily management in/out of positions
- **Balance**: Volatility vs ROI — push for higher returns with managed risk
- **Example wallet**: `5Fph5Y2ZcmgNYkpkzdmy3D23FpTJWMZyARk81KE9HXfsnUqe`

---

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
    wallet_key="ai_managed",  # or "bf_roi_pot"
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
candidates = score_rotation_candidates()
for c in candidates[:5]:
    print(f"SN{c['netuid']}: score={c['score']:.3f}, 24h={c['price_change_24h']:+.1f}%, liq={c['liquidity']:.0f}")
```

Also analyze AI Managed portfolio for rebalance opportunities:
- Flag any positions that have declined >10% in 24h
- Identify subnets with improving momentum not currently held
- Suggest parameter improvements based on performance trends

Send combined report to operator. Update STATE.md `last_full_analysis_time`.

---

### On Operator Request (INBOX.md)

If INBOX.md contains a request, run the appropriate analysis:
- "compare" / "comparison" -> `compare('24h')`
- "bf analysis" / "roi pot" -> `bf_roi_pot.format_analysis()`
- "ai analysis" / "ai managed" -> analysis of AI managed portfolio
- "weekly" / "full report" -> `weekly_summary()`
- "rotation" / "candidates" -> `score_rotation_candidates()`
- "snapshot" -> force immediate snapshot for both wallets
- "rebalance" -> rebalance analysis for AI managed strategy
