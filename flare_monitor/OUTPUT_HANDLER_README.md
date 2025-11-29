# Console Output Handler

## Overview

The `output.py` module provides a rich, interactive console interface for monitoring FXRP prices across multiple DEXes on the Flare Network. It uses the [Rich](https://rich.readthedocs.io/) library to create a beautiful, live-updating terminal UI.

## Features

### Core Functionality

1. **Live-Updating Price Table**
   - Displays prices from all monitored DEXes
   - Automatically updates when new price data arrives
   - Color-coded for easy reading

2. **Color-Coded Spreads**
   - Green: Higher price (opportunity to sell)
   - Red: Lower price (opportunity to buy)
   - Shows spread percentage between high and low

3. **DEX Status Indicators**
   - ✓ (green): DEX online and responding
   - ✗ (red): DEX offline or error
   - ? (yellow): Status unknown

4. **Status Panel**
   - Best arbitrage opportunity highlighted
   - DEX online/offline count
   - Timestamp of last update

5. **Message Types**
   - Info messages (cyan)
   - Success messages (green)
   - Warning messages (yellow)
   - Error messages (red)

## Architecture

### Class: `ConsoleOutputHandler`

The main class that manages all console output operations.

#### Key Methods

**Data Updates:**
- `update_price(price: Price)` - Update price for a DEX/pair
- `update_spread(spread: Spread)` - Update spread calculation
- `update_dex_status(status: DEXStatus)` - Update DEX online status

**Display Modes:**
- `render()` - One-time static render to console
- `start_live_display()` - Begin live-updating mode
- `update_live_display()` - Refresh live display with new data
- `stop_live_display()` - Stop live updating mode

**Messaging:**
- `print_info(message: str)` - Print informational message
- `print_success(message: str)` - Print success message
- `print_warning(message: str)` - Print warning message
- `print_error(message: str, error: Exception)` - Print error message

### Data Flow

```
Price Data → update_price() → Internal State → update_live_display() → Console
Spread Data → update_spread() → Internal State → update_live_display() → Console
DEX Status → update_dex_status() → Internal State → update_live_display() → Console
```

## Usage Examples

### Basic Usage

```python
from flare_monitor.output import ConsoleOutputHandler
from flare_monitor.models import Price, TradingPair
from decimal import Decimal
from datetime import datetime

# Create handler
handler = ConsoleOutputHandler()

# Create price data
pair = TradingPair(base_token="FXRP", quote_token="USDT0")
price = Price(
    pair=pair,
    dex_name="SparkDEX",
    price=Decimal("0.004500"),
    liquidity=Decimal("125000.50"),
    timestamp=datetime.now(),
)

# Update and display
handler.update_price(price)
handler.render()
```

### Live Display Mode

```python
import time

# Start live display
handler.start_live_display()

try:
    # Update prices in a loop
    while True:
        # Fetch new prices...
        handler.update_price(new_price)
        handler.update_live_display()
        time.sleep(1)
finally:
    # Stop when done
    handler.stop_live_display()
```

### Error Handling

```python
# Price with error
error_price = Price(
    pair=pair,
    dex_name="SparkDEX",
    price=None,
    liquidity=None,
    timestamp=datetime.now(),
    error="RPC connection timeout",
)
handler.update_price(error_price)

# Update DEX status
from flare_monitor.models import DEXStatus

status = DEXStatus(
    dex_name="SparkDEX",
    is_online=False,
    last_update=datetime.now(),
    error_count=3,
    last_error="RPC connection timeout",
)
handler.update_dex_status(status)
```

## Display Format

### Price Table

```
╔═══════════════════════════════════════════════════════════╗
║         FXRP Price Monitor - Flare Network               ║
╠═══════════════════════════════════════════════════════════╣
║ Pair       │ DEX        │ Price      │ Liquidity │ Spread │ Status ║
║────────────┼────────────┼────────────┼───────────┼────────┼────────║
║ FXRP/USDT0 │ Blazeswap  │ $0.004800  │ $98.75K   │ +6.67% │   ✓    ║
║            │ Pangolin   │ $0.004600  │ $210.50K  │   -    │   ✓    ║
║            │ SparkDEX   │ $0.004500  │ $125.00K  │ -6.67% │   ✓    ║
║────────────┼────────────┼────────────┼───────────┼────────┼────────║
║ FXRP/FLR   │ Blazeswap  │ 0.1280     │ $32.50K   │ +2.40% │   ✓    ║
║            │ Enosys     │ 0.1265     │ $28.75K   │   -    │   ✓    ║
║            │ SparkDEX   │ 0.1250     │ $45.00K   │ -2.40% │   ✓    ║
╚═══════════════════════════════════════════════════════════╝
```

### Status Panel

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Best Opportunity: +6.67% (Blazeswap → SparkDEX)          ┃
┃ DEX Status: 4/4 online                                   ┃
┃ Last Update: 2025-11-23 00:15:32                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Color Scheme

- **Cyan**: Headers, pair names, timestamps
- **Yellow**: DEX names, warnings
- **Green**: Positive spreads, success, online status
- **Red**: Negative spreads, errors, offline status
- **White**: Price values, general text
- **Dim**: Unavailable data, placeholders

## Implementation Details

### Price Formatting

Prices are formatted based on magnitude:
- `< $0.01`: 6 decimal places (e.g., `$0.004500`)
- `< $1.00`: 4 decimal places (e.g., `$0.4500`)
- `>= $1.00`: 4 decimal places, no $ (e.g., `125.4500`)

### Liquidity Formatting

Liquidity is formatted with suffixes:
- `>= $1M`: Millions (e.g., `$2.5M`)
- `>= $1K`: Thousands (e.g., `$125.5K`)
- `< $1K`: Full value (e.g., `$875.25`)

### Spread Calculation

For each pair, spreads are calculated as:
```python
spread_percent = ((max_price - min_price) / min_price) * 100
```

- Highest price shows positive spread (green)
- Lowest price shows negative spread (red)
- Middle prices show "-" (no spread indicator)

### Table Organization

- Pairs are sorted alphabetically
- Within each pair, DEXes are sorted by price (descending)
- Pair name only shown on first row for each pair
- Lines separate different pairs for clarity

## Testing

A comprehensive test script is provided: `test_output.py`

### Running the Test

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
python test_output.py
```

The test demonstrates:
1. Static display with sample data
2. Live-updating display (10 seconds)
3. Message types (info, success, warning, error)
4. Error handling with failed prices

## Integration with Monitor

The output handler is designed to integrate with the Monitor Manager:

```python
# In monitor manager
from flare_monitor.output import ConsoleOutputHandler

class MonitorManager:
    def __init__(self):
        self.output = ConsoleOutputHandler()

    async def start(self):
        # Start live display
        self.output.start_live_display()

        try:
            # Monitor loop
            while True:
                # Fetch prices from DEXes
                prices = await self.fetch_all_prices()

                # Update display
                for price in prices:
                    self.output.update_price(price)

                # Calculate spreads
                spreads = self.calculate_spreads(prices)
                for spread in spreads:
                    self.output.update_spread(spread)

                # Update display
                self.output.update_live_display()

                await asyncio.sleep(poll_interval)
        finally:
            self.output.stop_live_display()
```

## Dependencies

- **rich >= 13.0.0**: Terminal formatting and tables
- **pydantic >= 2.0.0**: Data validation (for models)

## Performance Considerations

1. **Refresh Rate**: Live display refreshes at 2Hz (twice per second)
2. **Data Updates**: Call `update_live_display()` after batch updates, not after each individual update
3. **Terminal Size**: Table layout adapts to terminal size automatically
4. **Memory**: Keeps only latest price for each DEX/pair combination

## Future Enhancements

Potential improvements for future versions:

1. **Filtering**: Allow filtering by pair or DEX
2. **Sorting**: Custom sort options (by spread, liquidity, etc.)
3. **History**: Show price change over time
4. **Charts**: Terminal-based sparkline charts
5. **Alerts**: Visual/audio alerts for significant opportunities
6. **Export**: Save current state to file
7. **Configuration**: Customizable colors and layout

## Troubleshooting

### Display Issues

**Problem**: Table doesn't render correctly
- **Solution**: Ensure terminal supports unicode and has sufficient width (80+ columns)

**Problem**: Colors not showing
- **Solution**: Check terminal supports ANSI colors, or set `TERM=xterm-256color`

**Problem**: Live display flickers
- **Solution**: Reduce update frequency or use `render()` instead of live mode

### Data Issues

**Problem**: Prices showing as "N/A"
- **Solution**: Check that Price objects have `price` field set (not None)

**Problem**: Spreads not calculating
- **Solution**: Ensure multiple prices exist for same pair

**Problem**: Status always showing "offline"
- **Solution**: Call `update_dex_status()` with correct status data

## Code Style

The module follows Python best practices:
- Type hints for all function signatures
- Comprehensive docstrings (Google style)
- PEP 8 compliant formatting
- Modular design with single responsibility methods

## License

Part of the Flare Monitor project. See main repository for license information.
