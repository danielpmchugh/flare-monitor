"""Monitor Manager - Orchestration layer for DEX price monitoring.

This module provides the MonitorManager class which coordinates all components
of the Flare Monitor system:
- Creates and manages DEX adapters (UniswapV2 and UniswapV3)
- Fetches prices concurrently from all DEXes
- Calculates spreads and arbitrage opportunities
- Updates console output with live data
- Handles errors gracefully without crashing

The MonitorManager runs continuously, polling DEXes at regular intervals
and updating the display with real-time price and spread information.

Architecture:
    Config → MonitorManager → [Adapters] → Prices → Calculator → Spreads → Console

Example:
    ```python
    import asyncio
    from flare_monitor.monitor import MonitorManager
    from flare_monitor.config import load_config

    async def main():
        config = load_config("config/config.yaml")
        manager = MonitorManager(config)
        await manager.initialize()
        await manager.run_monitoring_loop()

    asyncio.run(main())
    ```
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from flare_monitor.adapters.base import DEXAdapter
from flare_monitor.adapters.uniswap_v2 import UniswapV2Adapter
from flare_monitor.adapters.uniswap_v3 import UniswapV3Adapter
from flare_monitor.calculator import (
    PricePoint,
    SpreadResult,
    find_best_arbitrage,
)
from flare_monitor.config import Config
from flare_monitor.models import DEXStatus, Price, Spread, TradingPair
from flare_monitor.output import ConsoleOutputHandler


class RpcCircuitBreaker:
    """Circuit breaker pattern for RPC endpoint failure handling.

    This class implements the circuit breaker pattern to prevent
    overwhelming failing RPC endpoints and enable graceful degradation.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service recovered

    Attributes:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in half-open to close circuit
        timeout_seconds: Time to wait before trying half-open state
        failure_count: Current count of consecutive failures
        success_count: Count of successes in half-open state
        last_failure_time: Timestamp of last failure
        state: Current circuit state (closed/open/half_open)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit (default: 5)
            success_threshold: Successes to close circuit (default: 2)
            timeout_seconds: Seconds before attempting recovery (default: 60)
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"
        self.logger = logging.getLogger("flare_monitor.circuit_breaker")

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.logger.info("Circuit breaker closing - service recovered")
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
                self.last_failure_time = None
        elif self.state == "closed":
            # Reset failure count on success in closed state
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.last_failure_time = time.time()

        if self.state == "closed":
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.logger.warning(
                    f"Circuit breaker opening after {self.failure_count} failures - "
                    f"blocking requests for {self.timeout_seconds}s"
                )
                self.state = "open"
        elif self.state == "half_open":
            self.logger.warning("Circuit breaker reopening - service still failing")
            self.state = "open"
            self.success_count = 0

    def can_execute(self) -> bool:
        """Check if operations are allowed through the circuit.

        Returns:
            True if operation should proceed, False if blocked
        """
        if self.state == "closed":
            return True
        elif self.state == "open":
            # Check if timeout has elapsed
            if (self.last_failure_time and
                time.time() - self.last_failure_time >= self.timeout_seconds):
                self.logger.info("Circuit breaker entering half-open state - testing recovery")
                self.state = "half_open"
                self.success_count = 0
                return True
            return False
        else:  # half_open
            return True

    def get_state(self) -> str:
        """Get current circuit state.

        Returns:
            Current state: 'closed', 'open', or 'half_open'
        """
        return self.state


