# Spread Calculator Module

The spread calculator module provides functions to calculate price spreads between DEXes and identify arbitrage opportunities.

## Features

- **Decimal Precision**: All calculations use Python's `Decimal` type for precise financial calculations
- **Type Hints**: Full type annotations for better IDE support and code quality
- **Comprehensive Documentation**: Docstrings with examples for all functions
- **Edge Case Handling**: Robust handling of zero prices, single prices, empty lists, etc.
- **Error Handling**: Clear error messages for invalid inputs

## Core Functions

### `calculate_spread(price1, price2)`

Calculate the percentage spread between two prices.

```python
from decimal import Decimal
from flare_monitor.calculator import calculate_spread

spread = calculate_spread(Decimal('100'), Decimal('110'))
# Returns: Decimal('10.0')  # 10% spread
```

### `calculate_spread_detailed(price1, price2, dex1_name, dex2_name)`

Calculate detailed spread information including which DEX has the lower/higher price.

```python
from flare_monitor.calculator import calculate_spread_detailed

result = calculate_spread_detailed(
    Decimal('0.0045'), Decimal('0.0048'),
    'SparkDEX', 'Blazeswap'
)

print(result.low_dex)       # 'SparkDEX'
print(result.high_dex)      # 'Blazeswap'
print(result.spread_percent) # Decimal('6.67...')
```

### `find_best_arbitrage(prices, min_spread_threshold=None)`

Find the best arbitrage opportunity from a list of price points.

```python
from datetime import datetime
from flare_monitor.calculator import PricePoint, find_best_arbitrage

prices = [
    PricePoint('SparkDEX', Decimal('0.0045'), datetime.now()),
    PricePoint('Blazeswap', Decimal('0.0048'), datetime.now()),
    PricePoint('Pangolin', Decimal('0.0046'), datetime.now()),
]

best = find_best_arbitrage(prices)
print(best.low_dex)         # 'SparkDEX'
print(best.high_dex)        # 'Blazeswap'
print(best.spread_percent)  # Decimal('6.67...')
```

With minimum threshold:

```python
# Only return if spread >= 5%
best = find_best_arbitrage(prices, min_spread_threshold=Decimal('5'))
```

### `find_all_arbitrage_opportunities(prices, min_spread_threshold=None)`

Find all pairwise arbitrage opportunities, sorted by spread (descending).

```python
opportunities = find_all_arbitrage_opportunities(prices)
# Returns list of SpreadResult objects, sorted by spread_percent

for opp in opportunities:
    print(f"{opp.low_dex} → {opp.high_dex}: {opp.spread_percent:.2f}%")
```

### `calculate_profit_estimate(spread_result, trade_amount, fee_percent=0.3)`

Estimate potential profit from an arbitrage opportunity.

```python
from flare_monitor.calculator import calculate_profit_estimate

profit = calculate_profit_estimate(best, Decimal('1000'))
print(profit['gross_profit'])  # Profit before fees
print(profit['fees'])          # Trading fees (2 trades)
print(profit['net_profit'])    # Net profit after fees
print(profit['roi_percent'])   # ROI percentage
```

### `group_prices_by_pair(prices)`

Group price points by trading pair for multi-pair monitoring.

```python
prices_with_pairs = [
    ('FXRP/USDT', PricePoint('SparkDEX', Decimal('0.0045'), datetime.now())),
    ('FXRP/USDT', PricePoint('Blazeswap', Decimal('0.0048'), datetime.now())),
    ('FXRP/FLR', PricePoint('SparkDEX', Decimal('0.125'), datetime.now())),
]

grouped = group_prices_by_pair(prices_with_pairs)
# Returns: {'FXRP/USDT': [PricePoint, PricePoint], 'FXRP/FLR': [PricePoint]}
```

## Data Classes

### `PricePoint`

Represents a price from a specific DEX.

```python
from datetime import datetime
from flare_monitor.calculator import PricePoint

price = PricePoint(
    dex_name='SparkDEX',
    price=Decimal('0.0045'),
    timestamp=datetime.now(),
    liquidity=Decimal('100000')  # Optional
)
```

**Validation**: Raises `ValueError` if price is zero or negative.

