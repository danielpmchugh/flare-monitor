"""Tests for flare_monitor/output.py

This module tests console output functionality including:
- Table generation
- Color coding based on spread thresholds
- Spread formatting
- Price updates and formatting
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from flare_monitor.models import DEXStatus, Price, Spread, TradingPair
from flare_monitor.output import ConsoleOutputHandler


class TestConsoleOutputHandlerInit:
    """Tests for ConsoleOutputHandler initialization."""

    def test_handler_init(self):
        """Test handler initialization."""
        handler = ConsoleOutputHandler()
        
        assert handler.console is not None
        assert handler.prices == {}
        assert handler.spreads == {}
        assert handler.dex_statuses == {}
        assert handler.last_update is None

    def test_handler_init_creates_console(self):
        """Test that handler creates a console instance."""
        handler = ConsoleOutputHandler()
        assert handler.console is not None


class TestConsoleOutputHandlerPriceUpdates:
    """Tests for price update functionality."""

    def test_update_single_price(self, sample_price_valid):
        """Test updating a single price."""
        handler = ConsoleOutputHandler()
        handler.update_price(sample_price_valid)

        pair_key = (sample_price_valid.pair.base_token, sample_price_valid.pair.quote_token)
        assert pair_key in handler.prices
        assert len(handler.prices[pair_key]) == 1
        assert handler.prices[pair_key][0] == sample_price_valid

    def test_update_multiple_prices_same_pair(self, fxrp_usdt0_pair):
        """Test updating multiple prices for same pair."""
        handler = ConsoleOutputHandler()

        price1 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=datetime.now(timezone.utc),
        )
        price2 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="BlazeSwap",
            price=Decimal("0.0048"),
            timestamp=datetime.now(timezone.utc),
        )

        handler.update_price(price1)
        handler.update_price(price2)

        pair_key = ("FXRP", "USDT0")
        assert len(handler.prices[pair_key]) == 2

    def test_update_price_replaces_existing(self, fxrp_usdt0_pair):
        """Test that updating price for same DEX replaces the old one."""
        handler = ConsoleOutputHandler()

        price1 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=datetime.now(timezone.utc),
        )
        price2 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0046"),
            timestamp=datetime.now(timezone.utc),
        )

        handler.update_price(price1)
        handler.update_price(price2)

        pair_key = ("FXRP", "USDT0")
        assert len(handler.prices[pair_key]) == 1
        assert handler.prices[pair_key][0].price == Decimal("0.0046")

    def test_update_prices_batch(self, fxrp_usdt0_pair, fxrp_wflr_pair):
        """Test batch price updates."""
        handler = ConsoleOutputHandler()

        prices = [
            Price(
                pair=fxrp_usdt0_pair,
                dex_name="SparkDEX",
                price=Decimal("0.0045"),
                timestamp=datetime.now(timezone.utc),
            ),
            Price(
                pair=fxrp_wflr_pair,
                dex_name="SparkDEX",
                price=Decimal("0.50"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        handler.update_prices(prices)

        assert len(handler.prices) == 2


class TestConsoleOutputHandlerSpreadUpdates:
    """Tests for spread update functionality."""

    def test_update_single_spread(self, sample_spread):
        """Test updating a single spread."""
        handler = ConsoleOutputHandler()
        handler.update_spread(sample_spread)

        assert sample_spread.pair in handler.spreads
        assert handler.spreads[sample_spread.pair] == sample_spread

    def test_update_spread_replaces_existing(self, fxrp_usdt0_pair):
        """Test that updating spread replaces the old one."""
        handler = ConsoleOutputHandler()

        spread1 = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0048"),
            spread_percent=Decimal("6.67"),
            timestamp=datetime.now(timezone.utc),
        )

        spread2 = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0050"),
            spread_percent=Decimal("11.11"),
            timestamp=datetime.now(timezone.utc),
        )

        handler.update_spread(spread1)
        handler.update_spread(spread2)

        assert handler.spreads[fxrp_usdt0_pair].spread_percent == Decimal("11.11")

    def test_update_spreads_batch(self, fxrp_usdt0_pair, fxrp_wflr_pair):
        """Test batch spread updates."""
        handler = ConsoleOutputHandler()

        spreads = [
            Spread(
                pair=fxrp_usdt0_pair,
                low_dex="SparkDEX",
                high_dex="BlazeSwap",
                low_price=Decimal("0.0045"),
                high_price=Decimal("0.0048"),
                spread_percent=Decimal("6.67"),
                timestamp=datetime.now(timezone.utc),
            ),
            Spread(
                pair=fxrp_wflr_pair,
                low_dex="SparkDEX",
                high_dex="BlazeSwap",
                low_price=Decimal("0.50"),
                high_price=Decimal("0.52"),
                spread_percent=Decimal("4.00"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        handler.update_spreads(spreads)

        assert len(handler.spreads) == 2


class TestConsoleOutputHandlerDEXStatus:
    """Tests for DEX status updates."""

    def test_update_dex_status(self, dex_status_online):
        """Test updating DEX status."""
        handler = ConsoleOutputHandler()
        handler.update_dex_status(dex_status_online)

        assert dex_status_online.dex_name in handler.dex_statuses
        assert handler.dex_statuses[dex_status_online.dex_name] == dex_status_online

    def test_update_dex_status_offline(self, dex_status_offline):
        """Test updating offline DEX status."""
        handler = ConsoleOutputHandler()
        handler.update_dex_status(dex_status_offline)

        status = handler.dex_statuses[dex_status_offline.dex_name]
        assert status.is_online is False
        assert status.error_count == 5

    def test_update_multiple_dex_statuses(self, dex_status_online, dex_status_offline):
        """Test updating multiple DEX statuses."""
        handler = ConsoleOutputHandler()
        handler.update_dex_status(dex_status_online)
        handler.update_dex_status(dex_status_offline)

        assert len(handler.dex_statuses) == 2
        assert handler.dex_statuses["SparkDEX"].is_online is True
        assert handler.dex_statuses["BlazeSwap"].is_online is False


class TestConsoleOutputHandlerFormatting:
    """Tests for output formatting functions."""

    def test_format_spread_profitable(self, sample_spread):
        """Test formatting of profitable spread."""
        # Spread should be marked as profitable (> 0.5%)
        assert sample_spread.is_profitable()

    def test_format_spread_not_profitable(self, fxrp_usdt0_pair):
        """Test formatting of non-profitable spread."""
        # Small spread that doesn't exceed default fee
        spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.00451"),
            spread_percent=Decimal("0.22"),
            timestamp=datetime.now(timezone.utc),
        )
        
        assert not spread.is_profitable()

    def test_format_price_with_liquidity(self, sample_price_valid):
        """Test price formatting with liquidity."""
        str_repr = str(sample_price_valid)
        assert "SparkDEX" in str_repr
        assert "FXRP/USDT0" in str_repr

    def test_format_price_with_error(self, sample_price_error):
        """Test price formatting when error present."""
        str_repr = str(sample_price_error)
        assert "ERROR" in str_repr
        assert sample_price_error.error in str_repr


class TestConsoleOutputHandlerTimestamp:
    """Tests for timestamp tracking."""

    def test_last_update_set_on_price_update(self, sample_price_valid):
        """Test that last_update is set when price is updated."""
        handler = ConsoleOutputHandler()
        
        before = datetime.now(timezone.utc)
        handler.update_price(sample_price_valid)
        after = datetime.now(timezone.utc)

        assert handler.last_update is not None
        assert before <= handler.last_update <= after

    def test_last_update_updated_on_each_price(self, fxrp_usdt0_pair):
        """Test that last_update changes with each price update."""
        handler = ConsoleOutputHandler()

        price1 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=datetime.now(timezone.utc),
        )
        handler.update_price(price1)
        first_update = handler.last_update

        # Small delay
        import time
        time.sleep(0.01)

        price2 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="BlazeSwap",
            price=Decimal("0.0048"),
            timestamp=datetime.now(timezone.utc),
        )
        handler.update_price(price2)
        second_update = handler.last_update

        # Second update should be later than first
        assert second_update > first_update


class TestConsoleOutputHandlerDataStorage:
    """Tests for data storage and retrieval."""

    def test_prices_organized_by_pair(self, fxrp_usdt0_pair, fxrp_wflr_pair):
        """Test that prices are correctly organized by pair."""
        handler = ConsoleOutputHandler()

        price1 = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=datetime.now(timezone.utc),
        )
        price2 = Price(
            pair=fxrp_wflr_pair,
            dex_name="SparkDEX",
            price=Decimal("0.50"),
            timestamp=datetime.now(timezone.utc),
        )

        handler.update_price(price1)
        handler.update_price(price2)

        assert len(handler.prices) == 2
        assert ("FXRP", "USDT0") in handler.prices
        assert ("FXRP", "WFLR") in handler.prices

    def test_spreads_organized_by_pair(self, fxrp_usdt0_pair, fxrp_wflr_pair):
        """Test that spreads are correctly organized by pair."""
        handler = ConsoleOutputHandler()

        spread1 = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0048"),
            spread_percent=Decimal("6.67"),
            timestamp=datetime.now(timezone.utc),
        )
        spread2 = Spread(
            pair=fxrp_wflr_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.50"),
            high_price=Decimal("0.52"),
            spread_percent=Decimal("4.00"),
            timestamp=datetime.now(timezone.utc),
        )

        handler.update_spread(spread1)
        handler.update_spread(spread2)

        assert len(handler.spreads) == 2
        assert fxrp_usdt0_pair in handler.spreads
        assert fxrp_wflr_pair in handler.spreads
