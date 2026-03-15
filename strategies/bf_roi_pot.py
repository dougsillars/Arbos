"""
Strategy 1: BF ROI POT (Trusted Stake) - Concentrated Active Management

Targets 25-30%+ monthly ROI through concentrated positions with active rotation.
Analyzes current positions, rotation opportunities, and risk/reward balance.
"""
from .config import WALLETS
from .snapshots import load_latest, load_range
from .performance import calc_roi, position_changes


WALLET_KEY = "bf_roi_pot"
TARGET_MONTHLY_MIN = 25.0
TARGET_MONTHLY_MAX = 30.0


def analyze() -> dict:
    """
    Full analysis of the BF ROI POT portfolio.

    Returns dict with position breakdown, ROI tracking, rotation history,
    concentration metrics, and target tracking.
    """
    latest = load_latest(WALLET_KEY, 1)
    if not latest:
        return {"error": "No snapshot data available", "wallet_key": WALLET_KEY}

    snap = latest[0]
    positions = snap["positions"]
    total = snap["total_tao"]

    # Per-position analysis
    pos_analysis = []
    for p in positions:
        entry = {
            "netuid": p["netuid"],
            "tao_value": p["tao_value"],
            "pct_of_portfolio": p["pct_of_portfolio"],
            "hotkey_name": p.get("hotkey_name", ""),
            "subnet_rank": p.get("subnet_rank"),
        }
        # Add pool metrics if available
        if "pool" in p:
            entry["price_change_1h"] = p["pool"].get("price_change_1h", 0)
            entry["price_change_24h"] = p["pool"].get("price_change_24h", 0)
            entry["price_change_7d"] = p["pool"].get("price_change_7d", 0)
            entry["volume_24h"] = p["pool"].get("volume_24h", 0)
            entry["liquidity"] = p["pool"].get("liquidity", 0)
        pos_analysis.append(entry)

    # ROI across periods
    roi_data = {}
    for period in ["1h", "6h", "24h", "7d", "30d"]:
        roi_data[period] = calc_roi(WALLET_KEY, period)

    # Rotation detection (7d)
    rotations_24h = position_changes(WALLET_KEY, 24)
    rotations_7d = position_changes(WALLET_KEY, 168)

    # Concentration risk (HHI)
    weights = [p["tao_value"] / total for p in positions] if total > 0 else []
    hhi = sum(w * w for w in weights)

    # Target tracking
    monthly_roi = roi_data["30d"]["tao_pct"] if roi_data["30d"]["data_complete"] else None
    if monthly_roi is None and roi_data["7d"]["data_complete"]:
        # Project from 7d data
        monthly_roi = roi_data["7d"]["tao_pct"] * (30 / 7)
    elif monthly_roi is None and roi_data["24h"]["data_complete"]:
        monthly_roi = roi_data["24h"]["tao_pct"] * 30

    on_target = monthly_roi is not None and monthly_roi >= TARGET_MONTHLY_MIN

    return {
        "timestamp": snap["timestamp"],
        "wallet_key": WALLET_KEY,
        "wallet_name": WALLETS[WALLET_KEY]["name"],
        "total_tao": total,
        "free_tao": snap["free_tao"],
        "position_count": len(positions),
        "positions": pos_analysis,
        "concentration_hhi": round(hhi, 6),
        "top3_concentration_pct": snap["top3_concentration_pct"],
        "roi": roi_data,
        "rotations_24h": rotations_24h,
        "rotations_7d": rotations_7d,
        "projected_monthly_roi": round(monthly_roi, 2) if monthly_roi is not None else None,
        "on_target": on_target,
        "target_range": f"{TARGET_MONTHLY_MIN}-{TARGET_MONTHLY_MAX}%",
    }


