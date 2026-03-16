"""
Strategy 2: JPOT 2 (Investing88) - Diversified Mining Portfolio

Based on the Investing88 subnet scoring mechanism.
Tracks broad diversification across ~90 subnets and applies the 88 scoring model.

Investing88 Score = MAR * LSR * odds * daily_return
Where:
  MAR = gain / max(drawdown, risk_init/sqrt(days))
  LSR = sum(pnl) / sum(abs(pnl))
  odds = 50 + kelly(prob, pavg/lavg) / 2 * 100
  daily = daily compounded return %

Reference: https://github.com/mobiusfund/investing/tree/main/Investing/strat
"""
import math
from .config import (
    WALLETS, I88_CLIP_OUTLIERS, I88_CLIP_DEFAULT,
    I88_RISK_INIT_DTAO, I88_WIN_SIZE_DTAO, I88_DAYS_FINAL, I88_DAYS_DELAY,
)
from .snapshots import load_latest, load_range
from .performance import calc_roi, position_changes


WALLET_KEY = "ai_managed"


def _kelly(p, b):
    """Kelly criterion: optimal bet fraction."""
    return (p * (b + 1) - 1) / b if b > 0 else 0


def _drawdown(pnl_series):
    """Max drawdown from a series of daily P&L percentages."""
    peak, down = 0, 0
    gain = 0
    for pnl in pnl_series:
        gain += pnl
        peak = max(peak, gain)
        down = max(down, peak - gain)
    return down


def calc_i88_score(daily_pnl_pcts: list, risk_init: float = I88_RISK_INIT_DTAO,
                   clip_outliers: int = I88_CLIP_OUTLIERS) -> dict:
    """
    Calculate the Investing88 score from a series of daily P&L percentages.

    This replicates the scoring algorithm from simst.py.

    Args:
        daily_pnl_pcts: List of daily return percentages
        risk_init: Initial risk parameter (default 5 for dTAO)
        clip_outliers: Number of outlier days to clip (default 2)

    Returns:
        Dict with score components
    """
    if len(daily_pnl_pcts) < 2:
        return {"score": 0, "days": len(daily_pnl_pcts), "insufficient_data": True}

    days = len(daily_pnl_pcts)
    pnl = list(daily_pnl_pcts)

    # Clip outliers (top N profit days)
    sorted_positive = sorted([(i, v) for i, v in enumerate(pnl) if v > 0],
                             key=lambda x: x[1], reverse=True)
    clip_indices = [x[0] for x in sorted_positive[:clip_outliers + 1]]

    if len(clip_indices) == clip_outliers + 1:
        clip_val = pnl[clip_indices[-1]]
    elif clip_indices:
        clip_val = min(I88_CLIP_DEFAULT, pnl[clip_indices[-1]])
    else:
        clip_val = 0

    for idx in clip_indices:
        pnl[idx] = clip_val

    # Core metrics
    positive = [v for v in pnl if v > 0]
    negative = [v for v in pnl if v < 0]

    prob = len(positive) / days if days > 0 else 0
    pavg = sum(positive) / len(positive) if positive else 0
    lavg = abs(sum(negative) / len(negative)) if negative else 0.001

    # Cumulative gain
    cumulative = 1.0
    for p in pnl:
        cumulative *= (1 + p / 100)
    gain = (cumulative - 1) * 100

    # Drawdown
    risk = _drawdown(pnl)

    # Daily compounded return
    daily = ((1 + gain / 100) ** (1 / days) - 1) * 100 if days > 0 else 0
    apr = ((1 + daily / 100) ** 365 - 1) * 100

    # MAR (Modified Annualized Return ratio)
    mar = gain / max(risk, risk_init / math.sqrt(days)) if days > 0 else 0

    # LSR (Long/Short Ratio - directional consistency)
    abs_sum = sum(abs(v) for v in pnl)
    lsr = sum(pnl) / abs_sum if abs_sum > 0 else 0

    # Odds (Kelly-based)
    odds = 50 + _kelly(prob, pavg / lavg) / 2 * 100 if lavg > 0 else prob * 100
    odds = max(0, odds)

    # Final score
    score = mar * lsr * odds * daily
    score = max(0, score)

    # Days penalty for young strategies
    if days < I88_DAYS_FINAL:
        score *= (days / I88_DAYS_FINAL) ** I88_DAYS_DELAY

    return {
        "score": round(score, 4),
        "days": days,
        "gain_pct": round(gain, 4),
        "risk_pct": round(risk, 4),
        "daily_pct": round(daily, 4),
        "apr_pct": round(apr, 2),
        "mar": round(mar, 4),
        "lsr": round(lsr, 4),
        "odds": round(odds, 2),
        "prob": round(prob, 4),
        "insufficient_data": False,
    }


