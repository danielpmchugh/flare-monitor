"""
Data models for Flare Monitor.

This module defines the core Pydantic models used throughout the application
for representing trading pairs, token addresses, prices, and spread calculations.
All financial values use Python's Decimal type for precision.
"""

from datetime import datetime
from decimal import Decimal
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from web3 import Web3


class TradingPair(BaseModel):
    """
    Represents a trading pair on a DEX.

    A trading pair consists of a base token (the asset being priced) and a
    quote token (the asset used to price the base). For example, in FXRP/USDT0,
    FXRP is the base token and USDT0 is the quote token.

    Attributes:
        base_token: Symbol of the base token (e.g., "FXRP")
        quote_token: Symbol of the quote token (e.g., "USDT0")
    """

    base_token: str = Field(
        ...,
        description="Base token symbol",
        min_length=1,
        max_length=20,
    )
    quote_token: str = Field(
        ...,
        description="Quote token symbol",
        min_length=1,
        max_length=20,
    )

    @field_validator("base_token", "quote_token")
    @classmethod
    def validate_token_symbol(cls, v: str) -> str:
        """Validate that token symbols are uppercase and alphanumeric."""
        if not v.replace("_", "").isalnum():
            raise ValueError(
                f"Token symbol must be alphanumeric (underscores allowed): {v}"
            )
        return v.upper()

    @model_validator(mode="after")
    def validate_different_tokens(self) -> "TradingPair":
        """Ensure base and quote tokens are different."""
        if self.base_token == self.quote_token:
            raise ValueError(
                f"Base and quote tokens must be different: {self.base_token}"
            )
        return self

    def __str__(self) -> str:
        """Return standard pair notation (e.g., 'FXRP/USDT0')."""
        return f"{self.base_token}/{self.quote_token}"

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return f"TradingPair(base_token='{self.base_token}', quote_token='{self.quote_token}')"

    def __hash__(self) -> int:
        """Make TradingPair hashable for use in sets and dict keys."""
        return hash((self.base_token, self.quote_token))


class TokenAddress(BaseModel):
    """
    Represents a token contract address on the Flare network.

    This model stores the essential information needed to interact with an
    ERC-20 token contract, including its address, decimal precision, and symbol.

    Attributes:
        address: Ethereum-style checksummed address of the token contract
        decimals: Number of decimal places (0-18, typically 18 for most tokens)
        symbol: Token symbol for display purposes
    """

    # Maximum decimals allowed for ERC-20 tokens (standard is 18)
    MAX_DECIMALS: ClassVar[int] = 18

    address: str = Field(
        ...,
        description="Checksummed Ethereum address",
        min_length=42,
        max_length=42,
    )
    decimals: int = Field(
        ...,
        description="Token decimal precision",
        ge=0,
        le=MAX_DECIMALS,
    )
    symbol: str = Field(
        ...,
        description="Token symbol",
        min_length=1,
        max_length=20,
    )

    @field_validator("address")
    @classmethod
    def validate_checksum_address(cls, v: str) -> str:
        """
        Validate and convert to checksummed Ethereum address.

        Args:
            v: Address string to validate

        Returns:
            Checksummed address

        Raises:
            ValueError: If address is invalid
        """
        if not v.startswith("0x"):
            raise ValueError(f"Address must start with '0x': {v}")

        if len(v) != 42:
            raise ValueError(f"Address must be 42 characters (including '0x'): {v}")

        try:
            # Web3.to_checksum_address validates and returns checksummed version
            checksummed = Web3.to_checksum_address(v)
            return checksummed
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address '{v}': {e}")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize token symbol."""
        if not v.replace("_", "").isalnum():
            raise ValueError(
                f"Token symbol must be alphanumeric (underscores allowed): {v}"
            )
        return v.upper()

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"{self.symbol} ({self.address})"

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"TokenAddress(address='{self.address}', "
            f"decimals={self.decimals}, symbol='{self.symbol}')"
        )

    def __hash__(self) -> int:
        """Make TokenAddress hashable for use in sets and dict keys."""
        return hash(self.address)


