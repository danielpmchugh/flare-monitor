# Uniswap V2 ABIs for Flare DEX Interactions

This directory contains minimal but complete ABIs for interacting with Uniswap V2-compatible DEXs on the Flare network.

## ABI Files

### 1. IUniswapV2Factory.json
Interface for DEX factory contracts that create and track trading pairs.

**Key Functions:**
- `getPair(tokenA, tokenB)` - Get the pair address for two tokens
- `allPairs(index)` - Get pair address at specific index
- `allPairsLength()` - Get total number of pairs

### 2. IUniswapV2Router02.json
Interface for DEX router contracts that handle swaps and price quotes.

**Key Functions:**
- `getAmountsOut(amountIn, path)` - Calculate output amounts for a swap path
- `factory()` - Get the factory contract address
- `swapExactTokensForTokens()` - Execute a token swap (reference)

### 3. IUniswapV2Pair.json
Interface for individual liquidity pool pair contracts.

**Key Functions:**
- `getReserves()` - Get current reserves (reserve0, reserve1, timestamp)
- `token0()` - Get first token address
- `token1()` - Get second token address
- `totalSupply()` - Get total LP token supply
- `price0CumulativeLast()` - Get cumulative price for token0
- `price1CumulativeLast()` - Get cumulative price for token1

### 4. IERC20.json
Standard ERC20 token interface for interacting with tokens.

**Key Functions:**
- `balanceOf(address)` - Get token balance of an address
- `decimals()` - Get token decimal places
- `symbol()` - Get token symbol
- `name()` - Get token name
- `totalSupply()` - Get total token supply
- `allowance(owner, spender)` - Get spending allowance
- `approve(spender, amount)` - Approve spending
- `transfer(recipient, amount)` - Transfer tokens
- `transferFrom(sender, recipient, amount)` - Transfer tokens from another address

## Usage with web3.py

```python
import json
from web3 import Web3

# Load ABI
with open('abis/IUniswapV2Pair.json', 'r') as f:
    pair_abi = json.load(f)

# Create contract instance
w3 = Web3(Web3.HTTPProvider('https://flare-api.flare.network/ext/C/rpc'))
pair_address = '0x...'  # Pair contract address
pair_contract = w3.eth.contract(address=pair_address, abi=pair_abi)

# Call contract functions
reserves = pair_contract.functions.getReserves().call()
token0 = pair_contract.functions.token0().call()
token1 = pair_contract.functions.token1().call()

print(f"Reserve0: {reserves[0]}")
print(f"Reserve1: {reserves[1]}")
print(f"Token0: {token0}")
print(f"Token1: {token1}")
```

## Sources

These ABIs are based on the standard Uniswap V2 interfaces:
- Uniswap V2 Core: https://github.com/Uniswap/v2-core
- Uniswap V2 Periphery: https://github.com/Uniswap/v2-periphery

These are compatible with Uniswap V2 forks commonly used on Flare, including:
- SparkDEX
- BlazeSwap
- Other Uniswap V2 clones

## Notes

- All ABIs are minimal but include the essential functions needed for price monitoring and arbitrage
- ABIs follow the standard Solidity ABI format compatible with web3.py
- Functions marked as `view` or `constant` don't require gas and can be called freely
- Functions marked as `nonpayable` or without `view`/`constant` require transactions (not used for monitoring)
