# DEX ABI Quick Reference

Quick reference for using the collected ABIs with web3.py.

## Loading ABIs

```python
import json
from pathlib import Path

def load_abi(filename: str) -> list:
    """Load an ABI from the abis directory."""
    abi_path = Path(__file__).parent / 'abis' / filename
    with open(abi_path, 'r') as f:
        return json.load(f)

# Load specific ABIs
factory_abi = load_abi('IUniswapV2Factory.json')
router_abi = load_abi('IUniswapV2Router02.json')
pair_abi = load_abi('IUniswapV2Pair.json')
erc20_abi = load_abi('IERC20.json')
```

## Common Operations

### 1. Get Pair Address from Factory

```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://flare-api.flare.network/ext/C/rpc'))

factory_address = '0x...'  # DEX factory address
token_a = '0x...'  # Token A address
token_b = '0x...'  # Token B address

factory = w3.eth.contract(address=factory_address, abi=factory_abi)
pair_address = factory.functions.getPair(token_a, token_b).call()

print(f"Pair address: {pair_address}")
```

### 2. Get Pair Reserves

```python
pair = w3.eth.contract(address=pair_address, abi=pair_abi)

reserves = pair.functions.getReserves().call()
reserve0 = reserves[0]
reserve1 = reserves[1]
timestamp = reserves[2]

print(f"Reserve0: {reserve0}")
print(f"Reserve1: {reserve1}")
print(f"Last update: {timestamp}")
```

### 3. Get Token Information

```python
# Get pair tokens
token0_address = pair.functions.token0().call()
token1_address = pair.functions.token1().call()

# Get token details
token0 = w3.eth.contract(address=token0_address, abi=erc20_abi)
token1 = w3.eth.contract(address=token1_address, abi=erc20_abi)

# Fetch metadata
symbol0 = token0.functions.symbol().call()
symbol1 = token1.functions.symbol().call()
decimals0 = token0.functions.decimals().call()
decimals1 = token1.functions.decimals().call()

print(f"Token0: {symbol0} ({decimals0} decimals)")
print(f"Token1: {symbol1} ({decimals1} decimals)")
```

### 4. Calculate Exchange Rate

```python
# Calculate price of token0 in terms of token1
price_token0 = reserve1 / reserve0

# Adjust for decimals
adjusted_price = price_token0 * (10 ** decimals0) / (10 ** decimals1)

print(f"Price of {symbol0} in {symbol1}: {adjusted_price}")
```

### 5. Get Swap Quote from Router

```python
router_address = '0x...'  # DEX router address
router = w3.eth.contract(address=router_address, abi=router_abi)

amount_in = w3.to_wei(1, 'ether')  # 1 token
path = [token0_address, token1_address]

amounts_out = router.functions.getAmountsOut(amount_in, path).call()
amount_out = amounts_out[-1]  # Last element is final output

print(f"Swapping {w3.from_wei(amount_in, 'ether')} {symbol0}")
print(f"Will receive {w3.from_wei(amount_out, 'ether')} {symbol1}")
```

### 6. List All Pairs from Factory

```python
factory = w3.eth.contract(address=factory_address, abi=factory_abi)

# Get total number of pairs
total_pairs = factory.functions.allPairsLength().call()

print(f"Total pairs: {total_pairs}")

# Iterate through all pairs
for i in range(total_pairs):
    pair_address = factory.functions.allPairs(i).call()
    print(f"Pair {i}: {pair_address}")
```

### 7. Check Token Balance

```python
wallet_address = '0x...'  # Wallet to check

token = w3.eth.contract(address=token0_address, abi=erc20_abi)
balance = token.functions.balanceOf(wallet_address).call()
decimals = token.functions.decimals().call()

# Convert to human-readable format
readable_balance = balance / (10 ** decimals)

print(f"Balance: {readable_balance} {symbol0}")
```

## Helper Functions

### Calculate Liquidity Pool TVL

```python
def get_pool_tvl(pair_address: str, token0_price_usd: float, token1_price_usd: float) -> dict:
    """
    Calculate Total Value Locked in a liquidity pool.

    Args:
        pair_address: Address of the pair contract
        token0_price_usd: Price of token0 in USD
        token1_price_usd: Price of token1 in USD

    Returns:
        Dict with TVL information
    """
    pair = w3.eth.contract(address=pair_address, abi=pair_abi)

    reserves = pair.functions.getReserves().call()
    token0_address = pair.functions.token0().call()
    token1_address = pair.functions.token1().call()

    token0 = w3.eth.contract(address=token0_address, abi=erc20_abi)
    token1 = w3.eth.contract(address=token1_address, abi=erc20_abi)

    decimals0 = token0.functions.decimals().call()
    decimals1 = token1.functions.decimals().call()

    # Convert reserves to decimal
    reserve0_decimal = reserves[0] / (10 ** decimals0)
    reserve1_decimal = reserves[1] / (10 ** decimals1)

    # Calculate TVL
    tvl_token0 = reserve0_decimal * token0_price_usd
    tvl_token1 = reserve1_decimal * token1_price_usd
    total_tvl = tvl_token0 + tvl_token1

    return {
        'token0_tvl': tvl_token0,
        'token1_tvl': tvl_token1,
        'total_tvl': total_tvl,
        'reserve0': reserve0_decimal,
        'reserve1': reserve1_decimal
    }
```

### Get Price with Slippage

```python
def get_price_with_slippage(
    router_address: str,
    amount_in: int,
    path: list,
    slippage_percent: float = 0.5
) -> dict:
    """
    Get swap quote with slippage calculation.

    Args:
        router_address: Router contract address
        amount_in: Input amount (in wei)
        path: Token swap path
        slippage_percent: Slippage tolerance (default 0.5%)

    Returns:
        Dict with expected output and minimum output considering slippage
    """
    router = w3.eth.contract(address=router_address, abi=router_abi)

    amounts_out = router.functions.getAmountsOut(amount_in, path).call()
    expected_out = amounts_out[-1]

    # Calculate minimum output with slippage
    slippage_multiplier = 1 - (slippage_percent / 100)
    min_out = int(expected_out * slippage_multiplier)

    return {
        'expected_output': expected_out,
        'minimum_output': min_out,
        'slippage_percent': slippage_percent
    }
```

## Contract Addresses on Flare

Replace with actual addresses for your DEX:

```python
# Example addresses (replace with real ones)
SPARKDEX_FACTORY = '0x...'
SPARKDEX_ROUTER = '0x...'

# Common tokens on Flare
WFLR = '0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d'  # Wrapped FLR
USDT = '0x...'  # USDT on Flare
USDC = '0x...'  # USDC on Flare
```

## Error Handling

Always wrap contract calls in try-except blocks:

```python
try:
    reserves = pair.functions.getReserves().call()
except Exception as e:
    print(f"Error fetching reserves: {e}")
    # Handle error appropriately
```

## Performance Tips

1. **Batch Calls**: Use multicall pattern for multiple reads
2. **Cache ABIs**: Load ABIs once and reuse
3. **Use Websockets**: For real-time monitoring, use WSS endpoint
4. **Handle Chain Reorgs**: Always check block numbers

## See Also

- `/home/gspadz/github/flare/flare-monitor/abis/README.md` - Detailed ABI documentation
- Uniswap V2 Documentation: https://docs.uniswap.org/contracts/v2/overview
- Web3.py Documentation: https://web3py.readthedocs.io/
