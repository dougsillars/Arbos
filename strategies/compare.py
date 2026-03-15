"""
Side-by-side comparison dashboard for both portfolio strategies.
"""
from .config import WALLETS, PERIODS
from .snapshots import load_latest
from .performance import calc_roi, position_changes
from .bf_roi_pot import analyze as analyze_bf
from .investing88 import analyze as analyze_i88


def compare(period: str = "24h") -> str:
    """
    Generate a markdown comparison table for both wallets over a given period.
    """
    bf = load_latest("bf_roi_pot", 1)
    jp = load_latest("jpot2", 1)

    bf_roi = calc_roi("bf_roi_pot", period)
    jp_roi = calc_roi("jpot2", period)

    bf_snap = bf[0] if bf else {}
    jp_snap = jp[0] if jp else {}

    bf_changes = position_changes("bf_roi_pot", PERIODS.get(period, 24))
    jp_changes = position_changes("jpot2", PERIODS.get(period, 24))

    bf_rotations = len(bf_changes.get("added", [])) + len(bf_changes.get("removed", []))
    jp_rotations = len(jp_changes.get("added", [])) + len(jp_changes.get("removed", []))

    # Determine winner
    bf_pct = bf_roi.get("tao_pct", 0)
    jp_pct = jp_roi.get("tao_pct", 0)
    if bf_pct > jp_pct:
        winner = f"BF ROI POT ({bf_pct:+.2f}% vs {jp_pct:+.2f}%)"
    elif jp_pct > bf_pct:
        winner = f"JPOT 2 ({jp_pct:+.2f}% vs {bf_pct:+.2f}%)"
    else:
        winner = "Tied"

    data_note = ""
    if not bf_roi.get("data_complete") or not jp_roi.get("data_complete"):
        data_note = "\n*Note: Incomplete data for one or both wallets*"

    lines = [
        f"## Portfolio Comparison ({period})\n",
        f"| Metric | BF ROI POT | JPOT 2 (88) |",
        f"|--------|-----------|-------------|",
        f"| Total TAO | {bf_snap.get('total_tao', 0):,.2f} | {jp_snap.get('total_tao', 0):,.2f} |",
        f"| {period} ROI (TAO) | {bf_pct:+.2f}% | {jp_pct:+.2f}% |",
        f"| {period} TAO Change | {bf_roi.get('tao_change', 0):+.2f} | {jp_roi.get('tao_change', 0):+.2f} |",
        f"| Annualized | {bf_roi.get('annualized_pct', 0):+.0f}% | {jp_roi.get('annualized_pct', 0):+.0f}% |",
        f"| Position Count | {bf_snap.get('position_count', 0)} | {jp_snap.get('position_count', 0)} |",
        f"| Concentration (HHI) | {bf_snap.get('concentration_hhi', 0):.4f} | {jp_snap.get('concentration_hhi', 0):.4f} |",
        f"| Top 3 Weight % | {bf_snap.get('top3_concentration_pct', 0):.1f}% | {jp_snap.get('top3_concentration_pct', 0):.1f}% |",
        f"| Rotations ({period}) | {bf_rotations} | {jp_rotations} |",
        f"",
        f"**Winner ({period} ROI):** {winner}",
        data_note,
    ]

    return "\n".join(lines)


def multi_period_compare() -> str:
    """Compare both portfolios across all time periods."""
    lines = ["# Multi-Period Portfolio Comparison\n"]

    bf_snap = load_latest("bf_roi_pot", 1)
    jp_snap = load_latest("jpot2", 1)

    if bf_snap:
        lines.append(f"**BF ROI POT:** {bf_snap[0]['total_tao']:,.2f} TAO | "
                     f"{bf_snap[0]['position_count']} positions")
    if jp_snap:
        lines.append(f"**JPOT 2:** {jp_snap[0]['total_tao']:,.2f} TAO | "
                     f"{jp_snap[0]['position_count']} positions\n")

    lines.append("| Period | BF ROI % | JPOT2 ROI % | BF TAO +/- | JPOT2 TAO +/- | Winner |")
    lines.append("|--------|---------|------------|-----------|-------------|--------|")

    for period in ["1h", "6h", "24h", "7d", "30d"]:
        bf = calc_roi("bf_roi_pot", period)
        jp = calc_roi("jpot2", period)

        bf_pct = bf.get("tao_pct", 0)
        jp_pct = jp.get("tao_pct", 0)

        if bf_pct > jp_pct:
            winner = "BF"
        elif jp_pct > bf_pct:
            winner = "JPOT2"
        else:
            winner = "Tie"

        flag_bf = "" if bf.get("data_complete") else "*"
        flag_jp = "" if jp.get("data_complete") else "*"

        lines.append(
            f"| {period} | {bf_pct:+.2f}%{flag_bf} | {jp_pct:+.2f}%{flag_jp} | "
            f"{bf.get('tao_change', 0):+.2f} | {jp.get('tao_change', 0):+.2f} | {winner} |"
        )

    lines.append("\n*asterisk = incomplete data for that period*")
    return "\n".join(lines)


def weekly_summary() -> str:
    """
    Comprehensive weekly report combining both strategy analyses
    with the comparison dashboard.
    """
    lines = ["# Weekly Portfolio Summary\n"]
    lines.append(f"---\n")

    # Multi-period comparison
    lines.append(multi_period_compare())
    lines.append("\n---\n")

    # BF ROI POT analysis
    bf = analyze_bf()
    if "error" not in bf:
        from .bf_roi_pot import format_analysis as fmt_bf
        lines.append(fmt_bf(bf))
    else:
        lines.append(f"**BF ROI POT:** {bf.get('error', 'No data')}")

    lines.append("\n---\n")

    # JPOT2 analysis
    jp = analyze_i88()
    if "error" not in jp:
        from .investing88 import format_analysis as fmt_jp
        lines.append(fmt_jp(jp))
    else:
        lines.append(f"**JPOT 2:** {jp.get('error', 'No data')}")

    lines.append("\n---\n")

    # Key observations
    lines.append("## Key Observations\n")
    if "error" not in bf and "error" not in jp:
        bf_total = bf["total_tao"]
        jp_total = jp["total_tao"]
        bf_positions = bf["position_count"]
        jp_positions = jp["position_count"]

        lines.append(f"- **Size difference:** BF ROI POT ({bf_total:.0f} TAO) is "
                     f"{bf_total/jp_total:.1f}x larger than JPOT 2 ({jp_total:.0f} TAO)")
        lines.append(f"- **Concentration:** BF uses {bf_positions} positions (HHI: {bf['concentration_hhi']:.4f}) "
                     f"vs JPOT2's {jp_positions} positions (diversification: {jp.get('diversification_score', 0)}/100)")

        if bf.get("projected_monthly_roi") is not None:
            status = "ON" if bf["on_target"] else "BELOW"
            lines.append(f"- **BF ROI POT target:** {bf['projected_monthly_roi']:+.1f}% monthly projection "
                         f"({status} target of {bf['target_range']})")

        i88 = jp.get("i88_score", {})
        if not i88.get("insufficient_data"):
            lines.append(f"- **JPOT2 I88 score:** {i88['score']:.4f} "
                         f"(MAR: {i88['mar']:.2f}, LSR: {i88['lsr']:.2f})")

        if jp.get("laggards"):
            lines.append(f"- **JPOT2 laggards:** {len(jp['laggards'])} subnets below -2% (24h)")

    return "\n".join(lines)
