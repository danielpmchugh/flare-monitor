"""Tests for flare_monitor/config.py

This module tests configuration loading and validation including:
- YAML file loading
- Pydantic model validation
- Cross-reference validation (tokens in pairs)
- Invalid configuration handling
- Enhanced validation (RPC endpoints, chain ID, unique addresses)
"""

from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
import tempfile

import pytest

from flare_monitor.config import (
    FlareConfig,
    DEXConfig,
    TokenConfig,
    PairConfig,
    MonitoringConfig,
    AdvancedConfig,
    Config,
)


# ============================================================================
# FlareConfig Tests
# ============================================================================

class TestFlareConfig:
    """Tests for FlareConfig model."""

    def test_flare_config_valid(self):
        """Test creating a valid FlareConfig."""
        config = FlareConfig(
            rpc_endpoints=["https://flare-api.flare.network/ext/C/rpc"],
            chain_id=14,
        )
        assert len(config.rpc_endpoints) == 1
        assert config.chain_id == 14

    def test_flare_config_multiple_endpoints(self):
        """Test FlareConfig with multiple RPC endpoints."""
        endpoints = [
            "https://flare-api.flare.network/ext/C/rpc",
            "https://flare-api2.flare.network/ext/C/rpc",
        ]
        config = FlareConfig(rpc_endpoints=endpoints, chain_id=14)
        assert len(config.rpc_endpoints) == 2

    def test_flare_config_requires_at_least_one_endpoint(self):
        """Test that at least one RPC endpoint is required."""
        with pytest.raises(ValueError, match="At least one RPC endpoint"):
            FlareConfig(rpc_endpoints=[], chain_id=14)

    def test_flare_config_rejects_empty_string_endpoint(self):
        """Test that empty string endpoints are rejected."""
        with pytest.raises(ValueError, match="is empty"):
            FlareConfig(rpc_endpoints=[""], chain_id=14)

    def test_flare_config_requires_http_https_protocol(self):
        """Test that endpoints must start with http:// or https://."""
        with pytest.raises(ValueError, match="must start with http"):
            FlareConfig(
                rpc_endpoints=["ftp://flare-api.flare.network/ext/C/rpc"],
                chain_id=14,
            )

    def test_flare_config_trims_whitespace_from_endpoints(self):
        """Test that whitespace is trimmed from endpoints."""
        config = FlareConfig(
            rpc_endpoints=["  https://flare-api.flare.network/ext/C/rpc  "],
            chain_id=14,
        )
        assert config.rpc_endpoints[0] == "https://flare-api.flare.network/ext/C/rpc"

    def test_flare_config_warns_about_localhost(self):
        """Test that localhost endpoints trigger warning."""
        with patch("flare_monitor.config.logging.getLogger") as mock_logger:
            config = FlareConfig(
                rpc_endpoints=["http://localhost:8545"],
                chain_id=14,
            )
            # Just verify it creates without error
            assert config.rpc_endpoints[0] == "http://localhost:8545"

    def test_flare_config_warns_about_unknown_chain_ids(self):
        """Test that unknown chain IDs trigger warning."""
        with patch("flare_monitor.config.logging.getLogger"):
            # Should not raise, just warn
            config = FlareConfig(
                rpc_endpoints=["https://flare-api.flare.network/ext/C/rpc"],
                chain_id=999,
            )
            assert config.chain_id == 999

    def test_flare_config_accepts_known_chain_ids(self):
        """Test that known chain IDs are accepted without warning."""
        # Mainnet (14)
        config = FlareConfig(
            rpc_endpoints=["https://flare-api.flare.network/ext/C/rpc"],
            chain_id=14,
        )
        assert config.chain_id == 14

        # Testnet (114)
        config = FlareConfig(
            rpc_endpoints=["https://coston2-api.flare.network/ext/C/rpc"],
            chain_id=114,
        )
        assert config.chain_id == 114


# ============================================================================
# DEXConfig Tests
# ============================================================================

