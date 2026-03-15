"""
ROI calculations and performance tracking from snapshot data.
"""
from datetime import datetime, timezone, timedelta
from .config import WALLETS, PERIODS
from .snapshots import load_range, load_latest


def calc_roi(wallet_key: str, period: str = "24h") -> dict:
    """
    Calculate ROI for a wallet over a given period.

    Args:
        wallet_key: "bf_roi_pot" or "jpot2"
        period: One of "1h", "6h", "24h", "7d", "30d"

    Returns:
        Dict with ROI metrics
    """
    hours = PERIODS.get(period, 24)
    snapshots = load_range(wallet_key, hours + 1)  # +1 for buffer

    if len(snapshots) < 2:
        latest = load_latest(wallet_key, 1)
        return {
            "wallet_key": wallet_key,
            "wallet_name": WALLETS[wallet_key]["name"],
            "period": period,
            "start_tao": latest[0]["total_tao"] if latest else 0,
            "end_tao": latest[0]["total_tao"] if latest else 0,
            "tao_change": 0,
            "tao_pct": 0,
            "start_usd": latest[0].get("total_usd", 0) if latest else 0,
            "end_usd": latest[0].get("total_usd", 0) if latest else 0,
            "usd_change": 0,
            "usd_pct": 0,
            "annualized_pct": 0,
            "snapshots_used": len(latest),
            "data_complete": False,
        }

    start = snapshots[0]
    end = snapshots[-1]

    start_tao = start["total_tao"]
    end_tao = end["total_tao"]
    tao_change = end_tao - start_tao
    tao_pct = (tao_change / start_tao * 100) if start_tao > 0 else 0

    start_usd = start.get("total_usd", 0)
    end_usd = end.get("total_usd", 0)
    usd_change = end_usd - start_usd
    usd_pct = (usd_change / start_usd * 100) if start_usd > 0 else 0

    # Annualize based on TAO performance
    annualized = tao_pct * (8760 / hours) if hours > 0 else 0

    # Check if we have enough data for the full period
    actual_hours = len(snapshots)
    data_complete = actual_hours >= hours * 0.8  # 80% coverage

    return {
        "wallet_key": wallet_key,
        "wallet_name": WALLETS[wallet_key]["name"],
        "period": period,
        "start_tao": round(start_tao, 4),
        "end_tao": round(end_tao, 4),
        "tao_change": round(tao_change, 4),
        "tao_pct": round(tao_pct, 4),
        "start_usd": round(start_usd, 2),
        "end_usd": round(end_usd, 2),
        "usd_change": round(usd_change, 2),
        "usd_pct": round(usd_pct, 4),
        "annualized_pct": round(annualized, 2),
        "snapshots_used": len(snapshots),
        "data_complete": data_complete,
        "start_time": start["timestamp"],
        "end_time": end["timestamp"],
    }


def position_changes(wallet_key: str, hours_back: int = 24) -> dict:
    """
    Detect position changes (entries, exits, size changes) over a period.

    Returns dict with 'added', 'removed', 'changed' lists.
    """
    snapshots = load_range(wallet_key, hours_back + 1)
    if len(snapshots) < 2:
        return {"added": [], "removed": [], "changed": [], "data_available": False}

    start = snapshots[0]
    end = snapshots[-1]

    start_positions = {p["netuid"]: p for p in start["positions"]}
    end_positions = {p["netuid"]: p for p in end["positions"]}

    start_netuids = set(start_positions.keys())
    end_netuids = set(end_positions.keys())

    added = []
    for nid in end_netuids - start_netuids:
        p = end_positions[nid]
        added.append({
            "netuid": nid,
            "tao_value": p["tao_value"],
            "hotkey_name": p.get("hotkey_name", ""),
        })

    removed = []
    for nid in start_netuids - end_netuids:
        p = start_positions[nid]
        removed.append({
            "netuid": nid,
            "tao_value_at_exit": p["tao_value"],
            "hotkey_name": p.get("hotkey_name", ""),
        })

    changed = []
    for nid in start_netuids & end_netuids:
        s = start_positions[nid]
        e = end_positions[nid]
        delta = e["tao_value"] - s["tao_value"]
        pct = (delta / s["tao_value"] * 100) if s["tao_value"] > 0 else 0
        if abs(pct) > 0.5:  # Only report >0.5% changes
            changed.append({
                "netuid": nid,
                "start_tao": round(s["tao_value"], 4),
                "end_tao": round(e["tao_value"], 4),
                "delta_tao": round(delta, 4),
                "delta_pct": round(pct, 2),
                "hotkey_name": e.get("hotkey_name", ""),
            })

    changed.sort(key=lambda x: x["delta_pct"], reverse=True)

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "data_available": True,
        "period_hours": hours_back,
        "start_time": start["timestamp"],
        "end_time": end["timestamp"],
    }


def hourly_tao_series(wallet_key: str, hours_back: int = 24) -> list:
    """Return list of (timestamp, total_tao) tuples for charting."""
    snapshots = load_range(wallet_key, hours_back)
    return [(s["timestamp"], s["total_tao"]) for s in snapshots]


def format_report(wallet_key: str, periods: list = None) -> str:
    """Generate a markdown performance report for a single wallet."""
    if periods is None:
        periods = ["1h", "6h", "24h", "7d", "30d"]

    wallet = WALLETS[wallet_key]
    lines = [f"## {wallet['name']} Performance\n"]
    lines.append(f"**Address:** `{wallet['address'][:12]}...{wallet['address'][-6:]}`\n")

    latest = load_latest(wallet_key, 1)
    if latest:
        snap = latest[0]
        lines.append(f"**Current Total:** {snap['total_tao']:.2f} TAO")
        lines.append(f"**Positions:** {snap['position_count']}")
        lines.append(f"**Concentration (HHI):** {snap['concentration_hhi']:.4f}")
        lines.append(f"**Top 3 Concentration:** {snap['top3_concentration_pct']:.1f}%\n")

    lines.append("| Period | TAO Change | TAO ROI % | Annualized % | Data |")
    lines.append("|--------|-----------|-----------|-------------|------|")

    for p in periods:
        roi = calc_roi(wallet_key, p)
        flag = "ok" if roi["data_complete"] else "partial"
        lines.append(
            f"| {p} | {roi['tao_change']:+.2f} | {roi['tao_pct']:+.2f}% "
            f"| {roi['annualized_pct']:+.1f}% | {flag} |"
        )

    # Position changes (24h)
    changes = position_changes(wallet_key, 24)
    if changes["data_available"]:
        if changes["added"]:
            lines.append(f"\n**Positions Added (24h):** {len(changes['added'])}")
            for a in changes["added"]:
                lines.append(f"  - SN{a['netuid']}: {a['tao_value']:.2f} TAO")
        if changes["removed"]:
            lines.append(f"\n**Positions Removed (24h):** {len(changes['removed'])}")
            for r in changes["removed"]:
                lines.append(f"  - SN{r['netuid']}: was {r['tao_value_at_exit']:.2f} TAO")

    return "\n".join(lines)
