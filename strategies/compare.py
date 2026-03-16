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
    ai = load_latest("ai_managed", 1)

    bf_roi = calc_roi("bf_roi_pot", period)
    ai_roi = calc_roi("ai_managed", period)

    bf_snap = bf[0] if bf else {}
    ai_snap = ai[0] if ai else {}

    bf_changes = position_changes("bf_roi_pot", PERIODS.get(period, 24))
    ai_changes = position_changes("ai_managed", PERIODS.get(period, 24))

    bf_rotations = len(bf_changes.get("added", [])) + len(bf_changes.get("removed", []))
    ai_rotations = len(ai_changes.get("added", [])) + len(ai_changes.get("removed", []))

    # Determine winner
    bf_pct = bf_roi.get("tao_pct", 0)
    ai_pct = ai_roi.get("tao_pct", 0)
    if bf_pct > ai_pct:
        winner = f"BF ROI POT ({bf_pct:+.2f}% vs {ai_pct:+.2f}%)"
    elif ai_pct > bf_pct:
        winner = f"AI Managed ({ai_pct:+.2f}% vs {bf_pct:+.2f}%)"
    else:
        winner = "Tied"

    data_note = ""
    if not bf_roi.get("data_complete") or not ai_roi.get("data_complete"):
        data_note = "\n*Note: Incomplete data for one or both wallets*"

    lines = [
        f"## Portfolio Comparison ({period})\n",
        f"| Metric | BF ROI POT | AI Managed |",
        f"|--------|-----------|------------|",
        f"| Total TAO | {bf_snap.get('total_tao', 0):,.2f} | {ai_snap.get('total_tao', 0):,.2f} |",
        f"| {period} ROI (TAO) | {bf_pct:+.2f}% | {ai_pct:+.2f}% |",
        f"| {period} TAO Change | {bf_roi.get('tao_change', 0):+.2f} | {ai_roi.get('tao_change', 0):+.2f} |",
        f"| Annualized | {bf_roi.get('annualized_pct', 0):+.0f}% | {ai_roi.get('annualized_pct', 0):+.0f}% |",
        f"| Position Count | {bf_snap.get('position_count', 0)} | {ai_snap.get('position_count', 0)} |",
        f"| Concentration (HHI) | {bf_snap.get('concentration_hhi', 0):.4f} | {ai_snap.get('concentration_hhi', 0):.4f} |",
        f"| Top 3 Weight % | {bf_snap.get('top3_concentration_pct', 0):.1f}% | {ai_snap.get('top3_concentration_pct', 0):.1f}% |",
        f"| Rotations ({period}) | {bf_rotations} | {ai_rotations} |",
        f"",
        f"**Winner ({period} ROI):** {winner}",
        data_note,
    ]

    return "\n".join(lines)


def multi_period_compare() -> str:
    """Compare both portfolios across all time periods."""
    lines = ["# Multi-Period Portfolio Comparison\n"]

    bf_snap = load_latest("bf_roi_pot", 1)
    ai_snap = load_latest("ai_managed", 1)

    if bf_snap:
        lines.append(f"**BF ROI POT:** {bf_snap[0]['total_tao']:,.2f} TAO | "
                     f"{bf_snap[0]['position_count']} positions")
    if ai_snap:
        lines.append(f"**AI Managed:** {ai_snap[0]['total_tao']:,.2f} TAO | "
                     f"{ai_snap[0]['position_count']} positions\n")

    lines.append("| Period | BF ROI % | AI Managed % | BF TAO +/- | AI TAO +/- | Winner |")
    lines.append("|--------|---------|-------------|-----------|-----------|--------|")

    for period in ["1h", "6h", "24h", "7d", "30d"]:
        bf = calc_roi("bf_roi_pot", period)
        ai = calc_roi("ai_managed", period)

        bf_pct = bf.get("tao_pct", 0)
        ai_pct = ai.get("tao_pct", 0)

        if bf_pct > ai_pct:
            winner = "BF"
        elif ai_pct > bf_pct:
            winner = "AI"
        else:
            winner = "Tie"

        flag_bf = "" if bf.get("data_complete") else "*"
        flag_ai = "" if ai.get("data_complete") else "*"

        lines.append(
            f"| {period} | {bf_pct:+.2f}%{flag_bf} | {ai_pct:+.2f}%{flag_ai} | "
            f"{bf.get('tao_change', 0):+.2f} | {ai.get('tao_change', 0):+.2f} | {winner} |"
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

    # AI Managed analysis
    ai = analyze_i88()
    if "error" not in ai:
        from .investing88 import format_analysis as fmt_ai
        lines.append(fmt_ai(ai))
    else:
        lines.append(f"**AI Managed:** {ai.get('error', 'No data')}")

    lines.append("\n---\n")

    # Key observations
    lines.append("## Key Observations\n")
    if "error" not in bf and "error" not in ai:
        bf_total = bf["total_tao"]
        ai_total = ai["total_tao"]
        bf_positions = bf["position_count"]
        ai_positions = ai["position_count"]

        ratio = bf_total / ai_total if ai_total > 0 else 0
        lines.append(f"- **Size difference:** BF ROI POT ({bf_total:.0f} TAO) is "
                     f"{ratio:.1f}x {'larger' if ratio >= 1 else 'smaller'} than AI Managed ({ai_total:.0f} TAO)")
        lines.append(f"- **Concentration:** BF uses {bf_positions} positions (HHI: {bf['concentration_hhi']:.4f}) "
                     f"vs AI Managed's {ai_positions} positions (diversification: {ai.get('diversification_score', 0)}/100)")

        if bf.get("projected_monthly_roi") is not None:
            status = "ON" if bf["on_target"] else "BELOW"
            lines.append(f"- **BF ROI POT target:** {bf['projected_monthly_roi']:+.1f}% monthly projection "
                         f"({status} target of {bf['target_range']})")

        i88 = ai.get("i88_score", {})
        if not i88.get("insufficient_data"):
            lines.append(f"- **AI Managed I88 score:** {i88['score']:.4f} "
                         f"(MAR: {i88['mar']:.2f}, LSR: {i88['lsr']:.2f})")

        if ai.get("laggards"):
            lines.append(f"- **AI Managed laggards:** {len(ai['laggards'])} subnets below -2% (24h)")

    return "\n".join(lines)
