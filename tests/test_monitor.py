"""Tests for Monitor Manager.

This module tests the MonitorManager class which orchestrates all components
of the Flare Monitor system.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from web3 import AsyncWeb3

from flare_monitor.config import (
    AdvancedConfig,
    Config,
    DEXConfig,
    FlareConfig,
    MonitoringConfig,
    PairConfig,
    TokenConfig,
)
from flare_monitor.models import DEXStatus, Price, TradingPair
from flare_monitor.monitor import MonitorManager


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        flare=FlareConfig(
            rpc_endpoints=["https://flare-api.flare.network/ext/C/rpc"],
            chain_id=14,
        ),
        dexes=[
            DEXConfig(
                name="TestDEX_V2",
                type="uniswap_v2",
                factory_address="0x1234567890123456789012345678901234567890",
                router_address="0x0987654321098765432109876543210987654321",
                enabled=True,
            ),
            DEXConfig(
                name="TestDEX_V3",
                type="uniswap_v3",
                factory_address="0xabcdef0123456789abcdef0123456789abcdef01",
                router_address="0x123456789abcdef0123456789abcdef012345678",
                enabled=True,
            ),
            DEXConfig(
                name="DisabledDEX",
                type="uniswap_v2",
                factory_address="0x0000000000000000000000000000000000000001",
                router_address="0x0000000000000000000000000000000000000002",
                enabled=False,
            ),
        ],
        tokens={
            "FXRP": TokenConfig(
                address="0x0000000000000000000000000000000000000010",
                decimals=18,
                symbol="FXRP",
            ),
            "USDT0": TokenConfig(
                address="0x0000000000000000000000000000000000000020",
                decimals=6,
                symbol="USDT0",
            ),
        },
        pairs=[
            PairConfig(base="FXRP", quote="USDT0", enabled=True),
        ],
        monitoring=MonitoringConfig(
            poll_interval_seconds=2,
            spread_alert_threshold_percent=Decimal("5.0"),
            max_concurrent_requests=10,
            request_timeout_seconds=5,
            max_retries=3,
            retry_backoff_seconds=1,
        ),
        advanced=AdvancedConfig(enable_pair_cache=True),
    )


@pytest.fixture
async def mock_web3():
    """Create a mock AsyncWeb3 instance."""
    mock_w3 = Mock(spec=AsyncWeb3)
    mock_w3.eth = Mock()

    # chain_id is a coroutine property in AsyncWeb3
    async def get_chain_id():
        return 14

    type(mock_w3.eth).chain_id = property(lambda self: get_chain_id())
    mock_w3.to_checksum_address = lambda addr: addr
    return mock_w3


class TestMonitorManagerInit:
    """Tests for MonitorManager initialization."""

    def test_init(self, mock_config):
        """Test basic initialization."""
        manager = MonitorManager(mock_config)

        assert manager.config == mock_config
        assert manager.w3 is None
        assert manager.adapters == []
        assert manager.dex_statuses == {}
        assert manager.is_running is False

    @pytest.mark.asyncio
    async def test_initialize_web3_success(self, mock_config, mock_web3):
        """Test successful Web3 initialization."""
        manager = MonitorManager(mock_config)

        with patch("flare_monitor.monitor.AsyncWeb3") as mock_async_web3_class:
            mock_async_web3_class.AsyncHTTPProvider = Mock()
            mock_async_web3_class.return_value = mock_web3

            await manager._initialize_web3()

            assert manager.w3 == mock_web3
            mock_async_web3_class.AsyncHTTPProvider.assert_called_once_with(
                mock_config.flare.rpc_endpoints[0]
            )

    @pytest.mark.asyncio
    async def test_initialize_web3_chain_id_mismatch(self, mock_config):
        """Test Web3 initialization with chain ID mismatch (should warn but continue)."""
        manager = MonitorManager(mock_config)

        # Create a special mock with wrong chain ID
        mock_w3 = Mock(spec=AsyncWeb3)
        mock_w3.eth = Mock()

        async def get_wrong_chain_id():
            return 999

        type(mock_w3.eth).chain_id = property(lambda self: get_wrong_chain_id())
        mock_w3.to_checksum_address = lambda addr: addr

        with patch("flare_monitor.monitor.AsyncWeb3") as mock_async_web3_class:
            mock_async_web3_class.AsyncHTTPProvider = Mock()
            mock_async_web3_class.return_value = mock_w3

            # Should not raise exception, just warn
            await manager._initialize_web3()

            assert manager.w3 == mock_w3

    @pytest.mark.asyncio
    async def test_initialize_web3_all_endpoints_fail(self, mock_config):
        """Test Web3 initialization when all endpoints fail."""
        manager = MonitorManager(mock_config)

        with patch("flare_monitor.monitor.AsyncWeb3") as mock_async_web3_class:
            mock_async_web3_class.AsyncHTTPProvider = Mock()
            mock_async_web3_class.return_value.eth.chain_id = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            with pytest.raises(ConnectionError, match="Failed to connect to any RPC endpoint"):
                await manager._initialize_web3()

    @pytest.mark.asyncio
    async def test_create_adapters_v2_and_v3(self, mock_config, mock_web3):
        """Test creating both V2 and V3 adapters."""
        manager = MonitorManager(mock_config)
        manager.w3 = mock_web3

        with patch("flare_monitor.monitor.UniswapV2Adapter") as mock_v2, \
             patch("flare_monitor.monitor.UniswapV3Adapter") as mock_v3:

            # Create mock adapter instances
            mock_v2_instance = Mock()
            mock_v2_instance.get_dex_name.return_value = "TestDEX_V2"
            mock_v2.return_value = mock_v2_instance

            mock_v3_instance = Mock()
            mock_v3_instance.get_dex_name.return_value = "TestDEX_V3"
            mock_v3.return_value = mock_v3_instance

            await manager._create_adapters()

            # Should create 2 adapters (DisabledDEX is skipped)
            assert len(manager.adapters) == 2
            mock_v2.assert_called_once()
            mock_v3.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_adapters_skip_disabled(self, mock_config, mock_web3):
        """Test that disabled DEXes are skipped."""
        manager = MonitorManager(mock_config)
        manager.w3 = mock_web3

        with patch("flare_monitor.monitor.UniswapV2Adapter") as mock_v2, \
             patch("flare_monitor.monitor.UniswapV3Adapter") as mock_v3:

            mock_v2.return_value = Mock()
            mock_v3.return_value = Mock()

            await manager._create_adapters()

            # DisabledDEX should not be created
            # Only TestDEX_V2 and TestDEX_V3
            assert len(manager.adapters) == 2

    @pytest.mark.asyncio
    async def test_initialize_full(self, mock_config, mock_web3):
        """Test full initialization process."""
        manager = MonitorManager(mock_config)

        with patch("flare_monitor.monitor.AsyncWeb3") as mock_async_web3_class, \
             patch("flare_monitor.monitor.UniswapV2Adapter") as mock_v2, \
             patch("flare_monitor.monitor.UniswapV3Adapter") as mock_v3:

            mock_async_web3_class.AsyncHTTPProvider = Mock()
            mock_async_web3_class.return_value = mock_web3

            mock_v2_instance = Mock()
            mock_v2_instance.get_dex_name.return_value = "TestDEX_V2"
            mock_v2.return_value = mock_v2_instance

            mock_v3_instance = Mock()
            mock_v3_instance.get_dex_name.return_value = "TestDEX_V3"
            mock_v3.return_value = mock_v3_instance

            await manager.initialize()

            assert manager.w3 == mock_web3
            assert len(manager.adapters) == 2
            assert len(manager.dex_statuses) == 2
            assert "TestDEX_V2" in manager.dex_statuses
            assert "TestDEX_V3" in manager.dex_statuses

    @pytest.mark.asyncio
    async def test_initialize_no_adapters_raises(self, mock_config, mock_web3):
        """Test that initialization fails if no adapters are created."""
        # Disable all DEXes
        for dex in mock_config.dexes:
            dex.enabled = False

        manager = MonitorManager(mock_config)

        with patch("flare_monitor.monitor.AsyncWeb3") as mock_async_web3_class:
            mock_async_web3_class.AsyncHTTPProvider = Mock()
            mock_async_web3_class.return_value = mock_web3

            with pytest.raises(ValueError, match="No DEX adapters were created"):
                await manager.initialize()


class TestMonitorManagerPriceFetching:
    """Tests for price fetching functionality."""

    @pytest.mark.asyncio
    async def test_fetch_prices_for_pair_success(self, mock_config):
        """Test fetching prices for a single pair."""
        manager = MonitorManager(mock_config)

        # Create mock adapters
        mock_adapter1 = Mock()
        mock_adapter1.get_dex_name.return_value = "DEX1"
        mock_adapter1.get_price = AsyncMock(return_value=Price(
            pair=TradingPair(base_token="FXRP", quote_token="USDT0"),
            dex_name="DEX1",
            price=Decimal("0.0045"),
            liquidity=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        ))

        mock_adapter2 = Mock()
        mock_adapter2.get_dex_name.return_value = "DEX2"
        mock_adapter2.get_price = AsyncMock(return_value=Price(
            pair=TradingPair(base_token="FXRP", quote_token="USDT0"),
            dex_name="DEX2",
            price=Decimal("0.0048"),
            liquidity=Decimal("2000"),
            timestamp=datetime.now(timezone.utc),
        ))

        manager.adapters = [mock_adapter1, mock_adapter2]
        manager.dex_statuses = {
            "DEX1": DEXStatus(dex_name="DEX1"),
            "DEX2": DEXStatus(dex_name="DEX2"),
        }

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        prices = await manager.fetch_prices_for_pair(pair)

        assert len(prices) == 2
        assert all(isinstance(p, Price) for p in prices)
        assert prices[0].dex_name == "DEX1"
        assert prices[1].dex_name == "DEX2"

    @pytest.mark.asyncio
    async def test_fetch_prices_for_pair_with_error(self, mock_config):
        """Test fetching prices when one adapter fails."""
        manager = MonitorManager(mock_config)

        # Adapter 1 succeeds
        mock_adapter1 = Mock()
        mock_adapter1.get_dex_name.return_value = "DEX1"
        mock_adapter1.get_price = AsyncMock(return_value=Price(
            pair=TradingPair(base_token="FXRP", quote_token="USDT0"),
            dex_name="DEX1",
            price=Decimal("0.0045"),
            liquidity=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        ))

        # Adapter 2 returns error
        mock_adapter2 = Mock()
        mock_adapter2.get_dex_name.return_value = "DEX2"
        mock_adapter2.get_price = AsyncMock(return_value=Price(
            pair=TradingPair(base_token="FXRP", quote_token="USDT0"),
            dex_name="DEX2",
            price=None,
            liquidity=None,
            timestamp=datetime.now(timezone.utc),
            error="RPC timeout"
        ))

        manager.adapters = [mock_adapter1, mock_adapter2]
        manager.dex_statuses = {
            "DEX1": DEXStatus(dex_name="DEX1"),
            "DEX2": DEXStatus(dex_name="DEX2"),
        }

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        prices = await manager.fetch_prices_for_pair(pair)

        assert len(prices) == 2
        assert prices[0].is_valid
        assert not prices[1].is_valid
        assert prices[1].error == "RPC timeout"

    @pytest.mark.asyncio
    async def test_fetch_all_prices(self, mock_config):
        """Test fetching prices for all pairs."""
        manager = MonitorManager(mock_config)

        mock_adapter = Mock()
        mock_adapter.get_dex_name.return_value = "DEX1"
        mock_adapter.get_price = AsyncMock(return_value=Price(
            pair=TradingPair(base_token="FXRP", quote_token="USDT0"),
            dex_name="DEX1",
            price=Decimal("0.0045"),
            liquidity=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        ))

        manager.adapters = [mock_adapter]
        manager.dex_statuses = {"DEX1": DEXStatus(dex_name="DEX1")}

        price_map = await manager.fetch_all_prices()

        assert len(price_map) == 1
        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        assert pair in price_map
        assert len(price_map[pair]) == 1

    @pytest.mark.asyncio
    async def test_fetch_all_prices_no_enabled_pairs(self, mock_config):
        """Test fetching prices when no pairs are enabled."""
        # Disable all pairs
        for pair in mock_config.pairs:
            pair.enabled = False

        manager = MonitorManager(mock_config)
        manager.adapters = [Mock()]

        price_map = await manager.fetch_all_prices()

        assert price_map == {}


class TestMonitorManagerSpreadCalculation:
    """Tests for spread calculation functionality."""

    def test_calculate_spreads_success(self, mock_config):
        """Test spread calculation with valid prices."""
        manager = MonitorManager(mock_config)

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        price_map = {
            pair: [
                Price(
                    pair=pair,
                    dex_name="DEX1",
                    price=Decimal("0.0045"),
                    liquidity=Decimal("1000"),
                    timestamp=datetime.now(timezone.utc),
                ),
                Price(
                    pair=pair,
                    dex_name="DEX2",
                    price=Decimal("0.0048"),
                    liquidity=Decimal("2000"),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]
        }

        spreads = manager._calculate_spreads(price_map)

        # 6.67% spread should be above 5% threshold
        assert len(spreads) == 1
        assert spreads[0].pair == pair
        assert spreads[0].low_dex == "DEX1"
        assert spreads[0].high_dex == "DEX2"

    def test_calculate_spreads_below_threshold(self, mock_config):
        """Test that spreads below threshold are filtered out."""
        manager = MonitorManager(mock_config)

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        price_map = {
            pair: [
                Price(
                    pair=pair,
                    dex_name="DEX1",
                    price=Decimal("0.0045"),
                    liquidity=Decimal("1000"),
                    timestamp=datetime.now(timezone.utc),
                ),
                Price(
                    pair=pair,
                    dex_name="DEX2",
                    price=Decimal("0.004501"),  # ~0.02% spread
                    liquidity=Decimal("2000"),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]
        }

        spreads = manager._calculate_spreads(price_map)

        # Spread below 5% threshold should be filtered out
        assert len(spreads) == 0

    def test_calculate_spreads_insufficient_prices(self, mock_config):
        """Test spread calculation with insufficient valid prices."""
        manager = MonitorManager(mock_config)

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        price_map = {
            pair: [
                Price(
                    pair=pair,
                    dex_name="DEX1",
                    price=Decimal("0.0045"),
                    liquidity=Decimal("1000"),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]
        }

        spreads = manager._calculate_spreads(price_map)

        # Need at least 2 prices
        assert len(spreads) == 0


class TestMonitorManagerStatusTracking:
    """Tests for DEX status tracking."""

    def test_update_dex_status_success(self, mock_config):
        """Test updating status after successful fetch."""
        manager = MonitorManager(mock_config)
        manager.dex_statuses = {"DEX1": DEXStatus(dex_name="DEX1")}

        manager._update_dex_status_success("DEX1")

        status = manager.dex_statuses["DEX1"]
        assert status.is_online is True
        assert status.error_count == 0
        assert status.last_error is None
        assert status.last_update is not None

    def test_update_dex_status_error(self, mock_config):
        """Test updating status after failed fetch."""
        manager = MonitorManager(mock_config)
        manager.dex_statuses = {"DEX1": DEXStatus(dex_name="DEX1")}

        manager._update_dex_status_error("DEX1", "Test error")

        status = manager.dex_statuses["DEX1"]
        assert status.error_count == 1
        assert status.last_error == "Test error"

    def test_update_dex_status_multiple_errors_marks_offline(self, mock_config):
        """Test that multiple consecutive errors mark DEX as offline."""
        manager = MonitorManager(mock_config)
        manager.dex_statuses = {"DEX1": DEXStatus(dex_name="DEX1")}

        # Trigger multiple errors
        for i in range(3):
            manager._update_dex_status_error("DEX1", f"Error {i}")

        status = manager.dex_statuses["DEX1"]
        assert status.is_online is False
        assert status.error_count == 3


class TestMonitorManagerConsoleUpdate:
    """Tests for console output updates."""

    def test_update_console(self, mock_config):
        """Test console update with prices and spreads."""
        manager = MonitorManager(mock_config)

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        price_map = {
            pair: [
                Price(
                    pair=pair,
                    dex_name="DEX1",
                    price=Decimal("0.0045"),
                    liquidity=Decimal("1000"),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]
        }

        spreads = []

        # Should not raise exception
        manager._update_console(price_map, spreads)


def test_monitor_manager_repr(mock_config):
    """Test string representation."""
    manager = MonitorManager(mock_config)
    repr_str = repr(manager)

    assert "MonitorManager" in repr_str
    assert "adapters=0" in repr_str
    assert "pairs=1" in repr_str


# ============================================================================
# RpcCircuitBreaker Tests
# ============================================================================

class TestRpcCircuitBreaker:
    """Tests for RpcCircuitBreaker pattern implementation."""

    def test_circuit_breaker_init_defaults(self):
        """Test circuit breaker initialization with defaults."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.success_threshold == 2
        assert cb.timeout_seconds == 60
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_circuit_breaker_init_custom(self):
        """Test circuit breaker initialization with custom parameters."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker(
            failure_threshold=3,
            success_threshold=1,
            timeout_seconds=30
        )

        assert cb.failure_threshold == 3
        assert cb.success_threshold == 1
        assert cb.timeout_seconds == 30

    def test_circuit_breaker_record_success(self):
        """Test recording successful operation."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker()
        cb.record_success()

        assert cb.failure_count == 0
        assert cb.success_count == 1

    def test_circuit_breaker_record_failure(self):
        """Test recording failed operation."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker()
        cb.record_failure()

        assert cb.failure_count == 1
        assert cb.success_count == 0

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker(failure_threshold=3)

        assert cb.state == "closed"

        # Trigger failures
        for _ in range(3):
            cb.record_failure()

        assert cb.state == "open"

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test transition to half-open after timeout."""
        from flare_monitor.monitor import RpcCircuitBreaker
        import time

        cb = RpcCircuitBreaker(timeout_seconds=1)

        # Open circuit
        for _ in range(5):
            cb.record_failure()

        assert cb.state == "open"

        # Wait for timeout
        time.sleep(1.1)

        # Should transition to half-open
        can_attempt = cb.can_attempt()
        assert can_attempt is True
        assert cb.state == "half_open"

    def test_circuit_breaker_closes_on_success_in_half_open(self):
        """Test circuit closes when success threshold reached in half-open."""
        from flare_monitor.monitor import RpcCircuitBreaker
        import time

        cb = RpcCircuitBreaker(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1
        )

        # Open circuit
        for _ in range(3):
            cb.record_failure()

        assert cb.state == "open"

        # Wait and transition to half-open
        time.sleep(1.1)
        assert cb.can_attempt() is True

        # Record successes
        for _ in range(2):
            cb.record_success()

        assert cb.state == "closed"

    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test circuit reopens if failure during half-open."""
        from flare_monitor.monitor import RpcCircuitBreaker
        import time

        cb = RpcCircuitBreaker(
            failure_threshold=3,
            timeout_seconds=1
        )

        # Open circuit
        for _ in range(3):
            cb.record_failure()

        assert cb.state == "open"

        # Wait and transition to half-open
        time.sleep(1.1)
        assert cb.can_attempt() is True
        assert cb.state == "half_open"

        # Record failure in half-open
        cb.record_failure()

        assert cb.state == "open"

    def test_circuit_breaker_can_attempt_closed(self):
        """Test can_attempt returns True when closed."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker()
        assert cb.can_attempt() is True

    def test_circuit_breaker_can_attempt_open(self):
        """Test can_attempt returns False when open."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker(failure_threshold=2)

        # Open circuit
        for _ in range(2):
            cb.record_failure()

        assert cb.can_attempt() is False

    def test_circuit_breaker_is_open_property(self):
        """Test is_open property."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker(failure_threshold=2)

        assert cb.is_open() is False

        for _ in range(2):
            cb.record_failure()

        assert cb.is_open() is True

    def test_circuit_breaker_reset(self):
        """Test resetting circuit breaker."""
        from flare_monitor.monitor import RpcCircuitBreaker

        cb = RpcCircuitBreaker(failure_threshold=2)

        # Open circuit
        for _ in range(2):
            cb.record_failure()

        assert cb.state == "open"

        # Reset
        cb.reset()

        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.success_count == 0
