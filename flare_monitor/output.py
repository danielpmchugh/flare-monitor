"""Console output handler using Rich library for formatted display.

This module provides a beautiful, live-updating console interface for monitoring
FXRP prices across multiple DEXes on the Flare Network.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import DEXStatus, Price, Spread, TradingPair


class ConsoleOutputHandler:
    """Handles all console output for the Flare Monitor application.

    Uses Rich library to provide:
    - Live-updating price table
    - Color-coded spreads (green for opportunities, red for losses)
    - DEX status indicators
    - Timestamp of last update
    - Best arbitrage opportunity highlighting

    Attributes:
        console: Rich Console instance for rendering
        prices: Current price data from all DEXes
        spreads: Current spread calculations
        dex_statuses: Status information for each DEX
        last_update: Timestamp of most recent update
    """

    def __init__(self) -> None:
        """Initialize the console output handler."""
        self.console = Console()
        self.prices: Dict[tuple[str, str], List[Price]] = {}
        self.spreads: Dict[str, Spread] = {}
        self.dex_statuses: Dict[str, DEXStatus] = {}
        self.last_update: Optional[datetime] = None
        self._live: Optional[Live] = None

    def update_price(self, price: Price) -> None:
        """Update price data for a specific DEX and pair.

        Args:
            price: Price data to update
        """
        pair_key = (price.pair.base_token, price.pair.quote_token)

        if pair_key not in self.prices:
            self.prices[pair_key] = []

        # Find and update existing price for this DEX, or append new one
        updated = False
        for i, existing_price in enumerate(self.prices[pair_key]):
            if existing_price.dex_name == price.dex_name:
                self.prices[pair_key][i] = price
                updated = True
                break

        if not updated:
            self.prices[pair_key].append(price)

        self.last_update = datetime.now()

    def update_prices(self, prices: List[Price]) -> None:
        """Update multiple prices at once.

        Convenience method for batch updates.

        Args:
            prices: List of price data to update
        """
        for price in prices:
            self.update_price(price)

    def update_spread(self, spread: Spread) -> None:
        """Update spread data for a specific pair.

        Args:
            spread: Spread calculation to update
        """
        spread_key = str(spread.pair)
        self.spreads[spread_key] = spread
        self.last_update = datetime.now()

    def update_spreads(self, spreads: List[Spread]) -> None:
        """Update multiple spreads at once.

        Convenience method for batch updates.

        Args:
            spreads: List of spread calculations to update
        """
        for spread in spreads:
            self.update_spread(spread)

    def update_dex_status(self, status: DEXStatus) -> None:
        """Update status for a specific DEX.

        Args:
            status: DEX status information
        """
        self.dex_statuses[status.dex_name] = status
        self.last_update = datetime.now()

    def _create_price_table(self) -> Table:
        """Create a Rich table displaying current prices from all DEXes.

        Returns:
            Formatted table with prices, spreads, and status
        """
        table = Table(
            title="FXRP Price Monitor - Flare Network",
            title_style="bold cyan",
            show_header=True,
            header_style="bold white on blue",
            border_style="blue",
            show_lines=True,
        )

        # Add columns
        table.add_column("Pair", style="cyan", justify="left", width=12)
        table.add_column("DEX", style="yellow", justify="left", width=15)
        table.add_column("Price", style="white", justify="right", width=15)
        table.add_column("Liquidity", style="white", justify="right", width=15)
        table.add_column("Spread", style="white", justify="center", width=12)
        table.add_column("Status", justify="center", width=8)

        # Sort pairs for consistent display
        sorted_pairs = sorted(self.prices.keys())

        for pair_key in sorted_pairs:
            pair_prices = self.prices[pair_key]
            pair_str = f"{pair_key[0]}/{pair_key[1]}"

            # Calculate min/max prices for this pair
            valid_prices = [p for p in pair_prices if p.is_valid]
            if not valid_prices:
                continue

            min_price = min(p.price for p in valid_prices if p.price is not None)
            max_price = max(p.price for p in valid_prices if p.price is not None)

            # Sort DEXes by price for better readability
            sorted_prices = sorted(
                pair_prices,
                key=lambda p: p.price if p.price is not None else Decimal(0),
                reverse=True
            )

            for i, price in enumerate(sorted_prices):
                # Format price
                if price.error:
                    price_str = Text("ERROR", style="red")
                    liquidity_str = "-"
                    status_icon = Text("✗", style="red")
                elif price.price is None:
                    price_str = Text("N/A", style="dim")
                    liquidity_str = "-"
                    status_icon = Text("?", style="yellow")
                else:
                    # Format price based on magnitude
                    if price.price < Decimal("0.01"):
                        price_str = Text(f"${price.price:.6f}", style="white")
                    elif price.price < Decimal("1"):
                        price_str = Text(f"${price.price:.4f}", style="white")
                    else:
                        price_str = Text(f"{price.price:.4f}", style="white")

                    # Format liquidity
                    if price.liquidity is not None:
                        if price.liquidity >= 1_000_000:
                            liquidity_str = f"${price.liquidity / 1_000_000:.2f}M"
                        elif price.liquidity >= 1_000:
                            liquidity_str = f"${price.liquidity / 1_000:.2f}K"
                        else:
                            liquidity_str = f"${price.liquidity:.2f}"
                    else:
                        liquidity_str = "-"

                    status_icon = Text("✓", style="green")

                # Calculate and format spread
                if price.price and price.price == max_price and max_price != min_price:
                    spread_pct = ((max_price - min_price) / min_price) * 100
                    spread_str = Text(f"+{spread_pct:.2f}%", style="bold green")
                elif price.price and price.price == min_price and max_price != min_price:
                    spread_pct = ((max_price - min_price) / min_price) * 100
                    spread_str = Text(f"-{spread_pct:.2f}%", style="bold red")
                else:
                    spread_str = Text("-", style="dim")

                # Only show pair name on first row for this pair
                pair_display = pair_str if i == 0 else ""

                table.add_row(
                    pair_display,
                    price.dex_name,
                    price_str,
                    liquidity_str,
                    spread_str,
                    status_icon,
                )

        return table

    def _create_status_panel(self) -> Panel:
        """Create a panel showing overall status and best opportunity.

        Returns:
            Panel with status information
        """
        # Find best spread opportunity
        best_spread: Optional[Spread] = None
        if self.spreads:
            best_spread = max(
                self.spreads.values(),
                key=lambda s: s.spread_percent
            )

        # Create status text
        status_lines = []

        # Best opportunity
        if best_spread and best_spread.spread_percent > 0:
            opp_text = Text()
            opp_text.append("Best Opportunity: ", style="bold white")
            opp_text.append(
                f"+{best_spread.spread_percent:.2f}%",
                style="bold green"
            )
            opp_text.append(
                f" ({best_spread.high_dex} → {best_spread.low_dex})",
                style="cyan"
            )
            status_lines.append(opp_text)
        else:
            status_lines.append(
                Text("Best Opportunity: None detected", style="dim")
            )

        # DEX status summary
        online_count = sum(1 for s in self.dex_statuses.values() if s.is_online)
        total_count = len(self.dex_statuses)
        if total_count > 0:
            dex_status_text = Text()
            dex_status_text.append("DEX Status: ", style="bold white")
            dex_status_text.append(
                f"{online_count}/{total_count} online",
                style="green" if online_count == total_count else "yellow"
            )
            status_lines.append(dex_status_text)

        # Last update timestamp
        if self.last_update:
            update_text = Text()
            update_text.append("Last Update: ", style="bold white")
            update_text.append(
                self.last_update.strftime("%Y-%m-%d %H:%M:%S"),
                style="cyan"
            )
            status_lines.append(update_text)
        else:
            status_lines.append(
                Text("Last Update: Never", style="dim")
            )

        # Combine all status lines
        status_content = Text()
        for i, line in enumerate(status_lines):
            if i > 0:
                status_content.append("\n")
            status_content.append(line)

        return Panel(
            status_content,
            border_style="green",
            padding=(0, 1),
        )

    def _create_layout(self) -> Layout:
        """Create the overall layout for the display.

        Returns:
            Layout with table and status panel
        """
        layout = Layout()

        # Create main sections
        layout.split_column(
            Layout(name="main", ratio=4),
            Layout(name="status", size=5),
        )

        # Populate sections
        layout["main"].update(self._create_price_table())
        layout["status"].update(self._create_status_panel())

        return layout

    def render(self) -> None:
        """Render the current state to the console (one-time render)."""
        self.console.clear()
        layout = self._create_layout()
        self.console.print(layout)

    def start(self) -> None:
        """Start live-updating display mode.

        Alias for start_live_display() for convenience.
        """
        self.start_live_display()

    def start_live_display(self) -> None:
        """Start live-updating display mode.

        This creates a Rich Live display that automatically refreshes
        when data is updated. Call stop_live_display() to stop.
        """
        if self._live is not None:
            return  # Already running

        self._live = Live(
            self._create_layout(),
            console=self.console,
            refresh_per_second=2,
            screen=True,
        )
        self._live.start()

    def update_live_display(self) -> None:
        """Update the live display with current data.

        This should be called after updating prices, spreads, or statuses
        when in live display mode.
        """
        if self._live is not None:
            self._live.update(self._create_layout())

    def stop(self) -> None:
        """Stop the live-updating display mode.

        Alias for stop_live_display() for convenience.
        """
        self.stop_live_display()

    def stop_live_display(self) -> None:
        """Stop the live-updating display mode."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def show_error(self, dex: str, error: str) -> None:
        """Display an error for a specific DEX.

        This method is for showing DEX-specific errors in the context of the application.

        Args:
            dex: DEX name that encountered the error
            error: Error message to display
        """
        error_text = Text()
        error_text.append(f"{dex}: ", style="bold yellow")
        error_text.append("ERROR - ", style="bold red")
        error_text.append(error, style="red")

        self.console.print(Panel(error_text, border_style="red", padding=(0, 1)))

    def print_error(self, message: str, error: Optional[Exception] = None) -> None:
        """Print an error message to the console.

        Args:
            message: Error message to display
            error: Optional exception object
        """
        error_text = Text()
        error_text.append("ERROR: ", style="bold red")
        error_text.append(message, style="red")

        if error:
            error_text.append(f"\n{str(error)}", style="dim red")

        self.console.print(Panel(error_text, border_style="red", padding=(0, 1)))

    def print_warning(self, message: str) -> None:
        """Print a warning message to the console.

        Args:
            message: Warning message to display
        """
        warning_text = Text()
        warning_text.append("WARNING: ", style="bold yellow")
        warning_text.append(message, style="yellow")

        self.console.print(Panel(warning_text, border_style="yellow", padding=(0, 1)))

    def print_info(self, message: str) -> None:
        """Print an informational message to the console.

        Args:
            message: Info message to display
        """
        info_text = Text()
        info_text.append("INFO: ", style="bold cyan")
        info_text.append(message, style="cyan")

        self.console.print(info_text)

    def print_success(self, message: str) -> None:
        """Print a success message to the console.

        Args:
            message: Success message to display
        """
        success_text = Text()
        success_text.append("✓ ", style="bold green")
        success_text.append(message, style="green")

        self.console.print(success_text)
