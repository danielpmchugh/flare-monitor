"""Uniswap V2 adapter for DEX price fetching.

This module implements the DEXAdapter interface for Uniswap V2-style DEXes
on the Flare Network. It handles fetching prices from pair contracts,
calculating token prices with proper decimal handling, and managing token ordering.

Uniswap V2 uses the constant product automated market maker (CPAMM) formula:
x * y = k, where x and y are the reserves of the two tokens in the pool.
The price is derived from the ratio of reserves: price = reserve1 / reserve0.

Supports DEXes:
- SparkDEX: 0x16b619B04c961E8f4F06C10B42FDAbb328980A89
- BlazeSwap: 0x3ad13e1bDD283e4F8d8196b002b80D1BADF39884
- Pangolin: 0xbfe13753156b9c6b2818FB45ff3D2392ea43d79A
- Enosys: (addresses TBD)
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Optional, Tuple

from web3 import AsyncWeb3
from web3.contract.async_contract import AsyncContract
from web3.exceptions import ContractLogicError, BadFunctionCallOutput

from flare_monitor.adapters.base import DEXAdapter
from flare_monitor.config import TokenConfig
from flare_monitor.models import Price, TradingPair


class UniswapV2Adapter(DEXAdapter):
    """Adapter for Uniswap V2-compatible DEXes on Flare Network.

    This adapter implements price fetching from Uniswap V2-style AMM DEXes.
    It handles:
    - Getting pair addresses from factory contracts
    - Fetching reserves from pair contracts
    - Calculating prices with proper decimal adjustment
    - Managing token ordering (token0 vs token1)
    - Caching pair addresses for efficiency

    The adapter uses the standard Uniswap V2 interface:
    1. Factory.getPair(tokenA, tokenB) -> pair address
    2. Pair.getReserves() -> (reserve0, reserve1, blockTimestampLast)
    3. Pair.token0() -> address of token0
    4. Pair.token1() -> address of token1

    Critical: Token decimals must be handled correctly. USDT0 uses 6 decimals
    while most other tokens use 18. The price calculation adjusts for this:
    adjusted_price = (reserve_quote / 10^decimals_quote) / (reserve_base / 10^decimals_base)

    Attributes:
        factory_address: Address of the Uniswap V2 factory contract
        factory_contract: Web3 contract instance for factory
        pair_contract_abi: ABI for Uniswap V2 pair contracts
        tokens: Dictionary mapping token symbols to TokenConfig objects
        pair_cache: Cache of (base_address, quote_address) -> pair_address mappings
        enable_cache: Whether to use pair address caching

    Example:
        ```python
        from web3 import AsyncWeb3
        from flare_monitor.config import load_config

        config = load_config("config/config.yaml")
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(config.flare.rpc_endpoints[0]))

        adapter = UniswapV2Adapter(
            dex_name="SparkDEX",
            w3=w3,
            factory_address="0x16b619B04c961E8f4F06C10B42FDAbb328980A89",
            tokens=config.tokens
        )

        pair = TradingPair(base_token="FXRP", quote_token="USDT0")
        price = await adapter.get_price(pair)
        print(f"FXRP price: ${price.price}")
        ```
    """

    # Zero address constant (indicates pair doesn't exist)
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

    def __init__(
        self,
        dex_name: str,
        w3: AsyncWeb3,
        factory_address: str,
        tokens: Dict[str, TokenConfig],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_cache: bool = True,
    ) -> None:
        """Initialize the Uniswap V2 adapter.

        Args:
            dex_name: Human-readable name of the DEX (e.g., "SparkDEX")
            w3: AsyncWeb3 instance connected to Flare Network
            factory_address: Address of the Uniswap V2 factory contract
            tokens: Dictionary mapping token symbols to TokenConfig objects
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Base delay in seconds between retries (default: 1.0)
            enable_cache: Whether to cache pair addresses (default: True)

        Raises:
            FileNotFoundError: If ABI files cannot be found
            ValueError: If factory address is invalid or ABIs cannot be loaded
        """
        super().__init__(dex_name, w3, max_retries, retry_delay)

        self.factory_address = factory_address
        self.tokens = tokens
        self.enable_cache = enable_cache

        # Cache for pair addresses: (base_address, quote_address) -> pair_address
        self.pair_cache: Dict[Tuple[str, str], str] = {}

        # Load ABIs from files
        self.factory_contract = self._load_factory_contract()
        self.pair_contract_abi = self._load_pair_abi()

        self.logger.info(
            f"Initialized {dex_name} adapter with factory at {factory_address}"
        )

    def _load_factory_contract(self) -> AsyncContract:
        """Load the Uniswap V2 factory contract.

        Returns:
            AsyncContract instance for the factory

        Raises:
            FileNotFoundError: If factory ABI file not found
            ValueError: If ABI is invalid
        """
        abi_path = Path(__file__).parent.parent.parent / "abis" / "IUniswapV2Factory.json"

        try:
            with open(abi_path, "r") as f:
                factory_abi = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Factory ABI not found at {abi_path}. "
                f"Ensure abis/IUniswapV2Factory.json exists."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in factory ABI: {e}")

        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.factory_address),
            abi=factory_abi
        )

    def _load_pair_abi(self) -> list:
        """Load the Uniswap V2 pair contract ABI.

        Returns:
            List containing the pair contract ABI

        Raises:
            FileNotFoundError: If pair ABI file not found
            ValueError: If ABI is invalid
        """
        abi_path = Path(__file__).parent.parent.parent / "abis" / "IUniswapV2Pair.json"

        try:
            with open(abi_path, "r") as f:
                pair_abi = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Pair ABI not found at {abi_path}. "
                f"Ensure abis/IUniswapV2Pair.json exists."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in pair ABI: {e}")

        return pair_abi

    async def _get_pair_address(
        self,
        base_token: TokenConfig,
        quote_token: TokenConfig
    ) -> Optional[str]:
        """Get the pair address for two tokens from the factory.

        Queries the factory contract to find the pair address for the given tokens.
        Uses caching if enabled to reduce RPC calls.

        Args:
            base_token: Configuration for the base token
            quote_token: Configuration for the quote token

        Returns:
            Checksummed pair address, or None if pair doesn't exist

        Note:
            Uniswap V2 sorts tokens by address, so token order doesn't matter
            for factory.getPair() calls. The returned pair contract always
            stores tokens in sorted order.
        """
        # Create cache key (sorted to handle token order)
        cache_key = tuple(sorted([base_token.address.lower(), quote_token.address.lower()]))

        # Check cache first
        if self.enable_cache and cache_key in self.pair_cache:
            return self.pair_cache[cache_key]

        # Query factory contract
        async def fetch_pair_address() -> Optional[str]:
            try:
                pair_address = await self.factory_contract.functions.getPair(
                    self.w3.to_checksum_address(base_token.address),
                    self.w3.to_checksum_address(quote_token.address)
                ).call()

                # Check for zero address (pair doesn't exist)
                if pair_address.lower() == self.ZERO_ADDRESS.lower():
                    self.logger.debug(
                        f"{self.dex_name}: Pair {base_token.symbol}/{quote_token.symbol} "
                        f"(addresses: {base_token.address}/{quote_token.address}) "
                        f"does not exist in factory {self.factory_address}"
                    )
                    return None

                self.logger.debug(
                    f"{self.dex_name}: Found pair {base_token.symbol}/{quote_token.symbol} "
                    f"at address {pair_address}"
                )
                return self.w3.to_checksum_address(pair_address)

            except ContractLogicError as e:
                self.logger.error(
                    f"{self.dex_name}: Contract logic error getting pair address for "
                    f"{base_token.symbol}/{quote_token.symbol} from factory {self.factory_address}: "
                    f"{type(e).__name__}: {e}"
                )
                return None
            except BadFunctionCallOutput as e:
                self.logger.error(
                    f"{self.dex_name}: Bad function call output for getPair "
                    f"({base_token.symbol}/{quote_token.symbol}). Factory address may be invalid: "
                    f"{self.factory_address}"
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
                    f"{self.dex_name}: Unexpected error getting pair address for "
                    f"{base_token.symbol}/{quote_token.symbol}: {type(e).__name__}: {e}",
                    exc_info=True
                )
                return None

        pair_address = await self._retry_on_failure(
            f"get pair address for {base_token.symbol}/{quote_token.symbol}",
            fetch_pair_address
        )

        # Cache the result if valid
        if pair_address and self.enable_cache:
            self.pair_cache[cache_key] = pair_address

        return pair_address

    async def _get_reserves(
        self,
        pair_address: str
    ) -> Optional[Tuple[int, int, int]]:
        """Get reserves from a Uniswap V2 pair contract.

        Calls the getReserves() function on the pair contract to fetch
        the current reserve amounts and last update timestamp.

        Args:
            pair_address: Checksummed address of the pair contract

        Returns:
            Tuple of (reserve0, reserve1, blockTimestampLast) or None if error

        Note:
            Reserves are returned in the order of token0 and token1,
            which are sorted by address (not by base/quote).
        """
        async def fetch_reserves() -> Optional[Tuple[int, int, int]]:
            try:
                pair_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(pair_address),
                    abi=self.pair_contract_abi
                )

                reserves = await pair_contract.functions.getReserves().call()

                # Validate reserves structure
                if not reserves or len(reserves) < 3:
                    self.logger.error(
                        f"{self.dex_name}: Invalid reserves structure from pair {pair_address}: "
                        f"expected 3 values, got {len(reserves) if reserves else 0}"
                    )
                    return None

                reserve0, reserve1, block_timestamp_last = reserves

                # Validate reserve values are non-negative
                if reserve0 < 0 or reserve1 < 0:
                    self.logger.error(
                        f"{self.dex_name}: Negative reserves from pair {pair_address}: "
                        f"reserve0={reserve0}, reserve1={reserve1}"
                    )
                    return None

                self.logger.debug(
                    f"{self.dex_name}: Fetched reserves from {pair_address}: "
                    f"reserve0={reserve0}, reserve1={reserve1}, timestamp={block_timestamp_last}"
                )

                return (int(reserve0), int(reserve1), int(block_timestamp_last))

            except ContractLogicError as e:
                self.logger.error(
                    f"{self.dex_name}: Contract logic error getting reserves from pair {pair_address}: "
                    f"{type(e).__name__}: {e}"
                )
                return None
            except BadFunctionCallOutput as e:
                self.logger.error(
                    f"{self.dex_name}: Bad function call output for getReserves on pair {pair_address}. "
                    f"Pair address may be invalid or contract may not be a Uniswap V2 pair."
                )
                return None
            except (ValueError, TypeError) as e:
                self.logger.error(
                    f"{self.dex_name}: Invalid data type in reserves from pair {pair_address}: "
                    f"{type(e).__name__}: {e}"
                )
                return None
            except Exception as e:
                self.logger.error(
                    f"{self.dex_name}: Unexpected error getting reserves from pair {pair_address}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True
                )
                return None

        return await self._retry_on_failure(
            f"get reserves for pair {pair_address}",
            fetch_reserves
        )

    async def _get_token_order(
        self,
        pair_address: str
    ) -> Optional[Tuple[str, str]]:
        """Get the token addresses in the order stored by the pair contract.

        Queries the pair contract to determine which token is token0 and
        which is token1. This is needed to correctly interpret reserve values.

        Args:
            pair_address: Checksummed address of the pair contract

        Returns:
            Tuple of (token0_address, token1_address) or None if error

        Note:
            Uniswap V2 always stores tokens in ascending address order.
            token0 < token1 (lexicographically)
        """
        async def fetch_token_order() -> Optional[Tuple[str, str]]:
            try:
                pair_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(pair_address),
                    abi=self.pair_contract_abi
                )

                token0 = await pair_contract.functions.token0().call()
                token1 = await pair_contract.functions.token1().call()

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
            f"get token order for pair {pair_address}",
            fetch_token_order
        )

    def _calculate_price(
        self,
        reserve_base: int,
        reserve_quote: int,
        decimals_base: int,
        decimals_quote: int
    ) -> Decimal:
        """Calculate price from reserves with proper decimal adjustment.

        Converts raw reserve amounts to human-readable price by adjusting
        for token decimals. The formula is:

        price = (reserve_quote / 10^decimals_quote) / (reserve_base / 10^decimals_base)

        Which simplifies to:

        price = (reserve_quote * 10^decimals_base) / (reserve_base * 10^decimals_quote)

        Args:
            reserve_base: Raw reserve amount of base token (no decimal adjustment)
            reserve_quote: Raw reserve amount of quote token (no decimal adjustment)
            decimals_base: Number of decimals for base token (typically 18)
            decimals_quote: Number of decimals for quote token (6 for USDT0, 18 for most)

        Returns:
            Price as Decimal (quote token per base token)

        Raises:
            ValueError: If reserves are zero or negative, or decimals are invalid
            InvalidOperation: If decimal calculation fails

        Example:
            For FXRP/USDT0 with reserves (1000000000000000000, 4500000):
            - reserve_base = 1000000000000000000 (1 FXRP with 18 decimals)
            - reserve_quote = 4500000 (4.5 USDT0 with 6 decimals)
            - price = 4.5 USDT0 per FXRP

            Calculation:
            price = (4500000 * 10^18) / (1000000000000000000 * 10^6)
                  = 4500000000000000000000000 / 1000000000000000000000000
                  = 4.5
        """
        # Validate inputs
        if reserve_base <= 0:
            raise ValueError(f"Base reserve must be positive: {reserve_base}")
        if reserve_quote <= 0:
            raise ValueError(f"Quote reserve must be positive: {reserve_quote}")
        if decimals_base < 0 or decimals_base > 77:
            raise ValueError(f"Invalid base decimals (must be 0-77): {decimals_base}")
        if decimals_quote < 0 or decimals_quote > 77:
            raise ValueError(f"Invalid quote decimals (must be 0-77): {decimals_quote}")

        # Check for unusually large reserves that might indicate data corruption
        MAX_RESERVE = 10 ** 40  # Reasonable upper bound
        if reserve_base > MAX_RESERVE:
            raise ValueError(
                f"Base reserve suspiciously large (possible data corruption): {reserve_base}"
            )
        if reserve_quote > MAX_RESERVE:
            raise ValueError(
                f"Quote reserve suspiciously large (possible data corruption): {reserve_quote}"
            )

        try:
            # Convert to Decimal for precision
            reserve_base_decimal = Decimal(reserve_base)
            reserve_quote_decimal = Decimal(reserve_quote)

            # Calculate decimal adjustment factor
            # If base has more decimals, multiply by 10^(decimals_base - decimals_quote)
            # If quote has more decimals, divide by 10^(decimals_quote - decimals_base)
            decimal_difference = decimals_base - decimals_quote
            adjustment_factor = Decimal(10) ** decimal_difference

            # Calculate price: (reserve_quote / reserve_base) * adjustment_factor
            price = (reserve_quote_decimal / reserve_base_decimal) * adjustment_factor

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
                f"Decimal calculation failed for reserves ({reserve_base}, {reserve_quote}) "
                f"with decimals ({decimals_base}, {decimals_quote}): {e}"
            ) from e

    def _calculate_liquidity(
        self,
        reserve_quote: int,
        decimals_quote: int
    ) -> Decimal:
        """Calculate total liquidity in quote token units.

        Converts raw reserve amount to human-readable liquidity by adjusting
        for token decimals. For a trading pair, total liquidity is typically
        measured as 2 * reserve_quote (since both sides should have equal value).

        However, for consistency and simplicity, we report the quote token
        reserve value directly, which represents half the total pool value.

        Args:
            reserve_quote: Raw reserve amount of quote token
            decimals_quote: Number of decimals for quote token

        Returns:
            Liquidity as Decimal (in quote token units)

        Raises:
            ValueError: If reserve is negative

        Example:
            For a pool with 4500000 raw USDT0 (6 decimals):
            liquidity = 4500000 / 10^6 = 4.5 USDT0
        """
        if reserve_quote < 0:
            raise ValueError(f"Quote reserve cannot be negative: {reserve_quote}")

        # Convert to Decimal and adjust for decimals
        reserve_quote_decimal = Decimal(reserve_quote)
        adjustment_factor = Decimal(10) ** decimals_quote

        liquidity = reserve_quote_decimal / adjustment_factor

        return liquidity

    async def get_price(self, pair: TradingPair) -> Price:
        """Fetch the current price for a trading pair.

        This is the main entry point for fetching price data. It:
        1. Looks up token configurations
        2. Gets the pair address from factory
        3. Fetches reserves and token order from pair contract
        4. Calculates the price with proper decimal handling
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

            # Get pair address from factory
            pair_address = await self._get_pair_address(base_token, quote_token)
            if not pair_address:
                return self._handle_error(
                    pair,
                    ValueError(
                        f"Pair {pair.base_token}/{pair.quote_token} does not exist "
                        f"on {self.dex_name}"
                    )
                )

            # Get token order from pair contract
            token_order = await self._get_token_order(pair_address)
            if not token_order:
                return self._handle_error(
                    pair,
                    RuntimeError("Failed to get token order from pair contract")
                )

            token0_address, token1_address = token_order

            # Get reserves from pair contract
            reserves = await self._get_reserves(pair_address)
            if not reserves:
                return self._handle_error(
                    pair,
                    RuntimeError("Failed to get reserves from pair contract")
                )

            reserve0, reserve1, block_timestamp_last = reserves

            # Determine which reserve corresponds to base and quote tokens
            # Uniswap stores tokens in sorted order, so we need to check
            base_address_lower = base_token.address.lower()
            token0_address_lower = token0_address.lower()

            self.logger.debug(
                f"{self.dex_name}: Token ordering - "
                f"token0={token0_address}, token1={token1_address}, "
                f"base={base_token.address} ({base_token.symbol}), "
                f"quote={quote_token.address} ({quote_token.symbol})"
            )

            if base_address_lower == token0_address_lower:
                # Base token is token0, quote token is token1
                reserve_base = reserve0
                reserve_quote = reserve1
                self.logger.debug(
                    f"{self.dex_name}: Base is token0, Quote is token1"
                )
            else:
                # Base token is token1, quote token is token0
                reserve_base = reserve1
                reserve_quote = reserve0
                self.logger.debug(
                    f"{self.dex_name}: Base is token1, Quote is token0"
                )

            self.logger.debug(
                f"{self.dex_name}: Raw reserves - "
                f"reserve_base={reserve_base}, reserve_quote={reserve_quote}, "
                f"decimals_base={base_token.decimals}, decimals_quote={quote_token.decimals}"
            )

            # Check for zero reserves (shouldn't happen but be defensive)
            if reserve_base == 0 or reserve_quote == 0:
                return self._handle_error(
                    pair,
                    ValueError(f"Zero reserves in pair (base={reserve_base}, quote={reserve_quote})")
                )

            # Calculate price with proper decimal handling
            price = self._calculate_price(
                reserve_base,
                reserve_quote,
                base_token.decimals,
                quote_token.decimals
            )

            # Calculate liquidity
            liquidity = self._calculate_liquidity(
                reserve_quote,
                quote_token.decimals
            )

            # Get current timestamp
            timestamp = datetime.now(timezone.utc)

            self.logger.debug(
                f"{self.dex_name}: {pair} price={price:.8f}, "
                f"liquidity={liquidity:.2f}, "
                f"reserves=({reserve_base}, {reserve_quote})"
            )

            return Price(
                pair=pair,
                dex_name=self.dex_name,
                price=price,
                liquidity=liquidity,
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
            RuntimeError: If fetching reserves fails

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

        # Get pair address from factory
        pair_address = await self._get_pair_address(base_token, quote_token)
        if not pair_address:
            raise ValueError(
                f"Pair {pair.base_token}/{pair.quote_token} does not exist on {self.dex_name}"
            )

        # Get token order from pair contract
        token_order = await self._get_token_order(pair_address)
        if not token_order:
            raise RuntimeError("Failed to get token order from pair contract")

        token0_address, token1_address = token_order

        # Get reserves from pair contract
        reserves = await self._get_reserves(pair_address)
        if not reserves:
            raise RuntimeError("Failed to get reserves from pair contract")

        reserve0, reserve1, block_timestamp_last = reserves

        # Determine which reserve is the quote token
        quote_address_lower = quote_token.address.lower()
        token0_address_lower = token0_address.lower()

        if quote_address_lower == token0_address_lower:
            reserve_quote = reserve0
        else:
            reserve_quote = reserve1

        # Calculate and return liquidity
        liquidity = self._calculate_liquidity(
            reserve_quote,
            quote_token.decimals
        )

        return liquidity

    def get_dex_name(self) -> str:
        """Return the human-readable name of this DEX.

        Returns:
            str: DEX name (e.g., "SparkDEX", "BlazeSwap", "Pangolin")
        """
        return self.dex_name

    def __repr__(self) -> str:
        """String representation of the adapter.

        Returns:
            str: Representation showing adapter details
        """
        return (
            f"UniswapV2Adapter(dex_name='{self.dex_name}', "
            f"factory_address='{self.factory_address}', "
            f"num_tokens={len(self.tokens)})"
        )
