"""EIP-1559 gas optimization — base fee tracking, priority fee estimation, gas limit estimation."""
import time
import statistics
from web3 import Web3
from web3.exceptions import BlockNotFound


def get_web3(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to {rpc_url}")
    return w3


def get_base_fee_history(rpc_url: str, num_blocks: int = 20) -> list:
    """Fetch base fee history for the last N blocks using eth_feeHistory."""
    w3 = get_web3(rpc_url)
    latest_block = w3.eth.block_number
    # feeHistory returns {baseFeePerGas, gasUsedRatio, oldestBlock, reward}
    fee_history = w3.eth.fee_history(
        block_count=min(num_blocks, latest_block),
        newest_block="latest",
        reward_percentiles=[25, 50, 75],
    )
    results = []
    base_fees = fee_history["baseFeePerGas"]
    gas_ratios = fee_history["gasUsedRatio"]
    oldest = fee_history["oldestBlock"]

    for i, (base_fee, ratio) in enumerate(zip(base_fees, gas_ratios)):
        results.append({
            "block": oldest + i,
            "base_fee_gwei": float(Web3.from_wei(base_fee, "gwei")),
            "base_fee_wei": base_fee,
            "gas_used_ratio": ratio,
        })
    return results


def analyze_base_fee_trend(rpc_url: str, num_blocks: int = 20) -> dict:
    """Analyze whether base fees are rising, falling, or stable."""
    history = get_base_fee_history(rpc_url, num_blocks)
    if len(history) < 2:
        return {"trend": "insufficient_data", "blocks": len(history)}

    base_fees = [h["base_fee_gwei"] for h in history]
    gas_ratios = [h["gas_used_ratio"] for h in history]

    first_half = base_fees[: len(base_fees) // 2]
    second_half = base_fees[len(base_fees) // 2 :]
    avg_first = statistics.mean(first_half) if first_half else 0
    avg_second = statistics.mean(second_half) if second_half else 0

    if avg_second > avg_first * 1.1:
        trend = "rising"
    elif avg_second < avg_first * 0.9:
        trend = "falling"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "current_base_fee_gwei": base_fees[-1],
        "average_base_fee_gwei": round(statistics.mean(base_fees), 6),
        "min_base_fee_gwei": round(min(base_fees), 6),
        "max_base_fee_gwei": round(max(base_fees), 6),
        "std_dev_gwei": round(statistics.stdev(base_fees), 6) if len(base_fees) > 1 else 0,
        "avg_gas_used_ratio": round(statistics.mean(gas_ratios), 4),
        "blocks_analyzed": len(history),
    }


def estimate_priority_fee(rpc_url: str, percentile: int = 50) -> int:
    """Estimate priority fee (tip) based on recent block rewards."""
    w3 = get_web3(rpc_url)
    fee_history = w3.eth.fee_history(
        block_count=10,
        newest_block="latest",
        reward_percentiles=[percentile],
    )
    rewards = fee_history["reward"]
    flat_rewards = []
    for block_rewards in rewards:
        for r in block_rewards:
            if r > 0:
                flat_rewards.append(r)

    if not flat_rewards:
        return w3.to_wei(1, "gwei")

    return int(statistics.median(flat_rewards))


def get_optimal_fees(rpc_url: str, urgency: str = "medium") -> dict:
    """Get recommended EIP-1559 gas parameters based on network conditions.

    urgency: 'low', 'medium', 'high'
    """
    w3 = get_web3(rpc_url)
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.eth.gas_price)

    percentile_map = {"low": 25, "medium": 50, "high": 90}
    pct = percentile_map.get(urgency, 50)
    priority_fee = estimate_priority_fee(rpc_url, pct)

    multipliers = {"low": 1.1, "medium": 1.25, "high": 2.0}
    mult = multipliers.get(urgency, 1.25)
    max_fee = int(base_fee * mult) + priority_fee

    trend = analyze_base_fee_trend(rpc_url)

    # If rising, be more aggressive
    if trend["trend"] == "rising" and urgency != "high":
        max_fee = int(max_fee * 1.3)
        priority_fee = int(priority_fee * 1.2)

    return {
        "urgency": urgency,
        "maxFeePerGas": max_fee,
        "maxFeePerGas_gwei": float(Web3.from_wei(max_fee, "gwei")),
        "maxPriorityFeePerGas": priority_fee,
        "maxPriorityFeePerGas_gwei": float(Web3.from_wei(priority_fee, "gwei")),
        "current_base_fee_gwei": float(Web3.from_wei(base_fee, "gwei")),
        "trend": trend["trend"],
    }


def estimate_gas_limit(
    rpc_url: str,
    from_address: str,
    to_address: str,
    data: str = "0x",
    value: int = 0,
) -> dict:
    """Estimate gas limit for a transaction with safety margin."""
    w3 = get_web3(rpc_url)
    estimated = w3.eth.estimate_gas(
        {
            "from": Web3.to_checksum_address(from_address),
            "to": Web3.to_checksum_address(to_address),
            "data": data,
            "value": value,
        }
    )
    # Add 20% safety margin
    safe_limit = int(estimated * 1.2)
    return {
        "estimated_gas": estimated,
        "safe_gas_limit": safe_limit,
        "margin_percent": 20,
    }


def calculate_tx_cost(rpc_url: str, gas_limit: int, urgency: str = "medium") -> dict:
    """Calculate total transaction cost in ETH and USD estimate."""
    fees = get_optimal_fees(rpc_url, urgency)
    max_cost_wei = gas_limit * fees["maxFeePerGas"]
    likely_cost_wei = gas_limit * (fees["current_base_fee_gwei"] * 1e9 + fees["maxPriorityFeePerGas"])

    w3 = get_web3(rpc_url)
    return {
        "gas_limit": gas_limit,
        "max_cost_eth": float(w3.from_wei(max_cost_wei, "ether")),
        "likely_cost_eth": float(w3.from_wei(int(likely_cost_wei), "ether")),
        "max_fee_gwei": fees["maxFeePerGas_gwei"],
        "priority_fee_gwei": fees["maxPriorityFeePerGas_gwei"],
        "urgency": urgency,
    }


def wait_for_low_gas(
    rpc_url: str,
    max_base_fee_gwei: float,
    timeout: int = 300,
    poll_interval: float = 12.0,
) -> dict:
    """Wait until base fee drops below a target. Useful for non-urgent deployments."""
    w3 = get_web3(rpc_url)
    target_wei = w3.to_wei(max_base_fee_gwei, "gwei")
    start = time.time()

    while time.time() - start < timeout:
        latest = w3.eth.get_block("latest")
        base_fee = latest.get("baseFeePerGas", 0)
        current_gwei = float(Web3.from_wei(base_fee, "gwei"))

        if base_fee <= target_wei:
            return {
                "status": "ready",
                "base_fee_gwei": current_gwei,
                "target_gwei": max_base_fee_gwei,
                "waited_seconds": time.time() - start,
                "block": latest["number"],
            }

        print(f"  Base fee: {current_gwei:.2f} Gwei (target: {max_base_fee_gwei} Gwei) — waiting...")
        time.sleep(poll_interval)

    return {"status": "timeout", "timeout_seconds": timeout}


def build_eip1559_transaction(
    rpc_url: str,
    from_address: str,
    to_address: str,
    value: int = 0,
    data: str = "0x",
    urgency: str = "medium",
) -> dict:
    """Build a complete EIP-1559 transaction with optimized gas parameters."""
    w3 = get_web3(rpc_url)
    gas_est = estimate_gas_limit(rpc_url, from_address, to_address, data, value)
    fees = get_optimal_fees(rpc_url, urgency)

    return {
        "from": Web3.to_checksum_address(from_address),
        "to": Web3.to_checksum_address(to_address),
        "value": value,
        "data": data,
        "gas": gas_est["safe_gas_limit"],
        "maxFeePerGas": fees["maxFeePerGas"],
        "maxPriorityFeePerGas": fees["maxPriorityFeePerGas"],
        "nonce": w3.eth.get_transaction_count(Web3.to_checksum_address(from_address)),
        "chainId": w3.eth.chain_id,
        "type": 2,
    }
