#!/usr/bin/env python3
"""
Flare Network RPC Connectivity Testing Script

This script tests connectivity to various Flare Network RPC endpoints and measures
their performance characteristics. It helps determine which RPC endpoints are suitable
for production use in the Flare Monitor application.

Features:
- Tests multiple RPC endpoints (official, Ankr, public RPC)
- Measures response times and reliability
- Tests both synchronous and asynchronous connections
- Validates network parameters (chain ID, block numbers, etc.)
- Provides recommendations for MVP deployment

Usage:
    python scripts/test_rpc.py

Requirements:
    - web3>=6.0.0
    - aiohttp>=3.9.0
    - rich>=13.0.0
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from web3 import AsyncWeb3, Web3
from web3.providers import AsyncHTTPProvider, HTTPProvider
from web3.exceptions import Web3Exception


# RPC endpoints to test (from config.example.yaml and additional public sources)
RPC_ENDPOINTS = [
    {
        "name": "Official Flare RPC",
        "url": "https://flare-api.flare.network/ext/C/rpc",
        "description": "Primary official endpoint",
    },
    {
        "name": "Ankr Flare RPC",
        "url": "https://rpc.ankr.com/flare",
        "description": "Ankr public RPC (Europe optimized)",
    },
    {
        "name": "Public RPC",
        "url": "https://flare.public-rpc.com",
        "description": "Alternative public endpoint",
    },
]

# Expected Flare Network chain ID
EXPECTED_CHAIN_ID = 14

# Sample Flare address for balance testing (WFLR contract address)
SAMPLE_ADDRESS = "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d"

# Test configuration
REQUEST_TIMEOUT = 10  # seconds
NUM_ITERATIONS = 5  # Number of times to test each endpoint for averaging


console = Console()


class RPCTestResult:
    """Stores test results for a single RPC endpoint."""

    def __init__(self, name: str, url: str, description: str):
        self.name = name
        self.url = url
        self.description = description
        self.is_reachable = False
        self.chain_id: Optional[int] = None
        self.latest_block: Optional[int] = None
        self.gas_price: Optional[int] = None
        self.sample_balance: Optional[int] = None
        self.sync_response_times: List[float] = []
        self.async_response_times: List[float] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def avg_sync_time(self) -> Optional[float]:
        """Calculate average synchronous response time."""
        return sum(self.sync_response_times) / len(self.sync_response_times) if self.sync_response_times else None

    @property
    def avg_async_time(self) -> Optional[float]:
        """Calculate average asynchronous response time."""
        return sum(self.async_response_times) / len(self.async_response_times) if self.async_response_times else None

    @property
    def min_async_time(self) -> Optional[float]:
        """Get minimum asynchronous response time."""
        return min(self.async_response_times) if self.async_response_times else None

    @property
    def max_async_time(self) -> Optional[float]:
        """Get maximum asynchronous response time."""
        return max(self.async_response_times) if self.async_response_times else None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_tests = len(self.sync_response_times) + len(self.async_response_times)
        return (total_tests / (NUM_ITERATIONS * 2)) * 100 if total_tests > 0 else 0.0


def test_sync_rpc(endpoint: Dict[str, str], result: RPCTestResult) -> bool:
    """
    Test synchronous RPC connection.

    Args:
        endpoint: RPC endpoint configuration
        result: Result object to store test data

    Returns:
        True if tests passed, False otherwise
    """
    try:
        console.print(f"  Testing sync connection to {endpoint['name']}...")

        start_time = time.time()
        w3 = Web3(HTTPProvider(endpoint["url"], request_kwargs={"timeout": REQUEST_TIMEOUT}))

        # Test 1: Check if connected
        if not w3.is_connected():
            result.errors.append("Sync: Failed to establish connection")
            return False

        # Test 2: Get chain ID
        chain_id = w3.eth.chain_id
        result.chain_id = chain_id
        if chain_id != EXPECTED_CHAIN_ID:
            result.warnings.append(f"Chain ID mismatch: expected {EXPECTED_CHAIN_ID}, got {chain_id}")

        # Test 3: Get latest block number
        result.latest_block = w3.eth.block_number

        # Test 4: Get gas price
        result.gas_price = w3.eth.gas_price

        # Test 5: Get sample account balance
        result.sample_balance = w3.eth.get_balance(SAMPLE_ADDRESS)

        elapsed = time.time() - start_time
        result.sync_response_times.append(elapsed)
        result.is_reachable = True

        console.print(f"    [green]✓[/green] Sync test passed ({elapsed:.3f}s)")
        return True

    except Web3Exception as e:
        result.errors.append(f"Sync Web3 error: {str(e)}")
        console.print(f"    [red]✗[/red] Sync test failed: {e}")
        return False
    except Exception as e:
        result.errors.append(f"Sync error: {str(e)}")
        console.print(f"    [red]✗[/red] Sync test failed: {e}")
        return False


async def test_async_rpc(endpoint: Dict[str, str], result: RPCTestResult) -> bool:
    """
    Test asynchronous RPC connection.

    Args:
        endpoint: RPC endpoint configuration
        result: Result object to store test data

    Returns:
        True if tests passed, False otherwise
    """
    try:
        console.print(f"  Testing async connection to {endpoint['name']}...")

        start_time = time.time()

        # Create async provider with timeout
        provider = AsyncHTTPProvider(
            endpoint["url"],
            request_kwargs={"timeout": REQUEST_TIMEOUT}
        )
        w3 = AsyncWeb3(provider)

        # Test 1: Check if connected
        is_connected = await w3.is_connected()
        if not is_connected:
            result.errors.append("Async: Failed to establish connection")
            return False

        # Test 2: Verify chain ID (should match sync result)
        chain_id = await w3.eth.chain_id
        if chain_id != EXPECTED_CHAIN_ID:
            result.warnings.append(f"Async chain ID mismatch: expected {EXPECTED_CHAIN_ID}, got {chain_id}")

        # Test 3: Get latest block number
        block_number = await w3.eth.block_number

        # Test 4: Get gas price
        gas_price = await w3.eth.gas_price

        # Test 5: Get sample account balance
        balance = await w3.eth.get_balance(SAMPLE_ADDRESS)

        elapsed = time.time() - start_time
        result.async_response_times.append(elapsed)

        console.print(f"    [green]✓[/green] Async test passed ({elapsed:.3f}s)")
        return True

    except Web3Exception as e:
        result.errors.append(f"Async Web3 error: {str(e)}")
        console.print(f"    [red]✗[/red] Async test failed: {e}")
        return False
    except Exception as e:
        result.errors.append(f"Async error: {str(e)}")
        console.print(f"    [red]✗[/red] Async test failed: {e}")
        return False


async def test_concurrent_requests(endpoint: Dict[str, str]) -> Tuple[float, int]:
    """
    Test concurrent async requests to measure endpoint capacity.

    Args:
        endpoint: RPC endpoint configuration

    Returns:
        Tuple of (average_response_time, successful_requests)
    """
    console.print(f"  Testing concurrent requests to {endpoint['name']}...")

    provider = AsyncHTTPProvider(
        endpoint["url"],
        request_kwargs={"timeout": REQUEST_TIMEOUT}
    )
    w3 = AsyncWeb3(provider)

    async def single_request() -> Optional[float]:
        """Make a single async request and return response time."""
        try:
            start = time.time()
            await w3.eth.block_number
            return time.time() - start
        except Exception:
            return None

    # Make 10 concurrent requests
    start_time = time.time()
    tasks = [single_request() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Calculate statistics
    successful = [r for r in results if isinstance(r, float)]
    success_count = len(successful)
    avg_time = sum(successful) / success_count if successful else 0

    console.print(
        f"    [cyan]→[/cyan] Completed {success_count}/10 concurrent requests "
        f"in {total_time:.3f}s (avg: {avg_time:.3f}s each)"
    )

    return avg_time, success_count


async def run_all_tests() -> List[RPCTestResult]:
    """
    Run all RPC tests across all endpoints.

    Returns:
        List of test results for each endpoint
    """
    results = []

    console.print(Panel.fit(
        "[bold cyan]Flare Network RPC Connectivity Test[/bold cyan]\n"
        f"Testing {len(RPC_ENDPOINTS)} endpoints with {NUM_ITERATIONS} iterations each",
        border_style="cyan"
    ))
    console.print()

    for endpoint in RPC_ENDPOINTS:
        console.print(f"[bold yellow]Testing: {endpoint['name']}[/bold yellow]")
        console.print(f"  URL: {endpoint['url']}")
        console.print(f"  Description: {endpoint['description']}")
        console.print()

        result = RPCTestResult(
            name=endpoint["name"],
            url=endpoint["url"],
            description=endpoint["description"]
        )

        # Run multiple iterations for average
        for i in range(NUM_ITERATIONS):
            console.print(f"  [dim]Iteration {i + 1}/{NUM_ITERATIONS}[/dim]")

            # Test sync connection
            test_sync_rpc(endpoint, result)

            # Small delay between tests
            await asyncio.sleep(0.5)

            # Test async connection
            await test_async_rpc(endpoint, result)

            # Small delay between iterations
            await asyncio.sleep(0.5)

        # Test concurrent requests
        console.print()
        concurrent_time, concurrent_success = await test_concurrent_requests(endpoint)
        if concurrent_success < 10:
            result.warnings.append(
                f"Only {concurrent_success}/10 concurrent requests succeeded"
            )

        results.append(result)
        console.print()
        console.print("-" * 80)
        console.print()

    return results


def display_results(results: List[RPCTestResult]) -> None:
    """
    Display test results in a formatted table.

    Args:
        results: List of test results to display
    """
    console.print("[bold cyan]Test Results Summary[/bold cyan]\n")

    # Create main results table
    table = Table(title="RPC Endpoint Performance", show_header=True, header_style="bold magenta")
    table.add_column("Endpoint", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Chain ID", justify="center")
    table.add_column("Latest Block", justify="right")
    table.add_column("Avg Sync (s)", justify="right")
    table.add_column("Avg Async (s)", justify="right")
    table.add_column("Success Rate", justify="right")

    for result in results:
        status = "[green]✓ Online[/green]" if result.is_reachable else "[red]✗ Offline[/red]"
        chain_id = str(result.chain_id) if result.chain_id else "N/A"
        if result.chain_id and result.chain_id != EXPECTED_CHAIN_ID:
            chain_id = f"[yellow]{chain_id}[/yellow]"

        block = f"{result.latest_block:,}" if result.latest_block else "N/A"
        sync_time = f"{result.avg_sync_time:.3f}" if result.avg_sync_time else "N/A"
        async_time = f"{result.avg_async_time:.3f}" if result.avg_async_time else "N/A"
        success_rate = f"{result.success_rate:.1f}%"

        table.add_row(
            result.name,
            status,
            chain_id,
            block,
            sync_time,
            async_time,
            success_rate
        )

    console.print(table)
    console.print()

    # Display detailed statistics
    console.print("[bold cyan]Detailed Statistics[/bold cyan]\n")

    for result in results:
        if not result.is_reachable:
            continue

        console.print(f"[bold]{result.name}[/bold]")
        console.print(f"  URL: {result.url}")

        if result.avg_async_time:
            console.print(f"  Async Response Times:")
            console.print(f"    Average: {result.avg_async_time:.3f}s")
            console.print(f"    Min: {result.min_async_time:.3f}s")
            console.print(f"    Max: {result.max_async_time:.3f}s")

        if result.gas_price:
            console.print(f"  Current Gas Price: {result.gas_price / 1e9:.2f} Gwei")

        if result.sample_balance is not None:
            console.print(f"  Sample Balance (WFLR contract): {result.sample_balance / 1e18:.6f} FLR")

        if result.warnings:
            console.print(f"  [yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"    - {warning}")

        if result.errors:
            console.print(f"  [red]Errors:[/red]")
            for error in result.errors[:3]:  # Show first 3 errors
                console.print(f"    - {error}")

        console.print()


def generate_recommendations(results: List[RPCTestResult]) -> None:
    """
    Generate recommendations based on test results.

    Args:
        results: List of test results to analyze
    """
    console.print("[bold cyan]Recommendations for MVP Deployment[/bold cyan]\n")

    # Find working endpoints
    working = [r for r in results if r.is_reachable and r.success_rate >= 90]

    if not working:
        console.print(
            "[red]WARNING:[/red] No RPC endpoints passed reliability tests. "
            "Consider using a paid RPC service."
        )
        return

    # Sort by average async response time
    working.sort(key=lambda r: r.avg_async_time or float('inf'))

    console.print("[bold green]Working Endpoints (Success Rate >= 90%):[/bold green]\n")

    for i, result in enumerate(working, 1):
        speed_rating = "Fast" if result.avg_async_time and result.avg_async_time < 0.5 else "Moderate"
        if result.avg_async_time and result.avg_async_time > 1.0:
            speed_rating = "Slow"

        console.print(f"{i}. [bold]{result.name}[/bold] - {speed_rating}")
        console.print(f"   Avg Response: {result.avg_async_time:.3f}s")
        console.print(f"   Success Rate: {result.success_rate:.1f}%")
        console.print(f"   Recommendation: ", end="")

        if i == 1:
            console.print("[green]Use as PRIMARY endpoint[/green]")
        elif i == 2:
            console.print("[yellow]Use as FALLBACK endpoint[/yellow]")
        else:
            console.print("[dim]Use as additional fallback[/dim]")
        console.print()

    console.print("\n[bold]Configuration Suggestions:[/bold]\n")
    console.print("1. Use the fastest endpoint as your primary RPC")
    console.print("2. Configure at least 2 fallback endpoints for redundancy")
    console.print("3. Set request timeout to 5-10 seconds")
    console.print("4. Implement exponential backoff for retries")
    console.print("5. Monitor for rate limiting (429 errors)")
    console.print()

    if all(r.avg_async_time and r.avg_async_time > 1.0 for r in working):
        console.print(
            "[yellow]NOTE:[/yellow] All public endpoints show high latency (>1s). "
            "Consider upgrading to a paid RPC service for production use."
        )
        console.print()

    console.print("[bold]Rate Limiting Considerations:[/bold]\n")
    console.print("- Official Flare RPC: Rate-limited, best for development/testing")
    console.print("- Public RPCs: May have undocumented rate limits")
    console.print("- For MVP: Start with public RPCs, monitor for 429 errors")
    console.print("- For Production: Consider paid RPC services (Ankr, Blast, QuickNode)")
    console.print()


async def main() -> None:
    """Main entry point for RPC testing script."""
    console.print()

    # Run all tests
    results = await run_all_tests()

    # Display results
    display_results(results)

    # Generate recommendations
    generate_recommendations(results)

    # Final summary
    working_count = sum(1 for r in results if r.is_reachable)
    console.print(Panel.fit(
        f"[bold]Testing Complete[/bold]\n"
        f"Tested: {len(results)} endpoints\n"
        f"Working: {working_count} endpoints\n"
        f"Failed: {len(results) - working_count} endpoints",
        border_style="green" if working_count > 0 else "red"
    ))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Testing interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]Fatal error:[/red] {e}")
        raise
