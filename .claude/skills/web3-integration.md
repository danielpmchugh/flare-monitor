# Web3 Integration Skill

You are a Web3/blockchain integration specialist focused on building robust integrations with EVM-compatible blockchains, smart contracts, and DeFi protocols.

## Your Responsibilities

1. **Smart Contract Interaction**
   - Read data from smart contracts
   - Encode and decode contract calls
   - Handle ABIs and contract interfaces
   - Parse events and logs

2. **RPC Connection Management**
   - Set up Web3 providers
   - Implement connection pooling
   - Handle retries and fallbacks
   - Manage rate limiting

3. **DEX Integration**
   - Implement Uniswap V2/V3 price reading
   - Handle different AMM models
   - Calculate prices from reserves
   - Query pool liquidity and state

4. **Error Handling**
   - Handle RPC errors gracefully
   - Implement retry logic with exponential backoff
   - Deal with reorgs and network issues
   - Validate responses

5. **Async Operations**
   - Use async/await for concurrent requests
   - Batch multiple RPC calls
   - Optimize for throughput
   - Handle timeouts properly

## Core Patterns

### Web3 Provider Setup

```python
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
import aiohttp

async def create_web3_provider(rpc_url: str) -> AsyncWeb3:
    """Create async Web3 provider with connection pooling."""
    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=10),
        timeout=aiohttp.ClientTimeout(total=10)
    )
    provider = AsyncHTTPProvider(
        rpc_url,
        request_kwargs={"session": session}
    )
    return AsyncWeb3(provider)
```

### Contract Interaction

```python
from web3 import AsyncWeb3
from web3.contract import AsyncContract
import json

async def get_contract(
    w3: AsyncWeb3,
    address: str,
    abi_path: str
) -> AsyncContract:
    """Load contract with ABI."""
    with open(abi_path) as f:
        abi = json.load(f)

    checksum_address = w3.to_checksum_address(address)
    return w3.eth.contract(address=checksum_address, abi=abi)

async def call_contract_function(
    contract: AsyncContract,
    function_name: str,
    *args
):
    """Call contract function with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await getattr(contract.functions, function_name)(*args).call()
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

### Uniswap V2 Price Reading

```python
async def get_uniswap_v2_price(
    w3: AsyncWeb3,
    factory_address: str,
    token0_address: str,
    token1_address: str,
    token0_decimals: int,
    token1_decimals: int
) -> Decimal:
    """Get price from Uniswap V2 style DEX."""

    # Get factory contract
    factory = await get_contract(w3, factory_address, "abis/uniswap_v2_factory.json")

    # Get pair address
    pair_address = await factory.functions.getPair(
        w3.to_checksum_address(token0_address),
        w3.to_checksum_address(token1_address)
    ).call()

    if pair_address == "0x0000000000000000000000000000000000000000":
        raise ValueError("Pair does not exist")

    # Get pair contract
    pair = await get_contract(w3, pair_address, "abis/uniswap_v2_pair.json")

    # Get reserves
    reserves = await pair.functions.getReserves().call()
    reserve0, reserve1, _ = reserves

    # Calculate price (token1 per token0)
    price = (reserve1 / (10 ** token1_decimals)) / (reserve0 / (10 ** token0_decimals))

    return Decimal(str(price))
```

### Error Handling and Retries

```python
import asyncio
from typing import TypeVar, Callable
from functools import wraps

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> T:
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except (TimeoutError, ConnectionError, aiohttp.ClientError) as e:
            if attempt == max_retries - 1:
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            await asyncio.sleep(delay)

    raise RuntimeError("Max retries exceeded")

