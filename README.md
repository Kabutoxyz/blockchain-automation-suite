# Blockchain Automation Suite

Multi-chain EVM toolkit for deploying contracts, interacting with on-chain state, monitoring events, requesting testnet funds, and optimizing EIP-1559 gas parameters.

## Features

- **Contract Deployment** — Compile & deploy Solidity contracts (ERC-20, ERC-721, custom) to any EVM chain
- **Contract Interaction** — Read state, send transactions, manage tokens
- **Event Monitoring** — Watch for Transfer/Approval events using eth_getLogs
- **Testnet Faucets** — Request test ETH on Base Sepolia, Arbitrum Sepolia, Optimism Sepolia
- **Gas Optimization** — EIP-1559 base fee tracking, priority fee estimation, cost analysis

## Install

```bash
pip install -r requirements.txt
```

## CLI Usage

```bash
# Deploy an ERC-20 token
python cli.py deploy --rpc https://sepolia.base.org --private-key 0x... --erc20 --name MyToken --symbol MTK --supply 1000000

# Deploy an ERC-721 NFT
python cli.py deploy --rpc https://sepolia.base.org --private-key 0x... --erc721 --name MyNFT --symbol MNFT

# Read contract state
python cli.py call --rpc https://sepolia.base.org --address 0x... --function balanceOf --args '["0xYourAddress"]' --erc20-abi --read

# Monitor Transfer events
python cli.py monitor --rpc https://sepolia.base.org --address 0x... --from-block 1000000

# Check testnet balances
python cli.py testnet balance --address 0x...

# Request testnet ETH
python cli.py testnet faucet --network base-sepolia --address 0x...

# Analyze gas trend
python cli.py gas https://sepolia.base.org trend

# Get optimal gas fees
python cli.py gas https://sepolia.base.org estimate --urgency high

# Wait for low gas
python cli.py gas https://sepolia.base.org wait --max-fee 0.5 --timeout 600

# Calculate transaction cost
python cli.py gas https://sepolia.base.org cost --gas-limit 200000 --urgency medium
```

## Python API

```python
from src.deployer import deploy_erc20, deploy_erc721, deploy_from_source
from src.interact import read_function, send_transaction, erc20_transfer
from src.monitor import watch_transfers, get_contract_events
from src.testnet import check_balances_all_networks, request_testnet_eth
from src.gas_optimizer import get_optimal_fees, analyze_base_fee_trend

# Deploy
result = deploy_erc20(rpc_url, private_key, "Token", "TKN", 1000000)
print(result["contract_address"])

# Read
balance = read_function(rpc_url, contract_addr, abi, "balanceOf", [address])

# Monitor
watch_transfers(rpc_url, contract_addr, from_block=100000)

# Gas
fees = get_optimal_fees(rpc_url, urgency="medium")
```

## Supported Networks

| Network | RPC | Chain ID |
|---------|-----|----------|
| Base Sepolia | https://sepolia.base.org | 84532 |
| Arbitrum Sepolia | https://sepolia-rollup.arbitrum.io/rpc | 421614 |
| Optimism Sepolia | https://sepolia.optimism.io | 11155420 |

## Project Structure

```
blockchain-automation-suite/
├── cli.py                  # CLI entry point
├── requirements.txt
├── README.md
├── contracts/
│   ├── SampleERC20.sol     # Standard ERC-20 implementation
│   └── SampleERC721.sol    # Standard ERC-721 implementation
└── src/
    ├── deployer.py         # Contract compilation & deployment
    ├── interact.py         # Read/write contract interactions
    ├── monitor.py          # Event monitoring via eth_getLogs
    ├── testnet.py          # Testnet faucet automation
    └── gas_optimizer.py    # EIP-1559 gas analysis & optimization
```


<!-- Last updated: 2026-07-08 -->