class MonitorManager:
    """Orchestrates concurrent monitoring of all DEX/pair combinations.

    The MonitorManager is the central coordinator that:
    1. Initializes Web3 connections and creates DEX adapters
    2. Spawns async tasks to fetch prices from all DEXes
    3. Aggregates results and handles failures gracefully
    4. Calculates spreads using the calculator module
    5. Updates the console output with live data
    6. Implements circuit breaker pattern for RPC endpoint failures

    Attributes:
        config: Application configuration loaded from YAML
        w3: AsyncWeb3 instance for blockchain interactions
        adapters: List of initialized DEX adapters
        output: Console output handler for display
        dex_statuses: Dictionary mapping DEX name to status
        logger: Logger instance for this manager
        is_running: Flag indicating if monitoring loop is active
        rpc_circuit_breaker: Circuit breaker for RPC endpoint failures
        performance_metrics: Dictionary tracking performance statistics
    """

    def __init__(self, config: Config) -> None:
        """Initialize the Monitor Manager.

        Args:
            config: Validated configuration object from config loader

        Note:
            This only stores the config. Call initialize() to set up
            Web3 connections and create adapters.
        """
        self.config = config
        self.w3: Optional[AsyncWeb3] = None
        self.adapters: List[DEXAdapter] = []
        self.output = ConsoleOutputHandler()
        self.dex_statuses: Dict[str, DEXStatus] = {}
        self.logger = logging.getLogger("flare_monitor.monitor")
        self.is_running = False
        self.rpc_circuit_breaker = RpcCircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout_seconds=60
        )
        # Performance metrics tracking
        self.performance_metrics: Dict[str, Dict] = {
            "total_fetches": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "total_fetch_time": 0.0,
            "dex_metrics": {}
        }

    async def initialize(self) -> None:
        """Initialize Web3 connection and create DEX adapters.

        This method:
        1. Establishes connection to Flare Network via RPC
        2. Creates appropriate adapters (V2 or V3) for each enabled DEX
        3. Initializes DEX status tracking
        4. Validates that at least one adapter was created

        Raises:
            ValueError: If no adapters could be created
            ConnectionError: If Web3 connection fails
        """
        self.logger.info("Initializing Monitor Manager...")

        # Initialize Web3 connection
        await self._initialize_web3()

        # Create DEX adapters from configuration
        await self._create_adapters()

        # Initialize DEX statuses
        for adapter in self.adapters:
            dex_name = adapter.get_dex_name()
            self.dex_statuses[dex_name] = DEXStatus(
                dex_name=dex_name,
                is_online=True,
                last_update=None,
                error_count=0,
                last_error=None,
            )

        if not self.adapters:
            raise ValueError(
                "No DEX adapters were created. Check configuration and ensure "
                "at least one DEX is enabled."
            )

        self.logger.info(
            f"Monitor Manager initialized with {len(self.adapters)} adapters: "
            f"{[a.get_dex_name() for a in self.adapters]}"
        )

    async def _initialize_web3(self) -> None:
        """Initialize AsyncWeb3 connection to Flare Network.

        Uses the first RPC endpoint from configuration. Falls back to
        additional endpoints if the first one fails.

        Raises:
            ConnectionError: If all RPC endpoints fail
        """
        rpc_endpoints = self.config.flare.rpc_endpoints

        if not rpc_endpoints:
            raise ConnectionError("No RPC endpoints configured")

        for i, endpoint in enumerate(rpc_endpoints):
            try:
                self.logger.info(f"Connecting to Flare RPC: {endpoint}")
                self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(endpoint))

                # Test connection with timeout
                self.logger.debug(f"Testing RPC connection to {endpoint}...")
                chain_id = await asyncio.wait_for(
                    self.w3.eth.chain_id,
                    timeout=self.config.monitoring.request_timeout_seconds
                )

                self.logger.info(
                    f"Connected to Flare Network (chain_id={chain_id}) via {endpoint}"
                )

                # Verify chain ID matches configuration
                if chain_id != self.config.flare.chain_id:
                    self.logger.warning(
                        f"Chain ID mismatch: expected {self.config.flare.chain_id}, "
                        f"got {chain_id}. Continuing anyway..."
                    )

                # Mark circuit breaker as successful
                self.rpc_circuit_breaker.record_success()
                return

            except asyncio.TimeoutError:
                self.logger.error(
                    f"RPC endpoint {endpoint} timed out after "
                    f"{self.config.monitoring.request_timeout_seconds}s"
                )
                self.rpc_circuit_breaker.record_failure()
            except Web3Exception as e:
                self.logger.error(
                    f"Web3 error connecting to RPC endpoint {endpoint}: {type(e).__name__}: {e}"
                )
                self.rpc_circuit_breaker.record_failure()
            except Exception as e:
                self.logger.error(
                    f"Unexpected error connecting to RPC endpoint {endpoint}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True
                )
                self.rpc_circuit_breaker.record_failure()

            if i == len(rpc_endpoints) - 1:
                # Last endpoint, give up
                raise ConnectionError(
                    f"Failed to connect to any RPC endpoint. Tried: {rpc_endpoints}. "
                    f"Circuit breaker state: {self.rpc_circuit_breaker.get_state()}"
                )
            # Try next endpoint
            self.logger.info(f"Trying next RPC endpoint ({i + 2}/{len(rpc_endpoints)})...")
            continue

    async def _create_adapters(self) -> None:
        """Create DEX adapters based on configuration.

        Creates UniswapV2Adapter or UniswapV3Adapter instances for each
        enabled DEX in the configuration. Uses a factory pattern based on
        the DEX type field.

        Note:
            Only enabled DEXes are processed. Disabled DEXes are skipped.
        """
        for dex_config in self.config.dexes:
            if not dex_config.enabled:
                self.logger.info(f"Skipping disabled DEX: {dex_config.name}")
                continue

            try:
                self.logger.info(
                    f"Creating adapter for {dex_config.name} (type: {dex_config.type})"
                )

                # Factory pattern: create adapter based on type
                if dex_config.type == "uniswap_v2":
                    adapter = UniswapV2Adapter(
                        dex_name=dex_config.name,
                        w3=self.w3,
                        factory_address=dex_config.factory_address,
                        tokens=self.config.tokens,
                        max_retries=self.config.monitoring.max_retries,
                        retry_delay=self.config.monitoring.retry_backoff_seconds,
                        enable_cache=self.config.advanced.enable_pair_cache,
                    )
                elif dex_config.type == "uniswap_v3":
                    adapter = UniswapV3Adapter(
                        dex_name=dex_config.name,
                        w3=self.w3,
                        factory_address=dex_config.factory_address,
                        tokens=self.config.tokens,
                        max_retries=self.config.monitoring.max_retries,
                        retry_delay=self.config.monitoring.retry_backoff_seconds,
                        enable_cache=self.config.advanced.enable_pair_cache,
                    )
                else:
                    self.logger.error(
                        f"Unknown DEX type '{dex_config.type}' for {dex_config.name}, "
                        f"skipping"
                    )
                    continue

                self.adapters.append(adapter)
                self.logger.info(f"Successfully created adapter for {dex_config.name}")

            except Exception as e:
                self.logger.error(
                    f"Failed to create adapter for {dex_config.name}: {e}",
                    exc_info=True
                )
                # Continue with other adapters instead of failing completely
                continue

    async def fetch_prices_for_pair(self, pair: TradingPair) -> List[Price]:
        """Fetch prices from all DEXes for a single trading pair.

        Spawns concurrent async tasks for each adapter and gathers results.
        Individual adapter failures don't crash the entire fetch - errors
        are captured in the Price objects.

        Args:
            pair: The trading pair to fetch prices for

        Returns:
            List of Price objects, one per adapter. Prices may contain errors.

        Note:
            This method uses asyncio.gather with return_exceptions=True to
            ensure that one failing adapter doesn't prevent others from
            completing successfully.
        """
        self.logger.debug(f"Fetching prices for {pair} from {len(self.adapters)} DEXes")

        # Create tasks for all adapters
        tasks = []
        for adapter in self.adapters:
            task = self._fetch_price_with_status_update(adapter, pair)
            tasks.append(task)

        # Gather results (don't let exceptions propagate)
        prices = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log them
        valid_prices = []
        for i, price in enumerate(prices):
            if isinstance(price, Exception):
                adapter = self.adapters[i]
                self.logger.error(
                    f"Unexpected exception from {adapter.get_dex_name()}: {price}",
                    exc_info=price
                )
                # Update DEX status as offline
                self._update_dex_status_error(adapter.get_dex_name(), str(price))
            elif isinstance(price, Price):
                valid_prices.append(price)

        self.logger.debug(
            f"Fetched {len(valid_prices)} prices for {pair} "
            f"({len([p for p in valid_prices if p.is_valid])} valid)"
        )

        return valid_prices

    async def _fetch_price_with_status_update(
        self,
        adapter: DEXAdapter,
        pair: TradingPair
    ) -> Price:
        """Fetch price from adapter and update DEX status accordingly.

        Wraps the adapter.get_price() call with status tracking logic,
        performance metrics, and enhanced error context.
        Updates the DEX status based on success or failure.

        Args:
            adapter: DEX adapter to fetch price from
            pair: Trading pair to fetch

        Returns:
            Price object (may contain error)
        """
        dex_name = adapter.get_dex_name()
        start_time = time.time()

        # Initialize DEX metrics if not exists
        if dex_name not in self.performance_metrics["dex_metrics"]:
            self.performance_metrics["dex_metrics"][dex_name] = {
                "total_fetches": 0,
                "successful_fetches": 0,
                "failed_fetches": 0,
                "total_fetch_time": 0.0,
                "avg_fetch_time": 0.0,
            }

        # Check circuit breaker
        if not self.rpc_circuit_breaker.can_execute():
            self.logger.warning(
                f"Circuit breaker OPEN - skipping fetch for {dex_name} {pair}"
            )
            self._update_dex_status_error(
                dex_name,
                "Circuit breaker open - RPC endpoint unavailable"
            )
            return Price(
                pair=pair,
                dex_name=dex_name,
                price=None,
                liquidity=None,
                timestamp=datetime.now(timezone.utc),
                error="Circuit breaker open - RPC endpoint temporarily unavailable"
            )

        try:
            # Fetch price with timeout
            price = await asyncio.wait_for(
                adapter.get_price(pair),
                timeout=self.config.monitoring.request_timeout_seconds * 2
            )

            # Calculate fetch time
            fetch_time = time.time() - start_time

            # Update global metrics
            self.performance_metrics["total_fetches"] += 1
            self.performance_metrics["total_fetch_time"] += fetch_time

            # Update DEX-specific metrics
            dex_metrics = self.performance_metrics["dex_metrics"][dex_name]
            dex_metrics["total_fetches"] += 1
            dex_metrics["total_fetch_time"] += fetch_time

            # Update status and metrics based on price validity
            if price.is_valid:
                self._update_dex_status_success(dex_name)
                self.performance_metrics["successful_fetches"] += 1
                dex_metrics["successful_fetches"] += 1
                self.rpc_circuit_breaker.record_success()

                self.logger.debug(
                    f"{dex_name}: Successfully fetched {pair} in {fetch_time:.3f}s - "
                    f"price=${price.price:.6f}, liquidity=${price.liquidity:.2f}"
                )
            else:
                self._update_dex_status_error(dex_name, price.error or "Unknown error")
                self.performance_metrics["failed_fetches"] += 1
                dex_metrics["failed_fetches"] += 1

                self.logger.warning(
                    f"{dex_name}: Failed to fetch {pair} after {fetch_time:.3f}s - "
                    f"error: {price.error}"
                )

            # Update average fetch time
            if dex_metrics["total_fetches"] > 0:
                dex_metrics["avg_fetch_time"] = (
                    dex_metrics["total_fetch_time"] / dex_metrics["total_fetches"]
                )

            return price

        except asyncio.TimeoutError:
            fetch_time = time.time() - start_time
            error_msg = (
                f"Timeout after {fetch_time:.1f}s fetching {pair} from {dex_name}"
            )
            self.logger.error(error_msg)
            self._update_dex_status_error(dex_name, "Request timeout")
            self.performance_metrics["failed_fetches"] += 1
            self.performance_metrics["dex_metrics"][dex_name]["failed_fetches"] += 1
            self.rpc_circuit_breaker.record_failure()

            return Price(
                pair=pair,
                dex_name=dex_name,
                price=None,
                liquidity=None,
                timestamp=datetime.now(timezone.utc),
                error=error_msg
            )

        except Exception as e:
            # This shouldn't happen (adapters should catch exceptions),
            # but handle it defensively
            fetch_time = time.time() - start_time
            self.logger.error(
                f"Unexpected exception from {dex_name}.get_price({pair}) after {fetch_time:.3f}s: "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            self._update_dex_status_error(dex_name, str(e))
            self.performance_metrics["failed_fetches"] += 1
            self.performance_metrics["dex_metrics"][dex_name]["failed_fetches"] += 1

            # Return error Price
            return Price(
                pair=pair,
                dex_name=dex_name,
                price=None,
                liquidity=None,
                timestamp=datetime.now(timezone.utc),
                error=f"{type(e).__name__}: {str(e)}"
            )

    def _update_dex_status_success(self, dex_name: str) -> None:
        """Update DEX status after successful price fetch.

        Args:
            dex_name: Name of the DEX
        """
        if dex_name not in self.dex_statuses:
            self.dex_statuses[dex_name] = DEXStatus(dex_name=dex_name)

        status = self.dex_statuses[dex_name]
        status.is_online = True
        status.last_update = datetime.now(timezone.utc)
        status.error_count = 0
        status.last_error = None

        self.output.update_dex_status(status)

    def _update_dex_status_error(self, dex_name: str, error: str) -> None:
        """Update DEX status after failed price fetch.

        Args:
            dex_name: Name of the DEX
            error: Error message
        """
        if dex_name not in self.dex_statuses:
            self.dex_statuses[dex_name] = DEXStatus(dex_name=dex_name)

        status = self.dex_statuses[dex_name]
        status.error_count += 1
        status.last_error = error

        # Mark as offline after multiple consecutive errors
        ERROR_THRESHOLD = 3
        if status.error_count >= ERROR_THRESHOLD:
            status.is_online = False
            self.logger.warning(
                f"{dex_name} marked as offline after {status.error_count} consecutive errors"
            )

        self.output.update_dex_status(status)

    async def fetch_all_prices(self) -> Dict[TradingPair, List[Price]]:
        """Fetch prices for all configured pairs from all DEXes.

        Spawns concurrent tasks for each enabled trading pair and gathers
        results. This is the main data collection method.

        Returns:
            Dictionary mapping TradingPair to list of Price objects

        Note:
            Only enabled pairs are processed. Disabled pairs are skipped.
        """
        # Get enabled pairs
        enabled_pairs = [
            TradingPair(base_token=pair_config.base, quote_token=pair_config.quote)
            for pair_config in self.config.pairs
            if pair_config.enabled
        ]

        if not enabled_pairs:
            self.logger.warning("No enabled trading pairs found in configuration")
            return {}

        self.logger.debug(f"Fetching prices for {len(enabled_pairs)} pairs")

        # Create tasks for all pairs
        tasks = []
        for pair in enabled_pairs:
            task = self.fetch_prices_for_pair(pair)
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks)

        # Build result dictionary
        price_map: Dict[TradingPair, List[Price]] = {}
        for pair, prices in zip(enabled_pairs, results):
            price_map[pair] = prices

        return price_map

    def _calculate_spreads(
        self,
        price_map: Dict[TradingPair, List[Price]]
    ) -> List[Spread]:
        """Calculate spreads for all trading pairs.

        Uses the calculator module to find arbitrage opportunities.
        Only valid prices are considered for spread calculation.

        Args:
            price_map: Dictionary mapping pairs to their prices

        Returns:
            List of Spread objects for pairs with arbitrage opportunities

        Note:
            Spreads below the configured threshold are filtered out.
        """
        spreads = []

        for pair, prices in price_map.items():
            # Filter to only valid prices
            valid_prices = [p for p in prices if p.is_valid and p.price is not None]

            if len(valid_prices) < 2:
                # Need at least 2 prices to calculate spread
                self.logger.debug(
                    f"Skipping spread calculation for {pair}: "
                    f"only {len(valid_prices)} valid prices"
                )
                continue

            # Convert to PricePoint format for calculator
            price_points = [
                PricePoint(
                    dex_name=p.dex_name,
                    price=p.price,
                    timestamp=p.timestamp,
                    liquidity=p.liquidity
                )
                for p in valid_prices
            ]

            # Find best arbitrage opportunity
            spread_result = find_best_arbitrage(
                price_points,
                min_spread_threshold=self.config.monitoring.spread_alert_threshold_percent
            )

            if spread_result:
                # Convert SpreadResult to Spread model
                spread = Spread(
                    pair=pair,
                    low_dex=spread_result.low_dex,
                    high_dex=spread_result.high_dex,
                    low_price=spread_result.low_price,
                    high_price=spread_result.high_price,
                    spread_percent=spread_result.spread_percent,
                    timestamp=spread_result.timestamp
                )
                spreads.append(spread)

                self.logger.info(
                    f"Arbitrage opportunity: {pair} - {spread.spread_percent:.2f}% "
                    f"({spread.low_dex} ${spread.low_price:.6f} → "
                    f"{spread.high_dex} ${spread.high_price:.6f})"
                )

        return spreads

    def _update_console(
        self,
        price_map: Dict[TradingPair, List[Price]],
        spreads: List[Spread]
    ) -> None:
        """Update console output with latest prices and spreads.

        Args:
            price_map: Dictionary of trading pairs to prices
            spreads: List of calculated spreads
        """
        # Update all prices
        all_prices = []
        for prices in price_map.values():
            all_prices.extend(prices)

        self.output.update_prices(all_prices)

        # Update spreads
        self.output.update_spreads(spreads)

        # Update live display if running
        self.output.update_live_display()

    async def run_monitoring_loop(self) -> None:
        """Main monitoring loop - runs continuously.

        This is the main entry point for the monitoring system. It:
        1. Starts the live console display
        2. Enters an infinite loop that:
           - Fetches prices from all DEXes
           - Calculates spreads
           - Updates the console
           - Sleeps for the configured interval
        3. Handles shutdown gracefully on KeyboardInterrupt

        The loop continues until interrupted by the user (Ctrl+C) or
        an unrecoverable error occurs.

        Raises:
            Exception: If a critical error occurs that can't be recovered
        """
        self.is_running = True
        self.logger.info("Starting monitoring loop...")

        # Start live console display
        self.output.start_live_display()

        try:
            iteration = 0
            while self.is_running:
                iteration += 1
                loop_start = datetime.now()

                self.logger.debug(f"Starting monitoring iteration {iteration}")

                try:
                    # Fetch all prices
                    price_map = await self.fetch_all_prices()

                    # Calculate spreads
                    spreads = self._calculate_spreads(price_map)

                    # Update console output
                    self._update_console(price_map, spreads)

                    # Log summary
                    total_prices = sum(len(prices) for prices in price_map.values())
                    valid_prices = sum(
                        len([p for p in prices if p.is_valid])
                        for prices in price_map.values()
                    )
                    self.logger.info(
                        f"Iteration {iteration}: Fetched {total_prices} prices "
                        f"({valid_prices} valid), found {len(spreads)} arbitrage opportunities"
                    )

                except Exception as e:
                    # Log error but continue monitoring
                    self.logger.error(
                        f"Error in monitoring iteration {iteration}: {e}",
                        exc_info=True
                    )
                    self.output.print_error(
                        f"Error in monitoring loop: {str(e)}"
                    )

                # Calculate time to next iteration
                loop_duration = (datetime.now() - loop_start).total_seconds()
                sleep_time = max(
                    0,
                    self.config.monitoring.poll_interval_seconds - loop_duration
                )

                if sleep_time > 0:
                    self.logger.debug(
                        f"Iteration {iteration} took {loop_duration:.2f}s, "
                        f"sleeping for {sleep_time:.2f}s"
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"Iteration {iteration} took {loop_duration:.2f}s, "
                        f"longer than poll interval ({self.config.monitoring.poll_interval_seconds}s)"
                    )

        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted by user")
            self.output.print_info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
            self.output.print_error("Fatal error in monitoring loop", e)
            raise
        finally:
            # Clean shutdown
            self.is_running = False
            self.output.stop_live_display()
            self.logger.info("Monitoring loop stopped")

    async def stop(self) -> None:
        """Stop the monitoring loop gracefully.

        Sets the is_running flag to False, which will cause the monitoring
        loop to exit after the current iteration completes.
        """
        self.logger.info("Stopping monitoring loop...")
        self.is_running = False

    def __repr__(self) -> str:
        """String representation of the monitor manager.

        Returns:
            str: Representation showing number of adapters and pairs
        """
        return (
            f"MonitorManager(adapters={len(self.adapters)}, "
            f"pairs={len([p for p in self.config.pairs if p.enabled])})"
        )