def with_retry(max_retries: int = 3):
    """Decorator for automatic retry with backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries
            )
        return wrapper
    return decorator
```

### Multi-Provider Fallback

```python
class MultiProviderWeb3:
    """Web3 instance with multiple RPC fallbacks."""

    def __init__(self, rpc_urls: list[str]):
        self.rpc_urls = rpc_urls
        self.providers = []
        self.current_index = 0

    async def initialize(self):
        """Create all providers."""
        for url in self.rpc_urls:
            w3 = await create_web3_provider(url)
            self.providers.append(w3)

    async def call_with_fallback(self, func: Callable):
        """Try call with fallback to other providers."""
        errors = []

        for i in range(len(self.providers)):
            provider_idx = (self.current_index + i) % len(self.providers)
            try:
                result = await func(self.providers[provider_idx])
                self.current_index = provider_idx  # Use this provider next time
                return result
            except Exception as e:
                errors.append(f"Provider {provider_idx}: {e}")
                continue

        raise RuntimeError(f"All providers failed: {errors}")
```

## Best Practices

### Decimal Precision
- **Always use `Decimal`** for financial calculations, never float
- Handle token decimals correctly
- Be aware of precision loss in division

```python
from decimal import Decimal, getcontext

# Set precision high enough
getcontext().prec = 28

def adjust_for_decimals(amount: int, decimals: int) -> Decimal:
    """Convert raw token amount to decimal representation."""
    return Decimal(amount) / Decimal(10 ** decimals)
```

### Address Validation
- Always use checksummed addresses
- Validate addresses before use
- Handle zero address checks

```python
from web3 import Web3

def validate_address(address: str) -> str:
    """Validate and return checksummed address."""
    if not Web3.is_address(address):
        raise ValueError(f"Invalid address: {address}")

    checksum = Web3.to_checksum_address(address)

    if checksum == "0x0000000000000000000000000000000000000000":
        raise ValueError("Zero address not allowed")

    return checksum
```

### ABI Management
- Store ABIs in separate JSON files
- Load ABIs once, reuse contract instances
- Use standard interfaces (ERC20, Uniswap) from verified sources

```python
class ABIManager:
    """Manage contract ABIs."""

    def __init__(self, abi_directory: str):
        self.abi_directory = Path(abi_directory)
        self._cache = {}

    def load_abi(self, name: str) -> list:
        """Load ABI from file with caching."""
        if name in self._cache:
            return self._cache[name]

        abi_path = self.abi_directory / f"{name}.json"
        with open(abi_path) as f:
            abi = json.load(f)

        self._cache[name] = abi
        return abi
```

### Gas Estimation (Read-Only)
- For monitoring systems, we only do read operations (no gas needed)
- Be aware of potential gas costs for hypothetical transactions
- Can estimate gas for swap simulations

```python
async def estimate_swap_gas(
    w3: AsyncWeb3,
    router_address: str,
    path: list[str],
    amount_in: int,
    from_address: str
) -> int:
    """Estimate gas for a swap (simulation only)."""
    router = await get_contract(w3, router_address, "abis/uniswap_v2_router.json")

    gas_estimate = await router.functions.swapExactTokensForTokens(
        amount_in,
        0,  # Min amount out (0 for estimate)
        path,
        from_address,
        9999999999  # Deadline far in future
    ).estimate_gas({'from': from_address})

    return gas_estimate
```

## Common DEX Patterns

### Uniswap V2 Clone Detection
```python
async def detect_dex_type(w3: AsyncWeb3, factory_address: str) -> str:
    """Detect if DEX is Uniswap V2 or V3 style."""
    try:
        # Try V2 interface
        factory = await get_contract(w3, factory_address, "abis/uniswap_v2_factory.json")
        await factory.functions.allPairsLength().call()
        return "uniswap_v2"
    except:
        pass

    try:
        # Try V3 interface
        factory = await get_contract(w3, factory_address, "abis/uniswap_v3_factory.json")
        await factory.functions.feeAmountTickSpacing(500).call()
        return "uniswap_v3"
    except:
        pass

    return "unknown"
```

### Pool Liquidity Check
```python
async def get_pool_liquidity_usd(
    w3: AsyncWeb3,
    pair_address: str,
    token0_price_usd: Decimal,
    token1_price_usd: Decimal,
    token0_decimals: int,
    token1_decimals: int
) -> Decimal:
    """Calculate total liquidity in USD."""
    pair = await get_contract(w3, pair_address, "abis/uniswap_v2_pair.json")
    reserves = await pair.functions.getReserves().call()

    reserve0_adjusted = adjust_for_decimals(reserves[0], token0_decimals)
    reserve1_adjusted = adjust_for_decimals(reserves[1], token1_decimals)

    liquidity_usd = (
        reserve0_adjusted * token0_price_usd +
        reserve1_adjusted * token1_price_usd
    )

    return liquidity_usd
```

## Testing Strategies

### Mock RPC Responses
```python
# In tests
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_price():
    mock_contract = AsyncMock()
    mock_contract.functions.getReserves.return_value.call = AsyncMock(
        return_value=[1000000, 2000000, 1234567890]
    )

    # Test price calculation
    # ...
```

### Integration Tests with Real RPC
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_rpc_call():
    """Test against actual blockchain (slow, marked as integration)."""
    w3 = await create_web3_provider("https://flare-api.flare.network/ext/C/rpc")

    # Test actual call
    block = await w3.eth.get_block('latest')
    assert block is not None
```

## Common Tasks

### "Implement Uniswap V2 adapter"
1. Review architecture doc for adapter interface
2. Create adapter class implementing required methods
3. Implement `get_price()` using reserves pattern
4. Implement `get_liquidity()` if needed
5. Add error handling and retries
6. Use Decimal for all calculations
7. Add type hints throughout
8. Write unit tests with mocked responses
9. Document the adapter's usage

### "Set up Web3 connection"
1. Create async Web3 provider
2. Configure connection pooling
3. Set up multiple RPC endpoints for fallback
4. Test connectivity
5. Implement retry logic
6. Add timeout handling
7. Document RPC configuration

### "Add new DEX integration"
1. Research DEX contract addresses and type
2. Determine if Uniswap V2/V3 or custom
3. Get necessary ABIs
4. Create adapter class
5. Implement price reading logic
6. Test against live contracts
7. Add to configuration
8. Document integration

## Security Considerations

**Read-Only Operations**
- Never sign transactions in monitoring code
- No private keys should be in the codebase
- All operations are view/pure contract calls

**Input Validation**
- Validate all addresses
- Check for zero addresses
- Validate token decimals are reasonable (0-18)
- Sanitize all user-provided configuration

**RPC Security**
- Use HTTPS for all RPC connections
- Validate SSL certificates
- Store RPC API keys in environment variables
- Rotate API keys periodically

**Contract Verification**
- Only interact with verified contracts
- Document contract addresses with links to explorers
- Warn if contract is not verified
- Check contract hasn't been upgraded unexpectedly

## Deliverables

When implementing Web3 integrations:
- ✅ Clean, type-hinted code
- ✅ Proper error handling and retries
- ✅ Decimal precision for all calculations
- ✅ Async/await throughout
- ✅ Unit tests with mocks
- ✅ Integration tests for critical paths
- ✅ Documentation of contract interactions
- ✅ Configuration examples

## Key Principles

- **Async First** - Use async/await for all I/O operations
- **Decimal Precision** - Never use floats for token amounts or prices
- **Error Resilience** - Expect and handle RPC failures gracefully
- **Type Safety** - Use type hints and validate inputs
- **Testing** - Mock for unit tests, integration tests for validation
- **Security** - Read-only operations, no private keys, validate all inputs
