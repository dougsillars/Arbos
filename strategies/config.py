"""Configuration for dual portfolio tracking system."""
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SNAPSHOT_DIR = BASE_DIR / "context" / "snapshots"

WALLETS = {
    "bf_roi_pot": {
        "name": "BF ROI POT (Trusted Stake)",
        "address": "5C5FwRHVfsUUwW65SEAvh7dt7X9NKSLBEvwW1Prd15bUESvz",
        "strategy": "concentrated",
        "target_monthly_roi": 25.0,  # minimum target %
        "description": "Active management, 25-30%+ monthly ROI target, concentrated positions",
    },
    "jpot2": {
        "name": "JPOT 2 (Investing88)",
        "address": "5EvwoiVLL7uWL6gdA5eqFjScWUPDewBtd9VPaApiWx1Tx6cd",
        "strategy": "diversified",
        "description": "Investing88 scoring mechanism, ~90 subnet diversification",
        "leaderboard_url": "https://db.investing88.ai/",
    },
}

PERIODS = {
    "1h": 1,
    "6h": 6,
    "24h": 24,
    "7d": 168,
    "30d": 720,
}

# Investing88 scoring constants (from their const.py)
I88_VALI_TAKE = 0.18
I88_CLIP_OUTLIERS = 2
I88_CLIP_DEFAULT = 1
I88_RISK_INIT_DTAO = 5
I88_WIN_SIZE_DTAO = 30
I88_DAYS_FINAL = 30
I88_DAYS_DELAY = 1
