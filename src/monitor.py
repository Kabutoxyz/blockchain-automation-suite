"""Monitor on-chain events using eth_getLogs with filter patterns."""
import time
import json
from web3 import Web3
from web3.exceptions import BlockNotFound


# Standard event signatures
TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
APPROVAL_TOPIC = Web3.keccak(text="Approval(address,address,uint256)").hex()


def get_web3(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to {rpc_url}")
    return w3


def event_signature(sig_text: str) -> str:
    """Compute keccak256 topic0 for an event signature string."""
    return Web3.keccak(text=sig_text).hex()


def build_filter_params(
    address: str | None = None,
    topics: list | None = None,
    from_block: int | str = 0,
    to_block: int | str = "latest",
) -> dict:
    """Build eth_getLogs filter parameters."""
    params: dict = {
        "fromBlock": hex(from_block) if isinstance(from_block, int) else from_block,
        "toBlock": hex(to_block) if isinstance(to_block, int) else to_block,
    }
    if address:
        params["address"] = Web3.to_checksum_address(address)
    if topics:
        params["topics"] = topics
    return params


def get_logs(rpc_url: str, filter_params: dict) -> list:
    """Execute eth_getLogs RPC call and return decoded logs."""
    w3 = get_web3(rpc_url)
    logs = w3.eth.get_logs(filter_params)
    results = []
    for log in logs:
        entry = {
            "block_number": log["blockNumber"],
            "tx_hash": log["transactionHash"].hex(),
            "log_index": log["logIndex"],
            "address": log["address"],
            "topics": [t.hex() if isinstance(t, bytes) else t for t in log["topics"]],
            "data": log["data"].hex() if isinstance(log["data"], bytes) else log["data"],
        }
        results.append(entry)
    return results


def decode_transfer_event(log: dict) -> dict:
    """Decode a Transfer(address,address,uint256) event from raw log."""
    topics = log["topics"]
    if len(topics) < 3:
        return log
    from_addr = "0x" + topics[1][-40:]
    to_addr = "0x" + topics[2][-40:]
    data = log["data"]
    if data.startswith("0x"):
        data = data[2:]
    value = int(data, 16) if data else 0
    return {
        **log,
        "event": "Transfer",
        "from": Web3.to_checksum_address(from_addr),
        "to": Web3.to_checksum_address(to_addr),
        "value": value,
    }


def watch_transfers(
    rpc_url: str,
    contract_address: str,
    from_block: int,
    poll_interval: float = 5.0,
    callback=None,
):
    """Poll for new Transfer events from a contract. Yields decoded events."""
    w3 = get_web3(rpc_url)
    current_block = from_block
    print(f"Watching transfers on {contract_address} from block {from_block}...")

    while True:
        try:
            latest = w3.eth.block_number
            if latest < current_block:
                time.sleep(poll_interval)
                continue

            filter_params = build_filter_params(
                address=contract_address,
                topics=[TRANSFER_TOPIC],
                from_block=current_block,
                to_block=latest,
            )
            logs = get_logs(rpc_url, filter_params)
            for log in logs:
                decoded = decode_transfer_event(log)
                if callback:
                    callback(decoded)
                else:
                    print(
                        f"  Block {decoded['block_number']}: "
                        f"{decoded['from']} -> {decoded['to']} "
                        f"amount={decoded['value']}"
                    )
            current_block = latest + 1
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("Stopped watching.")
            break
        except Exception as e:
            print(f"Error polling: {e}")
            time.sleep(poll_interval)


def get_contract_events(
    rpc_url: str,
    contract_address: str,
    event_signature_text: str,
    from_block: int = 0,
    to_block: int | str = "latest",
) -> list:
    """Query past events matching a specific event signature."""
    topic0 = event_signature(event_signature_text)
    filter_params = build_filter_params(
        address=contract_address,
        topics=[topic0],
        from_block=from_block,
        to_block=to_block,
    )
    raw_logs = get_logs(rpc_url, filter_params)
    if "Transfer" in event_signature_text:
        return [decode_transfer_event(log) for log in raw_logs]
    return raw_logs


def monitor_pending_transactions(rpc_url: str, to_address: str | None = None, callback=None):
    """Subscribe to pending transactions using eth_subscribe (WebSocket required)."""
    w3 = get_web3(rpc_url)
    if not hasattr(w3.eth, "subscribe"):
        print("eth_subscribe requires a WebSocket provider.")
        return

    try:
        sub = w3.eth.subscribe("pendingTransactions")
        print(f"Monitoring pending transactions" + (f" to {to_address}" if to_address else ""))
        for tx_hash in sub:
            try:
                tx = w3.eth.get_transaction(tx_hash)
                if to_address and tx.get("to") and tx["to"].lower() != to_address.lower():
                    continue
                info = {
                    "hash": tx["hash"].hex(),
                    "from": tx["from"],
                    "to": tx.get("to", "contract_creation"),
                    "value": float(w3.from_wei(tx["value"], "ether")),
                    "gas": tx["gas"],
                    "gas_price": tx.get("gasPrice", 0),
                }
                if callback:
                    callback(info)
                else:
                    print(f"  Pending TX: {info['hash']} {info['from']} -> {info['to']} "
                          f"{info['value']} ETH")
            except Exception:
                continue
    except Exception as e:
        print(f"Subscription error: {e}")


def get_event_topics_for_contract(abi: list) -> dict:
    """Extract event signatures from an ABI and compute their topic0 hashes."""
    events = {}
    for item in abi:
        if item.get("type") == "event":
            name = item["name"]
            param_types = ",".join(p["type"] for p in item.get("inputs", []))
            sig = f"{name}({param_types})"
            events[name] = {
                "signature": sig,
                "topic0": event_signature(sig),
                "inputs": item.get("inputs", []),
            }
    return events
