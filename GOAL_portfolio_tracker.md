# Dual Trusted Stake Strategy Tracker

Monitor and analyze two competing Trusted Stake investment strategies. Fully AI managed with human execution. Compare performance to determine best client offering.

**IMPORTANT: Be token-efficient. Minimize Claude API calls and output. Taostats API calls are cheap — use them freely. Do NOT send Telegram messages unless it's a scheduled daily report or operator request.**

## Strategy 1: AI Managed (Diversified, Low Volatility)
- **Wallet**: `5EvwoiVLL7uWL6gdA5eqFjScWUPDewBtd9VPaApiWx1Tx6cd`
- **wallet_key**: `ai_managed`
- **Target**: 15-20% ROI per month (GOAL >20%)
- **Approach**: Big spread of subnets, low volatility, steadily growing equity curve
- **Based on**: SN88 / Investing88 methodology with AI-tuned parameters
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

Read STATE.md to determine what action to take. It tracks: `last_snapshot_time`, `last_report_time`, `last_suggestion_review_time`.

**If nothing is due, update STATE.md with `last_check_time` and exit the step immediately. Do NOT generate output or send messages.**

---

### 4-Hour Snapshots (if >3.5 hours since last_snapshot_time)

For EACH wallet address:

1. `mcp__taostats__GetAccountLatest(address=WALLET_ADDRESS)` -> save the `.data[0]` result
2. `mcp__taostats__GetStakeBalance(coldkey=WALLET_ADDRESS, limit=100, order="balance_as_tao_desc")`
   - If pagination shows more pages, fetch page=2, etc. until all positions retrieved
3. `mcp__taostats__GetLatestSubnetPool(limit=100, order="netuid_asc")` (fetch once, shared)
   - Fetch page=2 if needed for full coverage
4. Fetch TAO flow data for ALL subnets via `subnet/latest/v1` (or use taostats MCP equivalent):
   Each subnet has `net_flow_1_day`, `net_flow_7_days`, `net_flow_30_days` — these indicate TAO flowing in/out of a subnet.
   - Positive flow = investors adding TAO (bullish signal)
   - Negative flow = investors withdrawing TAO (bearish signal)
   - Track changes in flow between snapshots — a subnet shifting from negative to positive 1D flow is a leading indicator
   - Compare 1D vs 7D vs 30D to identify trend reversals (e.g., negative 30D but positive 1D = potential recovery)
   Store flow data alongside pool data in snapshots for trend analysis.

5. Fetch 4-hour price history for ALL subnets (~128 subnets, use limit=200 per page):
   `mcp__taostats__GetDtaoPoolHistoryV1(netuid=NETUID, frequency="by_hour", limit=4, order="timestamp_desc")`
   Do this for every netuid (1-128+). ~8 pages of calls. This data is essential for finding opportunities across ALL subnets, not just held ones.
   (Account history endpoint only updates daily, so use subnet pool history for intraday price tracking)

5. Save snapshots using Python:
```python
import json, sys
sys.path.insert(0, '.')
from strategies.snapshots import save_snapshot

path = save_snapshot(
    wallet_key="ai_managed",  # or "bf_roi_pot"
    account_data=account_data,
    stakes=stakes_list,
    subnet_pools=pool_list,
)
print(f"Saved: {path}")
```

6. Update STATE.md: set `last_snapshot_time` to current UTC ISO timestamp

---

### Daily Report (if >23 hours since last_report_time)

Generate a combined report and **ALWAYS send it to the operator via `context/outbox/`**. Every summary, analysis, or report you generate MUST be written to the outbox — never just print it or save it silently. The operator reads Telegram, not log files.

```python
import sys; sys.path.insert(0, '.')
from pathlib import Path
from datetime import datetime, timezone
from strategies.compare import compare, weekly_summary

report = compare('24h')
outbox = Path("context/outbox")
outbox.mkdir(parents=True, exist_ok=True)
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
(outbox / f"daily_report_{ts}.md").write_text(report)
```

Also run rotation candidate analysis and **append results to the same outbox report**:
```python
from strategies.bf_roi_pot import score_rotation_candidates
candidates = score_rotation_candidates()
rotation_text = "\n".join(f"SN{c['netuid']}: score={c['score']:.3f}, 24h={c['price_change_24h']:+.1f}%, liq={c['liquidity']:.0f}" for c in candidates[:5])
# Append to the report file or write a second outbox file
(outbox / f"rotation_{ts}.md").write_text(f"## Rotation Candidates\n\n{rotation_text}")
```

Include suggestion accuracy stats in the report (see below).

Update STATE.md `last_report_time`.