def diversification_score(positions: list) -> float:
    """
    Score 0-100 based on evenness of position distribution.
    100 = perfectly even across all positions.
    """
    if not positions:
        return 0
    n = len(positions)
    if n == 1:
        return 0
    total = sum(p["tao_value"] for p in positions)
    if total <= 0:
        return 0
    weights = [p["tao_value"] / total for p in positions]
    hhi = sum(w * w for w in weights)
    # Perfect distribution HHI = 1/n, worst = 1.0
    # Normalize: 0 when HHI=1, 100 when HHI=1/n
    perfect_hhi = 1.0 / n
    score = max(0, (1 - hhi) / (1 - perfect_hhi) * 100) if perfect_hhi < 1 else 100
    return round(score, 1)


def analyze() -> dict:
    """
    Full analysis of the JPOT 2 (Investing88) portfolio.

    Returns dict with distribution stats, diversification score,
    top/bottom performers, laggards, and aggregate ROI.
    """
    latest = load_latest(WALLET_KEY, 1)
    if not latest:
        return {"error": "No snapshot data available", "wallet_key": WALLET_KEY}

    snap = latest[0]
    positions = snap["positions"]
    total = snap["total_tao"]

    # Distribution stats
    tao_values = [p["tao_value"] for p in positions]
    n = len(tao_values)

    if n > 0:
        mean_tao = sum(tao_values) / n
        sorted_vals = sorted(tao_values)
        median_tao = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        variance = sum((v - mean_tao) ** 2 for v in tao_values) / n
        std_dev = math.sqrt(variance)
    else:
        mean_tao = median_tao = std_dev = 0

    distribution = {
        "mean_tao": round(mean_tao, 4),
        "median_tao": round(median_tao, 4),
        "max_tao": round(max(tao_values) if tao_values else 0, 4),
        "min_tao": round(min(tao_values) if tao_values else 0, 4),
        "std_dev": round(std_dev, 4),
    }

    # Diversification score
    div_score = diversification_score(positions)

    # Top and bottom performers (by pool 24h price change if available)
    positions_with_pool = [p for p in positions if "pool" in p]
    if positions_with_pool:
        by_24h = sorted(positions_with_pool, key=lambda p: p["pool"].get("price_change_24h", 0), reverse=True)
        top10 = [{
            "netuid": p["netuid"],
            "tao_value": p["tao_value"],
            "price_change_24h": p["pool"].get("price_change_24h", 0),
            "hotkey_name": p.get("hotkey_name", ""),
        } for p in by_24h[:10]]
        bottom10 = [{
            "netuid": p["netuid"],
            "tao_value": p["tao_value"],
            "price_change_24h": p["pool"].get("price_change_24h", 0),
            "hotkey_name": p.get("hotkey_name", ""),
        } for p in by_24h[-10:]]

        # Laggards: negative 24h performance
        laggards = [{
            "netuid": p["netuid"],
            "tao_value": p["tao_value"],
            "price_change_24h": p["pool"].get("price_change_24h", 0),
        } for p in by_24h if p["pool"].get("price_change_24h", 0) < -2]
    else:
        top10 = bottom10 = laggards = []

    # ROI across periods
    roi_data = {}
    for period in ["1h", "6h", "24h", "7d", "30d"]:
        roi_data[period] = calc_roi(WALLET_KEY, period)

    # Build daily P&L series from snapshots for i88 scoring
    daily_snapshots = load_range(WALLET_KEY, 24 * I88_WIN_SIZE_DTAO)
    daily_pnl = []
    for i in range(1, len(daily_snapshots)):
        prev = daily_snapshots[i - 1]["total_tao"]
        curr = daily_snapshots[i]["total_tao"]
        if prev > 0:
            daily_pnl.append((curr - prev) / prev * 100)

    i88_score = calc_i88_score(daily_pnl) if daily_pnl else {"score": 0, "insufficient_data": True}

    return {
        "timestamp": snap["timestamp"],
        "wallet_key": WALLET_KEY,
        "wallet_name": WALLETS[WALLET_KEY]["name"],
        "total_tao": total,
        "free_tao": snap["free_tao"],
        "position_count": n,
        "distribution": distribution,
        "diversification_score": div_score,
        "top10": top10,
        "bottom10": bottom10,
        "laggards": laggards,
        "roi": roi_data,
        "i88_score": i88_score,
    }


