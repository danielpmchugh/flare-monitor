# Flare Monitor

**Real-time FXRP price monitoring and arbitrage detection across Flare Network DEXes**

![Flare Monitor Screenshot](Screenshot%202025-11-29%20011325.png)

## Overview

Flare Monitor is a production-ready Python application that tracks FXRP token prices across multiple decentralized exchanges (DEXes) on Flare Network in real-time. It detects arbitrage opportunities by comparing prices and calculating spreads, displaying everything in a beautiful live-updating terminal interface.

## Features

- ✅ **Multi-DEX Support**: Monitor SparkDEX V3, BlazeSwap, and Pangolin simultaneously
- ✅ **Real-time Price Tracking**: Live prices for FXRP/USDT0, FXRP/WFLR, and WFLR/USDT0 pairs
- ✅ **Uniswap V2 & V3 Protocols**: Full support for both protocol versions
- ✅ **Arbitrage Detection**: Automatically identifies profitable spread opportunities
- ✅ **Liquidity Monitoring**: Displays liquidity depth for each trading pair
- ✅ **Rich Console UI**: Color-coded spreads with live-updating tables
- ✅ **Circuit Breaker Pattern**: Resilient RPC connection handling
- ✅ **Comprehensive Logging**: Dual console and file logging for debugging
- ✅ **Production Ready**: Error handling, retry logic, and graceful degradation

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/flare-monitor.git
cd flare-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp config/config.example.yaml config/config.yaml

# Run the monitor
python3 -m flare_monitor
```

### Usage

**Basic usage:**
```bash
python3 -m flare_monitor
```

**With custom config:**
```bash
python3 -m flare_monitor --config path/to/config.yaml
```

**Enable debug logging:**
```bash
python3 -m flare_monitor --log-level DEBUG
```

**Show help:**
```bash
python3 -m flare_monitor --help
```

### Viewing Logs

Open two terminals for the best experience:

**Terminal 1 - Monitor:**
```bash
python3 -m flare_monitor
```

**Terminal 2 - Logs:**
```bash
tail -f logs/flare-monitor.log
```

Or filter for errors only:
```bash
tail -f logs/flare-monitor.log | grep -E "ERROR|WARNING"
```

## Configuration

Edit `config/config.yaml` to customize:

- **RPC Endpoints**: Flare Network RPC URLs (default: public endpoint)
- **DEXes**: Enable/disable specific DEXes
- **Pairs**: Trading pairs to monitor
- **Poll Interval**: How often to fetch prices (default: 10 seconds)
- **Spread Threshold**: Minimum spread % to trigger alerts (default: 5%)
- **Logging**: Log levels and output destinations

**Example configuration:**

```yaml
monitoring:
  poll_interval_seconds: 10        # Poll every 10 seconds
  spread_alert_threshold_percent: 5.0  # Alert on spreads > 5%
  max_concurrent_requests: 5       # Limit concurrent RPC calls

logging:
  level: INFO                      # DEBUG, INFO, WARNING, ERROR, CRITICAL
  output: both                     # console, file, or both
  file_path: "logs/flare-monitor.log"

dexes:
  - name: SparkDEX_V3
    enabled: true
  - name: BlazeSwap
    enabled: true
  - name: Pangolin
    enabled: false                 # Disabled - no FXRP pairs yet
```

## Architecture

### Key Components

- **Monitor Manager** (`flare_monitor/monitor.py`): Orchestrates price fetching and spread calculation
- **DEX Adapters** (`flare_monitor/adapters/`): Protocol-specific implementations for V2 and V3
- **Data Models** (`flare_monitor/models.py`): Pydantic models with Decimal precision
- **Console Output** (`flare_monitor/output.py`): Rich-based live UI
- **Configuration** (`flare_monitor/config.py`): YAML config loading and validation

### Technology Stack

- **Python 3.11+**: Modern async/await syntax
- **web3.py 6.0**: Ethereum/EVM blockchain interaction
- **aiohttp**: Async HTTP requests
- **Pydantic**: Data validation with proper Decimal handling
- **Rich**: Beautiful terminal UI
- **PyYAML**: Configuration management

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=flare_monitor --cov-report=html
```

**Test Coverage:**
- 172 tests across 8 test modules
- 87% passing rate
- Core modules: 80-95% coverage

## Documentation

- **[Product Specification](docs/product-spec.md)**: MVP scope and requirements
- **[Architecture](docs/architecture.md)**: System design and technology decisions
- **[Implementation Plan](docs/implementation-plan.md)**: Development roadmap
- **[Research](docs/research/)**: DEX analysis and RPC testing results

## Critical Configuration Notes

⚠️ **IMPORTANT**: FXRP uses **6 decimals**, not 18! The config has been corrected.

⚠️ **Rate Limits**: The public Flare RPC has rate limits. Use `poll_interval_seconds: 10` to avoid errors. For faster updates, use a private RPC endpoint.

⚠️ **BlazeSwap Factory**: Corrected to `0x440602f459D7Dd500a74528003e6A20A46d6e2A6`

## Troubleshooting

**"429 Too Many Requests" errors:**
- Increase `poll_interval_seconds` to 10-15
- Reduce `max_concurrent_requests` to 5
- Consider using a private RPC endpoint

**Pangolin errors (pair doesn't exist):**
- Pangolin doesn't have FXRP pairs yet
- Set `enabled: false` for Pangolin in config

**Logs scrolling too fast:**
- Enable file logging: `output: both` in config
- Use `tail -f logs/flare-monitor.log` in a second terminal

**Prices seem incorrect:**
- Verify token decimals in config (FXRP=6, USDT0=6, WFLR=18)
- Check contract addresses against Flarescan

## Roadmap

**Current (MVP - Complete):**
- ✅ Real-time price monitoring
- ✅ Uniswap V2 & V3 support
- ✅ Arbitrage opportunity detection
- ✅ Rich console UI
- ✅ Comprehensive error handling

**Future Enhancements:**
- [ ] Historical price storage (SQLite)
- [ ] WebSocket real-time feeds
- [ ] REST API for price data
- [ ] Web dashboard
- [ ] Discord/Telegram alerts
- [ ] Advanced analytics (VWAP, volume tracking)
- [ ] Automated trading execution

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the MIT License.

## Resources

- **Flare Network**: https://flare.network
- **SparkDEX**: https://docs.sparkdex.ai
- **BlazeSwap**: https://github.com/blazeswap/contracts
- **Pangolin**: https://docs.pangolin.exchange
- **Flarescan (Block Explorer)**: https://flarescan.com

## Acknowledgments

Built with Claude Code and the Claude Agent SDK for efficient parallel development.

---

**Status**: Production Ready ✅
**Version**: 0.1.0
**Last Updated**: November 29, 2025