### `SpreadResult`

Represents a calculated spread between two DEXes.

```python
@dataclass
class SpreadResult:
    low_dex: str              # DEX with lower price (buy here)
    high_dex: str             # DEX with higher price (sell here)
    low_price: Decimal        # Lower price
    high_price: Decimal       # Higher price
    spread_percent: Decimal   # Percentage spread
    absolute_spread: Decimal  # Absolute difference
    timestamp: datetime       # When calculated
```

## Edge Cases Handled

### Empty Price List
```python
result = find_best_arbitrage([])
# Returns: None
```

### Single Price
```python
result = find_best_arbitrage([single_price])
# Returns: None (no arbitrage possible)
```

### Identical Prices
```python
prices = [
    PricePoint('DEX1', Decimal('1'), datetime.now()),
    PricePoint('DEX2', Decimal('1'), datetime.now()),
]
result = find_best_arbitrage(prices)
# Returns: None (0% spread)
```

### Zero or Negative Prices
```python
# Raises ValueError
PricePoint('DEX1', Decimal('0'), datetime.now())
PricePoint('DEX1', Decimal('-1'), datetime.now())
calculate_spread(Decimal('0'), Decimal('100'))
```

## Decimal Precision

All calculations use Python's `Decimal` type to avoid floating-point precision issues:

```python
# Maintains precision
spread = calculate_spread(
    Decimal('0.123456789012345678901234567890'),
    Decimal('0.123456789012345678901234567891')
)
```

## Error Handling

The module provides clear error messages:

```python
# ValueError for invalid prices
calculate_spread(Decimal('0'), Decimal('100'))
# ValueError: Price 1 must be positive, got 0

# TypeError for non-numeric values
calculate_spread('invalid', Decimal('100'))
# TypeError: Prices must be numeric values: ...

# ValueError for invalid PricePoint objects
find_best_arbitrage([PricePoint(...), "not a price point"])
# ValueError: All items must be PricePoint objects, got <class 'str'>
```

## Spread Calculation Formula

The spread percentage is calculated as:

```
spread_percent = ((high_price - low_price) / low_price) * 100
```

This represents the percentage profit if you buy at the low price and sell at the high price, before considering fees and slippage.

## Profit Estimation

The profit estimation is simplified and does NOT account for:
- Slippage (price impact of large trades)
- Gas fees (transaction costs)
- Liquidity depth (available liquidity at the quoted price)
- Price changes during execution

It's useful for quick estimates but should not be relied upon for actual trading decisions.

Default assumptions:
- Trading fee: 0.3% per trade (total 0.6% for buy + sell)
- No slippage
- No gas fees

## Usage in Monitoring Application

The calculator is designed to be called continuously by the monitor:

```python
# In monitoring loop
async def monitor_prices():
    while True:
        # Fetch prices from all DEXes
        prices = await fetch_all_prices()

        # Find best arbitrage
        best = find_best_arbitrage(
            prices,
            min_spread_threshold=Decimal('5.0')  # 5% minimum
        )

        if best:
            # Alert user to opportunity
            print(f"Arbitrage: {best}")

        await asyncio.sleep(2)  # Poll interval
```

## Testing

Run the comprehensive test suite:

```bash
python3 test_calculator_manual.py
```

Run the demonstration:

```bash
python3 demo_calculator.py
```

## Performance

The calculator is optimized for real-time use:

- O(n) complexity for finding best arbitrage (single pass through prices)
- O(n²) complexity for finding all pairwise opportunities
- Efficient for typical use cases (4-10 DEXes per pair)
- Successfully tested with 100+ price points

## Thread Safety

The calculator functions are stateless and thread-safe. However, `PricePoint` and `SpreadResult` objects should not be shared between threads without proper synchronization.

## Future Enhancements

Potential improvements for future versions:

1. **Liquidity-weighted spreads**: Factor in available liquidity
2. **Gas cost estimation**: Include transaction costs
3. **Slippage calculation**: Estimate price impact
4. **Historical spread tracking**: Track spreads over time
5. **Multi-hop arbitrage**: A→B→C→A cycles
6. **Volatility adjustment**: Risk-adjusted spreads
