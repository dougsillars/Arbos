"""
Hourly snapshot storage and retrieval for portfolio tracking.

The Arbos agent calls MCP tools to fetch data, then passes it here for storage.
Snapshots are saved as JSON files: context/snapshots/{wallet_key}/{YYYY-MM-DDTHH}.json
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .config import SNAPSHOT_DIR, WALLETS


def save_snapshot(wallet_key: str, account_data: dict, stakes: list,
                  subnet_pools: list = None, tao_price_usd: float = 0.0) -> str:
    """
    Normalize raw MCP output and save as a snapshot.

    Args:
        wallet_key: "bf_roi_pot" or "jpot2"
        account_data: Raw output from GetAccountLatest .data[0]
        stakes: Combined list from GetStakeBalance .data (all pages)
        subnet_pools: Optional list from GetLatestSubnetPool .data
        tao_price_usd: Optional TAO/USD price

    Returns:
        Path to saved snapshot file
    """
    now = datetime.now(timezone.utc)
    wallet = WALLETS[wallet_key]

    # Parse account balances (values come as strings in TAO)
    free = float(account_data.get("balance_free", 0))
    staked = float(account_data.get("balance_staked", 0))
    total = float(account_data.get("balance_total", 0))

    # Build subnet price lookup from pool data
    pool_prices = {}
    pool_data = {}
    if subnet_pools:
        for pool in subnet_pools:
            nid = pool.get("netuid")
            if nid is not None:
                pool_prices[nid] = float(pool.get("price", 0))
                pool_data[nid] = {
                    "price": float(pool.get("price", 0)),
                    "market_cap": float(pool.get("market_cap", 0)),
                    "price_change_1h": float(pool.get("price_change_one_hour", 0)),
                    "price_change_24h": float(pool.get("price_change_one_day", 0)),
                    "price_change_7d": float(pool.get("price_change_one_week", 0)),
                    "volume_24h": float(pool.get("tao_volume_one_day", 0)),
                    "liquidity": float(pool.get("liquidity", 0)),
                }

    # Build position list from stakes
    positions = []
    total_staked_tao = 0.0
    for s in stakes:
        balance_raw = int(s.get("balance", 0))
        tao_value_raw = int(s.get("balance_as_tao", 0))
        tao_value = tao_value_raw / 1e9
        alpha_balance = balance_raw / 1e9
        netuid = s.get("netuid", 0)

        hotkey_data = s.get("hotkey", {})
        hotkey = hotkey_data.get("ss58", "") if isinstance(hotkey_data, dict) else str(hotkey_data)
        hotkey_name = s.get("hotkey_name", "")

        pos = {
            "netuid": netuid,
            "hotkey": hotkey,
            "hotkey_name": hotkey_name,
            "alpha_balance": round(alpha_balance, 4),
            "tao_value": round(tao_value, 4),
            "subnet_rank": s.get("subnet_rank"),
        }

        # Add pool data if available
        if netuid in pool_data:
            pos["pool"] = pool_data[netuid]

        positions.append(pos)
        total_staked_tao += tao_value

    # Sort by TAO value descending
    positions.sort(key=lambda p: p["tao_value"], reverse=True)

    # Calculate portfolio percentages
    for p in positions:
        p["pct_of_portfolio"] = round(
            (p["tao_value"] / total * 100) if total > 0 else 0, 2
        )

    # Concentration metrics
    weights = [p["tao_value"] / total for p in positions] if total > 0 else []
    hhi = sum(w * w for w in weights) if weights else 0
    top3_pct = sum(p["pct_of_portfolio"] for p in positions[:3])

    snapshot = {
        "timestamp": now.isoformat(),
        "wallet_key": wallet_key,
        "wallet_name": wallet["name"],
        "address": wallet["address"],
        "tao_price_usd": tao_price_usd,
        "total_tao": round(total, 4),
        "free_tao": round(free, 4),
        "staked_tao": round(total_staked_tao, 4),
        "total_usd": round(total * tao_price_usd, 2) if tao_price_usd else 0,
        "position_count": len(positions),
        "concentration_hhi": round(hhi, 6),
        "top3_concentration_pct": round(top3_pct, 2),
        "positions": positions,
        "all_subnet_pools": pool_data if pool_data else {},
    }

    # Save to file
    wallet_dir = SNAPSHOT_DIR / wallet_key
    wallet_dir.mkdir(parents=True, exist_ok=True)
    filename = now.strftime("%Y-%m-%dT%H") + ".json"
    filepath = wallet_dir / filename

    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2)

    return str(filepath)


def load_latest(wallet_key: str, n: int = 1) -> list:
    """Load the N most recent snapshots for a wallet."""
    wallet_dir = SNAPSHOT_DIR / wallet_key
    if not wallet_dir.exists():
        return []
    files = sorted(wallet_dir.glob("*.json"), reverse=True)
    results = []
    for f in files[:n]:
        with open(f) as fp:
            results.append(json.load(fp))
    return results


def load_range(wallet_key: str, hours_back: int) -> list:
    """Load all snapshots within a time window."""
    wallet_dir = SNAPSHOT_DIR / wallet_key
    if not wallet_dir.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H")

    results = []
    for f in sorted(wallet_dir.glob("*.json")):
        if f.stem >= cutoff_str:
            with open(f) as fp:
                results.append(json.load(fp))
    return results


def list_snapshots(wallet_key: str) -> list:
    """Return sorted list of snapshot file paths."""
    wallet_dir = SNAPSHOT_DIR / wallet_key
    if not wallet_dir.exists():
        return []
    return sorted(wallet_dir.glob("*.json"))


def get_snapshot_at(wallet_key: str, target_time: datetime) -> dict | None:
    """Get the snapshot closest to a target time."""
    wallet_dir = SNAPSHOT_DIR / wallet_key
    if not wallet_dir.exists():
        return None

    target_str = target_time.strftime("%Y-%m-%dT%H")
    files = sorted(wallet_dir.glob("*.json"))

    # Find closest file
    best = None
    best_diff = float("inf")
    for f in files:
        diff = abs(ord(f.stem[-2:]) - ord(target_str[-2:])) if f.stem[:10] == target_str[:10] else 999
        # Simple: just use filename comparison
        if f.stem <= target_str:
            best = f

    if best:
        with open(best) as fp:
            return json.load(fp)
    elif files:
        with open(files[0]) as fp:
            return json.load(fp)
    return None
