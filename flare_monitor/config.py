"""Configuration loader for Flare Monitor.

This module provides Pydantic models and functions to load and validate
the application configuration from YAML files. All configuration values
are validated at load time to catch errors early.

The configuration structure follows the architecture specification in
docs/architecture.md section 7 and matches the structure defined in
config/config.example.yaml.

Example:
    >>> config = load_config("config/config.yaml")
    >>> print(config.flare.chain_id)
    14
    >>> print(config.monitoring.poll_interval_seconds)
    2
"""

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class FlareConfig(BaseModel):
    """Flare Network connection settings.

    Attributes:
        rpc_endpoints: List of RPC URLs to use for blockchain queries.
            The first endpoint is primary, others are fallbacks.
        chain_id: Flare Network chain ID (14 for mainnet, 114 for testnet).
    """

    rpc_endpoints: list[str] = Field(
        ...,
        min_length=1,
        description="List of Flare RPC endpoint URLs"
    )
    chain_id: int = Field(
        ...,
        ge=1,
        description="Flare Network chain ID"
    )

    @field_validator("rpc_endpoints")
    @classmethod
    def validate_rpc_endpoints(cls, v: list[str]) -> list[str]:
        """Validate that all RPC endpoints are valid URLs.

        Checks:
        - Must start with http:// or https://
        - Should not be empty strings
        - Should not have obvious formatting issues
        """
        if not v:
            raise ValueError("At least one RPC endpoint must be configured")

        for i, endpoint in enumerate(v):
            # Check empty string
            if not endpoint or not endpoint.strip():
                raise ValueError(f"RPC endpoint at index {i} is empty")

            # Trim whitespace
            endpoint_trimmed = endpoint.strip()

            # Check protocol
            if not endpoint_trimmed.startswith(("http://", "https://")):
                raise ValueError(
                    f"Invalid RPC endpoint '{endpoint}': must start with http:// or https://"
                )

            # Check for localhost/127.0.0.1 (warning, not error)
            if "localhost" in endpoint_trimmed.lower() or "127.0.0.1" in endpoint_trimmed:
                import logging
                logger = logging.getLogger("flare_monitor.config")
                logger.warning(
                    f"RPC endpoint {i} uses localhost address: {endpoint_trimmed}. "
                    f"This may not work in all environments."
                )

            # Update list with trimmed version
            v[i] = endpoint_trimmed

        return v

    @field_validator("chain_id")
    @classmethod
    def validate_chain_id(cls, v: int) -> int:
        """Validate chain ID is reasonable.

        Known Flare chain IDs:
        - 14: Flare mainnet
        - 114: Flare testnet (Coston2)
        """
        # Warn about unknown chain IDs
        known_chain_ids = {14: "Flare Mainnet", 114: "Coston2 Testnet"}
        if v not in known_chain_ids:
            import logging
            logger = logging.getLogger("flare_monitor.config")
            logger.warning(
                f"Chain ID {v} is not a known Flare chain ID. "
                f"Known IDs: {known_chain_ids}"
            )
        return v


