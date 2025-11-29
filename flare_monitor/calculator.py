"""
Spread calculator module for identifying arbitrage opportunities.

This module provides functions to calculate price spreads between different DEXes
and identify the best arbitrage opportunities from a list of prices.
"""

from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PricePoint:
    """
    Represents a price point from a specific DEX.

    Attributes:
        dex_name: Name of the DEX (e.g., 'SparkDEX', 'Blazeswap')
        price: Price as a Decimal for precision
        timestamp: When the price was fetched
        liquidity: Optional liquidity information (for future use)
    """
    dex_name: str
    price: Decimal
    timestamp: datetime
    liquidity: Optional[Decimal] = None

    def __post_init__(self):
        """Validate price is positive."""
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")


@dataclass
class SpreadResult:
    """
    Represents a calculated spread between two DEXes.

    Attributes:
        low_dex: DEX with the lower price (buy here)
        high_dex: DEX with the higher price (sell here)
        low_price: Lower price
        high_price: Higher price
        spread_percent: Percentage spread ((high - low) / low * 100)
        absolute_spread: Absolute difference (high - low)
        timestamp: When the spread was calculated
    """
    low_dex: str
    high_dex: str
    low_price: Decimal
    high_price: Decimal
    spread_percent: Decimal
    absolute_spread: Decimal
    timestamp: datetime

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Spread: {self.spread_percent:.2f}% "
            f"({self.low_dex} ${self.low_price:.6f} → "
            f"{self.high_dex} ${self.high_price:.6f})"
        )


def calculate_spread(
    price1: Decimal,
    price2: Decimal,
    price1_name: str = "Price 1",
    price2_name: str = "Price 2"
) -> Decimal:
    """
    Calculate the percentage spread between two prices.

    The spread is calculated as: ((max_price - min_price) / min_price) * 100

    Args:
        price1: First price (must be positive)
        price2: Second price (must be positive)
        price1_name: Optional name for price1 (for error messages)
        price2_name: Optional name for price2 (for error messages)

    Returns:
        Decimal: Spread percentage (always non-negative)

    Raises:
        ValueError: If either price is zero or negative
        TypeError: If prices are not Decimal or convertible to Decimal

    Examples:
        >>> from decimal import Decimal
        >>> calculate_spread(Decimal('100'), Decimal('110'))
        Decimal('10.00')
        >>> calculate_spread(Decimal('0.0045'), Decimal('0.0048'))
        Decimal('6.666666666666666666666666667')
    """
    # Validate inputs
    try:
        price1 = Decimal(str(price1))
        price2 = Decimal(str(price2))
    except (InvalidOperation, ValueError) as e:
        raise TypeError(f"Prices must be numeric values: {e}")

    if price1 <= 0:
        raise ValueError(f"{price1_name} must be positive, got {price1}")
    if price2 <= 0:
        raise ValueError(f"{price2_name} must be positive, got {price2}")

    # Calculate spread
    low_price = min(price1, price2)
    high_price = max(price1, price2)

    spread = ((high_price - low_price) / low_price) * Decimal('100')

    return spread


def calculate_spread_detailed(
    price1: Decimal,
    price2: Decimal,
    dex1_name: str,
    dex2_name: str,
    timestamp: Optional[datetime] = None
) -> SpreadResult:
    """
    Calculate detailed spread information between two prices.

    Args:
        price1: First DEX price
        price2: Second DEX price
        dex1_name: Name of first DEX
        dex2_name: Name of second DEX
        timestamp: Optional timestamp (defaults to now)

    Returns:
        SpreadResult: Detailed spread information

    Raises:
        ValueError: If either price is zero or negative
        TypeError: If prices are not Decimal or convertible to Decimal

    Examples:
        >>> from decimal import Decimal
        >>> from datetime import datetime
        >>> result = calculate_spread_detailed(
        ...     Decimal('0.0045'), Decimal('0.0048'),
        ...     'SparkDEX', 'Blazeswap'
        ... )
        >>> result.low_dex
        'SparkDEX'
        >>> result.spread_percent > Decimal('6')
        True
    """
    # Validate and convert prices
    try:
        price1 = Decimal(str(price1))
        price2 = Decimal(str(price2))
    except (InvalidOperation, ValueError) as e:
        raise TypeError(f"Prices must be numeric values: {e}")

    if price1 <= 0:
        raise ValueError(f"Price for {dex1_name} must be positive, got {price1}")
    if price2 <= 0:
        raise ValueError(f"Price for {dex2_name} must be positive, got {price2}")

    # Determine low and high
    if price1 <= price2:
        low_price, high_price = price1, price2
        low_dex, high_dex = dex1_name, dex2_name
    else:
        low_price, high_price = price2, price1
        low_dex, high_dex = dex2_name, dex1_name

    # Calculate spread
    absolute_spread = high_price - low_price
    spread_percent = (absolute_spread / low_price) * Decimal('100')

    return SpreadResult(
        low_dex=low_dex,
        high_dex=high_dex,
        low_price=low_price,
        high_price=high_price,
        spread_percent=spread_percent,
        absolute_spread=absolute_spread,
        timestamp=timestamp or datetime.now()
    )