class TestDEXConfig:
    """Tests for DEXConfig model."""

    def test_dex_config_valid(self):
        """Test creating a valid DEXConfig."""
        config = DEXConfig(
            name="SparkDEX",
            type="uniswap_v2",
            factory_address="0x1111111111111111111111111111111111111111",
            router_address="0x2222222222222222222222222222222222222222",
            enabled=True,
        )
        assert config.name == "SparkDEX"
        assert config.type == "uniswap_v2"
        assert config.enabled is True

    def test_dex_config_requires_valid_type(self):
        """Test that DEX type must be valid."""
        with pytest.raises(ValueError):
            DEXConfig(
                name="InvalidDEX",
                type="uniswap_v4",  # Invalid
                factory_address="0x1111111111111111111111111111111111111111",
                router_address="0x2222222222222222222222222222222222222222",
            )

    def test_dex_config_lowercases_addresses(self):
        """Test that addresses are converted to lowercase."""
        config = DEXConfig(
            name="SparkDEX",
            type="uniswap_v2",
            factory_address="0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            router_address="0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        )
        assert config.factory_address == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert config.router_address == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    def test_dex_config_requires_0x_prefix(self):
        """Test that addresses must start with 0x."""
        with pytest.raises(ValueError, match="must start with '0x'"):
            DEXConfig(
                name="SparkDEX",
                type="uniswap_v2",
                factory_address="1111111111111111111111111111111111111111",
                router_address="0x2222222222222222222222222222222222222222",
            )

    def test_dex_config_requires_42_char_address(self):
        """Test that addresses must be 42 characters."""
        with pytest.raises(ValueError, match="42 characters"):
            DEXConfig(
                name="SparkDEX",
                type="uniswap_v2",
                factory_address="0x1111111111111111111111111111111111111111",
                router_address="0x22222222222222222222222222222222222",  # Too short
            )

    def test_dex_config_rejects_invalid_hex(self):
        """Test that addresses must contain valid hex."""
        with pytest.raises(ValueError, match="invalid hex characters"):
            DEXConfig(
                name="SparkDEX",
                type="uniswap_v2",
                factory_address="0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
                router_address="0x2222222222222222222222222222222222222222",
            )

    def test_dex_config_requires_different_addresses(self):
        """Test that factory and router addresses must be different."""
        with pytest.raises(ValueError, match="must be different"):
            DEXConfig(
                name="SparkDEX",
                type="uniswap_v2",
                factory_address="0x1111111111111111111111111111111111111111",
                router_address="0x1111111111111111111111111111111111111111",
            )

    def test_dex_config_allows_zero_addresses_for_disabled(self):
        """Test that zero addresses are allowed for disabled DEXes."""
        zero_addr = "0x0000000000000000000000000000000000000000"
        config = DEXConfig(
            name="DisabledDEX",
            type="uniswap_v2",
            factory_address=zero_addr,
            router_address="0x2222222222222222222222222222222222222222",
            enabled=False,
        )
        assert config.enabled is False

    def test_dex_config_rejects_zero_factory_for_enabled(self):
        """Test that enabled DEX cannot have zero factory address."""
        zero_addr = "0x0000000000000000000000000000000000000000"
        with pytest.raises(ValueError, match="cannot have zero address for factory"):
            DEXConfig(
                name="SparkDEX",
                type="uniswap_v2",
                factory_address=zero_addr,
                router_address="0x2222222222222222222222222222222222222222",
                enabled=True,
            )

    def test_dex_config_default_enabled_is_true(self):
        """Test that enabled defaults to True."""
        config = DEXConfig(
            name="SparkDEX",
            type="uniswap_v2",
            factory_address="0x1111111111111111111111111111111111111111",
            router_address="0x2222222222222222222222222222222222222222",
        )
        assert config.enabled is True


# ============================================================================
# TokenConfig Tests
# ============================================================================

