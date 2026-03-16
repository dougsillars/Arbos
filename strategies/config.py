"""Configuration for dual portfolio tracking system."""
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SNAPSHOT_DIR = BASE_DIR / "context" / "snapshots"

WALLETS = {
    "ai_managed": {
        "name": "AI Managed (Trusted Stake SN88)",
        "address": "5EvwoiVLL7uWL6gdA5eqFjScWUPDewBtd9VPaApiWx1Tx6cd",
        "strategy": "diversified",
        "target_monthly_roi": 20.0,  # minimum target %
        "description": "AI-managed broad spread, low volatility, steady equity curve, 15-20%+ monthly ROI",
        "leaderboard_url": "https://db.investing88.ai/",
    },
    "bf_roi_pot": {
        "name": "BF ROI POT (Trusted Stake)",
        "address": "5GmSL6ioeTuybuK8Jhk34mvnQc5gowYArAShgeRhQK1QewUr",
        "strategy": "concentrated",
        "target_monthly_roi": 25.0,  # minimum target %
        "description": "Active daily management, 25-30%+ monthly ROI, fewer subnets, higher volatility tolerance",
        "example_wallet": "5Fph5Y2ZcmgNYkpkzdmy3D23FpTJWMZyARk81KE9HXfsnUqe",
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