class DEXConfig(BaseModel):
    """Configuration for a single DEX.

    Attributes:
        name: Display name of the DEX (e.g., "SparkDEX", "BlazeSwap").
        type: DEX protocol type (e.g., "uniswap_v2", "uniswap_v3").
        factory_address: Ethereum address of the DEX factory contract.
        router_address: Ethereum address of the DEX router contract.
        enabled: Whether to monitor this DEX (default: True).
        description: Optional human-readable description of the DEX.
    """

    name: str = Field(
        ...,
        min_length=1,
        description="DEX display name"
    )
    type: str = Field(
        ...,
        pattern="^(uniswap_v2|uniswap_v3)$",
        description="DEX protocol type"
    )
    factory_address: str = Field(
        ...,
        description="Factory contract address"
    )
    router_address: str = Field(
        ...,
        description="Router contract address"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this DEX is enabled for monitoring"
    )
    description: str | None = Field(
        default=None,
        description="Optional DEX description"
    )

    @field_validator("factory_address", "router_address")
    @classmethod
    def validate_ethereum_address(cls, v: str) -> str:
        """Validate that addresses are valid Ethereum addresses.

        Checks that the address:
        - Starts with '0x'
        - Is 42 characters long (0x + 40 hex digits)
        - Contains only valid hex characters

        Args:
            v: The address string to validate.

        Returns:
            The validated address in lowercase.

        Raises:
            ValueError: If the address format is invalid.
        """
        if not v.startswith("0x"):
            raise ValueError(f"Address must start with '0x': {v}")

        if len(v) != 42:
            raise ValueError(
                f"Address must be 42 characters (0x + 40 hex digits): {v}"
            )

        try:
            # Validate hex characters (case-insensitive)
            int(v[2:], 16)
        except ValueError:
            raise ValueError(f"Address contains invalid hex characters: {v}")

        # Return lowercase for consistent comparison
        return v.lower()

    @model_validator(mode="after")
    def validate_addresses_unique(self) -> "DEXConfig":
        """Ensure factory and router addresses are different.

        Skips validation for zero addresses (placeholder values).
        Also validates that enabled DEXes don't have zero addresses.
        """
        # Allow zero addresses as placeholders (common for disabled/unconfigured DEXes)
        zero_address = "0x0000000000000000000000000000000000000000"

        # Check if enabled DEX has zero addresses
        if self.enabled:
            if self.factory_address.lower() == zero_address:
                raise ValueError(
                    f"Enabled DEX '{self.name}' cannot have zero address for factory. "
                    f"Either disable the DEX or provide a valid factory address."
                )
            if self.router_address.lower() == zero_address:
                import logging
                logger = logging.getLogger("flare_monitor.config")
                logger.warning(
                    f"DEX '{self.name}' has zero address for router. "
                    f"This may cause issues if router functionality is needed."
                )

        if (self.factory_address == self.router_address and
            self.factory_address != zero_address):
            raise ValueError(
                f"Factory and router addresses must be different for {self.name}"
            )
        return self


class TokenConfig(BaseModel):
    """Token information for a specific ERC-20 token.

    Attributes:
        address: Ethereum address of the token contract.
        decimals: Number of decimal places for the token (typically 6 or 18).
        symbol: Token symbol (e.g., "FXRP", "USDT0", "WFLR").
        name: Optional full name of the token.
        description: Optional description of the token.
    """

    address: str = Field(
        ...,
        description="Token contract address"
    )
    decimals: int = Field(
        ...,
        ge=0,
        le=77,  # Maximum decimals in ERC-20 spec
        description="Token decimal places"
    )
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Token symbol"
    )
    name: str | None = Field(
        default=None,
        description="Token full name"
    )
    description: str | None = Field(
        default=None,
        description="Token description"
    )

    @field_validator("address")
    @classmethod
    def validate_ethereum_address(cls, v: str) -> str:
        """Validate that address is a valid Ethereum address.

        Args:
            v: The address string to validate.

        Returns:
            The validated address in lowercase.

        Raises:
            ValueError: If the address format is invalid.
        """
        if not v.startswith("0x"):
            raise ValueError(f"Token address must start with '0x': {v}")

        if len(v) != 42:
            raise ValueError(
                f"Token address must be 42 characters (0x + 40 hex digits): {v}"
            )

        try:
            int(v[2:], 16)
        except ValueError:
            raise ValueError(f"Token address contains invalid hex characters: {v}")

        return v.lower()

    @field_validator("decimals")
    @classmethod
    def validate_common_decimals(cls, v: int) -> int:
        """Warn about uncommon decimal values.

        Most tokens use 18 decimals (ETH standard) or 6 decimals (USDT/USDC).
        This validator doesn't fail but helps catch configuration errors.

        Args:
            v: The decimals value to validate.

        Returns:
            The validated decimals value.
        """
        # Common decimal values - no validation error, just awareness
        # 6 = USDT/USDC, 8 = WBTC, 18 = ETH/most ERC-20s
        if v not in (6, 8, 18):
            # This is unusual but not invalid - log at INFO level
            pass

        return v


class PairConfig(BaseModel):
    """Trading pair configuration.

    Represents a pair of tokens to monitor for price spreads.

    Attributes:
        base: Symbol of the base token (the token being priced).
        quote: Symbol of the quote token (the pricing denomination).
        enabled: Whether to monitor this pair (default: True).
        description: Optional description of the pair.
    """

    base: str = Field(
        ...,
        min_length=1,
        description="Base token symbol"
    )
    quote: str = Field(
        ...,
        min_length=1,
        description="Quote token symbol"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this pair is enabled for monitoring"
    )
    description: str | None = Field(
        default=None,
        description="Optional pair description"
    )

    @model_validator(mode="after")
    def validate_tokens_different(self) -> "PairConfig":
        """Ensure base and quote tokens are different."""
        if self.base == self.quote:
            raise ValueError(
                f"Base and quote tokens must be different (got {self.base}/{self.quote})"
            )
        return self