def format_analysis(analysis: dict = None) -> str:
    """Generate markdown report for JPOT 2 strategy."""
    if analysis is None:
        analysis = analyze()

    if "error" in analysis:
        return f"**JPOT 2:** {analysis['error']}"

    lines = [f"# {analysis['wallet_name']} Analysis\n"]
    lines.append(f"**Snapshot:** {analysis['timestamp']}")
    lines.append(f"**Total:** {analysis['total_tao']:.2f} TAO | "
                 f"**Positions:** {analysis['position_count']} | "
                 f"**Diversification:** {analysis['diversification_score']}/100\n")

    # I88 Score
    i88 = analysis.get("i88_score", {})
    if not i88.get("insufficient_data"):
        lines.append("### Investing88 Score Metrics\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| **Score** | **{i88['score']:.4f}** |")
        lines.append(f"| Gain % | {i88['gain_pct']:+.2f}% |")
        lines.append(f"| Daily % | {i88['daily_pct']:+.4f}% |")
        lines.append(f"| APR | {i88['apr_pct']:+.1f}% |")
        lines.append(f"| MAR | {i88['mar']:.4f} |")
        lines.append(f"| LSR | {i88['lsr']:.4f} |")
        lines.append(f"| Odds | {i88['odds']:.1f} |")
        lines.append(f"| Risk (DD%) | {i88['risk_pct']:.2f}% |")
        lines.append(f"| Days | {i88['days']} |")

    # Distribution
    dist = analysis["distribution"]
    lines.append("\n### Position Distribution\n")
    lines.append(f"| Stat | TAO |")
    lines.append(f"|------|-----|")
    lines.append(f"| Mean | {dist['mean_tao']:.2f} |")
    lines.append(f"| Median | {dist['median_tao']:.2f} |")
    lines.append(f"| Max | {dist['max_tao']:.2f} |")
    lines.append(f"| Min | {dist['min_tao']:.2f} |")
    lines.append(f"| Std Dev | {dist['std_dev']:.2f} |")

    # ROI
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

    # Top performers
    if analysis["top10"]:
        lines.append("\n### Top 10 Performers (24h)\n")
        lines.append("| Subnet | TAO | 24h Change |")
        lines.append("|--------|-----|-----------|")
        for p in analysis["top10"]:
            lines.append(f"| SN{p['netuid']} | {p['tao_value']:.2f} | {p['price_change_24h']:+.1f}% |")

    # Laggards
    if analysis["laggards"]:
        lines.append(f"\n### Laggards ({len(analysis['laggards'])} subnets below -2% 24h)\n")
        lines.append("| Subnet | TAO | 24h Change |")
        lines.append("|--------|-----|-----------|")
        for p in analysis["laggards"][:10]:
            lines.append(f"| SN{p['netuid']} | {p['tao_value']:.2f} | {p['price_change_24h']:+.1f}% |")

    lines.append("\n*partial data marked with asterisk*")
    return "\n".join(lines)
