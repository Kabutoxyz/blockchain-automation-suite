#!/usr/bin/env python3
"""CLI for blockchain-automation-suite — deploy, interact, monitor, testnet, gas."""
import argparse
import json
import sys

from src.deployer import (
    deploy_erc20, deploy_erc721, deploy_from_source,
    ERC20_ABI, ERC721_ABI, compile_solidity, deploy_contract, get_web3,
)
from src.interact import (
    read_function, send_transaction, erc20_transfer, erc20_approve,
    erc20_balance, erc721_mint, erc721_owner_of, get_eth_balance,
    estimate_gas, get_transaction_receipt, get_block_info,
)
from src.monitor import (
    watch_transfers, get_contract_events, get_event_topics_for_contract,
    get_logs, build_filter_params, TRANSFER_TOPIC, APPROVAL_TOPIC,
)
from src.testnet import (
    check_balance, check_balances_all_networks, request_testnet_eth,
    get_chain_info, TESTNET_CONFIGS, wait_for_balance,
)
from src.gas_optimizer import (
    get_base_fee_history, analyze_base_fee_trend, estimate_priority_fee,
    get_optimal_fees, estimate_gas_limit, calculate_tx_cost,
    wait_for_low_gas, build_eip1559_transaction,
)


def pp(obj):
    """Pretty-print JSON-serializable object."""
    print(json.dumps(obj, indent=2, default=str))


# ─── deploy subcommand ───────────────────────────────────────────────────────

def cmd_deploy(args):
    """Deploy a contract."""
    if args.erc20:
        result = deploy_erc20(args.rpc, args.private_key, args.name, args.symbol, args.supply)
        print("ERC-20 deployed!")
        pp(result)
    elif args.erc721:
        result = deploy_erc721(args.rpc, args.private_key, args.name, args.symbol)
        print("ERC-721 deployed!")
        pp(result)
    elif args.source:
        ctor_args = json.loads(args.constructor_args) if args.constructor_args else []
        result = deploy_from_source(args.rpc, args.source, args.private_key, ctor_args)
        print("Contract deployed!")
        pp(result)
    else:
        print("Specify --erc20, --erc721, or --source <path>", file=sys.stderr)
        sys.exit(1)


def cmd_call(args):
    """Call a contract function."""
    abi = json.loads(args.abi) if args.abi else (ERC20_ABI if args.erc20_abi else ERC721_ABI)
    call_args = json.loads(args.args) if args.args else None

    if args.read:
        result = read_function(args.rpc, args.address, abi, args.function, call_args)
        print(f"Result: {result}")
    else:
        result = send_transaction(
            args.rpc, args.address, abi, args.private_key, args.function, call_args
        )
        print("Transaction sent!")
        pp(result)


def cmd_monitor(args):
    """Monitor contract events."""
    if args.watch:
        def printer(event):
            print(json.dumps(event, indent=2, default=str))
        watch_transfers(args.rpc, args.address, args.from_block, args.interval, printer)
    else:
        events = get_contract_events(
            args.rpc, args.address, args.event_sig or "Transfer(address,address,uint256)",
            args.from_block, args.to_block
        )
        print(f"Found {len(events)} events:")
        pp(events)


def cmd_testnet(args):
    """Testnet faucet and balance operations."""
    if args.action == "balance":
        result = check_balances_all_networks(args.address)
        pp(result)
    elif args.action == "faucet":
        results = request_testnet_eth(args.network, args.address)
        pp(results)
    elif args.action == "info":
        for network in TESTNET_CONFIGS:
            try:
                info = get_chain_info(network)
                pp(info)
            except Exception as e:
                print(f"{network}: {e}")
    elif args.action == "wait":
        w3 = get_web3(args.rpc or TESTNET_CONFIGS[args.network]["rpc"])
        target = int(args.target_eth * 1e18)
        result = wait_for_balance(args.network, args.address, target)
        pp(result)


def cmd_gas(args):
    """Gas optimization commands."""
    if args.action == "history":
        history = get_base_fee_history(args.rpc, args.blocks)
        pp(history)
    elif args.action == "trend":
        trend = analyze_base_fee_trend(args.rpc, args.blocks)
        pp(trend)
    elif args.action == "estimate":
        fees = get_optimal_fees(args.rpc, args.urgency)
        pp(fees)
    elif args.action == "cost":
        result = calculate_tx_cost(args.rpc, args.gas_limit, args.urgency)
        pp(result)
    elif args.action == "wait":
        result = wait_for_low_gas(args.rpc, args.max_fee, args.timeout)
        pp(result)
    elif args.action == "build":
        result = build_eip1559_transaction(
            args.rpc, args.from_address, args.to_address,
            args.value_wei or 0, args.data or "0x", args.urgency,
        )
        pp(result)