**RULE: Any time you generate a summary, comparison, analysis, or report of any kind, you MUST write it to `context/outbox/`. If it's not in the outbox, the operator will never see it.**

**This is the ONLY scheduled Telegram message. Do not message the operator at other times unless requested.**

---

### Predictions & Suggestions System

**This is a core feature.** On each snapshot, generate and track investment suggestions.

#### Generating Suggestions
After each 4-hour snapshot, analyze ALL subnet price histories and generate specific, actionable suggestions for each wallet:
- "Rotate out of SN{X} into SN{Y}" (with rationale: momentum, liquidity, risk)
- "Increase position in SN{X} by Z%"
- "Reduce exposure to SN{X}"
- "Add new position in SN{Y}"

Use the full 4-hour price history AND tao_flow data across ALL subnets to identify:
- **Momentum trends**: price + positive flow = strong conviction
- **Flow divergence**: price flat/down but flow turning positive = early entry signal
- **Exodus signals**: negative flow accelerating = exit signal
- **Mean reversion**: oversold subnets with flow stabilizing
- Compare 1D/7D/30D flow to spot trend reversals

Save suggestions to `context/suggestions/{wallet_key}/{YYYY-MM-DD}.json`:
```json
{
  "timestamp": "ISO timestamp",
  "wallet_key": "bf_roi_pot",
  "suggestions": [
    {
      "id": "uuid",
      "action": "rotate_out",
      "from_netuid": 5,
      "to_netuid": 12,
      "rationale": "SN5 declining 3 consecutive snapshots with -2k TAO 1D flow, SN12 momentum +8% 4h with +5k TAO 1D flow and strong liquidity",
      "confidence": 0.7,
      "expected_impact_pct": 2.5
    }
  ],
  "market_context": {
    "tao_trend": "bullish/bearish/neutral",
    "top_movers": [{"netuid": 12, "change_4h": 8.5, "net_flow_1d": 5000}],
    "flow_signals": [{"netuid": 15, "flow_reversal": "neg_to_pos", "net_flow_1d": 1200, "net_flow_7d": -3000}]
  }
}
```

#### Reviewing Suggestions (if >23 hours since last_suggestion_review_time)
Once daily, review past suggestions against actual outcomes:
1. Load suggestions from 24h, 48h, and 7d ago
2. Check what actually happened to the suggested subnets using pool history:
   `mcp__taostats__GetDtaoPoolHistoryV1(netuid=NETUID, frequency="by_hour", limit=24, order="timestamp_desc")`
3. Score each suggestion: did the recommended action outperform what happened?
4. Save review to `context/suggestions/reviews/{YYYY-MM-DD}.json`:
```json
{
  "timestamp": "ISO timestamp",
  "reviews": [
    {
      "suggestion_id": "uuid",
      "suggestion_date": "2026-03-16",
      "action": "rotate_out SN5 -> SN12",
      "actual_from_change_pct": -2.1,
      "actual_to_change_pct": 5.3,
      "would_have_gained_pct": 7.4,
      "verdict": "good_call",
      "confidence_was": 0.7
    }
  ],
  "accuracy_summary": {
    "total_reviewed": 5,
    "good_calls": 3,
    "bad_calls": 2,
    "accuracy_pct": 60.0,
    "cumulative_accuracy_pct": 58.0
  }
}
```

5. Use past accuracy to calibrate future confidence scores — if a type of suggestion has been historically wrong, lower its confidence
6. Update STATE.md `last_suggestion_review_time`

---

### Sending Telegram Messages

**You do NOT have direct access to the Telegram API.** To send a message to the operator, write a `.md` file to `context/outbox/`. After your step finishes, arbos will send it and delete the file.

```python
from pathlib import Path
from datetime import datetime, timezone
outbox = Path("context/outbox")
outbox.mkdir(parents=True, exist_ok=True)
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
(outbox / f"report_{ts}.md").write_text("Your report text here")
```

Each file becomes one Telegram message (auto-split if >4000 chars). Use this for daily reports, operator responses, etc.

---

### On Operator Request (INBOX.md)

If INBOX.md contains a request, run the appropriate analysis:
- "compare" / "comparison" -> `compare('24h')`
- "bf analysis" / "roi pot" -> `bf_roi_pot.format_analysis()`
- "ai analysis" / "ai managed" -> analysis of AI managed portfolio
- "weekly" / "full report" -> `weekly_summary()`
- "rotation" / "candidates" -> `score_rotation_candidates()`
- "snapshot" -> force immediate snapshot for both wallets
- "suggestions" -> show latest suggestions and accuracy stats
- "review" -> force suggestion review
