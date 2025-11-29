# Flare Monitor - Architecture Document

## 1. Overview

Flare Monitor is a single-process, asynchronous Python application that monitors FXRP token prices across multiple DEXes on the Flare Network and calculates arbitrage spreads in real-time.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Flare Monitor Application                  │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Config    │───▶│   Monitor    │───▶│  Spread   │ │
│  │   Loader    │    │   Manager    │    │Calculator │ │
│  └─────────────┘    └───────┬──────┘    └─────┬─────┘ │
│                             │                  │       │
│                      ┌──────▼──────────────────▼─────┐ │
│                      │    Console Output Handler     │ │
│                      └──────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Concurrent DEX     │
                    │  Monitor Tasks      │
                    │  ├── SparkDEX       │
                    │  ├── Blazeswap      │
                    │  ├── Pangolin       │
                    │  └── Enosys         │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Flare Network      │
                    │  RPC Endpoint       │
                    └─────────────────────┘
```

### Key Architectural Principles

1. **Simplicity**: Single application, minimal dependencies, easy to understand
2. **Concurrency**: Async/await for parallel DEX monitoring without threading complexity
3. **Configuration-Driven**: DEX endpoints, pairs, and thresholds defined in config files
4. **Extensibility**: Plugin-style DEX adapters for easy addition of new exchanges
5. **Fail-Safe**: Individual DEX failures don't crash the entire application

### Design Goals

- Sub-second price updates for active trading pairs
- Easy addition of new DEXes and trading pairs
- Clear, readable console output
- Low resource consumption
- Simple deployment (single Python script)

### Constraints

- Local development and execution initially
- Console-only output (no web interface in MVP)
- Polling-based updates (WebSocket enhancement deferred)
- No persistent storage (future enhancement)

## 2. Architectural Decisions

### ADR-001: Python with Asyncio

**Decision**: Use Python 3.11+ with asyncio for the implementation

**Rationale**:
- Strong Web3 ecosystem (`web3.py`)
- Native async/await support for concurrent monitoring
- Rich libraries for console output and data processing
- Fast development iteration
- Lower barrier to entry for contributors

**Alternatives Considered**:
- Node.js/TypeScript: Good Web3 support but less familiar for data processing
- Go: Better performance but steeper learning curve, overkill for MVP
- Rust: Maximum performance but slow development, premature optimization

**Trade-offs**:
- Python is slower than compiled languages but fast enough for this use case
- GIL limitations not relevant (I/O-bound, not CPU-bound)
- Async debugging can be tricky but manageable with proper logging

---

### ADR-002: Direct RPC Calls to DEX Smart Contracts

**Decision**: Query DEX liquidity pools directly via Flare RPC using smart contract ABIs

**Rationale**:
- Most Flare DEXes are Uniswap V2/V3 forks (standard interfaces)
- No dependency on third-party APIs or indexers
- Most reliable and decentralized approach
- Full control over query frequency and data format

**Alternatives Considered**:
- DEX-specific APIs: Not all DEXes provide them, creates inconsistency
- The Graph/subgraphs: May not exist for all Flare DEXes
- Centralized data providers: Introduces trust dependency

**Trade-offs**:
- Slightly more complex (need to handle ABIs and encoding)
- Must manage RPC rate limits
- Need to understand each DEX's contract structure

---

### ADR-003: Polling-Based Updates

**Decision**: Use polling (periodic queries) rather than event-driven updates

**Rationale**:
- Simpler implementation for MVP
- Predictable resource usage
- Easier to reason about and debug
- Good enough for sub-second updates

**Alternatives Considered**:
- WebSocket subscriptions: Better for real-time but more complex
- Event listening: Requires running a local node or complex event filtering

**Trade-offs**:
- Slightly higher latency (up to poll interval)
- More RPC calls than event-driven approach
- Can be enhanced to WebSocket later without architectural changes

---

### ADR-004: Configuration Files over Database

**Decision**: Use YAML/JSON configuration files for DEX endpoints, trading pairs, and settings

**Rationale**:
- Simple to edit and version control
- No database setup required
- Easy to understand and modify
- Perfect for MVP scope

**Alternatives Considered**:
- Environment variables: Too limited for complex DEX configurations
- SQLite database: Overkill for configuration data
- Hard-coded: Inflexible, hard to modify

**Trade-offs**:
- Changes require application restart
- Not suitable for runtime configuration updates
- Fine for current requirements

---

### ADR-005: Monolithic Application Structure

**Decision**: Single Python application with modular internal structure

**Rationale**:
- Simplest deployment model
- Easier development and debugging
- No inter-process communication overhead
- Can refactor to services later if needed

**Alternatives Considered**:
- Microservices: Over-engineered for current scope
- Separate monitor and calculator: Adds complexity without clear benefit

**Trade-offs**:
- All components share same process lifecycle
- Harder to scale horizontally (not a current requirement)
- Good fit for MVP, can evolve later

## 3. Technology Stack

### Core Language & Runtime
- **Python 3.11+**: Primary language
  - Type hints for better code quality
  - Improved asyncio performance
  - Pattern matching for cleaner code

### Key Libraries

**Blockchain Interaction**
- **web3.py (v6+)**: Ethereum/EVM blockchain interaction
  - Standard for Python Web3 development
  - Full support for contract calls and ABI encoding
  - Async provider support

**Async & Concurrency**
- **asyncio**: Built-in async runtime
- **aiohttp**: Async HTTP client for RPC calls
  - Better performance than synchronous requests
  - Connection pooling built-in

**Configuration**
- **PyYAML**: YAML parsing for configuration files
- **pydantic**: Data validation and settings management
  - Type validation for configs
  - Clear error messages

**Console Output**
- **rich**: Beautiful terminal formatting
  - Live updating tables
  - Color coding and formatting
  - Progress indicators

**Development Tools**
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **black**: Code formatting
- **mypy**: Static type checking
- **ruff**: Fast Python linter

### External Services
- **Flare RPC Endpoint**: Public or private RPC provider
  - Public: Free but rate-limited
  - Private: Better performance, paid
  - Fallback endpoints for reliability

## 4. System Components

### 4.1 Config Loader
**Responsibility**: Load and validate configuration from files

**Inputs**: `config.yaml` file
**Outputs**: Validated configuration objects
**Key Functions**:
- Parse YAML configuration
- Validate DEX endpoints and contract addresses
- Load trading pair specifications
- Provide default values for optional settings

---

### 4.2 DEX Adapter (Interface)
**Responsibility**: Abstract interface for DEX price fetching

**Key Functions**:
- `async get_price(pair: TradingPair) -> Price`
- `async get_liquidity(pair: TradingPair) -> Liquidity`
- `get_dex_name() -> str`

**Implementations**:
- `UniswapV2Adapter`: For UniswapV2-style DEXes (SparkDEX, Blazeswap)
- `UniswapV3Adapter`: For UniswapV3-style DEXes (if applicable)
- Each adapter knows how to read reserves/prices from its DEX type

---

### 4.3 Monitor Manager
**Responsibility**: Orchestrate concurrent monitoring of all DEX/pair combinations

**Key Functions**:
- Initialize DEX adapters from configuration
- Spawn async tasks for each DEX/pair
- Collect price updates from all sources
- Handle individual DEX failures gracefully
- Emit price updates to calculator

**Data Flow**:
```
Config → Create Adapters → Spawn Tasks → Fetch Prices → Emit Updates
```

---

### 4.4 Spread Calculator
**Responsibility**: Calculate price spreads and identify arbitrage opportunities

**Inputs**: Price updates from multiple DEXes
**Outputs**: Spread calculations and alerts

**Key Functions**:
- Track latest price from each DEX for each pair
- Calculate spreads when prices update
- Identify max spread opportunities
- Apply threshold filtering
- Trigger alerts for significant spreads

**Calculation Logic**:
```
spread_percent = ((high_price - low_price) / low_price) * 100
profit_after_fees = spread_percent - (gas_fees + slippage_estimate)
```

---

### 4.5 Console Output Handler
**Responsibility**: Display real-time information in terminal

**Features**:
- Live-updating price table (using `rich.table`)
- Color-coded spreads (green for opportunities, red for losses)
- Timestamp of last update
- DEX availability status
- Alert highlights

**Display Layout**:
```
╔═══════════════════════════════════════════════════════╗
║         FXRP Price Monitor - Flare Network           ║
╠═══════════════════════════════════════════════════════╣
║ Pair          DEX         Price      Spread    Status ║
║ FXRP/USDT0    SparkDEX    $0.0045    -        ✓      ║
║ FXRP/USDT0    Blazeswap   $0.0048    +6.67%   ✓      ║
║ FXRP/USDT0    Pangolin    $0.0046    -        ✓      ║
║ FXRP/FLR      SparkDEX    0.125      -        ✓      ║
╠═══════════════════════════════════════════════════════╣
║ Best Opportunity: +6.67% (Blazeswap → SparkDEX)      ║
║ Last Update: 2025-11-23 00:15:32                     ║
╚═══════════════════════════════════════════════════════╝
```

## 5. Data Architecture

### 5.1 Core Data Models

```python
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class TradingPair(BaseModel):
    """Represents a trading pair"""
    base_token: str        # e.g., "FXRP"
    quote_token: str       # e.g., "USDT0"

