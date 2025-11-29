"""
Pytest configuration and shared fixtures.

This module contains pytest fixtures used across all test modules
for consistent test setup and data.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock

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
from flare_monitor.models import (
    DEXStatus,
    Price,
    Spread,
    TradingPair,
    TokenAddress,
)


# ============================================================================
# Token and Pair Fixtures
# ============================================================================

@pytest.fixture
def fxrp_token() -> TokenAddress:
    """Create a TokenAddress for FXRP."""
    return TokenAddress(
        address="0x0000000000000000000000000000000000000001",
        decimals=18,
        symbol="FXRP",
    )


@pytest.fixture
def usdt0_token() -> TokenAddress:
    """Create a TokenAddress for USDT0."""
    return TokenAddress(
        address="0x0000000000000000000000000000000000000002",
        decimals=6,
        symbol="USDT0",
    )


@pytest.fixture
def wflr_token() -> TokenAddress:
    """Create a TokenAddress for WFLR."""
    return TokenAddress(
        address="0x0000000000000000000000000000000000000003",
        decimals=18,
        symbol="WFLR",
    )


@pytest.fixture
def fxrp_usdt0_pair() -> TradingPair:
    """Create a TradingPair for FXRP/USDT0."""
    return TradingPair(base_token="FXRP", quote_token="USDT0")


@pytest.fixture
def fxrp_wflr_pair() -> TradingPair:
    """Create a TradingPair for FXRP/WFLR."""
    return TradingPair(base_token="FXRP", quote_token="WFLR")


@pytest.fixture
def wflr_usdt0_pair() -> TradingPair:
    """Create a TradingPair for WFLR/USDT0."""
    return TradingPair(base_token="WFLR", quote_token="USDT0")


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def basic_flare_config() -> FlareConfig:
    """Create a basic FlareConfig."""
    return FlareConfig(
        rpc_endpoints=["https://flare-api.flare.network/ext/C/rpc"],
        chain_id=14,
    )


@pytest.fixture
def basic_token_config() -> dict:
    """Create basic token configurations."""
    return {
        "FXRP": TokenConfig(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        ),
        "USDT0": TokenConfig(
            address="0x0000000000000000000000000000000000000002",
            decimals=6,
            symbol="USDT0",
        ),
        "WFLR": TokenConfig(
            address="0x0000000000000000000000000000000000000003",
            decimals=18,
            symbol="WFLR",
        ),
    }


@pytest.fixture
def basic_dex_configs() -> list[DEXConfig]:
    """Create basic DEX configurations."""
    return [
        DEXConfig(
            name="SparkDEX",
            type="uniswap_v2",
            factory_address="0x1111111111111111111111111111111111111111",
            router_address="0x2222222222222222222222222222222222222222",
            enabled=True,
        ),
        DEXConfig(
            name="BlazeSwap",
            type="uniswap_v2",
            factory_address="0x3333333333333333333333333333333333333333",
            router_address="0x4444444444444444444444444444444444444444",
            enabled=True,
        ),
        DEXConfig(
            name="SparkDEX V3",
            type="uniswap_v3",
            factory_address="0x5555555555555555555555555555555555555555",
            router_address="0x6666666666666666666666666666666666666666",
            enabled=True,
        ),
    ]


@pytest.fixture
def basic_monitoring_config() -> MonitoringConfig:
    """Create basic MonitoringConfig."""
    return MonitoringConfig(
        poll_interval_seconds=2,
        spread_alert_threshold_percent=Decimal("5.0"),
        max_concurrent_requests=10,
        request_timeout_seconds=5,
        max_retries=3,
        retry_backoff_seconds=1,
    )


@pytest.fixture
def complete_config(
    basic_flare_config,
    basic_token_config,
    basic_dex_configs,
    basic_monitoring_config,
) -> Config:
    """Create a complete Config object for testing."""
    return Config(
        flare=basic_flare_config,
        dexes=basic_dex_configs,
        tokens=basic_token_config,
        pairs=[
            PairConfig(base="FXRP", quote="USDT0", enabled=True),
            PairConfig(base="FXRP", quote="WFLR", enabled=True),
            PairConfig(base="WFLR", quote="USDT0", enabled=True),
        ],
        monitoring=basic_monitoring_config,
        advanced=AdvancedConfig(enable_pair_cache=True),
    )


# ============================================================================
# Price and Spread Fixtures
# ============================================================================

@pytest.fixture
def sample_price_valid(fxrp_usdt0_pair) -> Price:
    """Create a valid Price object."""
    return Price(
        pair=fxrp_usdt0_pair,
        dex_name="SparkDEX",
        price=Decimal("0.0045"),
        liquidity=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_price_error(fxrp_usdt0_pair) -> Price:
    """Create a Price object with an error."""
    return Price(
        pair=fxrp_usdt0_pair,
        dex_name="SparkDEX",
        price=None,
        liquidity=None,
        timestamp=datetime.now(timezone.utc),
        error="Connection timeout",
    )


@pytest.fixture
def sample_spread(fxrp_usdt0_pair) -> Spread:
    """Create a valid Spread object."""
    return Spread(
        pair=fxrp_usdt0_pair,
        low_dex="SparkDEX",
        high_dex="BlazeSwap",
        low_price=Decimal("0.0045"),
        high_price=Decimal("0.0048"),
        spread_percent=Decimal("6.67"),
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_spread_no_opportunity(fxrp_usdt0_pair) -> Spread:
    """Create a Spread with zero spread (no opportunity)."""
    return Spread(
        pair=fxrp_usdt0_pair,
        low_dex="SparkDEX",
        high_dex="SparkDEX",
        low_price=Decimal("0.0045"),
        high_price=Decimal("0.0045"),
        spread_percent=Decimal("0.00"),
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================================
# DEX Status Fixtures
# ============================================================================

@pytest.fixture
def dex_status_online() -> DEXStatus:
    """Create an online DEXStatus."""
    return DEXStatus(
        dex_name="SparkDEX",
        is_online=True,
        last_update=datetime.now(timezone.utc),
        error_count=0,
    )


@pytest.fixture
def dex_status_offline() -> DEXStatus:
    """Create an offline DEXStatus."""
    return DEXStatus(
        dex_name="BlazeSwap",
        is_online=False,
        last_update=datetime.now(timezone.utc),
        error_count=5,
        last_error="Connection timeout",
    )


# ============================================================================
# Mock Web3 Fixtures
# ============================================================================

@pytest.fixture
def mock_web3():
    """Create a mock AsyncWeb3 instance."""
    mock_w3 = MagicMock(spec=AsyncWeb3)
    mock_w3.eth = MagicMock()

    # Create async mock for chain_id property
    async def get_chain_id():
        return 14

    type(mock_w3.eth).chain_id = property(lambda self: get_chain_id())
    mock_w3.to_checksum_address = lambda addr: addr
    mock_w3.is_connected = AsyncMock(return_value=True)

    return mock_w3


@pytest.fixture
def mock_contract():
    """Create a mock Web3 contract instance."""
    mock = AsyncMock()
    mock.functions = MagicMock()
    return mock


@pytest.fixture
def mock_contract_call():
    """Create a mock contract function call."""
    mock = AsyncMock()
    mock.call = AsyncMock()
    return mock


# ============================================================================
# ABI Fixtures
# ============================================================================

@pytest.fixture
def uniswap_v2_factory_abi():
    """Return simplified Uniswap V2 Factory ABI."""
    return [
        {
            "type": "function",
            "name": "getPair",
            "inputs": [
                {"name": "tokenA", "type": "address"},
                {"name": "tokenB", "type": "address"},
            ],
            "outputs": [{"name": "pair", "type": "address"}],
        }
    ]


@pytest.fixture
def uniswap_v2_pair_abi():
    """Return simplified Uniswap V2 Pair ABI."""
    return [
        {
            "type": "function",
            "name": "getReserves",
            "outputs": [
                {"name": "_reserve0", "type": "uint112"},
                {"name": "_reserve1", "type": "uint112"},
                {"name": "_blockTimestampLast", "type": "uint32"},
            ],
        },
        {
            "type": "function",
            "name": "token0",
            "outputs": [{"name": "", "type": "address"}],
        },
        {
            "type": "function",
            "name": "token1",
            "outputs": [{"name": "", "type": "address"}],
        },
    ]


@pytest.fixture
def uniswap_v3_factory_abi():
    """Return simplified Uniswap V3 Factory ABI."""
    return [
        {
            "type": "function",
            "name": "getPool",
            "inputs": [
                {"name": "tokenA", "type": "address"},
                {"name": "tokenB", "type": "address"},
                {"name": "fee", "type": "uint24"},
            ],
            "outputs": [{"name": "pool", "type": "address"}],
        }
    ]


@pytest.fixture
def uniswap_v3_pool_abi():
    """Return simplified Uniswap V3 Pool ABI."""
    return [
        {
            "type": "function",
            "name": "slot0",
            "outputs": [
                {"name": "sqrtPriceX96", "type": "uint160"},
                {"name": "tick", "type": "int24"},
                {"name": "observationIndex", "type": "uint16"},
                {"name": "observationCardinality", "type": "uint16"},
                {"name": "observationCardinalityNext", "type": "uint16"},
                {"name": "feeProtocol", "type": "uint8"},
                {"name": "unlocked", "type": "bool"},
            ],
        },
        {
            "type": "function",
            "name": "liquidity",
            "outputs": [{"name": "", "type": "uint128"}],
        },
        {
            "type": "function",
            "name": "token0",
            "outputs": [{"name": "", "type": "address"}],
        },
        {
            "type": "function",
            "name": "token1",
            "outputs": [{"name": "", "type": "address"}],
        },
    ]


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def now() -> datetime:
    """Return current datetime in UTC."""
    return datetime.now(timezone.utc)


@pytest.fixture
def decimal_0045() -> Decimal:
    """Return a test Decimal value."""
    return Decimal("0.0045")


@pytest.fixture
def decimal_0048() -> Decimal:
    """Return another test Decimal value."""
    return Decimal("0.0048")