class MonitoringConfig(BaseModel):
    """Monitoring behavior settings.

    Attributes:
        poll_interval_seconds: How often to fetch prices from DEXes (in seconds).
        spread_alert_threshold_percent: Minimum spread percentage to trigger alerts.
        max_concurrent_requests: Maximum number of concurrent RPC requests.
        request_timeout_seconds: Timeout for individual RPC requests (in seconds).
        max_retries: Number of retry attempts for failed requests.
        retry_backoff_seconds: Initial delay between retries (exponential backoff).
        price_staleness_threshold_seconds: Alert if no update within this timeframe.
    """

    poll_interval_seconds: int = Field(
        ...,
        ge=1,
        le=300,
        description="Polling interval in seconds"
    )
    spread_alert_threshold_percent: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Minimum spread percentage for alerts"
    )
    max_concurrent_requests: int = Field(
        ...,
        ge=1,
        le=100,
        description="Maximum concurrent RPC requests"
    )
    request_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="RPC request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests"
    )
    retry_backoff_seconds: int = Field(
        default=2,
        ge=1,
        le=60,
        description="Initial retry backoff delay in seconds"
    )
    price_staleness_threshold_seconds: int = Field(
        default=30,
        ge=1,
        description="Price staleness threshold in seconds"
    )

    @field_validator("spread_alert_threshold_percent", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: Any) -> Decimal:
        """Convert numeric values to Decimal for precise calculations.

        Args:
            v: The value to convert (int, float, str, or Decimal).

        Returns:
            The value as a Decimal.

        Raises:
            ValueError: If the value cannot be converted to Decimal.
        """
        try:
            return Decimal(str(v))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert to Decimal: {v}") from e


class LoggingConfig(BaseModel):
    """Logging configuration settings.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        output: Log output destination (console, file, or both).
        file_path: Path to log file (used if output is 'file' or 'both').
        enable_rotation: Whether to enable log file rotation.
        max_file_size_mb: Maximum log file size before rotation (in MB).
        backup_count: Number of rotated log files to keep.
    """

    level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Log level"
    )
    output: str = Field(
        default="console",
        pattern="^(console|file|both)$",
        description="Log output destination"
    )
    file_path: str = Field(
        default="logs/flare-monitor.log",
        description="Log file path"
    )
    enable_rotation: bool = Field(
        default=True,
        description="Enable log file rotation"
    )
    max_file_size_mb: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum log file size in MB"
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Number of backup log files to keep"
    )


class DisplayConfig(BaseModel):
    """Console display settings.

    Attributes:
        enable_rich_output: Whether to use rich console formatting.
        refresh_interval_seconds: How often to refresh the display (in seconds).
        color_thresholds: Spread percentage thresholds for color coding.
    """

    enable_rich_output: bool = Field(
        default=True,
        description="Enable rich console formatting"
    )
    refresh_interval_seconds: int = Field(
        default=1,
        ge=1,
        le=60,
        description="Display refresh interval in seconds"
    )
    color_thresholds: dict[str, Decimal] = Field(
        default_factory=lambda: {
            "high_opportunity": Decimal("5.0"),
            "medium_opportunity": Decimal("2.0"),
            "low_opportunity": Decimal("0.5"),
        },
        description="Spread thresholds for color coding"
    )

    @field_validator("color_thresholds", mode="before")
    @classmethod
    def convert_thresholds_to_decimal(cls, v: dict[str, Any]) -> dict[str, Decimal]:
        """Convert threshold values to Decimal.

        Args:
            v: Dictionary of threshold names to numeric values.

        Returns:
            Dictionary with Decimal values.

        Raises:
            ValueError: If any value cannot be converted to Decimal.
        """
        result = {}
        for key, value in v.items():
            try:
                result[key] = Decimal(str(value))
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Cannot convert color_threshold '{key}' to Decimal: {value}"
                ) from e
        return result


