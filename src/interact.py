"""Interact with deployed smart contracts — call functions, read state, send transactions."""
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account


def get_web3(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to {rpc_url}")
    return w3


def read_function(
    rpc_url: str, contract_address: str, abi: list, function_name: str, args: list | None = None
):
    """Call a view/pure function (no gas cost)."""
    w3 = get_web3(rpc_url)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address), abi=abi
    )
    func = contract.functions[function_name]
    if args:
        return func(*args).call()
    return func().call()


def send_transaction(
    rpc_url: str,
    contract_address: str,
    abi: list,
    private_key: str,
    function_name: str,
    args: list | None = None,
    value: int = 0,
    gas_limit: int = 300_000,
) -> dict:
    """Send a state-changing transaction to a contract function."""
    w3 = get_web3(rpc_url)
    account = Account.from_key(private_key)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address), abi=abi
    )

    func = contract.functions[function_name]
    tx_params = {
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": gas_limit,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
    }
    if value > 0:
        tx_params["value"] = value

    if args:
        tx = func(*args).build_transaction(tx_params)
    else:
        tx = func().build_transaction(tx_params)

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return {
        "tx_hash": tx_hash.hex(),
        "status": receipt["status"],
        "gas_used": receipt["gasUsed"],
        "block_number": receipt["blockNumber"],
    }


def erc20_transfer(
    rpc_url: str, contract: str, abi: list, private_key: str, to: str, amount: int
) -> dict:
    """Transfer ERC-20 tokens."""
    return send_transaction(rpc_url, contract, abi, private_key, "transfer", [to, amount])


def erc20_approve(
    rpc_url: str, contract: str, abi: list, private_key: str, spender: str, amount: int
) -> dict:
    """Approve ERC-20 spending."""
    return send_transaction(rpc_url, contract, abi, private_key, "approve", [spender, amount])


def erc20_balance(rpc_url: str, contract: str, abi: list, address: str) -> int:
    """Read ERC-20 balance."""
    return read_function(rpc_url, contract, abi, "balanceOf", [address])


def erc721_mint(
    rpc_url: str, contract: str, abi: list, private_key: str, to: str, uri: str
) -> dict:
    """Mint an ERC-721 token."""
    return send_transaction(rpc_url, contract, abi, private_key, "mint", [to, uri])


def erc721_owner_of(rpc_url: str, contract: str, abi: list, token_id: int) -> str:
    """Get ERC-721 token owner."""
    return read_function(rpc_url, contract, abi, "ownerOf", [token_id])


def get_eth_balance(rpc_url: str, address: str) -> dict:
    """Get native ETH balance for an address."""
    w3 = get_web3(rpc_url)
    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
    return {
        "address": address,
        "balance_wei": balance_wei,
        "balance_eth": float(w3.from_wei(balance_wei, "ether")),
    }


def estimate_gas(
    rpc_url: str,
    contract_address: str,
    abi: list,
    function_name: str,
    args: list | None = None,
    from_address: str | None = None,
    value: int = 0,
) -> int:
    """Estimate gas for a contract call."""
    w3 = get_web3(rpc_url)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address), abi=abi
    )
    func = contract.functions[function_name]
    params = {}
    if from_address:
        params["from"] = Web3.to_checksum_address(from_address)
    if value > 0:
        params["value"] = value
    if args:
        return func(*args).estimate_gas(params)
    return func().estimate_gas(params)


def get_transaction_receipt(rpc_url: str, tx_hash: str) -> dict:
    """Get full transaction receipt."""
    w3 = get_web3(rpc_url)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    return dict(receipt)


def get_block_info(rpc_url: str, block_number: int | str = "latest") -> dict:
    """Get block information."""
    w3 = get_web3(rpc_url)
    block = w3.eth.get_block(block_number)
    return {
        "number": block["number"],
        "hash": block["hash"].hex(),
        "timestamp": block["timestamp"],
        "gas_used": block["gasUsed"],
        "gas_limit": block["gasLimit"],
        "base_fee_per_gas": block.get("baseFeePerGas", 0),
        "transactions_count": len(block["transactions"]),
    }
