#!/usr/bin/env python3
"""
Blockchain Automation Suite - Gas Price Checker
Monitors gas prices across multiple chains
"""
import requests
from datetime import datetime

def get_eth_gas():
    """Get Ethereum gas prices from Etherscan"""
    url = "https://api.etherscan.io/api"
    params = {'module': 'gastracker', 'action': 'gasoracle'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1':
                result = data['result']
                print(f"\n⛽ Ethereum Gas Prices")
                print(f"Safe: {result['SafeGasPrice']} Gwei")
                print(f"Propose: {result['ProposeGasPrice']} Gwei")
                print(f"Fast: {result['FastGasPrice']} Gwei")
                return True
        print(f"❌ Error fetching ETH gas")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_solana_tps():
    """Get Solana TPS"""
    url = "https://api.mainnet-beta.solana.com"
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getRecentPerformanceSamples", "params": [1]}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and data['result']:
                sample = data['result'][0]
                tps = sample['numTransactions'] / sample['samplePeriodSecs']
                print(f"\n⚡ Solana Network")
                print(f"TPS: {tps:.0f}")
                print(f"Slot: {sample.get('slot', 'N/A')}")
                return True
        print(f"❌ Error fetching Solana TPS")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_polygon_gas():
    """Get Polygon gas prices"""
    url = "https://api.polygonscan.com/api"
    params = {'module': 'gastracker', 'action': 'gasoracle'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1':
                result = data['result']
                print(f"\n🟣 Polygon Gas Prices")
                print(f"Safe: {result['SafeGasPrice']} Gwei")
                print(f"Propose: {result['ProposeGasPrice']} Gwei")
                print(f"Fast: {result['FastGasPrice']} Gwei")
                return True
        print(f"❌ Error fetching Polygon gas")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print(f"🔧 Blockchain Automation Suite")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 40)
    
    get_eth_gas()
    get_solana_tps()
    get_polygon_gas()
    
    print("\n✅ All checks completed!")