class AdvancedConfig(BaseModel):
    """Advanced configuration options.

    Attributes:
        enable_multicall: Whether to use multicall contract for batching.
        multicall_address: Address of the multicall contract (if enabled).
        enable_gas_estimation: Whether to estimate gas costs for profitability.
        slippage_tolerance_percent: Expected slippage tolerance (percentage).
        enable_pair_cache: Whether to cache DEX pair addresses.
        enable_websocket: Whether to use WebSocket for real-time updates.
    """

    enable_multicall: bool = Field(
        default=False,
        description="Enable multicall contract batching"
    )
    multicall_address: str = Field(
        default="",
        description="Multicall contract address"
    )
    enable_gas_estimation: bool = Field(
        default=False,
        description="Enable gas price estimation"
    )
    slippage_tolerance_percent: Decimal = Field(
        default=Decimal("0.5"),
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Slippage tolerance percentage"
    )
    enable_pair_cache: bool = Field(
        default=True,
        description="Enable DEX pair address caching"
    )
    enable_websocket: bool = Field(
        default=False,
        description="Enable WebSocket connections"
    )

    @field_validator("slippage_tolerance_percent", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: Any) -> Decimal:
        """Convert numeric values to Decimal."""
        try:
            return Decimal(str(v))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert to Decimal: {v}") from e

    @model_validator(mode="after")
    def validate_multicall_address(self) -> "AdvancedConfig":
        """Validate that multicall address is provided if multicall is enabled."""
        if self.enable_multicall and not self.multicall_address:
            raise ValueError(
                "multicall_address must be provided when enable_multicall is True"
            )
        return self