def main():
    parser = argparse.ArgumentParser(
        description="Blockchain Automation Suite — EVM contract tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # ── deploy ──
    p_deploy = subparsers.add_parser("deploy", help="Deploy a contract")
    p_deploy.add_argument("--rpc", required=True, help="RPC URL")
    p_deploy.add_argument("--private-key", required=True, help="Deployer private key")
    p_deploy.add_argument("--erc20", action="store_true", help="Deploy SampleERC20")
    p_deploy.add_argument("--erc721", action="store_true", help="Deploy SampleERC721")
    p_deploy.add_argument("--source", help="Path to custom .sol file")
    p_deploy.add_argument("--name", default="TestToken", help="Token name")
    p_deploy.add_argument("--symbol", default="TT", help="Token symbol")
    p_deploy.add_argument("--supply", type=int, default=1000000, help="ERC-20 initial supply")
    p_deploy.add_argument("--constructor-args", help="JSON array of constructor args")
    p_deploy.set_defaults(func=cmd_deploy)

    # ── call ──
    p_call = subparsers.add_parser("call", help="Call a contract function")
    p_call.add_argument("--rpc", required=True, help="RPC URL")
    p_call.add_argument("--address", required=True, help="Contract address")
    p_call.add_argument("--function", required=True, help="Function name")
    p_call.add_argument("--args", help="JSON array of arguments")
    p_call.add_argument("--abi", help="Full ABI as JSON string")
    p_call.add_argument("--erc20-abi", action="store_true", help="Use built-in ERC-20 ABI")
    p_call.add_argument("--private-key", help="Private key (for state-changing calls)")
    p_call.add_argument("--read", action="store_true", help="Read-only call (no tx)")
    p_call.set_defaults(func=cmd_call)

    # ── monitor ──
    p_monitor = subparsers.add_parser("monitor", help="Monitor on-chain events")
    p_monitor.add_argument("--rpc", required=True, help="RPC URL")
    p_monitor.add_argument("--address", required=True, help="Contract address")
    p_monitor.add_argument("--from-block", type=int, default=0, help="Start block")
    p_monitor.add_argument("--to-block", type=int, default=99999999, help="End block")
    p_monitor.add_argument("--event-sig", help="Event signature e.g. Transfer(address,address,uint256)")
    p_monitor.add_argument("--watch", action="store_true", help="Continuously poll for events")
    p_monitor.add_argument("--interval", type=float, default=5.0, help="Poll interval seconds")
    p_monitor.set_defaults(func=cmd_monitor)

    # ── testnet ──
    p_testnet = subparsers.add_parser("testnet", help="Testnet faucet and balance tools")
    p_testnet.add_argument("action", choices=["balance", "faucet", "info", "wait"],
                           help="Action to perform")
    p_testnet.add_argument("--address", help="Wallet address")
    p_testnet.add_argument("--network", default="base-sepolia", help="Network name")
    p_testnet.add_argument("--rpc", help="Override RPC URL")
    p_testnet.add_argument("--target-eth", type=float, default=0.01, help="Target ETH for wait")
    p_testnet.set_defaults(func=cmd_testnet)

    # ── gas ──
    p_gas = subparsers.add_parser("gas", help="Gas optimization tools")
    p_gas.add_argument("--rpc", required=True, help="RPC URL")
    p_gas.add_argument("action", choices=["history", "trend", "estimate", "cost", "wait", "build"],
                       help="Gas action")
    p_gas.add_argument("--blocks", type=int, default=20, help="Number of blocks to analyze")
    p_gas.add_argument("--urgency", choices=["low", "medium", "high"], default="medium")
    p_gas.add_argument("--gas-limit", type=int, default=21000, help="Gas limit for cost calc")
    p_gas.add_argument("--max-fee", type=float, default=1.0, help="Max base fee (Gwei) for wait")
    p_gas.add_argument("--timeout", type=int, default=300, help="Timeout for wait (seconds)")
    p_gas.add_argument("--from-address", help="From address for build")
    p_gas.add_argument("--to-address", help="To address for build")
    p_gas.add_argument("--value-wei", type=int, help="Value in wei for build")
    p_gas.add_argument("--data", help="Calldata hex for build")
    p_gas.set_defaults(func=cmd_gas)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
