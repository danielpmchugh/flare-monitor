"""Tests for flare_monitor/models.py

This module tests all Pydantic models including:
- TradingPair validation
- TokenAddress validation and checksumming
- Price model with Decimal precision
- Spread calculations and validation
- DEXStatus model
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from flare_monitor.models import (
    TradingPair,
    TokenAddress,
    Price,
    Spread,
    DEXStatus,
)


# ============================================================================
# TradingPair Tests
# ============================================================================

class TestTradingPair:
    """Tests for TradingPair model."""

    def test_trading_pair_creation_valid(self):
        """Test creating a valid TradingPair."""
        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        assert pair.base_token == "FXRP"
        assert pair.quote_token == "USDT0"

    def test_trading_pair_normalizes_lowercase_to_uppercase(self):
        """Test that token symbols are normalized to uppercase."""
        pair = TradingPair(base_token="fxrp", quote_token="usdt0")
        assert pair.base_token == "FXRP"
        assert pair.quote_token == "USDT0"

    def test_trading_pair_rejects_same_tokens(self):
        """Test that base and quote tokens must be different."""
        with pytest.raises(ValueError, match="must be different"):
            TradingPair(base_token="FXRP", quote_token="FXRP")

    def test_trading_pair_rejects_empty_tokens(self):
        """Test that empty token symbols are rejected."""
        with pytest.raises(ValueError):
            TradingPair(base_token="", quote_token="USDT0")

    def test_trading_pair_rejects_invalid_characters(self):
        """Test that invalid characters in token symbols are rejected."""
        with pytest.raises(ValueError, match="alphanumeric"):
            TradingPair(base_token="FXR!P", quote_token="USDT0")

    def test_trading_pair_allows_underscores(self):
        """Test that underscores are allowed in token symbols."""
        pair = TradingPair(base_token="FX_RP", quote_token="USDT_0")
        assert pair.base_token == "FX_RP"
        assert pair.quote_token == "USDT_0"

    def test_trading_pair_str_representation(self):
        """Test string representation is 'BASE/QUOTE' format."""
        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        assert str(pair) == "FXRP/USDT0"

    def test_trading_pair_repr(self):
        """Test repr includes class name and fields."""
        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        repr_str = repr(pair)
        assert "TradingPair" in repr_str
        assert "FXRP" in repr_str
        assert "USDT0" in repr_str

    def test_trading_pair_is_hashable(self):
        """Test that TradingPair can be used as dict key or in set."""
        pair1 = TradingPair(base_token="FXRP", quote_token="USDT0")
        pair2 = TradingPair(base_token="FXRP", quote_token="USDT0")

        pair_dict = {pair1: "spread_data"}
        assert pair_dict[pair2] == "spread_data"  # Same pair should access same key

        pair_set = {pair1, pair2}
        assert len(pair_set) == 1  # Should be same hash

    def test_trading_pair_max_length_validation(self):
        """Test that excessively long token symbols are rejected."""
        with pytest.raises(ValueError):
            TradingPair(base_token="A" * 21, quote_token="USDT0")


# ============================================================================
# TokenAddress Tests
# ============================================================================

class TestTokenAddress:
    """Tests for TokenAddress model."""

    def test_token_address_creation_valid(self):
        """Test creating a valid TokenAddress."""
        token = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        )
        assert token.address == "0x0000000000000000000000000000000000000001"
        assert token.decimals == 18
        assert token.symbol == "FXRP"

    def test_token_address_requires_0x_prefix(self):
        """Test that address must start with 0x."""
        with pytest.raises(ValueError, match="must start with '0x'"):
            TokenAddress(
                address="0000000000000000000000000000000000000001",
                decimals=18,
                symbol="FXRP",
            )

    def test_token_address_requires_42_characters(self):
        """Test that address must be 42 characters including 0x."""
        with pytest.raises(ValueError, match="42 characters"):
            TokenAddress(
                address="0x00000000000000000000000000000000000001",  # Too short
                decimals=18,
                symbol="FXRP",
            )

    def test_token_address_requires_valid_hex(self):
        """Test that address must contain valid hex characters."""
        with pytest.raises(ValueError, match="Invalid Ethereum address"):
            TokenAddress(
                address="0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
                decimals=18,
                symbol="FXRP",
            )

    def test_token_address_decimals_range(self):
        """Test that decimals must be 0-18."""
        # Valid: 0
        token = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=0,
            symbol="FXRP",
        )
        assert token.decimals == 0

        # Valid: 18
        token = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        )
        assert token.decimals == 18

        # Invalid: -1
        with pytest.raises(ValueError):
            TokenAddress(
                address="0x0000000000000000000000000000000000000001",
                decimals=-1,
                symbol="FXRP",
            )

        # Invalid: 19
        with pytest.raises(ValueError):
            TokenAddress(
                address="0x0000000000000000000000000000000000000001",
                decimals=19,
                symbol="FXRP",
            )

    def test_token_address_normalizes_symbol_uppercase(self):
        """Test that token symbol is normalized to uppercase."""
        token = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="fxrp",
        )
        assert token.symbol == "FXRP"

    def test_token_address_str_representation(self):
        """Test string representation includes symbol and address."""
        token = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        )
        str_repr = str(token)
        assert "FXRP" in str_repr
        assert "0x0000000000000000000000000000000000000001" in str_repr

    def test_token_address_is_hashable(self):
        """Test that TokenAddress can be used in sets and as dict keys."""
        token1 = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        )
        token2 = TokenAddress(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        )

        token_set = {token1, token2}
        assert len(token_set) == 1  # Same address hash


# ============================================================================
# Price Tests
# ============================================================================

class TestPrice:
    """Tests for Price model."""

    def test_price_creation_valid(self, fxrp_usdt0_pair):
        """Test creating a valid Price."""
        now = datetime.now(timezone.utc)
        price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            liquidity=Decimal("50000.00"),
            timestamp=now,
        )
        assert price.pair == fxrp_usdt0_pair
        assert price.dex_name == "SparkDEX"
        assert price.price == Decimal("0.0045")
        assert price.liquidity == Decimal("50000.00")
        assert price.timestamp == now

    def test_price_requires_positive_price(self, fxrp_usdt0_pair):
        """Test that price must be positive."""
        now = datetime.now(timezone.utc)

        # Zero not allowed
        with pytest.raises(ValueError, match="must be positive"):
            Price(
                pair=fxrp_usdt0_pair,
                dex_name="SparkDEX",
                price=Decimal("0"),
                timestamp=now,
            )

        # Negative not allowed
        with pytest.raises(ValueError, match="must be positive"):
            Price(
                pair=fxrp_usdt0_pair,
                dex_name="SparkDEX",
                price=Decimal("-0.0045"),
                timestamp=now,
            )

    def test_price_allows_none_price_for_errors(self, fxrp_usdt0_pair):
        """Test that price can be None when there's an error."""
        now = datetime.now(timezone.utc)
        price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=None,
            error="Connection timeout",
            timestamp=now,
        )
        assert price.price is None
        assert price.error is not None

    def test_price_liquidity_non_negative(self, fxrp_usdt0_pair):
        """Test that liquidity must be non-negative."""
        now = datetime.now(timezone.utc)

        # Zero is allowed
        price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            liquidity=Decimal("0"),
            timestamp=now,
        )
        assert price.liquidity == Decimal("0")

        # Negative not allowed
        with pytest.raises(ValueError, match="cannot be negative"):
            Price(
                pair=fxrp_usdt0_pair,
                dex_name="SparkDEX",
                price=Decimal("0.0045"),
                liquidity=Decimal("-100"),
                timestamp=now,
            )

    def test_price_rejects_nan(self, fxrp_usdt0_pair):
        """Test that NaN is rejected."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="cannot be NaN"):
            Price(
                pair=fxrp_usdt0_pair,
                dex_name="SparkDEX",
                price=Decimal("NaN"),
                timestamp=now,
            )

    def test_price_rejects_infinity(self, fxrp_usdt0_pair):
        """Test that Infinity is rejected."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="cannot be infinite"):
            Price(
                pair=fxrp_usdt0_pair,
                dex_name="SparkDEX",
                price=Decimal("Infinity"),
                timestamp=now,
            )

    def test_price_is_valid_property(self, fxrp_usdt0_pair):
        """Test is_valid property."""
        now = datetime.now(timezone.utc)

        # Valid when no error and has price
        valid_price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=now,
        )
        assert valid_price.is_valid is True

        # Invalid when error present
        error_price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=None,
            error="Pair not found",
            timestamp=now,
        )
        assert error_price.is_valid is False

        # Invalid when price is None (no error message needed)
        no_price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=None,
            timestamp=now,
        )
        assert no_price.is_valid is False

    def test_price_str_representation(self, fxrp_usdt0_pair):
        """Test string representation."""
        now = datetime.now(timezone.utc)
        price = Price(
            pair=fxrp_usdt0_pair,
            dex_name="SparkDEX",
            price=Decimal("0.0045"),
            timestamp=now,
        )
        str_repr = str(price)
        assert "FXRP/USDT0" in str_repr
        assert "SparkDEX" in str_repr
        assert "0.00450000" in str_repr  # Decimal formatting


# ============================================================================
# Spread Tests
# ============================================================================

class TestSpread:
    """Tests for Spread model."""

    def test_spread_creation_valid(self, fxrp_usdt0_pair):
        """Test creating a valid Spread."""
        now = datetime.now(timezone.utc)
        spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0048"),
            spread_percent=Decimal("6.67"),
            timestamp=now,
        )
        assert spread.pair == fxrp_usdt0_pair
        assert spread.low_dex == "SparkDEX"
        assert spread.high_dex == "BlazeSwap"

    def test_spread_requires_high_gte_low_price(self, fxrp_usdt0_pair):
        """Test that high_price must be >= low_price."""
        now = datetime.now(timezone.utc)

        # high < low should fail
        with pytest.raises(ValueError, match="must be >="):
            Spread(
                pair=fxrp_usdt0_pair,
                low_dex="SparkDEX",
                high_dex="BlazeSwap",
                low_price=Decimal("0.0048"),
                high_price=Decimal("0.0045"),
                spread_percent=Decimal("6.67"),
                timestamp=now,
            )

    def test_spread_validates_spread_percentage(self, fxrp_usdt0_pair):
        """Test that spread_percent matches calculated spread."""
        now = datetime.now(timezone.utc)

        low = Decimal("0.0045")
        high = Decimal("0.0048")
        # Correct spread: (0.0048 - 0.0045) / 0.0045 * 100 = 6.666...
        correct_spread = Decimal("6.67")

        # Should accept with correct percentage
        spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=low,
            high_price=high,
            spread_percent=correct_spread,
            timestamp=now,
        )
        assert spread.spread_percent == correct_spread

        # Should reject with incorrect percentage
        with pytest.raises(ValueError, match="doesn't match"):
            Spread(
                pair=fxrp_usdt0_pair,
                low_dex="SparkDEX",
                high_dex="BlazeSwap",
                low_price=low,
                high_price=high,
                spread_percent=Decimal("10.00"),  # Wrong
                timestamp=now,
            )

    def test_spread_allows_zero_spread_same_dex(self, fxrp_usdt0_pair):
        """Test that zero spread is allowed when from same DEX."""
        now = datetime.now(timezone.utc)
        spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="SparkDEX",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0045"),
            spread_percent=Decimal("0.00"),
            timestamp=now,
        )
        assert spread.spread_percent == Decimal("0.00")

    def test_spread_rejects_zero_spread_different_dexes(self, fxrp_usdt0_pair):
        """Test that zero spread with different DEXes is invalid."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="must be different"):
            Spread(
                pair=fxrp_usdt0_pair,
                low_dex="SparkDEX",
                high_dex="BlazeSwap",
                low_price=Decimal("0.0045"),
                high_price=Decimal("0.0045"),
                spread_percent=Decimal("0.00"),
                timestamp=now,
            )

    def test_spread_is_profitable(self, fxrp_usdt0_pair):
        """Test is_profitable method."""
        now = datetime.now(timezone.utc)

        # Spread 6.67% with default 0.5% fee is profitable
        profitable_spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0048"),
            spread_percent=Decimal("6.67"),
            timestamp=now,
        )
        assert profitable_spread.is_profitable()
        assert profitable_spread.is_profitable(Decimal("5")) is True  # Custom fee

        # Spread 0.2% with 0.5% fee is not profitable
        unprofitable_spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.004509"),  # 0.2% spread
            spread_percent=Decimal("0.20"),
            timestamp=now,
        )
        assert unprofitable_spread.is_profitable() is False

    def test_spread_estimated_profit(self, fxrp_usdt0_pair):
        """Test estimated_profit method."""
        now = datetime.now(timezone.utc)
        spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0048"),
            spread_percent=Decimal("6.67"),
            timestamp=now,
        )

        # With default 0.5% fee
        profit = spread.estimated_profit()
        assert profit == Decimal("6.67") - Decimal("0.5")

        # With custom fee
        custom_profit = spread.estimated_profit(Decimal("2.0"))
        assert custom_profit == Decimal("6.67") - Decimal("2.0")

    def test_spread_str_representation(self, fxrp_usdt0_pair):
        """Test string representation."""
        now = datetime.now(timezone.utc)
        spread = Spread(
            pair=fxrp_usdt0_pair,
            low_dex="SparkDEX",
            high_dex="BlazeSwap",
            low_price=Decimal("0.0045"),
            high_price=Decimal("0.0048"),
            spread_percent=Decimal("6.67"),
            timestamp=now,
        )
        str_repr = str(spread)
        assert "FXRP/USDT0" in str_repr
        assert "6.67" in str_repr
        assert "SparkDEX" in str_repr
        assert "BlazeSwap" in str_repr


# ============================================================================
# DEXStatus Tests
# ============================================================================

class TestDEXStatus:
    """Tests for DEXStatus model."""

    def test_dex_status_creation_online(self):
        """Test creating an online DEXStatus."""
        now = datetime.now(timezone.utc)
        status = DEXStatus(
            dex_name="SparkDEX",
            is_online=True,
            last_update=now,
            error_count=0,
        )
        assert status.dex_name == "SparkDEX"
        assert status.is_online is True
        assert status.error_count == 0

    def test_dex_status_creation_offline(self):
        """Test creating an offline DEXStatus."""
        now = datetime.now(timezone.utc)
        status = DEXStatus(
            dex_name="BlazeSwap",
            is_online=False,
            last_update=now,
            error_count=5,
            last_error="Connection timeout",
        )
        assert status.dex_name == "BlazeSwap"
        assert status.is_online is False
        assert status.error_count == 5
        assert status.last_error == "Connection timeout"

    def test_dex_status_error_count_non_negative(self):
        """Test that error_count must be non-negative."""
        with pytest.raises(ValueError):
            DEXStatus(
                dex_name="SparkDEX",
                error_count=-1,
            )

    def test_dex_status_default_values(self):
        """Test default values for optional fields."""
        status = DEXStatus(dex_name="SparkDEX")
        assert status.is_online is True  # Default online
        assert status.error_count == 0
        assert status.last_update is None
        assert status.last_error is None

    def test_dex_status_str_representation(self):
        """Test string representation."""
        now = datetime.now(timezone.utc)

        # Online status
        online_status = DEXStatus(
            dex_name="SparkDEX",
            is_online=True,
        )
        assert "online" in str(online_status)

        # Offline status
        offline_status = DEXStatus(
            dex_name="BlazeSwap",
            is_online=False,
            error_count=5,
            last_error="Timeout",
        )
        str_repr = str(offline_status)
        assert "offline" in str_repr
        assert "5" in str_repr
        assert "Timeout" in str_repr
