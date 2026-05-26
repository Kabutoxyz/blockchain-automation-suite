"""Testnet faucet automation for Base Sepolia, Arbitrum Sepolia, Optimism Sepolia."""
import time
import requests
from web3 import Web3


TESTNET_CONFIGS = {
    "base-sepolia": {
        "rpc": "https://sepolia.base.org",
        "chain_id": 84532,
        "explorer": "https://sepolia.basescan.org",
        "faucet_url": "https://www.alchemy.com/faucets/base-sepolia",
        "currency": "ETH",
    },
    "arbitrum-sepolia": {
        "rpc": "https://sepolia-rollup.arbitrum.io/rpc",
        "chain_id": 421614,
        "explorer": "https://sepolia.arbiscan.io",
        "faucet_url": "https://www.alchemy.com/faucets/arbitrum-sepolia",
        "currency": "ETH",
    },
    "optimism-sepolia": {
        "rpc": "https://sepolia.optimism.io",
        "chain_id": 11155420,
        "explorer": "https://sepolia-optimistic.etherscan.io",
        "faucet_url": "https://www.alchemy.com/faucets/optimism-sepolia",
        "currency": "ETH",
    },
}


def get_testnet_config(network: str) -> dict:
    """Get configuration for a testnet."""
    network = network.lower().strip()
    if network not in TESTNET_CONFIGS:
        raise ValueError(f"Unknown network: {network}. Available: {list(TESTNET_CONFIGS.keys())}")
    return TESTNET_CONFIGS[network]


def check_balance(network: str, address: str) -> dict:
    """Check ETH balance on a testnet."""
    config = get_testnet_config(network)
    w3 = Web3(Web3.HTTPProvider(config["rpc"]))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to {config['rpc']}")
    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
    return {
        "network": network,
        "address": address,
        "balance_wei": balance_wei,
        "balance_eth": float(w3.from_wei(balance_wei, "ether")),
        "chain_id": config["chain_id"],
    }


def check_balances_all_networks(address: str) -> list:
    """Check ETH balance across all supported testnets."""
    results = []
    for network in TESTNET_CONFIGS:
        try:
            bal = check_balance(network, address)
            results.append(bal)
        except Exception as e:
            results.append({"network": network, "error": str(e)})
    return results


def request_from_alchemy_faucet(network: str, address: str) -> dict:
    """Request testnet ETH from Alchemy faucet API."""
    config = get_testnet_config(network)
    alchemy_network_map = {
        "base-sepolia": "base-sepolia",
        "arbitrum-sepolia": "arb-sepolia",
        "optimism-sepolia": "opt-sepolia",
    }
    alchemy_net = alchemy_network_map.get(network)
    if not alchemy_net:
        return {"error": f"No Alchemy faucet mapping for {network}"}

    url = f"https://faucet-api.alchemy.com/api/sendGasToken"
    payload = {
        "address": Web3.to_checksum_address(address),
        "network": alchemy_net,
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "network": network,
                "status": "success",
                "response": data,
                "faucet": "alchemy",
            }
        else:
            return {
                "network": network,
                "status": "failed",
                "http_status": resp.status_code,
                "response": resp.text,
                "faucet": "alchemy",
            }
    except Exception as e:
        return {"network": network, "status": "error", "error": str(e)}


def request_from_google_faucet(address: str) -> dict:
    """Request testnet ETH from Google Cloud Web3 Faucet (Ethereum Sepolia)."""
    url = "https://cloud.google.com/application/web3/faucet/ethereum/sepolia/api"
    payload = {"address": Web3.to_checksum_address(address)}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return {"network": "ethereum-sepolia", "status": "success", "response": resp.json(), "faucet": "google"}
        return {"network": "ethereum-sepolia", "status": "failed", "http_status": resp.status_code, "response": resp.text}
    except Exception as e:
        return {"network": "ethereum-sepolia", "status": "error", "error": str(e)}


def request_from_quicknode_faucet(network: str, address: str) -> dict:
    """Request testnet ETH from QuickNode Multi-Chain Faucet."""
    qn_network_map = {
        "base-sepolia": "base-sepolia",
        "arbitrum-sepolia": "arbitrum-sepolia",
        "optimism-sepolia": "optimism-sepolia",
    }
    qn_net = qn_network_map.get(network)
    if not qn_net:
        return {"error": f"No QuickNode faucet for {network}"}

    url = f"https://faucet.quicknode.com/api/faucet"
    payload = {
        "address": Web3.to_checksum_address(address),
        "network": qn_net,
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return {"network": network, "status": "success", "response": resp.json(), "faucet": "quicknode"}
        return {"network": network, "status": "failed", "http_status": resp.status_code, "response": resp.text}
    except Exception as e:
        return {"network": network, "status": "error", "error": str(e)}


def request_testnet_eth(network: str, address: str) -> list:
    """Try multiple faucets for a given network. Returns list of results."""
    results = []
    results.append(request_from_alchemy_faucet(network, address))
    time.sleep(1)
    results.append(request_from_quicknode_faucet(network, address))
    return results


def wait_for_balance(
    network: str, address: str, target_wei: int, timeout: int = 300, poll_interval: float = 10.0
) -> dict:
    """Poll until balance reaches target or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        bal = check_balance(network, address)
        if bal["balance_wei"] >= target_wei:
            return {
                "status": "funded",
                "elapsed_seconds": time.time() - start,
                **bal,
            }
        print(f"  Waiting... balance={bal['balance_eth']} ETH (target={Web3.from_wei(target_wei, 'ether')} ETH)")
        time.sleep(poll_interval)
    return {"status": "timeout", "elapsed_seconds": timeout}


def get_chain_info(network: str) -> dict:
    """Get live chain information from a testnet."""
    config = get_testnet_config(network)
    w3 = Web3(Web3.HTTPProvider(config["rpc"]))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to {config['rpc']}")
    latest = w3.eth.get_block("latest")
    return {
        "network": network,
        "chain_id": config["chain_id"],
        "latest_block": latest["number"],
        "block_timestamp": latest["timestamp"],
        "gas_limit": latest["gasLimit"],
        "gas_used": latest["gasUsed"],
        "base_fee": latest.get("baseFeePerGas", 0),
        "explorer": config["explorer"],
    }