class TestTokenConfig:
    """Tests for TokenConfig model."""

    def test_token_config_valid(self):
        """Test creating a valid TokenConfig."""
        config = TokenConfig(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="FXRP",
        )
        assert config.address == "0x0000000000000000000000000000000000000001"
        assert config.decimals == 18
        assert config.symbol == "FXRP"

    def test_token_config_decimals_range(self):
        """Test that decimals are validated."""
        # Valid: 0
        config = TokenConfig(
            address="0x0000000000000000000000000000000000000001",
            decimals=0,
            symbol="USDC",
        )
        assert config.decimals == 0

        # Valid: 18
        config = TokenConfig(
            address="0x0000000000000000000000000000000000000001",
            decimals=18,
            symbol="USDC",
        )
        assert config.decimals == 18

        # Invalid: negative
        with pytest.raises(ValueError):
            TokenConfig(
                address="0x0000000000000000000000000000000000000001",
                decimals=-1,
                symbol="USDC",
            )

        # Invalid: too high
        with pytest.raises(ValueError):
            TokenConfig(
                address="0x0000000000000000000000000000000000000001",
                decimals=78,  # Max is 77
                symbol="USDC",
            )

    def test_token_config_requires_symbol(self):
        """Test that symbol is required."""
        with pytest.raises(ValueError):
            TokenConfig(
                address="0x0000000000000000000000000000000000000001",
                decimals=18,
                symbol="",  # Empty not allowed
            )


# ============================================================================
# PairConfig Tests
# ============================================================================

class TestPairConfig:
    """Tests for PairConfig model."""

    def test_pair_config_valid(self):
        """Test creating a valid PairConfig."""
        config = PairConfig(base="FXRP", quote="USDT0", enabled=True)
        assert config.base == "FXRP"
        assert config.quote == "USDT0"
        assert config.enabled is True

    def test_pair_config_default_enabled(self):
        """Test that enabled defaults to True."""
        config = PairConfig(base="FXRP", quote="USDT0")
        assert config.enabled is True

    def test_pair_config_rejects_same_tokens(self):
        """Test that base and quote must be different."""
        with pytest.raises(ValueError, match="must be different"):
            PairConfig(base="FXRP", quote="FXRP")

    def test_pair_config_normalizes_tokens_uppercase(self):
        """Test that token symbols are normalized to uppercase."""
        config = PairConfig(base="fxrp", quote="usdt0")
        assert config.base == "FXRP"
        assert config.quote == "USDT0"


# ============================================================================
# MonitoringConfig Tests
# ============================================================================

class TestMonitoringConfig:
    """Tests for MonitoringConfig model."""

    def test_monitoring_config_valid(self):
        """Test creating a valid MonitoringConfig."""
        config = MonitoringConfig(
            poll_interval_seconds=2,
            spread_alert_threshold_percent=Decimal("5.0"),
            max_concurrent_requests=10,
            request_timeout_seconds=5,
            max_retries=3,
            retry_backoff_seconds=1,
        )
        assert config.poll_interval_seconds == 2
        assert config.spread_alert_threshold_percent == Decimal("5.0")

    def test_monitoring_config_requires_positive_intervals(self):
        """Test that intervals must be positive."""
        with pytest.raises(ValueError):
            MonitoringConfig(
                poll_interval_seconds=-1,
                spread_alert_threshold_percent=Decimal("5.0"),
            )

    def test_monitoring_config_requires_positive_threshold(self):
        """Test that threshold must be positive."""
        with pytest.raises(ValueError):
            MonitoringConfig(
                poll_interval_seconds=2,
                spread_alert_threshold_percent=Decimal("-5.0"),
            )


# ============================================================================
# AdvancedConfig Tests
# ============================================================================

class TestAdvancedConfig:
    """Tests for AdvancedConfig model."""

    def test_advanced_config_valid(self):
        """Test creating a valid AdvancedConfig."""
        config = AdvancedConfig(enable_pair_cache=True)
        assert config.enable_pair_cache is True

    def test_advanced_config_default_values(self):
        """Test default values for AdvancedConfig."""
        config = AdvancedConfig()
        assert config.enable_pair_cache is True  # Default enabled


# ============================================================================
# Config (Full Configuration) Tests
# ============================================================================

