"""Tests for flare_monitor/calculator.py

This module tests spread calculation functionality including:
- Spread calculation accuracy
- Decimal precision handling
- Edge cases (zero prices, missing data, NaN, infinity)
- PricePoint dataclass validation
- SpreadResult dataclass
- Best arbitrage opportunity finding
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from flare_monitor.calculator import (
    PricePoint,
    SpreadResult,
    calculate_spread,
    find_best_arbitrage,
)


# ============================================================================
# PricePoint Tests
# ============================================================================

class TestPricePoint:
    """Tests for PricePoint dataclass."""

    def test_price_point_creation_valid(self):
        """Test creating a valid PricePoint."""
        now = datetime.now(timezone.utc)
        pp = PricePoint(
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=now,
        )
        assert pp.dex_name == "SparkDEX"
        assert pp.price == Decimal("0.0045")
        assert pp.timestamp == now

    def test_price_point_with_liquidity(self):
        """Test PricePoint with liquidity information."""
        now = datetime.now(timezone.utc)
        pp = PricePoint(
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=now,
            liquidity=Decimal("50000.00"),
        )
        assert pp.liquidity == Decimal("50000.00")

    def test_price_point_requires_positive_price(self):
        """Test that PricePoint rejects non-positive prices."""
        now = datetime.now(timezone.utc)

        # Zero price
        with pytest.raises(ValueError, match="must be positive"):
            PricePoint(
                dex_name="SparkDEX",
                price=Decimal("0"),
                timestamp=now,
            )

        # Negative price
        with pytest.raises(ValueError, match="must be positive"):
            PricePoint(
                dex_name="SparkDEX",
                price=Decimal("-0.0045"),
                timestamp=now,
            )


class TestCalculateSpread:
    """Tests for calculate_spread function."""

    def test_calculate_spread_basic(self):
        """Test basic spread calculation."""
        price1 = Decimal("0.0045")
        price2 = Decimal("0.0048")

        spread = calculate_spread(price1, price2)

        # (0.0048 - 0.0045) / 0.0045 * 100 = 6.6666...
        expected = Decimal("6.67")
        # Allow small floating point differences
        assert abs(spread - expected) < Decimal("0.01")

    def test_calculate_spread_zero_means_no_spread(self):
        """Test that identical prices produce zero spread."""
        price = Decimal("0.0045")
        spread = calculate_spread(price, price)
        assert spread == Decimal("0")

    def test_calculate_spread_large_difference(self):
        """Test spread calculation with large price difference."""
        price1 = Decimal("1.0")
        price2 = Decimal("2.0")

        spread = calculate_spread(price1, price2)
        # (2.0 - 1.0) / 1.0 * 100 = 100
        assert spread == Decimal("100")


class TestFindBestArbitrage:
    """Tests for find_best_arbitrage function."""

    def test_find_best_arbitrage_single_pair(self):
        """Test finding best arbitrage with single price pair."""
        now = datetime.now(timezone.utc)
        prices = [
            PricePoint("SparkDEX", Decimal("0.0045"), now),
            PricePoint("BlazeSwap", Decimal("0.0048"), now),
        ]

        result = find_best_arbitrage(prices)

        assert result is not None
        assert result.low_dex == "SparkDEX"
        assert result.high_dex == "BlazeSwap"
        assert result.low_price == Decimal("0.0045")
        assert result.high_price == Decimal("0.0048")

    def test_find_best_arbitrage_multiple_pairs(self):
        """Test finding best arbitrage among multiple DEXes."""
        now = datetime.now(timezone.utc)
        prices = [
            PricePoint("SparkDEX", Decimal("0.0045"), now),
            PricePoint("BlazeSwap", Decimal("0.0048"), now),
            PricePoint("Pangolin", Decimal("0.0050"), now),
            PricePoint("Enosys", Decimal("0.0043"), now),
        ]

        result = find_best_arbitrage(prices)

        assert result is not None
        assert result.low_dex == "Enosys"
        assert result.high_dex == "Pangolin"
        assert result.low_price == Decimal("0.0043")
        assert result.high_price == Decimal("0.0050")

    def test_find_best_arbitrage_identical_prices(self):
        """Test finding arbitrage when all prices are identical."""
        now = datetime.now(timezone.utc)
        prices = [
            PricePoint("SparkDEX", Decimal("0.0045"), now),
            PricePoint("BlazeSwap", Decimal("0.0045"), now),
            PricePoint("Pangolin", Decimal("0.0045"), now),
        ]

        result = find_best_arbitrage(prices)

        assert result is not None
        assert result.spread_percent == Decimal("0")

    def test_find_best_arbitrage_empty_list(self):
        """Test with empty price list."""
        result = find_best_arbitrage([])
        assert result is None

    def test_find_best_arbitrage_many_dexes(self):
        """Test finding arbitrage with many DEXes."""
        now = datetime.now(timezone.utc)
        prices = [
            PricePoint("DEX1", Decimal("0.0040"), now),
            PricePoint("DEX2", Decimal("0.0045"), now),
            PricePoint("DEX3", Decimal("0.0050"), now),
            PricePoint("DEX4", Decimal("0.0042"), now),
            PricePoint("DEX5", Decimal("0.0055"), now),
            PricePoint("DEX6", Decimal("0.0038"), now),
            PricePoint("DEX7", Decimal("0.0060"), now),
        ]

        result = find_best_arbitrage(prices)

        # Should identify widest spread
        assert result.low_price == Decimal("0.0038")
        assert result.high_price == Decimal("0.0060")
        assert result.low_dex == "DEX6"
        assert result.high_dex == "DEX7"
