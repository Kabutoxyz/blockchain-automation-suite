"""Deploy Solidity contracts to EVM chains using web3.py."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from web3 import Web3
from eth_account import Account


CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"

# Minimal ABIs for common interfaces
ERC20_ABI = json.loads('[{"inputs":[{"name":"_name","type":"string"},{"name":"_symbol","type":"string"},{"name":"_initialSupply","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"name":"transfer","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"spender","type":"address"},{"name":"value","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"}]')

ERC721_ABI = json.loads('[{"inputs":[{"name":"_name","type":"string"},{"name":"_symbol","type":"string"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"name":"to","type":"address"},{"name":"uri","type":"string"}],"name":"mint","outputs":[{"type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"to","type":"address"},{"name":"tokenId","type":"uint256"}],"name":"approve","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"tokenId","type":"uint256"}],"name":"transferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"tokenId","type":"uint256"}],"name":"tokenURI","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"}]')


def get_web3(rpc_url: str) -> Web3:
    """Create a Web3 instance connected to the given RPC URL."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to {rpc_url}")
    return w3


def compile_solidity(source_path: str, solc_version: str = "0.8.20") -> dict:
    """Compile a Solidity file using solc and return ABI + bytecode."""
    try:
        import solcx
    except ImportError:
        raise ImportError("Install py-solc-x: pip install py-solc-x")

    solcx.install_solc(solc_version)
    solcx.set_solc_version(solc_version)

    with open(source_path, "r") as f:
        source = f.read()

    compiled = solcx.compile_standard(
        {
            "language": "Solidity",
            "sources": {os.path.basename(source_path): {"content": source}},
            "settings": {
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
                "optimizer": {"enabled": True, "runs": 200},
            },
        },
        solc_version=solc_version,
    )

    contract_name = list(compiled["contracts"].values())[0]
    name_key = list(contract_name.keys())[0]
    data = contract_name[name_key]
    return {
        "abi": data["abi"],
        "bytecode": data["evm"]["bytecode"]["object"],
    }


def deploy_contract(
    w3: Web3,
    abi: list,
    bytecode: str,
    private_key: str,
    constructor_args: list | None = None,
    gas_limit: int = 3_000_000,
) -> str:
    """Deploy a contract and return the transaction hash."""
    account = Account.from_key(private_key)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    if constructor_args:
        tx = contract.constructor(*constructor_args).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gas": gas_limit,
                "maxFeePerGas": w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
            }
        )
    else:
        tx = contract.constructor().build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gas": gas_limit,
                "maxFeePerGas": w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
            }
        )

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()


def deploy_from_source(
    rpc_url: str,
    source_path: str,
    private_key: str,
    constructor_args: list | None = None,
    solc_version: str = "0.8.20",
) -> dict:
    """Compile and deploy a Solidity contract, return tx hash + receipt."""
    w3 = get_web3(rpc_url)
    compiled = compile_solidity(source_path, solc_version)
    tx_hash = deploy_contract(
        w3, compiled["abi"], compiled["bytecode"], private_key, constructor_args
    )
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return {
        "tx_hash": tx_hash,
        "contract_address": receipt["contractAddress"],
        "gas_used": receipt["gasUsed"],
        "block_number": receipt["blockNumber"],
        "abi": compiled["abi"],
    }


def get_contract(w3: Web3, address: str, abi: list):
    """Return a contract instance at the given address."""
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def deploy_erc20(
    rpc_url: str, private_key: str, name: str, symbol: str, supply: int
) -> dict:
    """Deploy the SampleERC20 contract."""
    source = str(CONTRACTS_DIR / "SampleERC20.sol")
    return deploy_from_source(
        rpc_url, source, private_key, constructor_args=[name, symbol, supply]
    )


def deploy_erc721(rpc_url: str, private_key: str, name: str, symbol: str) -> dict:
    """Deploy the SampleERC721 contract."""
    source = str(CONTRACTS_DIR / "SampleERC721.sol")
    return deploy_from_source(
        rpc_url, source, private_key, constructor_args=[name, symbol]
    )