def score_rotation_candidates(current_netuids: list, subnet_pools: list) -> list:
    """
    Score subnets NOT currently held as potential rotation candidates.

    Uses a composite score of:
    - 24h price momentum (40% weight)
    - Liquidity depth (30% weight)
    - Market cap ranking (30% weight)

    Args:
        current_netuids: List of netuids currently held
        subnet_pools: Raw list from GetLatestSubnetPool

    Returns:
        Top 10 candidates sorted by score
    """
    held = set(current_netuids)
    candidates = []

    # Collect metrics for normalization
    all_liquidity = []
    all_mcap = []
    for pool in subnet_pools:
        nid = pool.get("netuid", 0)
        if nid == 0:
            continue
        liq = float(pool.get("liquidity", 0))
        mcap = float(pool.get("market_cap", 0))
        all_liquidity.append(liq)
        all_mcap.append(mcap)

    max_liq = max(all_liquidity) if all_liquidity else 1
    max_mcap = max(all_mcap) if all_mcap else 1

    for pool in subnet_pools:
        nid = pool.get("netuid", 0)
        if nid == 0 or nid in held:
            continue

        price_change_24h = float(pool.get("price_change_one_day", 0))
        liquidity = float(pool.get("liquidity", 0))
        market_cap = float(pool.get("market_cap", 0))
        volume_24h = float(pool.get("tao_volume_one_day", 0))
        price = float(pool.get("price", 0))

        # Skip very low liquidity pools
        if liquidity < 100:
            continue

        # Normalize components to 0-1 range
        momentum_score = max(0, min(price_change_24h / 20, 1))  # Cap at 20%
        liquidity_score = liquidity / max_liq if max_liq > 0 else 0
        mcap_score = market_cap / max_mcap if max_mcap > 0 else 0

        composite = (momentum_score * 0.4) + (liquidity_score * 0.3) + (mcap_score * 0.3)

        candidates.append({
            "netuid": nid,
            "score": round(composite, 4),
            "price_change_24h": round(price_change_24h, 2),
            "liquidity": round(liquidity, 2),
            "market_cap": round(market_cap, 2),
            "volume_24h": round(volume_24h, 2),
            "price_tao": round(price, 6),
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:10]


def format_analysis(analysis: dict = None) -> str:
    """Generate markdown report for BF ROI POT strategy."""
    if analysis is None:
        analysis = analyze()

    if "error" in analysis:
        return f"**BF ROI POT:** {analysis['error']}"

    lines = [f"# {analysis['wallet_name']} Analysis\n"]
    lines.append(f"**Snapshot:** {analysis['timestamp']}")
    lines.append(f"**Total:** {analysis['total_tao']:.2f} TAO | "
                 f"**Positions:** {analysis['position_count']} | "
                 f"**HHI:** {analysis['concentration_hhi']:.4f}\n")

    # Target tracking
    if analysis["projected_monthly_roi"] is not None:
        status = "ON TARGET" if analysis["on_target"] else "BELOW TARGET"
        lines.append(f"**Monthly ROI Projection:** {analysis['projected_monthly_roi']:+.2f}% "
                     f"(target: {analysis['target_range']}) -- **{status}**\n")

    # Position table
    lines.append("### Current Positions\n")
    lines.append("| SN | TAO Value | % Portfolio | 24h Price | 7d Price | Liquidity |")
    lines.append("|----|-----------|-------------|-----------|----------|-----------|")
    for p in analysis["positions"]:
        name = f"SN{p['netuid']}"
        if p.get("hotkey_name"):
            name += f" ({p['hotkey_name']})"
        p24 = p.get("price_change_24h", 0)
        p7d = p.get("price_change_7d", 0)
        liq = p.get("liquidity", 0)
        lines.append(f"| {name} | {p['tao_value']:.2f} | {p['pct_of_portfolio']:.1f}% | "
                     f"{p24:+.1f}% | {p7d:+.1f}% | {liq:.0f} |")

    # ROI table
    lines.append("\n### Performance\n")
    lines.append("| Period | TAO Change | ROI % | Annualized |")
    lines.append("|--------|-----------|-------|-----------|")
    for period in ["1h", "6h", "24h", "7d", "30d"]:
        roi = analysis["roi"].get(period, {})
        if roi:
            flag = "" if roi.get("data_complete") else " *"
            lines.append(f"| {period} | {roi.get('tao_change', 0):+.2f} | "
                         f"{roi.get('tao_pct', 0):+.2f}%{flag} | "
                         f"{roi.get('annualized_pct', 0):+.0f}% |")

    # Rotations
    r24 = analysis.get("rotations_24h", {})
    if r24.get("data_available"):
        if r24["added"] or r24["removed"]:
            lines.append("\n### Rotations (24h)\n")
            for a in r24.get("added", []):
                lines.append(f"- **ENTERED** SN{a['netuid']}: {a['tao_value']:.2f} TAO")
            for r in r24.get("removed", []):
                lines.append(f"- **EXITED** SN{r['netuid']}: was {r['tao_value_at_exit']:.2f} TAO")

    lines.append("\n*partial data marked with asterisk*")
    return "\n".join(lines)