class TokenAddress(BaseModel):
    """Token contract address on Flare"""
    address: str
    decimals: int
    symbol: str

class Price(BaseModel):
    """Price data from a DEX"""
    pair: TradingPair
    dex_name: str
    price: Decimal
    liquidity: Decimal     # Total liquidity in pool
    timestamp: datetime

class Spread(BaseModel):
    """Calculated spread between DEXes"""
    pair: TradingPair
    low_dex: str
    high_dex: str
    low_price: Decimal
    high_price: Decimal
    spread_percent: Decimal
    timestamp: datetime
```

### 5.2 Configuration Schema

```yaml
# config.yaml structure
flare:
  rpc_endpoints:
    - https://flare-api.flare.network/ext/C/rpc
    - https://flare.public-rpc.com
  chain_id: 14

dexes:
  - name: SparkDEX
    type: uniswap_v2
    factory_address: "0x..."
    router_address: "0x..."

  - name: Blazeswap
    type: uniswap_v2
    factory_address: "0x..."
    router_address: "0x..."

tokens:
  FXRP:
    address: "0x..."
    decimals: 18
  USDT0:
    address: "0x..."
    decimals: 6
  FLR:
    address: "0x..."
    decimals: 18

pairs:
  - base: FXRP
    quote: USDT0
  - base: FXRP
    quote: FLR