def find_best_arbitrage(
    prices: List[PricePoint],
    min_spread_threshold: Optional[Decimal] = None
) -> Optional[SpreadResult]:
    """
    Find the best arbitrage opportunity from a list of price points.

    Identifies the maximum spread by finding the lowest and highest prices
    in the list. Returns None if there are insufficient prices or if the
    spread doesn't meet the minimum threshold.

    Args:
        prices: List of PricePoint objects from different DEXes
        min_spread_threshold: Optional minimum spread percentage to consider

    Returns:
        SpreadResult: Best arbitrage opportunity, or None if no opportunity found

    Raises:
        ValueError: If prices list contains invalid data

    Examples:
        >>> from decimal import Decimal
        >>> from datetime import datetime
        >>> prices = [
        ...     PricePoint('SparkDEX', Decimal('0.0045'), datetime.now()),
        ...     PricePoint('Blazeswap', Decimal('0.0048'), datetime.now()),
        ...     PricePoint('Pangolin', Decimal('0.0046'), datetime.now()),
        ... ]
        >>> result = find_best_arbitrage(prices)
        >>> result.low_dex
        'SparkDEX'
        >>> result.high_dex
        'Blazeswap'
    """
    # Edge case: empty list
    if not prices:
        return None

    # Edge case: single price (no arbitrage possible)
    if len(prices) < 2:
        return None

    # Validate all prices
    for price_point in prices:
        if not isinstance(price_point, PricePoint):
            raise ValueError(f"All items must be PricePoint objects, got {type(price_point)}")
        if price_point.price <= 0:
            raise ValueError(f"Invalid price for {price_point.dex_name}: {price_point.price}")

    # Find min and max prices
    min_price_point = min(prices, key=lambda p: p.price)
    max_price_point = max(prices, key=lambda p: p.price)

    # Edge case: all prices are the same
    if min_price_point.price == max_price_point.price:
        return None

    # Calculate spread
    result = calculate_spread_detailed(
        min_price_point.price,
        max_price_point.price,
        min_price_point.dex_name,
        max_price_point.dex_name,
        datetime.now()
    )

    # Check threshold
    if min_spread_threshold is not None:
        if result.spread_percent < min_spread_threshold:
            return None

    return result


