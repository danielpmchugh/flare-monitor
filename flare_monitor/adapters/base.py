"""Abstract base class for DEX adapters.

This module defines the DEXAdapter interface that all concrete DEX adapters
must implement. It provides the contract for fetching price and liquidity data
from various decentralized exchanges on the Flare Network.

The adapter pattern allows for easy addition of new DEXes while maintaining
a consistent interface for the monitoring system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from web3 import AsyncWeb3

from flare_monitor.models import Price, TradingPair


class DEXAdapter(ABC):
    """Abstract base class for DEX price and liquidity adapters.

    This class defines the interface that all DEX adapters must implement.
    It provides common initialization, error handling, and retry logic that
    can be shared across different DEX implementations.

    Each concrete adapter (e.g., UniswapV2Adapter) handles the specific
    smart contract interactions for its DEX type.

    Attributes:
        dex_name: Human-readable name of the DEX (e.g., "SparkDEX", "Blazeswap")
        w3: AsyncWeb3 instance for blockchain interactions
        logger: Logger instance for this adapter
        max_retries: Maximum number of retry attempts for failed requests
        retry_delay: Base delay in seconds between retries (uses exponential backoff)

    Example:
        ```python
        from web3 import AsyncWeb3
        from flare_monitor.adapters.base import DEXAdapter
        from flare_monitor.models import TradingPair, Price

        class UniswapV2Adapter(DEXAdapter):
            def __init__(self, dex_name: str, w3: AsyncWeb3, factory_address: str):
                super().__init__(dex_name, w3)
                self.factory_address = factory_address
                # Load contract ABIs, etc.

            async def get_price(self, pair: TradingPair) -> Price:
                # Fetch reserves from Uniswap V2 pair contract
                try:
                    reserves = await self._get_reserves(pair)
                    price = self._calculate_price(reserves, pair)
                    return Price(
                        pair=pair,
                        dex_name=self.dex_name,
                        price=price,
                        liquidity=await self.get_liquidity(pair)
                    )
                except Exception as e:
                    self.logger.error(f"Failed to get price for {pair}: {e}")
                    return Price(pair=pair, dex_name=self.dex_name, error=str(e))

            async def get_liquidity(self, pair: TradingPair) -> Decimal:
                # Fetch total liquidity from pool
                reserves = await self._get_reserves(pair)
                return self._calculate_liquidity(reserves)

            def get_dex_name(self) -> str:
                return self.dex_name
        ```
    """

    def __init__(
        self,
        dex_name: str,
        w3: AsyncWeb3,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the DEX adapter.

        Args:
            dex_name: Human-readable name of the DEX
            w3: AsyncWeb3 instance connected to Flare Network
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Base delay in seconds between retries (default: 1.0)
        """
        self.dex_name = dex_name
        self.w3 = w3
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(f"flare_monitor.adapters.{dex_name}")

    @abstractmethod
    async def get_price(self, pair: TradingPair) -> Price:
        """Fetch the current price for a trading pair.

        This method queries the DEX smart contracts to get the current
        exchange rate for the specified trading pair. It should handle
        any DEX-specific logic for calculating the price from reserves
        or other contract data.

        Args:
            pair: The trading pair to fetch the price for

        Returns:
            Price: Price object containing the current price data.
                   If an error occurs, the Price object should have the
                   error field set and price/liquidity as None.

        Raises:
            No exceptions should propagate. All errors should be caught
            and returned in the Price object's error field.

        Example:
            ```python
            pair = TradingPair(base_token="FXRP", quote_token="USDT0")
            price = await adapter.get_price(pair)
            if price.is_valid:
                print(f"Current price: {price.price}")
            else:
                print(f"Error fetching price: {price.error}")
            ```
        """
        pass

    @abstractmethod
    async def get_liquidity(self, pair: TradingPair) -> Decimal:
        """Get the total liquidity in the trading pair pool.

        This method queries the DEX to determine the total value locked
        in the liquidity pool for the specified trading pair. The liquidity
        is typically expressed in terms of the quote token.

        Args:
            pair: The trading pair to fetch liquidity for

        Returns:
            Decimal: Total liquidity value in the pool (in quote token units)

        Raises:
            Exception: May raise exceptions for network errors, contract errors,
                      or invalid pair addresses. Callers should handle exceptions.

        Example:
            ```python
            pair = TradingPair(base_token="FXRP", quote_token="USDT0")
            liquidity = await adapter.get_liquidity(pair)
            print(f"Total liquidity: ${liquidity}")
            ```
        """
        pass

    @abstractmethod
    def get_dex_name(self) -> str:
        """Return the human-readable name of this DEX.

        Returns:
            str: DEX name (e.g., "SparkDEX", "Blazeswap", "Pangolin")

        Example:
            ```python
            name = adapter.get_dex_name()
            print(f"Using adapter for: {name}")
            ```
        """
        pass

    async def _retry_on_failure(
        self,
        operation: str,
        func,
        *args,
        **kwargs
    ) -> Optional[any]:
        """Execute a function with retry logic and exponential backoff.

        This is a helper method that implements robust retry logic with
        exponential backoff for handling transient failures (network issues,
        RPC timeouts, etc.).

        Args:
            operation: Description of the operation (for logging)
            func: Async function to execute
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Optional[any]: Result of the function, or None if all retries failed

        Example:
            ```python
            result = await self._retry_on_failure(
                "fetch reserves",
                self._fetch_reserves_from_contract,
                pair_address
            )
            ```
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    delay = self.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"{self.dex_name}: {operation} failed (attempt {attempt + 1}/"
                        f"{self.max_retries}), retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"{self.dex_name}: {operation} failed after {self.max_retries} "
                        f"attempts: {e}"
                    )

        return None

    def _handle_error(self, pair: TradingPair, error: Exception) -> Price:
        """Create a Price object with error information.

        This helper method standardizes error handling across all adapters
        by creating a Price object that indicates a failure.

        Args:
            pair: The trading pair that was being queried
            error: The exception that occurred

        Returns:
            Price: Price object with error field set

        Example:
            ```python
            try:
                price_value = await self._fetch_price(pair)
            except Exception as e:
                return self._handle_error(pair, e)
            ```
        """
        from datetime import datetime, timezone

        error_msg = f"{type(error).__name__}: {str(error)}"
        self.logger.error(f"{self.dex_name}: Error fetching price for {pair}: {error_msg}")
        return Price(
            pair=pair,
            dex_name=self.dex_name,
            price=None,
            liquidity=None,
            timestamp=datetime.now(timezone.utc),
            error=error_msg,
        )

    def __repr__(self) -> str:
        """String representation of the adapter.

        Returns:
            str: Representation showing adapter type and DEX name
        """
        return f"{self.__class__.__name__}(dex_name='{self.dex_name}')"