class Price(BaseModel):
    """
    Price data from a specific DEX at a point in time.

    Represents the current price of a trading pair on a particular DEX,
    including liquidity information and timestamp. All financial values
    use Decimal for precision.

    For error handling, price and liquidity can be None if the fetch failed,
    in which case the error field should contain the error message.

    Attributes:
        pair: The trading pair being priced
        dex_name: Name of the DEX providing this price
        price: Current price (quote token per base token), None if error
        liquidity: Total liquidity in the pool (in quote token value), None if error
        timestamp: When this price was fetched
        error: Error message if price fetch failed, None otherwise
    """

    pair: TradingPair = Field(
        ...,
        description="Trading pair for this price"
    )
    dex_name: str = Field(
        ...,
        description="Name of the DEX",
        min_length=1,
        max_length=50,
    )
    price: Optional[Decimal] = Field(
        default=None,
        description="Price in quote token per base token",
    )
    liquidity: Optional[Decimal] = Field(
        default=None,
        description="Total pool liquidity in quote token value",
    )
    timestamp: datetime = Field(
        ...,
        description="Time when price was fetched"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if price fetch failed"
    )

    @field_validator("price", "liquidity")
    @classmethod
    def validate_decimal_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """
        Validate that Decimal values are reasonable.

        Ensures values are not NaN or Infinity, which can occur from
        bad calculations or malformed data. None values are allowed for error cases.
        """
        if v is None:
            return v
        if v.is_nan():
            raise ValueError("Value cannot be NaN")
        if v.is_infinite():
            raise ValueError("Value cannot be infinite")
        return v

    @field_validator("price")
    @classmethod
    def validate_price_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure price is strictly positive when provided."""
        if v is None:
            return v
        if v <= 0:
            raise ValueError(f"Price must be positive: {v}")
        return v

    @field_validator("liquidity")
    @classmethod
    def validate_liquidity_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure liquidity is non-negative when provided."""
        if v is None:
            return v
        if v < 0:
            raise ValueError(f"Liquidity cannot be negative: {v}")
        return v

    @property
    def is_valid(self) -> bool:
        """
        Check if price data is valid.

        Returns True if price data was successfully fetched (no error and has price).
        """
        return self.error is None and self.price is not None

    def __str__(self) -> str:
        """Return human-readable price information."""
        if not self.is_valid:
            return f"{self.pair} on {self.dex_name}: ERROR - {self.error}"
        return (
            f"{self.pair} on {self.dex_name}: "
            f"{self.price:.8f} (liquidity: {self.liquidity:.2f})"
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"Price(pair={self.pair!r}, dex_name='{self.dex_name}', "
            f"price=Decimal('{self.price}'), liquidity=Decimal('{self.liquidity}'), "
            f"timestamp={self.timestamp.isoformat()!r})"
        )

    class Config:
        """Pydantic configuration."""
        # Allow arbitrary types (for Decimal)
        arbitrary_types_allowed = True
        # Use JSON-serializable format for datetime
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }


class Spread(BaseModel):
    """
    Calculated price spread between two DEXes for a trading pair.

    Represents an arbitrage opportunity (or lack thereof) by comparing
    the highest and lowest prices for a pair across different DEXes.
    The spread percentage indicates the potential profit margin.

    Attributes:
        pair: The trading pair being compared
        low_dex: DEX offering the lowest price (best place to buy)
        high_dex: DEX offering the highest price (best place to sell)
        low_price: Lowest price across DEXes
        high_price: Highest price across DEXes
        spread_percent: Percentage difference ((high - low) / low * 100)
        timestamp: When this spread was calculated
    """

    pair: TradingPair = Field(
        ...,
        description="Trading pair for this spread"
    )
    low_dex: str = Field(
        ...,
        description="DEX with lowest price (buy here)",
        min_length=1,
        max_length=50,
    )
    high_dex: str = Field(
        ...,
        description="DEX with highest price (sell here)",
        min_length=1,
        max_length=50,
    )
    low_price: Decimal = Field(
        ...,
        description="Lowest price across DEXes",
        gt=0,
    )
    high_price: Decimal = Field(
        ...,
        description="Highest price across DEXes",
        gt=0,
    )
    spread_percent: Decimal = Field(
        ...,
        description="Percentage spread ((high - low) / low * 100)"
    )
    timestamp: datetime = Field(
        ...,
        description="Time when spread was calculated"
    )

    @field_validator("low_price", "high_price")
    @classmethod
    def validate_price_positive(cls, v: Decimal) -> Decimal:
        """Ensure prices are strictly positive."""
        if v <= 0:
            raise ValueError(f"Price must be positive: {v}")
        if v.is_nan() or v.is_infinite():
            raise ValueError("Price must be a valid number")
        return v

    @model_validator(mode="after")
    def validate_spread_consistency(self) -> "Spread":
        """
        Validate that high price >= low price and spread calculation is correct.

        Ensures data consistency and that the spread percentage matches
        the actual price difference.
        """
        if self.high_price < self.low_price:
            raise ValueError(
                f"High price ({self.high_price}) must be >= low price ({self.low_price})"
            )

        # Calculate expected spread percentage
        expected_spread = (
            (self.high_price - self.low_price) / self.low_price * Decimal("100")
        )

        # Allow for small floating point differences (0.01%)
        tolerance = Decimal("0.01")
        diff = abs(self.spread_percent - expected_spread)

        if diff > tolerance:
            raise ValueError(
                f"Spread percentage ({self.spread_percent}%) doesn't match "
                f"calculated spread ({expected_spread:.2f}%). "
                f"Difference: {diff:.4f}%"
            )

        return self

    @model_validator(mode="after")
    def validate_different_dexes(self) -> "Spread":
        """Ensure low and high DEXes are different when spread exists."""
        if self.spread_percent != 0 and self.low_dex == self.high_dex:
            raise ValueError(
                f"Low and high DEX must be different when spread exists: {self.low_dex}"
            )
        return self

    def is_profitable(self, fee_percent: Decimal = Decimal("0.5")) -> bool:
        """
        Determine if spread represents a profitable arbitrage opportunity.

        Args:
            fee_percent: Estimated total fees (gas + slippage + DEX fees).
                        Default 0.5% is conservative estimate.

        Returns:
            True if spread exceeds fee threshold
        """
        return self.spread_percent > fee_percent

    def estimated_profit(
        self,
        fee_percent: Decimal = Decimal("0.5")
    ) -> Decimal:
        """
        Calculate estimated profit after fees.

        Args:
            fee_percent: Estimated total fees (gas + slippage + DEX fees)

        Returns:
            Estimated profit percentage (can be negative)
        """
        return self.spread_percent - fee_percent

    def __str__(self) -> str:
        """Return human-readable spread information."""
        return (
            f"{self.pair}: {self.spread_percent:.2f}% "
            f"({self.low_dex} -> {self.high_dex})"
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"Spread(pair={self.pair!r}, "
            f"low_dex='{self.low_dex}', high_dex='{self.high_dex}', "
            f"low_price=Decimal('{self.low_price}'), "
            f"high_price=Decimal('{self.high_price}'), "
            f"spread_percent=Decimal('{self.spread_percent}'), "
            f"timestamp={self.timestamp.isoformat()!r})"
        )

    class Config:
        """Pydantic configuration."""
        # Allow arbitrary types (for Decimal)
        arbitrary_types_allowed = True
        # Use JSON-serializable format for datetime
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }


class DEXStatus(BaseModel):
    """
    Status information for a DEX.

    Tracks the health and availability of a DEX connection, including
    error tracking and last successful update timing.

    Attributes:
        dex_name: Name of the DEX
        is_online: Whether the DEX is currently responding
        last_update: Timestamp of last successful price fetch
        error_count: Number of consecutive errors encountered
        last_error: Most recent error message (if any)
    """

    dex_name: str = Field(
        ...,
        description="DEX name",
        min_length=1,
        max_length=50,
    )
    is_online: bool = Field(
        default=True,
        description="DEX online status"
    )
    last_update: Optional[datetime] = Field(
        default=None,
        description="Last successful update timestamp"
    )
    error_count: int = Field(
        default=0,
        description="Consecutive error count",
        ge=0,
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message"
    )

    @field_validator("error_count")
    @classmethod
    def validate_error_count(cls, v: int) -> int:
        """Ensure error count is non-negative."""
        if v < 0:
            raise ValueError(f"Error count cannot be negative: {v}")
        return v

    def __str__(self) -> str:
        """Return human-readable status information."""
        status = "online" if self.is_online else "offline"
        if self.last_error:
            return f"{self.dex_name}: {status} (errors: {self.error_count}, last: {self.last_error})"
        return f"{self.dex_name}: {status}"

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"DEXStatus(dex_name='{self.dex_name}', "
            f"is_online={self.is_online}, "
            f"error_count={self.error_count})"
        )

    class Config:
        """Pydantic configuration."""
        # Use JSON-serializable format for datetime
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }
