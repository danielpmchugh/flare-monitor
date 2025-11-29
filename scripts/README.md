# Flare Monitor Scripts

This directory contains utility scripts for testing and development.

## Available Scripts

### test_rpc.py

Tests connectivity to Flare Network RPC endpoints and measures performance.

**Purpose:**
- Verify RPC endpoints are reachable and functional
- Measure response times (sync and async)
- Test concurrent request handling
- Validate chain ID and network data
- Generate performance recommendations

**Usage:**
```bash
# Using virtual environment
./venv/bin/python scripts/test_rpc.py

# Or with activated venv
python scripts/test_rpc.py
```

**Features:**
- Tests multiple RPC endpoints in parallel
- Measures average, min, and max response times
- Tests both synchronous and asynchronous connections
- Validates chain ID (should be 14 for Flare mainnet)
- Performs concurrent load testing (10 simultaneous requests)
- Generates detailed recommendations for production use
- Color-coded rich console output

**Sample Output:**
```
RPC Endpoint Performance
┌────────────────────┬─────────┬─────────┬────────┬─────────┬────────┬─────────┐
│ Endpoint           │ Status  │ Chain   │ Latest │ Avg     │ Avg    │ Success │
│                    │         │ ID      │ Block  │ Sync(s) │ Async  │ Rate    │
├────────────────────┼─────────┼─────────┼────────┼─────────┼────────┼─────────┤
│ Public RPC         │ ✓       │ 14      │ 51,... │ 0.247   │ 0.427  │ 100.0%  │
│ Ankr Flare RPC     │ ✓       │ 14      │ 51,... │ 0.283   │ 0.490  │ 100.0%  │
│ Official Flare RPC │ ✓       │ 14      │ 51,... │ 0.656   │ 0.888  │ 100.0%  │
└────────────────────┴─────────┴─────────┴────────┴─────────┴────────┴─────────┘
```

**Documentation:**
See `docs/research/rpc-testing.md` for detailed test results and analysis.

**Requirements:**
- web3>=6.0.0
- aiohttp>=3.9.0
- rich>=13.0.0

All requirements are included in `requirements.txt`.

## Adding New Scripts

When adding new utility scripts:

1. Place in the `scripts/` directory
2. Add shebang: `#!/usr/bin/env python3`
3. Include docstring with description and usage
4. Make executable: `chmod +x scripts/your_script.py`
5. Update this README with script documentation
6. Add type hints for better code quality
7. Include error handling and informative output