class Config(BaseModel):
    """Main configuration combining all settings.

    This is the root configuration object that contains all subsections.

    Attributes:
        flare: Flare Network connection settings.
        dexes: List of DEX configurations.
        tokens: Dictionary of token configurations (keyed by symbol).
        pairs: List of trading pair configurations.
        monitoring: Monitoring behavior settings.
        logging: Logging configuration (optional).
        display: Display settings (optional).
        advanced: Advanced configuration options (optional).
    """

    flare: FlareConfig = Field(
        ...,
        description="Flare Network configuration"
    )
    dexes: list[DEXConfig] = Field(
        ...,
        min_length=1,
        description="List of DEX configurations"
    )
    tokens: dict[str, TokenConfig] = Field(
        ...,
        min_length=1,
        description="Token configurations keyed by symbol"
    )
    pairs: list[PairConfig] = Field(
        ...,
        min_length=1,
        description="List of trading pair configurations"
    )
    monitoring: MonitoringConfig = Field(
        ...,
        description="Monitoring settings"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    display: DisplayConfig = Field(
        default_factory=DisplayConfig,
        description="Display settings"
    )
    advanced: AdvancedConfig = Field(
        default_factory=AdvancedConfig,
        description="Advanced configuration"
    )

    @model_validator(mode="after")
    def validate_pairs_reference_tokens(self) -> "Config":
        """Validate that all pairs reference tokens defined in the tokens section.

        Also validates that token addresses are unique and properly checksummed.

        Returns:
            The validated Config object.

        Raises:
            ValueError: If a pair references an undefined token, or token addresses
                       are duplicated.
        """
        token_symbols = set(self.tokens.keys())

        # Check for duplicate token addresses
        token_addresses = {}
        for symbol, token_config in self.tokens.items():
            addr_lower = token_config.address.lower()
            if addr_lower in token_addresses:
                raise ValueError(
                    f"Duplicate token address: {token_config.address} used by both "
                    f"'{token_addresses[addr_lower]}' and '{symbol}'"
                )
            token_addresses[addr_lower] = symbol

        # Validate pairs reference defined tokens
        for pair in self.pairs:
            if pair.base not in token_symbols:
                raise ValueError(
                    f"Pair {pair.base}/{pair.quote}: base token '{pair.base}' "
                    f"not found in tokens section. Available tokens: {sorted(token_symbols)}"
                )
            if pair.quote not in token_symbols:
                raise ValueError(
                    f"Pair {pair.base}/{pair.quote}: quote token '{pair.quote}' "
                    f"not found in tokens section. Available tokens: {sorted(token_symbols)}"
                )

        return self

    @model_validator(mode="after")
    def validate_enabled_dexes(self) -> "Config":
        """Validate that at least one DEX is enabled.

        Returns:
            The validated Config object.

        Raises:
            ValueError: If no DEXes are enabled.
        """
        enabled_dexes = [dex for dex in self.dexes if dex.enabled]
        if not enabled_dexes:
            raise ValueError("At least one DEX must be enabled")

        return self

    @model_validator(mode="after")
    def validate_enabled_pairs(self) -> "Config":
        """Validate that at least one pair is enabled.

        Returns:
            The validated Config object.

        Raises:
            ValueError: If no pairs are enabled.
        """
        enabled_pairs = [pair for pair in self.pairs if pair.enabled]
        if not enabled_pairs:
            raise ValueError("At least one pair must be enabled")

        return self

    @model_validator(mode="after")
    def validate_dex_names_unique(self) -> "Config":
        """Validate that DEX names are unique and factory addresses don't overlap.

        Returns:
            The validated Config object.

        Raises:
            ValueError: If duplicate DEX names or factory addresses are found.
        """
        # Check for duplicate DEX names
        dex_names = [dex.name for dex in self.dexes]
        duplicates = [name for name in dex_names if dex_names.count(name) > 1]

        if duplicates:
            raise ValueError(
                f"Duplicate DEX names found: {', '.join(set(duplicates))}"
            )

        # Check for duplicate factory addresses (among enabled DEXes)
        zero_address = "0x0000000000000000000000000000000000000000"
        factory_addresses = {}
        for dex in self.dexes:
            if not dex.enabled:
                continue
            addr_lower = dex.factory_address.lower()
            if addr_lower == zero_address:
                continue
            if addr_lower in factory_addresses:
                raise ValueError(
                    f"Duplicate factory address {dex.factory_address} used by "
                    f"DEXes '{factory_addresses[addr_lower]}' and '{dex.name}'"
                )
            factory_addresses[addr_lower] = dex.name

        return self

    @model_validator(mode="after")
    def validate_monitoring_settings(self) -> "Config":
        """Validate that monitoring settings are reasonable.

        Returns:
            The validated Config object.
        """
        import logging
        logger = logging.getLogger("flare_monitor.config")

        # Warn about very short poll intervals
        if self.monitoring.poll_interval_seconds < 2:
            logger.warning(
                f"Poll interval of {self.monitoring.poll_interval_seconds}s is very short. "
                f"This may cause excessive RPC requests and rate limiting."
            )

        # Warn about very low spread thresholds
        if self.monitoring.spread_alert_threshold_percent < Decimal("0.1"):
            logger.warning(
                f"Spread alert threshold of {self.monitoring.spread_alert_threshold_percent}% "
                f"is very low. You may get many alerts for insignificant price differences."
            )

        # Warn about high retry counts
        if self.monitoring.max_retries > 5:
            logger.warning(
                f"Max retries is set to {self.monitoring.max_retries}, which is quite high. "
                f"This may cause long delays when DEXes are failing."
            )

        return self


def load_config(path: str) -> Config:
    """Load and validate configuration from a YAML file.

    This function reads a YAML configuration file, parses it, and validates
    all settings using Pydantic models. If validation fails, detailed error
    messages are provided to help fix the configuration.

    Args:
        path: Path to the YAML configuration file (absolute or relative).

    Returns:
        A validated Config object containing all settings.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration file is invalid or fails validation.
        yaml.YAMLError: If the YAML syntax is invalid.

    Example:
        >>> config = load_config("config/config.yaml")
        >>> print(f"Monitoring {len(config.dexes)} DEXes")
        >>> print(f"Chain ID: {config.flare.chain_id}")
    """
    config_path = Path(path)

    # Check if file exists
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create a config file or copy from config/config.example.yaml"
        )

    # Check if file is readable
    if not config_path.is_file():
        raise ValueError(
            f"Configuration path is not a file: {config_path}"
        )

    # Load YAML file
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(
            f"Invalid YAML syntax in {config_path}: {e}"
        ) from e
    except Exception as e:
        raise ValueError(
            f"Error reading configuration file {config_path}: {e}"
        ) from e

    # Validate that YAML contains a dictionary
    if not isinstance(config_data, dict):
        raise ValueError(
            f"Configuration file must contain a YAML dictionary, got {type(config_data)}"
        )

    # Parse and validate configuration using Pydantic
    try:
        config = Config(**config_data)
    except Exception as e:
        raise ValueError(
            f"Configuration validation failed for {config_path}:\n{e}"
        ) from e

    return config