def find_all_arbitrage_opportunities(
    prices: List[PricePoint],
    min_spread_threshold: Optional[Decimal] = None
) -> List[SpreadResult]:
    """
    Find all pairwise arbitrage opportunities from a list of price points.

    Calculates spreads for all unique pairs of DEXes and returns them
    sorted by spread percentage (highest first).

    Args:
        prices: List of PricePoint objects from different DEXes
        min_spread_threshold: Optional minimum spread percentage to include

    Returns:
        List[SpreadResult]: All arbitrage opportunities, sorted by spread (descending)

    Examples:
        >>> from decimal import Decimal
        >>> from datetime import datetime
        >>> prices = [
        ...     PricePoint('SparkDEX', Decimal('0.0045'), datetime.now()),
        ...     PricePoint('Blazeswap', Decimal('0.0048'), datetime.now()),
        ...     PricePoint('Pangolin', Decimal('0.0046'), datetime.now()),
        ... ]
        >>> opportunities = find_all_arbitrage_opportunities(prices)
        >>> len(opportunities)
        3
        >>> opportunities[0].spread_percent > opportunities[1].spread_percent
        True
    """
    if len(prices) < 2:
        return []

    opportunities = []

    # Calculate spreads for all unique pairs
    for i in range(len(prices)):
        for j in range(i + 1, len(prices)):
            price1 = prices[i]
            price2 = prices[j]

            # Skip if either price is invalid
            if price1.price <= 0 or price2.price <= 0:
                continue

            result = calculate_spread_detailed(
                price1.price,
                price2.price,
                price1.dex_name,
                price2.dex_name,
                datetime.now()
            )

            # Apply threshold filter
            if min_spread_threshold is None or result.spread_percent >= min_spread_threshold:
                opportunities.append(result)

    # Sort by spread percentage (descending)
    opportunities.sort(key=lambda x: x.spread_percent, reverse=True)

    return opportunities


def calculate_profit_estimate(
    spread_result: SpreadResult,
    trade_amount: Decimal,
    fee_percent: Decimal = Decimal('0.3')
) -> Dict[str, Decimal]:
    """
    Estimate potential profit from an arbitrage opportunity.

    This is a simplified calculation that doesn't account for:
    - Slippage
    - Gas fees
    - Liquidity depth
    - Price impact

    Args:
        spread_result: The arbitrage opportunity
        trade_amount: Amount to trade (in quote currency)
        fee_percent: Trading fee percentage (default 0.3% per trade)

    Returns:
        Dict with keys: 'gross_profit', 'fees', 'net_profit', 'roi_percent'

    Examples:
        >>> from decimal import Decimal
        >>> from datetime import datetime
        >>> spread = SpreadResult(
        ...     'SparkDEX', 'Blazeswap',
        ...     Decimal('100'), Decimal('110'),
        ...     Decimal('10'), Decimal('10'),
        ...     datetime.now()
        ... )
        >>> profit = calculate_profit_estimate(spread, Decimal('1000'))
        >>> profit['gross_profit'] > Decimal('0')
        True
    """
    # Calculate gross profit (spread * trade amount / 100)
    gross_profit = (spread_result.spread_percent * trade_amount) / Decimal('100')

    # Calculate fees (2 trades: buy and sell)
    total_fee_percent = fee_percent * Decimal('2')
    fees = (total_fee_percent * trade_amount) / Decimal('100')

    # Net profit
    net_profit = gross_profit - fees

    # ROI
    roi_percent = (net_profit / trade_amount) * Decimal('100') if trade_amount > 0 else Decimal('0')

    return {
        'gross_profit': gross_profit,
        'fees': fees,
        'net_profit': net_profit,
        'roi_percent': roi_percent
    }


def group_prices_by_pair(
    prices: List[Tuple[str, PricePoint]]
) -> Dict[str, List[PricePoint]]:
    """
    Group price points by trading pair.

    Useful when monitoring multiple trading pairs across multiple DEXes.

    Args:
        prices: List of (pair_symbol, PricePoint) tuples

    Returns:
        Dict mapping pair symbols to lists of PricePoints

    Examples:
        >>> from decimal import Decimal
        >>> from datetime import datetime
        >>> prices = [
        ...     ('FXRP/USDT', PricePoint('SparkDEX', Decimal('0.0045'), datetime.now())),
        ...     ('FXRP/USDT', PricePoint('Blazeswap', Decimal('0.0048'), datetime.now())),
        ...     ('FXRP/FLR', PricePoint('SparkDEX', Decimal('0.125'), datetime.now())),
        ... ]
        >>> grouped = group_prices_by_pair(prices)
        >>> len(grouped['FXRP/USDT'])
        2
        >>> len(grouped['FXRP/FLR'])
        1
    """
    grouped: Dict[str, List[PricePoint]] = {}

    for pair_symbol, price_point in prices:
        if pair_symbol not in grouped:
            grouped[pair_symbol] = []
        grouped[pair_symbol].append(price_point)

    return grouped