monitoring:
  poll_interval_seconds: 2
  spread_alert_threshold_percent: 5.0
  max_concurrent_requests: 10
```

### 5.3 In-Memory State

No persistent storage in MVP. Application maintains:
- Latest price for each DEX/pair combination
- Current spread calculations
- DEX availability status

All state is ephemeral and rebuilt on restart.

## 6. Integration Architecture

### 6.1 Flare Network RPC Integration

**Connection Management**:
- Connection pool with configurable size
- Automatic retry with exponential backoff
- Fallback to secondary RPC endpoints on failure
- Request timeout (5 seconds default)

**Rate Limiting**:
- Respect RPC provider limits
- Configurable delay between requests
- Batch requests where possible

**Error Handling**:
```python
async def fetch_with_retry(rpc_call, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await rpc_call()
        except (TimeoutError, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 6.2 DEX Smart Contract Interaction

**Uniswap V2 Pattern** (SparkDEX, Blazeswap, etc.):
```python
# Get pair address from factory
pair_address = factory.functions.getPair(token0, token1).call()

# Get reserves from pair contract
reserves = pair.functions.getReserves().call()
reserve0, reserve1, timestamp = reserves

# Calculate price
price = reserve1 / reserve0  # Adjusted for decimals
```

**Contract ABI Management**:
- Standard Uniswap V2/V3 ABIs stored in `abis/` directory
- Load once at startup
- Reuse contract instances across calls

## 7. Configuration Management

### 7.1 Configuration Files

**Location**: `config/config.yaml`
**Format**: YAML for readability
**Validation**: Pydantic models ensure correctness

### 7.2 Environment Variables

```bash
# Optional overrides
FLARE_RPC_URL=https://custom-rpc.example.com
LOG_LEVEL=DEBUG
POLL_INTERVAL=1
```

### 7.3 Secrets Management

For MVP:
- RPC API keys (if using private endpoints) in `.env` file
- `.env` in `.gitignore`
- Load with `python-dotenv`

Future: Consider vault solutions for production

## 8. Deployment Architecture

### 8.1 Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python -m flare_monitor
```

### 8.2 Process Management

For long-running monitoring:
- **systemd** (Linux): Service unit file
- **PM2** (cross-platform): Process manager
- **screen/tmux**: Simple terminal multiplexer
- **Docker**: Containerized deployment (future)

### 8.3 Resource Requirements

**Minimum**:
- CPU: 1 core
- RAM: 256 MB
- Network: Stable internet connection
- Disk: 100 MB

**Recommended**:
- CPU: 2 cores (for responsive UI)
- RAM: 512 MB
- Network: Low latency connection
- Disk: 1 GB (for logs)

## 9. Observability

### 9.1 Logging Strategy

**Levels**:
- **DEBUG**: RPC calls, price updates, calculations
- **INFO**: DEX status changes, spread alerts
- **WARNING**: Failed RPC calls, degraded performance
- **ERROR**: Unhandled exceptions, critical failures

**Format**:
```
2025-11-23 00:15:32 [INFO] SparkDEX: FXRP/USDT0 = $0.0045
2025-11-23 00:15:32 [WARNING] Blazeswap: RPC timeout, retrying...
2025-11-23 00:15:33 [INFO] Spread Alert: +6.7% (Blazeswap → SparkDEX)
```

**Output**:
- Console for development
- Rotating file logs for production (`logs/flare-monitor.log`)
- Configurable verbosity

### 9.2 Metrics

Tracked internally (console display):
- Successful/failed RPC calls per DEX
- Average response time per DEX
- Price update frequency
- Spread opportunity count

Future: Export to Prometheus/Grafana

### 9.3 Debugging

- Rich console output with color coding
- Detailed error messages with context
- Async task debugging with `asyncio` debug mode
- RPC request/response logging at DEBUG level

## 10. Development Workflow

### 10.1 Project Structure

```
flare-monitor/
├── config/
│   ├── config.yaml           # Main configuration
│   └── config.example.yaml   # Example configuration
├── flare_monitor/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── config.py            # Config loading
│   ├── models.py            # Data models
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py          # DEX adapter interface
│   │   ├── uniswap_v2.py    # Uniswap V2 adapter
│   │   └── uniswap_v3.py    # Uniswap V3 adapter
│   ├── monitor.py           # Monitor manager
│   ├── calculator.py        # Spread calculator
│   └── output.py            # Console output
├── abis/
│   ├── uniswap_v2_factory.json
│   ├── uniswap_v2_pair.json
│   └── erc20.json
├── tests/
│   ├── test_adapters.py
│   ├── test_calculator.py
│   └── test_monitor.py
├── docs/
│   ├── product-spec.md
│   └── architecture.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml           # Project metadata
└── README.md
```

### 10.2 Development Process

1. **Setup**: Clone repo, create venv, install dependencies
2. **Configure**: Copy `config.example.yaml` to `config.yaml`, edit as needed
3. **Develop**: Write code with type hints, follow Black formatting
4. **Test**: Run `pytest` for unit tests
5. **Run**: `python -m flare_monitor`
6. **Lint**: `ruff check .` and `mypy flare_monitor/`

### 10.3 Testing Strategy

**Unit Tests**:
- DEX adapter logic (mocked RPC calls)
- Spread calculations
- Configuration validation

**Integration Tests**:
- Live RPC calls (marked as slow, skipped by default)
- End-to-end monitoring flow

**Manual Testing**:
- Run against live Flare network
- Verify price accuracy against DEX UIs
- Test error scenarios (RPC failures, invalid pairs)

### 10.4 Dependencies

**Core** (`requirements.txt`):
```
web3>=6.0.0
aiohttp>=3.9.0
pydantic>=2.0.0
PyYAML>=6.0
rich>=13.0.0
python-dotenv>=1.0.0
```

**Development** (`requirements-dev.txt`):
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
mypy>=1.5.0
ruff>=0.1.0
```

## 11. Security Considerations

### 11.1 RPC Endpoint Security
- Use HTTPS for all RPC connections
- Validate SSL certificates
- Keep RPC API keys in environment variables
- Rotate API keys periodically

### 11.2 Smart Contract Interaction
- Read-only operations (no transactions signed)
- Validate contract addresses against known DEX deployments
- ABI checksums to prevent tampering

### 11.3 Input Validation
- Validate all configuration inputs with Pydantic
- Sanitize user-provided addresses
- Check token decimals to prevent calculation errors

### 11.4 Dependencies
- Regular `pip audit` for vulnerability scanning
- Pin dependencies to specific versions
- Review dependency updates before upgrading

### 11.5 No Private Keys
- This is a monitoring tool, NOT a trading bot
- No wallet integration
- No transaction signing
- Read-only blockchain access

## 12. Future Considerations

### 12.1 Scalability Paths

**Horizontal Scaling**:
- Split DEXes across multiple instances
- Use message queue (Redis pub/sub) for price sharing
- Load balancer for API requests (when API added)

**Vertical Scaling**:
- Current architecture handles 10+ DEXes on single core
- Bottleneck will be RPC rate limits, not CPU/memory

### 12.2 Planned Architectural Evolution

**Phase 2 - Persistence**:
- Add SQLite for historical price storage
- Time-series optimization for analytics
- Data retention policies

**Phase 3 - Advanced Features**:
- WebSocket for real-time price updates
- REST API for external access
- Web dashboard (separate frontend)

**Phase 4 - Production Hardening**:
- Replace SQLite with PostgreSQL/TimescaleDB
- Add Redis for caching and pub/sub
- Prometheus metrics export
- Grafana dashboards
- Alert webhooks (Discord, Telegram, Slack)

### 12.3 Technical Debt

**Known Limitations**:
- Polling vs. event-driven (acceptable for MVP)
- No persistent storage (future enhancement)
- Console-only output (web UI later)
- Manual DEX configuration (auto-discovery possible)

**Refactoring Candidates**:
- Extract RPC client to separate module as it grows
- Consider strategy pattern for different DEX types
- Abstract output layer for multiple targets (console, API, websocket)

### 12.4 Migration Path

The current architecture supports clean migration:
1. **Add API**: FastAPI alongside existing monitor (Phase 3)
2. **Add Storage**: SQLite integration without changing core logic (Phase 2)
3. **Add Services**: Split into microservices when needed (Phase 4)
4. **Add WebSocket**: Replace polling in DEX adapters (Phase 3)

Each enhancement is additive and doesn't require full rewrite.

---

## Summary

This architecture provides a solid foundation for the Flare Monitor MVP:
- Simple, focused, and easy to understand
- Async-first for efficient concurrent monitoring
- Extensible design for adding DEXes and features
- Clear migration path to more sophisticated architecture
- Balances MVP speed with long-term viability

The monolithic async Python approach is the right choice for getting started quickly while learning the Flare DEX ecosystem and validating the concept before committing to more complex architectures.
