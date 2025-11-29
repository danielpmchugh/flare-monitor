"""Uniswap V3 adapter for DEX price fetching.

This module implements the DEXAdapter interface for Uniswap V3-style DEXes
on the Flare Network. It handles fetching prices from pool contracts,
calculating token prices from sqrtPriceX96, and managing multiple fee tiers.

Uniswap V3 uses concentrated liquidity with tick ranges and multiple fee tiers:
- Liquidity providers can provide liquidity in specific price ranges
- Multiple fee tiers (0.05%, 0.30%, 1.00%) for different pairs
- Price is calculated from sqrtPriceX96 instead of reserves
- Need to query pool contracts directly (not just factory.getPair)

Key differences from V2:
1. Factory.getPool(token0, token1, fee) instead of getPair
2. Pool contract has slot0() instead of getReserves()
3. Price calculation from sqrtPriceX96 (not reserves)
4. Need to handle fee tiers

Supports DEXes:
- SparkDEX V3.1: 0x8A2578d23d4C532cC9A98FaD91C0523f5efDE652
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from web3 import AsyncWeb3
from web3.contract.async_contract import AsyncContract
from web3.exceptions import ContractLogicError, BadFunctionCallOutput

from flare_monitor.adapters.base import DEXAdapter
from flare_monitor.config import TokenConfig
from flare_monitor.models import Price, TradingPair


class UniswapV3Adapter(DEXAdapter):
    """Adapter for Uniswap V3-compatible DEXes on Flare Network.

    This adapter implements price fetching from Uniswap V3-style AMM DEXes.
    It handles:
    - Getting pool addresses from factory contracts with fee tiers
    - Fetching slot0 data from pool contracts
    - Calculating prices from sqrtPriceX96
    - Managing token ordering (token0 vs token1)
    - Finding pools with highest liquidity across fee tiers
    - Caching pool addresses for efficiency

    The adapter uses the Uniswap V3 interface:
    1. Factory.getPool(tokenA, tokenB, fee) -> pool address
    2. Pool.slot0() -> (sqrtPriceX96, tick, ...)
    3. Pool.liquidity() -> total liquidity
    4. Pool.token0() -> address of token0
    5. Pool.token1() -> address of token1

    Critical: Token decimals must be handled correctly. USDT0 uses 6 decimals
    while most other tokens use 18. The price calculation from sqrtPriceX96
    adjusts for this.

    Price calculation formula:
    price = (sqrtPriceX96 / 2^96) ^ 2 * (10^decimals_base / 10^decimals_quote)

    Attributes:
        factory_address: Address of the Uniswap V3 factory contract
        factory_contract: Web3 contract instance for factory
        pool_contract_abi: ABI for Uniswap V3 pool contracts
        tokens: Dictionary mapping token symbols to TokenConfig objects
        pool_cache: Cache of (base_address, quote_address, fee) -> pool_address mappings
        enable_cache: Whether to use pool address caching
        fee_tiers: List of fee tiers to try (in basis points)

    Example:
        ```python
        from web3 import AsyncWeb3
        from flare_monitor.config import load_config

        config = load_config("config/config.yaml")
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(config.flare.rpc_endpoints[0]))

        adapter = UniswapV3Adapter(
            dex_name="SparkDEX V3",
            w3=w3,
            factory_address="0x8A2578d23d4C532cC9A98FaD91C0523f5efDE652",
            tokens=config.tokens
        )

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        price = await adapter.get_price(pair)
        print(f"FXRP price: ${price.price}")
        ```
    """

    # Zero address constant (indicates pool doesn't exist)
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

    # Common Uniswap V3 fee tiers (in basis points)
    # 500 = 0.05%, 3000 = 0.30%, 10000 = 1.00%
    DEFAULT_FEE_TIERS = [500, 3000, 10000]

    # Q96 constant for sqrtPriceX96 calculations
    Q96 = Decimal(2) ** 96

    def __init__(
        self,
        dex_name: str,
        w3: AsyncWeb3,
        factory_address: str,
        tokens: Dict[str, TokenConfig],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_cache: bool = True,
        fee_tiers: Optional[List[int]] = None,
    ) -> None:
        """Initialize the Uniswap V3 adapter.

        Args:
            dex_name: Human-readable name of the DEX (e.g., "SparkDEX V3")
            w3: AsyncWeb3 instance connected to Flare Network
            factory_address: Address of the Uniswap V3 factory contract
            tokens: Dictionary mapping token symbols to TokenConfig objects
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Base delay in seconds between retries (default: 1.0)
            enable_cache: Whether to cache pool addresses (default: True)
            fee_tiers: List of fee tiers to try (default: [500, 3000, 10000])

        Raises:
            FileNotFoundError: If ABI files cannot be found
            ValueError: If factory address is invalid or ABIs cannot be loaded
        """
        super().__init__(dex_name, w3, max_retries, retry_delay)

        self.factory_address = factory_address
        self.tokens = tokens
        self.enable_cache = enable_cache
        self.fee_tiers = fee_tiers or self.DEFAULT_FEE_TIERS

        # Cache for pool addresses: (base_address, quote_address, fee) -> pool_address
        self.pool_cache: Dict[Tuple[str, str, int], str] = {}

        # Load ABIs from files
        self.factory_contract = self._load_factory_contract()
        self.pool_contract_abi = self._load_pool_abi()

        self.logger.info(
            f"Initialized {dex_name} adapter with factory at {factory_address}, "
            f"fee tiers: {self.fee_tiers}"
        )

    def _load_factory_contract(self) -> AsyncContract:
        """Load the Uniswap V3 factory contract.

        Returns:
            AsyncContract instance for the factory

        Raises:
            FileNotFoundError: If factory ABI file not found
            ValueError: If ABI is invalid
        """
        abi_path = Path(__file__).parent.parent.parent / "abis" / "IUniswapV3Factory.json"

        try:
            with open(abi_path, "r") as f:
                factory_abi = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Factory ABI not found at {abi_path}. "
                f"Ensure abis/IUniswapV3Factory.json exists."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in factory ABI: {e}")

        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.factory_address),
            abi=factory_abi
        )

    def _load_pool_abi(self) -> list:
        """Load the Uniswap V3 pool contract ABI.

        Returns:
            List containing the pool contract ABI

        Raises:
            FileNotFoundError: If pool ABI file not found
            ValueError: If ABI is invalid
        """
        abi_path = Path(__file__).parent.parent.parent / "abis" / "IUniswapV3Pool.json"

        try:
            with open(abi_path, "r") as f:
                pool_abi = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Pool ABI not found at {abi_path}. "
                f"Ensure abis/IUniswapV3Pool.json exists."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in pool ABI: {e}")

        return pool_abi

    async def _get_pool_address(
        self,
        base_token: TokenConfig,
        quote_token: TokenConfig,
        fee: int
    ) -> Optional[str]:
        """Get the pool address for two tokens and a fee tier from the factory.

        Queries the factory contract to find the pool address for the given tokens
        and fee tier. Uses caching if enabled to reduce RPC calls.

        Args:
            base_token: Configuration for the base token
            quote_token: Configuration for the quote token
            fee: Fee tier in basis points (e.g., 500, 3000, 10000)

        Returns:
            Checksummed pool address, or None if pool doesn't exist

        Note:
            Uniswap V3 sorts tokens by address, so token order doesn't matter
            for factory.getPool() calls. The returned pool contract always
            stores tokens in sorted order.
        """
        # Create cache key (sorted to handle token order)
        sorted_addresses = sorted([base_token.address.lower(), quote_token.address.lower()])
        cache_key = (sorted_addresses[0], sorted_addresses[1], fee)

        # Check cache first
        if self.enable_cache and cache_key in self.pool_cache:
            return self.pool_cache[cache_key]

        # Query factory contract
        async def fetch_pool_address() -> Optional[str]:
            try:
                pool_address = await self.factory_contract.functions.getPool(
                    self.w3.to_checksum_address(base_token.address),
                    self.w3.to_checksum_address(quote_token.address),
                    fee
                ).call()

                # Check for zero address (pool doesn't exist)
                if pool_address.lower() == self.ZERO_ADDRESS.lower():
                    self.logger.debug(
                        f"{self.dex_name}: Pool {base_token.symbol}/{quote_token.symbol} "
                        f"with fee {fee} does not exist in factory"
                    )
                    return None

                return self.w3.to_checksum_address(pool_address)

            except ContractLogicError as e:
                self.logger.error(
                    f"{self.dex_name}: Contract logic error getting pool address for "
                    f"{base_token.symbol}/{quote_token.symbol} (fee={fee}) from factory {self.factory_address}: "
                    f"{type(e).__name__}: {e}"
                )
                return None
            except BadFunctionCallOutput as e:
                self.logger.error(
                    f"{self.dex_name}: Bad function call output for getPool "
                    f"({base_token.symbol}/{quote_token.symbol}, fee={fee}). "
                    f"Factory address may be invalid: {self.factory_address}"
                )
                return None
            except ValueError as e:
                self.logger.error(
                    f"{self.dex_name}: Invalid address format for tokens "
                    f"{base_token.symbol} ({base_token.address}) / "
                    f"{quote_token.symbol} ({quote_token.address}): {e}"
                )
                return None
            except Exception as e:
                self.logger.error(
                    f"{self.dex_name}: Unexpected error getting pool address for "
                    f"{base_token.symbol}/{quote_token.symbol} (fee={fee}): {type(e).__name__}: {e}",
                    exc_info=True
                )
                return None

        pool_address = await self._retry_on_failure(
            f"get pool address for {base_token.symbol}/{quote_token.symbol} (fee={fee})",
            fetch_pool_address
        )

        # Cache the result if valid
        if pool_address and self.enable_cache:
            self.pool_cache[cache_key] = pool_address

        return pool_address

    async def _get_slot0(
        self,
        pool_address: str
    ) -> Optional[Tuple[int, int]]:
        """Get slot0 data from a Uniswap V3 pool contract.

        Calls the slot0() function on the pool contract to fetch
        the current sqrtPriceX96 and tick.

        Args:
            pool_address: Checksummed address of the pool contract

        Returns:
            Tuple of (sqrtPriceX96, tick) or None if error

        Note:
            slot0 returns multiple values, but we only need sqrtPriceX96 and tick
            for price calculation.
        """
        async def fetch_slot0() -> Optional[Tuple[int, int]]:
            try:
                pool_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(pool_address),
                    abi=self.pool_contract_abi
                )

                slot0_data = await pool_contract.functions.slot0().call()
                sqrt_price_x96 = int(slot0_data[0])
                tick = int(slot0_data[1])

                return (sqrt_price_x96, tick)

            except ContractLogicError as e:
                self.logger.error(
                    f"{self.dex_name}: Contract logic error getting slot0 from pool {pool_address}: "
                    f"{type(e).__name__}: {e}"
                )
                return None
            except BadFunctionCallOutput as e:
                self.logger.error(
                    f"{self.dex_name}: Bad function call output for slot0 on pool {pool_address}. "
                    f"Pool address may be invalid or contract may not be a Uniswap V3 pool."
                )
                return None
            except (ValueError, TypeError) as e:
                self.logger.error(
                    f"{self.dex_name}: Invalid data type in slot0 from pool {pool_address}: "
                    f"{type(e).__name__}: {e}"
                )
                return None
            except Exception as e:
                self.logger.error(
                    f"{self.dex_name}: Unexpected error getting slot0 from pool {pool_address}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True
                )
                return None

        return await self._retry_on_failure(
            f"get slot0 for pool {pool_address}",
            fetch_slot0
        )

    async def _get_liquidity(
        self,
        pool_address: str
    ) -> Optional[int]:
        """Get liquidity from a Uniswap V3 pool contract.

        Calls the liquidity() function on the pool contract to fetch
        the current total liquidity.

        Args:
            pool_address: Checksummed address of the pool contract

        Returns:
            Total liquidity as int, or None if error
        """
        async def fetch_liquidity() -> Optional[int]:
            try:
                pool_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(pool_address),
                    abi=self.pool_contract_abi
                )

                liquidity = await pool_contract.functions.liquidity().call()
                return int(liquidity)

            except ContractLogicError as e:
                self.logger.error(
                    f"{self.dex_name}: Contract error getting liquidity: {e}"
                )
                return None
            except Exception as e:
                self.logger.error(
                    f"{self.dex_name}: Unexpected error getting liquidity: {e}"
                )
                return None

        return await self._retry_on_failure(
            f"get liquidity for pool {pool_address}",
            fetch_liquidity
        )

    async def _get_token_order(
        self,
        pool_address: str
    ) -> Optional[Tuple[str, str]]:
        """Get the token addresses in the order stored by the pool contract.

        Queries the pool contract to determine which token is token0 and
        which is token1. This is needed to correctly interpret sqrtPriceX96.

        Args:
            pool_address: Checksummed address of the pool contract

        Returns:
            Tuple of (token0_address, token1_address) or None if error

        Note:
            Uniswap V3 always stores tokens in ascending address order.
            token0 < token1 (lexicographically)
        """
        async def fetch_token_order() -> Optional[Tuple[str, str]]:
            try:
                pool_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(pool_address),
                    abi=self.pool_contract_abi
                )

                token0 = await pool_contract.functions.token0().call()
                token1 = await pool_contract.functions.token1().call()

                return (
                    self.w3.to_checksum_address(token0),
                    self.w3.to_checksum_address(token1)
                )

            except ContractLogicError as e:
                self.logger.error(
                    f"{self.dex_name}: Contract error getting token order: {e}"
                )
                return None
            except Exception as e:
                self.logger.error(
                    f"{self.dex_name}: Unexpected error getting token order: {e}"
                )
                return None

        return await self._retry_on_failure(
            f"get token order for pool {pool_address}",
            fetch_token_order
        )

    async def _find_best_pool(
        self,
        base_token: TokenConfig,
        quote_token: TokenConfig
    ) -> Optional[Tuple[str, int]]:
        """Find the pool with the highest liquidity across fee tiers.

        Tries all configured fee tiers and returns the pool address and fee
        for the pool with the highest liquidity.

        Args:
            base_token: Configuration for the base token
            quote_token: Configuration for the quote token

        Returns:
            Tuple of (pool_address, fee) for best pool, or None if no pools exist

        Note:
            This method queries multiple pools and may take longer than
            a simple pool lookup. Results are cached for efficiency.
        """
        best_pool = None
        best_liquidity = 0
        best_fee = None

        for fee in self.fee_tiers:
            pool_address = await self._get_pool_address(base_token, quote_token, fee)
            if not pool_address:
                continue

            liquidity = await self._get_liquidity(pool_address)
            if liquidity and liquidity > best_liquidity:
                best_liquidity = liquidity
                best_pool = pool_address
                best_fee = fee

        if best_pool:
            self.logger.debug(
                f"{self.dex_name}: Best pool for {base_token.symbol}/{quote_token.symbol}: "
                f"{best_pool} with fee {best_fee} and liquidity {best_liquidity}"
            )
            return (best_pool, best_fee)

        return None

    def _calculate_price_from_sqrt_price_x96(
        self,
        sqrt_price_x96: int,
        decimals_base: int,
        decimals_quote: int,
        base_is_token0: bool
    ) -> Decimal:
        """Calculate price from sqrtPriceX96 with proper decimal adjustment.

        Converts sqrtPriceX96 to human-readable price by:
        1. Calculating price = (sqrtPriceX96 / 2^96) ^ 2
        2. Adjusting for token decimals
        3. Handling token ordering (token0 vs token1)

        The sqrtPriceX96 represents sqrt(price) * 2^96 where price is token1/token0.
        To get base/quote price, we need to account for token ordering.

        Args:
            sqrt_price_x96: sqrtPriceX96 value from pool.slot0()
            decimals_base: Number of decimals for base token
            decimals_quote: Number of decimals for quote token
            base_is_token0: True if base token is token0, False if base is token1

        Returns:
            Price as Decimal (quote token per base token)

        Raises:
            ValueError: If sqrt_price_x96 is zero or negative, or decimals are invalid
            InvalidOperation: If decimal calculation fails

        Example:
            For FXRP/USDT0 where FXRP is token0 and USDT0 is token1:
            - sqrt_price_x96 represents sqrt(USDT0/FXRP) * 2^96
            - We want price in USDT0 per FXRP
            - base_is_token0 = True
            - price = (sqrt_price_x96 / 2^96)^2 * (10^18 / 10^6)
        """
        # Validate inputs
        if sqrt_price_x96 <= 0:
            raise ValueError(f"sqrtPriceX96 must be positive: {sqrt_price_x96}")
        if decimals_base < 0 or decimals_base > 77:
            raise ValueError(f"Invalid base decimals (must be 0-77): {decimals_base}")
        if decimals_quote < 0 or decimals_quote > 77:
            raise ValueError(f"Invalid quote decimals (must be 0-77): {decimals_quote}")

        # Check for suspiciously large sqrtPriceX96 that might indicate data corruption
        MAX_SQRT_PRICE = 2 ** 160  # Uniswap V3 uses uint160 for sqrtPriceX96
        if sqrt_price_x96 > MAX_SQRT_PRICE:
            raise ValueError(
                f"sqrtPriceX96 exceeds maximum value (possible data corruption): {sqrt_price_x96}"
            )

        try:
            # Convert to Decimal for precision
            sqrt_price_x96_decimal = Decimal(sqrt_price_x96)

            # Calculate price = (sqrtPriceX96 / 2^96) ^ 2
            # This gives us token1/token0 price in raw units (before decimal adjustment)
            price_raw = (sqrt_price_x96_decimal / self.Q96) ** 2

            # Now we need to adjust for token decimals and ordering
            # In Uniswap V3: price_raw = (token1 / token0) in terms of raw values
            # To get human-readable price: price_human = (token1_human / token0_human)
            #   = (token1_raw / 10^decimals_token1) / (token0_raw / 10^decimals_token0)
            #   = (token1_raw / token0_raw) * (10^decimals_token0 / 10^decimals_token1)
            #   = price_raw * (10^decimals_token0 / 10^decimals_token1)

            if base_is_token0:
                # base is token0, quote is token1
                # price_raw = token1_raw / token0_raw = quote_raw / base_raw
                # price_human = price_raw * (10^decimals_token0 / 10^decimals_token1)
                #             = price_raw * (10^decimals_base / 10^decimals_quote)
                decimal_adjustment = Decimal(10) ** (decimals_base - decimals_quote)
                price = price_raw * decimal_adjustment
            else:
                # base is token1, quote is token0
                # price_raw = token1_raw / token0_raw = base_raw / quote_raw
                # We want quote/base, so invert: 1 / price_raw = quote_raw / base_raw
                # price_human = (1 / price_raw) * (10^decimals_token1 / 10^decimals_token0)
                #             = (1 / price_raw) * (10^decimals_base / 10^decimals_quote)
                if price_raw == 0:
                    raise ValueError("Cannot calculate price: price_raw is zero")
                decimal_adjustment = Decimal(10) ** (decimals_base - decimals_quote)
                price = decimal_adjustment / price_raw

            # Sanity check the result
            if price <= 0:
                raise ValueError(f"Calculated price is non-positive: {price}")
            if price > Decimal(10 ** 15):  # Unreasonably high price
                self.logger.warning(
                    f"{self.dex_name}: Calculated price is very high: {price}. "
                    f"This may indicate incorrect token decimals or data corruption."
                )

            return price

        except InvalidOperation as e:
            raise InvalidOperation(
                f"Decimal calculation failed for sqrtPriceX96={sqrt_price_x96} "
                f"with decimals ({decimals_base}, {decimals_quote}): {e}"
            ) from e

    def _calculate_liquidity_value(
        self,
        liquidity: int,
        sqrt_price_x96: int,
        decimals_base: int,
        decimals_quote: int,
        base_is_token0: bool
    ) -> Decimal:
        """Calculate total liquidity value in quote token units.

        Converts raw liquidity amount to approximate quote token value.
        This is a simplified calculation that estimates the total value.

        For concentrated liquidity, the exact calculation depends on the
        tick range, but we use a simplified approximation based on the
        current price and total liquidity.

        Args:
            liquidity: Raw liquidity value from pool.liquidity()
            sqrt_price_x96: Current sqrtPriceX96 from pool.slot0()
            decimals_base: Number of decimals for base token
            decimals_quote: Number of decimals for quote token
            base_is_token0: True if base token is token0

        Returns:
            Liquidity as Decimal (in quote token units)

        Raises:
            ValueError: If liquidity or sqrt_price_x96 is negative
        """
        if liquidity < 0:
            raise ValueError(f"Liquidity cannot be negative: {liquidity}")
        if sqrt_price_x96 <= 0:
            raise ValueError(f"sqrtPriceX96 must be positive: {sqrt_price_x96}")

        # Convert to Decimal
        liquidity_decimal = Decimal(liquidity)
        sqrt_price_x96_decimal = Decimal(sqrt_price_x96)

        # For a simplified approximation, we estimate the quote token value as:
        # liquidity_value ≈ liquidity * sqrt_price / 2^96
        # This is a rough estimate that works reasonably well for active pools

        if base_is_token0:
            # liquidity is in token1 (quote) units at current tick
            # value ≈ liquidity * 2 / 2^96 (factor of 2 for both sides of pool)
            value = liquidity_decimal * sqrt_price_x96_decimal / self.Q96
        else:
            # liquidity is in token0 (quote) units at current tick
            value = liquidity_decimal / (sqrt_price_x96_decimal / self.Q96)

        # Adjust for decimals
        adjustment_factor = Decimal(10) ** (-decimals_quote)
        value = value * adjustment_factor

        return value

    async def get_price(self, pair: TradingPair) -> Price:
        """Fetch the current price for a trading pair.

        This is the main entry point for fetching price data. It:
        1. Looks up token configurations
        2. Finds the best pool across fee tiers
        3. Fetches slot0 and liquidity from pool contract
        4. Calculates the price from sqrtPriceX96
        5. Returns a Price object with all data

        Args:
            pair: The trading pair to fetch the price for

        Returns:
            Price object containing price, liquidity, timestamp, and any errors

        Note:
            If any step fails, returns a Price object with the error field set.
            No exceptions are raised - all errors are captured and returned.
        """
        try:
            # Get token configurations
            base_token = self.tokens.get(pair.base_token)
            quote_token = self.tokens.get(pair.quote_token)

            if not base_token:
                return self._handle_error(
                    pair,
                    ValueError(f"Base token {pair.base_token} not found in configuration")
                )
            if not quote_token:
                return self._handle_error(
                    pair,
                    ValueError(f"Quote token {pair.quote_token} not found in configuration")
                )

            # Find the best pool across fee tiers
            pool_info = await self._find_best_pool(base_token, quote_token)
            if not pool_info:
                return self._handle_error(
                    pair,
                    ValueError(
                        f"No pools found for {pair.base_token}/{pair.quote_token} "
                        f"on {self.dex_name}"
                    )
                )

            pool_address, fee = pool_info

            # Get token order from pool contract
            token_order = await self._get_token_order(pool_address)
            if not token_order:
                return self._handle_error(
                    pair,
                    RuntimeError("Failed to get token order from pool contract")
                )

            token0_address, token1_address = token_order

            # Get slot0 data from pool contract
            slot0_data = await self._get_slot0(pool_address)
            if not slot0_data:
                return self._handle_error(
                    pair,
                    RuntimeError("Failed to get slot0 from pool contract")
                )

            sqrt_price_x96, tick = slot0_data

            # Get liquidity from pool contract
            liquidity = await self._get_liquidity(pool_address)
            if liquidity is None:
                return self._handle_error(
                    pair,
                    RuntimeError("Failed to get liquidity from pool contract")
                )

            # Determine token ordering
            base_address_lower = base_token.address.lower()
            token0_address_lower = token0_address.lower()
            base_is_token0 = (base_address_lower == token0_address_lower)

            self.logger.debug(
                f"{self.dex_name}: Token ordering - "
                f"token0={token0_address}, token1={token1_address}, "
                f"base={base_token.address} ({base_token.symbol}), "
                f"quote={quote_token.address} ({quote_token.symbol}), "
                f"base_is_token0={base_is_token0}"
            )

            # Check for zero liquidity
            if liquidity == 0:
                return self._handle_error(
                    pair,
                    ValueError(f"Zero liquidity in pool")
                )

            # Calculate price from sqrtPriceX96
            price = self._calculate_price_from_sqrt_price_x96(
                sqrt_price_x96,
                base_token.decimals,
                quote_token.decimals,
                base_is_token0
            )

            # Calculate liquidity value
            liquidity_value = self._calculate_liquidity_value(
                liquidity,
                sqrt_price_x96,
                base_token.decimals,
                quote_token.decimals,
                base_is_token0
            )

            # Get current timestamp
            timestamp = datetime.now(timezone.utc)

            self.logger.debug(
                f"{self.dex_name}: {pair} price={price:.8f}, "
                f"liquidity={liquidity_value:.2f}, "
                f"sqrtPriceX96={sqrt_price_x96}, tick={tick}, "
                f"raw_liquidity={liquidity}, fee={fee}"
            )

            return Price(
                pair=pair,
                dex_name=self.dex_name,
                price=price,
                liquidity=liquidity_value,
                timestamp=timestamp,
                error=None
            )

        except Exception as e:
            return self._handle_error(pair, e)

    async def get_liquidity(self, pair: TradingPair) -> Decimal:
        """Get the total liquidity in the trading pair pool.

        This method is similar to get_price() but only returns the liquidity value.
        It's provided to satisfy the DEXAdapter interface and for cases where
        only liquidity information is needed.

        Args:
            pair: The trading pair to fetch liquidity for

        Returns:
            Decimal: Total liquidity value in quote token units

        Raises:
            ValueError: If pair doesn't exist or tokens not configured
            RuntimeError: If fetching pool data fails

        Note:
            This method raises exceptions on failure, unlike get_price()
            which returns errors in the Price object. This is intentional
            as per the base adapter interface design.
        """
        # Get token configurations
        base_token = self.tokens.get(pair.base_token)
        quote_token = self.tokens.get(pair.quote_token)

        if not base_token:
            raise ValueError(f"Base token {pair.base_token} not found in configuration")
        if not quote_token:
            raise ValueError(f"Quote token {pair.quote_token} not found in configuration")

        # Find the best pool across fee tiers
        pool_info = await self._find_best_pool(base_token, quote_token)
        if not pool_info:
            raise ValueError(
                f"No pools found for {pair.base_token}/{pair.quote_token} on {self.dex_name}"
            )

        pool_address, fee = pool_info

        # Get token order from pool contract
        token_order = await self._get_token_order(pool_address)
        if not token_order:
            raise RuntimeError("Failed to get token order from pool contract")

        token0_address, token1_address = token_order

        # Get slot0 data from pool contract
        slot0_data = await self._get_slot0(pool_address)
        if not slot0_data:
            raise RuntimeError("Failed to get slot0 from pool contract")

        sqrt_price_x96, tick = slot0_data

        # Get liquidity from pool contract
        liquidity = await self._get_liquidity(pool_address)
        if liquidity is None:
            raise RuntimeError("Failed to get liquidity from pool contract")

        # Determine token ordering
        base_address_lower = base_token.address.lower()
        token0_address_lower = token0_address.lower()
        base_is_token0 = (base_address_lower == token0_address_lower)

        # Calculate and return liquidity value
        liquidity_value = self._calculate_liquidity_value(
            liquidity,
            sqrt_price_x96,
            base_token.decimals,
            quote_token.decimals,
            base_is_token0
        )

        return liquidity_value

    def get_dex_name(self) -> str:
        """Return the human-readable name of this DEX.

        Returns:
            str: DEX name (e.g., "SparkDEX V3", "Uniswap V3")
        """
        return self.dex_name

    def __repr__(self) -> str:
        """String representation of the adapter.

        Returns:
            str: Representation showing adapter details
        """
        return (
            f"UniswapV3Adapter(dex_name='{self.dex_name}', "
            f"factory_address='{self.factory_address}', "
            f"num_tokens={len(self.tokens)}, "
            f"fee_tiers={self.fee_tiers})"
        )
