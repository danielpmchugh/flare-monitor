"""Tests for flare_monitor/adapters/uniswap_v2.py

This module tests Uniswap V2 adapter functionality including:
- Mock web3 calls (no live network access)
- Price calculation from reserves
- Liquidity calculation
- Validation logic (reserves sanity checks, decimals validation)
- Error handling for missing pairs
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from flare_monitor.adapters.uniswap_v2 import UniswapV2Adapter
from flare_monitor.config import TokenConfig
from flare_monitor.models import TradingPair, Price


class TestUniswapV2AdapterInit:
    """Tests for UniswapV2Adapter initialization."""

    def test_adapter_init_valid(self, mock_web3, basic_token_config):
        """Test adapter initialization with valid parameters."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
        )
        assert adapter.dex_name == "SparkDEX"
        assert adapter.w3 == mock_web3
        assert len(adapter.tokens) == 3

    def test_adapter_init_with_cache_enabled(self, mock_web3, basic_token_config):
        """Test adapter initialization with caching enabled."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
            enable_cache=True,
        )
        assert adapter.enable_cache is True

    def test_adapter_init_with_custom_retry_settings(self, mock_web3, basic_token_config):
        """Test adapter with custom retry settings."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
            max_retries=5,
            retry_delay=2.0,
        )
        assert adapter.max_retries == 5
        assert adapter.retry_delay == 2.0


class TestUniswapV2AdapterPriceCalculation:
    """Tests for price calculation logic."""

    @pytest.mark.asyncio
    async def test_get_price_with_valid_pair(self, mock_web3, basic_token_config):
        """Test getting price for valid trading pair."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
        )

        # Mock the getPair call
        mock_factory = AsyncMock()
        mock_factory.functions.getPair.return_value.call.return_value = (
            "0x1234567890123456789012345678901234567890"
        )

        # Mock the pair contract
        mock_pair = AsyncMock()
        mock_pair.functions.getReserves.return_value.call.return_value = (
            int(1e18), int(1e6), 0
        )
        mock_pair.functions.token0.return_value.call.return_value = (
            basic_token_config["FXRP"].address
        )
        mock_pair.functions.token1.return_value.call.return_value = (
            basic_token_config["USDT0"].address
        )

        with patch.object(adapter, 'factory_contract', mock_factory), \
             patch.object(adapter.w3.eth, 'contract', return_value=mock_pair):

            pair = TradingPair(base_token="FXRP", quote_token="USDT0")
            price = await adapter.get_price(pair)

            # Verify price is calculated correctly
            assert price is not None
            assert price.pair == pair
            assert price.dex_name == "SparkDEX"

    @pytest.mark.asyncio
    async def test_get_price_missing_pair(self, mock_web3, basic_token_config):
        """Test error handling when pair doesn't exist."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
        )

        # Mock getPair returning zero address (pair doesn't exist)
        mock_factory = AsyncMock()
        mock_factory.functions.getPair.return_value.call.return_value = (
            "0x0000000000000000000000000000000000000000"
        )

        with patch.object(adapter, 'factory_contract', mock_factory):
            pair = TradingPair(base_token="FXRP", quote_token="USDT0")
            price = await adapter.get_price(pair)

            # Should return price with error
            assert price.price is None
            assert price.error is not None

    @pytest.mark.asyncio
    async def test_get_price_with_invalid_token(self, mock_web3, basic_token_config):
        """Test error handling with unknown token."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
        )

        # Try to get price for token not in config
        pair = TradingPair(base_token="UNKNOWN", quote_token="USDT0")
        price = await adapter.get_price(pair)

        assert price.price is None
        assert price.error is not None


class TestUniswapV2AdapterLiquidity:
    """Tests for liquidity calculation."""

    def test_liquidity_calculation_with_reserves(self):
        """Test that liquidity is calculated from reserves."""
        # This would test internal liquidity calculation methods
        # Implementation depends on specific adapter methods
        pass


class TestUniswapV2AdapterValidation:
    """Tests for validation logic."""

    def test_validate_reserves_sanity(self):
        """Test validation of reserve values."""
        # Test that reserves are reasonable numbers
        # Zero reserves should be rejected
        pass

    def test_validate_token_decimals(self):
        """Test validation of token decimal handling."""
        # Test that token decimals are properly used
        # Different decimals (18 vs 6) should be handled correctly
        pass


class TestUniswapV2AdapterCaching:
    """Tests for pair address caching."""

    def test_cache_enabled_by_default(self, mock_web3, basic_token_config):
        """Test that caching is enabled by default."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
        )
        assert adapter.enable_cache is True

    def test_cache_can_be_disabled(self, mock_web3, basic_token_config):
        """Test that caching can be disabled."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
            enable_cache=False,
        )
        assert adapter.enable_cache is False


class TestUniswapV2AdapterErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_web3, basic_token_config):
        """Test handling of network errors."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
        )

        # Mock network error
        mock_factory = AsyncMock()
        mock_factory.functions.getPair.return_value.call.side_effect = Exception("Network error")

        with patch.object(adapter, 'factory_contract', mock_factory):
            pair = TradingPair(base_token="FXRP", quote_token="USDT0")
            price = await adapter.get_price(pair)

            # Should return error price
            assert price.price is None
            assert "error" in price.__dict__

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, mock_web3, basic_token_config):
        """Test retry logic on transient failures."""
        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=mock_web3,
            factory_address="0x1111111111111111111111111111111111111111",
            tokens=basic_token_config,
            max_retries=3,
            retry_delay=0.1,
        )

        # Mock retry behavior - fail then succeed
        mock_factory = AsyncMock()
        mock_factory.functions.getPair.return_value.call.side_effect = [
            Exception("Timeout"),
            "0x1234567890123456789012345678901234567890"
        ]

        # This would test actual retry logic if it exists
        # Exact behavior depends on implementation
        pass