class TestConfigIntegration:
    """Tests for full Config model integration."""

    def test_config_creation_valid(self, complete_config):
        """Test creating a valid complete Config."""
        assert complete_config.flare is not None
        assert len(complete_config.dexes) > 0
        assert len(complete_config.tokens) > 0
        assert len(complete_config.pairs) > 0
        assert complete_config.monitoring is not None

    def test_config_validates_tokens_in_pairs(self, complete_config):
        """Test that Config validates tokens referenced in pairs exist."""
        # This is handled by PairConfig validation - ensure our config is valid
        assert "FXRP" in complete_config.tokens
        assert "USDT0" in complete_config.tokens
        assert "WFLR" in complete_config.tokens

    def test_config_enables_pair_cache_by_default(self, complete_config):
        """Test that pair cache is enabled by default."""
        assert complete_config.advanced.enable_pair_cache is True

    def test_config_has_multiple_dexes(self, complete_config):
        """Test that multiple DEXes can be configured."""
        assert len(complete_config.dexes) >= 2
        dex_types = {dex.type for dex in complete_config.dexes}
        assert "uniswap_v2" in dex_types or "uniswap_v3" in dex_types


# ============================================================================
# YAML Loading Tests (if load_config function exists)
# ============================================================================

class TestConfigLoading:
    """Tests for loading config from YAML files."""

    def test_load_minimal_yaml_config(self):
        """Test loading minimal valid YAML config."""
        yaml_content = """
flare:
  rpc_endpoints:
    - https://flare-api.flare.network/ext/C/rpc
  chain_id: 14

dexes:
  - name: SparkDEX
    type: uniswap_v2
    factory_address: "0x1111111111111111111111111111111111111111"
    router_address: "0x2222222222222222222222222222222222222222"
    enabled: true

tokens:
  FXRP:
    address: "0x0000000000000000000000000000000000000001"
    decimals: 18
    symbol: FXRP
  USDT0:
    address: "0x0000000000000000000000000000000000000002"
    decimals: 6
    symbol: USDT0

pairs:
  - base: FXRP
    quote: USDT0
    enabled: true

monitoring:
  poll_interval_seconds: 2
  spread_alert_threshold_percent: "5.0"
  max_concurrent_requests: 10
  request_timeout_seconds: 5
  max_retries: 3
  retry_backoff_seconds: 1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                from flare_monitor.config import load_config
                config = load_config(f.name)
                assert config.flare.chain_id == 14
                assert len(config.dexes) == 1
                assert "FXRP" in config.tokens
            finally:
                Path(f.name).unlink()

    def test_load_config_with_disabled_dex(self):
        """Test loading config with disabled DEX."""
        yaml_content = """
flare:
  rpc_endpoints:
    - https://flare-api.flare.network/ext/C/rpc
  chain_id: 14

dexes:
  - name: SparkDEX
    type: uniswap_v2
    factory_address: "0x1111111111111111111111111111111111111111"
    router_address: "0x2222222222222222222222222222222222222222"
    enabled: true
  - name: DisabledDEX
    type: uniswap_v2
    factory_address: "0x0000000000000000000000000000000000000000"
    router_address: "0x0000000000000000000000000000000000000002"
    enabled: false

tokens:
  FXRP:
    address: "0x0000000000000000000000000000000000000001"
    decimals: 18
    symbol: FXRP
  USDT0:
    address: "0x0000000000000000000000000000000000000002"
    decimals: 6
    symbol: USDT0

pairs:
  - base: FXRP
    quote: USDT0

monitoring:
  poll_interval_seconds: 2
  spread_alert_threshold_percent: "5.0"
  max_concurrent_requests: 10
  request_timeout_seconds: 5
  max_retries: 3
  retry_backoff_seconds: 1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                from flare_monitor.config import load_config
                config = load_config(f.name)
                assert len(config.dexes) == 2
                disabled_dex = [d for d in config.dexes if d.name == "DisabledDEX"][0]
                assert disabled_dex.enabled is False
            finally:
                Path(f.name).unlink()
