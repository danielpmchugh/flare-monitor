# Flare Monitor - Implementation Plan

## Current State

**Existing Assets**:
- ✅ Product specification document (updated with MVP scope)
- ✅ Architecture document
- ✅ Project repository initialized
- ✅ README.md placeholder

**Phase 0 Progress** (Foundation & Research): ✅ **COMPLETE**
- ✅ Task 1: Flare DEX research complete (`docs/research/flare-dexes.md`)
- ✅ Task 2: Python project structure created (all directories and __init__.py files)
- ✅ Task 3: Dependencies installed (requirements.txt, pyproject.toml, venv working)
- ✅ Task 4: Configuration schema created (`config/config.example.yaml`)
- ✅ Task 5: RPC connectivity tested (`docs/research/rpc-testing.md`)
- ✅ Task 6: Uniswap V2 ABIs collected (`abis/*.json`)

**Additional Work**:
- ✅ Spread calculator implemented early (Task 11 - out of sequence but functional)

**Status**: Phase 0 is 100% complete (6/6 tasks). Ready to start Phase 1 (Core Components).

---

## Unknowns & Research Needs - ✅ ALL RESOLVED

All unknowns have been researched and documented:

### 🔍 DEX Discovery & Verification - ✅ **COMPLETE**
- ✅ **All 4 DEXes verified** live on Flare Network (SparkDEX, BlazeSwap, Pangolin, Enosys)
- ✅ **Active with liquidity** - SparkDEX leads with $5.2M daily volume
- ✅ **All are Uniswap V2 forks** - Standard adapter will work for all
- ✅ **Contract addresses documented** - All verified on Flarescan
- **Source**: `docs/research/flare-dexes.md`

### 🪙 Token Addresses - ✅ **COMPLETE**
- ✅ **FXRP**: `0xad552a648c74d49e10027ab8a618a3ad4901c5be` (18 decimals)
- ✅ **USDT0**: `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` (6 decimals, LayerZero OFT)
- ✅ **WFLR**: `0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d` (18 decimals, wrapped native)
- **Source**: `docs/research/flare-dexes.md`, `config/config.example.yaml`

### 🌐 RPC Infrastructure - ✅ **COMPLETE**
- ✅ **3 working endpoints** tested: Public RPC (fastest 0.427s), Ankr, Official Flare
- ✅ **No rate limiting** observed during testing with 10 concurrent requests
- ✅ **Public RPC sufficient** for MVP - No paid provider needed
- ✅ **Response times excellent** - Sub-second async calls
- **Source**: `docs/research/rpc-testing.md`, `scripts/test_rpc.py`

### ⛽ Gas Economics - ✅ **DOCUMENTED**
- ✅ **Current gas price**: 25 Gwei (consistent across all RPCs)
- ✅ **Gas costs for swaps**: To be measured during Task 10 (Uniswap V2 adapter)
- ✅ **Flare gas is low** compared to Ethereum (EVM-compatible chain)
- **Note**: For monitoring (read-only), gas is not a concern

### 📊 Liquidity & Pair Availability - ✅ **COMPLETE**
- ✅ **FXRP/USDT0**: Available on SparkDEX, BlazeSwap, Enosys (primary pair)
- ✅ **FXRP/WFLR**: Available on SparkDEX, BlazeSwap (secondary pair)
- ✅ **WFLR/USDT0**: Available for triangular arbitrage calculations
- ✅ **Total Flare TVL**: ~$170M across all DEXes
- **Source**: `docs/research/flare-dexes.md`

**All research complete. No blockers remaining for implementation.**

---

## Phases

### Phase 0: Foundation & Research
**Goal**: Set up project infrastructure and gather all required information to build confidently

**Completion Criteria**:
- Project structure created
- Dependencies installed and working
- All DEX contract addresses documented
- Can successfully call Flare RPC endpoint
- Configuration schema defined

#### Tasks

1. **Research Flare Network DEXes** ✅ COMPLETE
   - Description: Identify and document all active DEXes on Flare Network with contract addresses, types, and characteristics
   - Dependencies: None
   - Outputs: DEX research document with addresses and specifications (`docs/research/flare-dexes.md`)
   - Status: Complete - All 4 DEXes documented (SparkDEX, BlazeSwap, Pangolin, Enosys) with contract addresses

2. **Set up Python project structure** ✅ COMPLETE
   - Description: Create directory structure, virtual environment, pyproject.toml, and initial module layout
   - Dependencies: None
   - Outputs: Complete project skeleton matching architecture doc structure
   - Status: Complete - All directories created, __init__.py files in place, .gitignore and .env.example configured

3. **Define and install dependencies** ✅ COMPLETE
   - Description: Create requirements.txt with web3.py, aiohttp, pydantic, rich, etc.
   - Dependencies: Task 2 (project structure)
   - Outputs: requirements.txt, requirements-dev.txt, working virtual environment
   - Status: Complete - All dependencies installed in venv, pyproject.toml configured

4. **Create configuration schema** ✅ COMPLETE
   - Description: Design YAML configuration structure and create example config file
   - Dependencies: None (can use placeholder addresses)
   - Outputs: config.example.yaml with documented fields
   - Status: Complete - Comprehensive config with all 4 DEXes, 3 pairs, monitoring settings documented

5. **Test Flare RPC connectivity** ✅ COMPLETE
   - Description: Write simple script to connect to Flare RPC and query basic network info
   - Dependencies: Task 3 (dependencies installed)
   - Outputs: Verified working RPC endpoint(s), documented connection parameters
   - Status: Complete - All 3 RPC endpoints tested and working. Public RPC recommended as primary (0.427s avg response)

6. **Collect DEX ABIs** ✅ COMPLETE
   - Description: Gather Uniswap V2 ABIs (factory, router, pair, ERC20) and store in abis/ directory
   - Dependencies: Task 1 (know which ABIs we need)
   - Outputs: JSON ABI files in abis/ directory
   - Status: Complete - All 4 Uniswap V2 ABIs collected, validated, and documented

---

### Phase 1: Core Components
**Goal**: Build individual system components that can be developed and tested independently

**Completion Criteria**:
- All core modules implemented
- Unit tests passing for each component
- Components can be instantiated and called independently
- No integration yet (components work in isolation)

**Progress**: 5/7 tasks complete (71%)

#### Tasks

7. **Implement data models** ✅ COMPLETE
   - Description: Create Pydantic models for TradingPair, Price, Spread, TokenAddress, and configuration classes
   - Dependencies: Task 3 (pydantic installed)
   - Outputs: models.py with all data structures and validation
   - Status: Complete - 512 lines, 5 models with full Decimal precision and validation

8. **Implement configuration loader** ✅ COMPLETE
   - Description: Build system to load, validate, and parse YAML configuration files
   - Dependencies: Tasks 3 (PyYAML installed), 4 (config schema defined), 7 (config models)
   - Outputs: config.py module with loading and validation logic
   - Status: Complete - 697 lines, loads config.example.yaml successfully with comprehensive validation

9. **Create DEX adapter interface** ✅ COMPLETE
   - Description: Define abstract base class for DEX adapters with get_price(), get_liquidity() methods
   - Dependencies: Tasks 3 (dependencies), 7 (models)
   - Outputs: adapters/base.py with DEXAdapter abstract class
   - Status: Complete - 263 lines, abstract base class with retry logic and error handling built-in

10. **Implement Uniswap V2 adapter** 🔓 READY
    - Description: Build concrete adapter for Uniswap V2-style DEXes that reads reserves and calculates prices
    - Dependencies: Tasks 5 (RPC working ✅), 6 (ABIs available ✅), 7 (models ✅), 9 (base adapter ✅)
    - Outputs: adapters/uniswap_v2.py with working price fetching
    - Status: Ready - All dependencies met

11. **Build spread calculator** ✅ COMPLETE (Done Early)
    - Description: Create logic to compare prices from multiple DEXes and calculate spreads
    - Dependencies: Task 7 (models)
    - Outputs: calculator.py with spread calculation and opportunity detection
    - Status: Complete - Implemented early with comprehensive testing

12. **Create console output handler** ✅ COMPLETE
    - Description: Build Rich-based console UI for displaying prices and spreads in formatted tables
    - Dependencies: Task 7 (models)
    - Outputs: output.py with live-updating console display
    - Status: Complete - 426 lines, Rich-based UI with color coding and live updates

13. **Write unit tests for components** 🔓 READY
    - Description: Create pytest tests for models, config loader, calculator, and adapters (with mocked RPC)
    - Dependencies: Tasks 7-12 (components to test)
    - Outputs: Comprehensive test suite in tests/ directory
    - Parallelizable with: None (depends on all components)

---

### Phase 2: Integration & Orchestration
**Goal**: Connect components together into a working end-to-end system

**Completion Criteria**:
- Monitor manager coordinates all DEX adapters
- Prices flow from adapters → spread calculator → console output
- Application can run and display real-time data
- Error handling works gracefully
- Basic MVP is functional

#### Tasks

14. **Implement monitor manager** 🎯 🔗
    - Description: Build orchestration layer that creates DEX adapters, spawns async tasks, and coordinates price collection
    - Dependencies: Tasks 8 (config), 9 (adapter interface), 10 (concrete adapter)
    - Outputs: monitor.py with MonitorManager class
    - Parallelizable with: None (integrates multiple components)

15. **Create application entry point** 🔗
    - Description: Build __main__.py that initializes config, creates monitor manager, and starts the application loop
    - Dependencies: Tasks 8 (config), 12 (output), 14 (monitor manager)
    - Outputs: __main__.py with application lifecycle management
    - Parallelizable with: None (final integration)

16. **Add error handling and retry logic** 🔗
    - Description: Implement robust error handling for RPC failures, timeouts, and missing pairs
    - Dependencies: Tasks 10 (adapter), 14 (monitor manager)
    - Outputs: Graceful degradation when DEXes fail or RPC is unavailable
    - Parallelizable with: Task 17

17. **Add logging system** ⚡
    - Description: Set up Python logging with appropriate levels, formatting, and file output
    - Dependencies: None (can be done early)
    - Outputs: Comprehensive logging throughout application
    - Parallelizable with: Task 16

18. **Integration testing** 🔗
    - Description: Test end-to-end flow with live Flare RPC calls and real DEX data
    - Dependencies: Task 15 (working application)
    - Outputs: Validated working MVP against live network
    - Parallelizable with: None (final validation)

---

### Phase 3: Polish & Enhancement
**Goal**: Refine the MVP, fix edge cases, and prepare for real-world usage

**Completion Criteria**:
- Documentation complete
- Edge cases handled
- Performance optimized
- Ready for continuous operation
- User-friendly configuration

#### Tasks

19. **Update configuration with real addresses** 🔗
    - Description: Populate config.yaml with actual DEX addresses, tokens, and optimized settings
    - Dependencies: Task 1 (research complete), 18 (integration tested)
    - Outputs: Production-ready config.yaml
    - Parallelizable with: Tasks 20, 21

20. **Add more DEX adapters** ⚡
    - Description: Implement adapters for additional DEXes discovered during research
    - Dependencies: Tasks 1 (DEX research), 9 (adapter interface), 10 (example adapter)
    - Outputs: Additional adapter implementations for full DEX coverage
    - Parallelizable with: Tasks 19, 21, 22

21. **Optimize performance** ⚡
    - Description: Fine-tune polling intervals, connection pooling, and async task management
    - Dependencies: Task 18 (working system to benchmark)
    - Outputs: Improved response times and resource usage
    - Parallelizable with: Tasks 19, 20, 22

22. **Improve console output** ⚡
    - Description: Enhance UI with better formatting, color coding, sorting, and filtering options
    - Dependencies: Task 18 (working output)
    - Outputs: Polished user interface with helpful information display
    - Parallelizable with: Tasks 19, 20, 21

23. **Write user documentation** ⚡
    - Description: Update README with installation, configuration, and usage instructions
    - Dependencies: Task 18 (working application)
    - Outputs: Complete README.md with examples and troubleshooting
    - Parallelizable with: Tasks 19, 20, 21, 22

24. **Add deployment guide** ⚡
    - Description: Document how to run as systemd service, PM2 process, or Docker container
    - Dependencies: Task 23 (basic docs)
    - Outputs: Deployment documentation for various environments
    - Parallelizable with: Tasks 20, 21, 22

---

### Phase 4: Future Enhancements
**Goal**: Features deferred from MVP that add significant value

**Completion Criteria**: N/A (Future work as needed)

#### Tasks

25. **Add persistent storage (SQLite)**
    - Description: Implement historical price storage for analysis and backtesting
    - Dependencies: Working MVP
    - Outputs: Database schema and storage integration

26. **Implement WebSocket price feeds**
    - Description: Replace polling with event-driven updates where supported
    - Dependencies: Working MVP, DEX WebSocket API research
    - Outputs: Real-time event-driven price updates

27. **Build REST API**
    - Description: Add FastAPI server to expose price data and spreads via HTTP endpoints
    - Dependencies: Working MVP
    - Outputs: REST API with documentation

28. **Create web dashboard**
    - Description: Build browser-based UI for monitoring prices and spreads
    - Dependencies: Task 27 (API)
    - Outputs: Web frontend with real-time updates

29. **Add alert webhooks**
    - Description: Send notifications to Discord, Telegram, Slack when spreads exceed thresholds
    - Dependencies: Working MVP
    - Outputs: Configurable webhook integrations

30. **Implement advanced analytics**
    - Description: VWAP calculations, historical spread analysis, profitability modeling
    - Dependencies: Task 25 (historical data storage)
    - Outputs: Analytics module with insights

---

## Dependency Graph

```
Phase 0: Foundation
─────────────────────
         ┌─────────────┐
         │ 1. Research │ ⚡
         │    DEXes    │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │ 6. Collect  │
         │    ABIs     │
         └─────────────┘

┌───────────────┐
│ 2. Project    │ ⚡
│   Structure   │
└───┬───────────┘
    │
┌───▼──────────────┐
│ 3. Dependencies  │
└───┬──────────────┘
    │
┌───▼──────────────┐
│ 5. Test RPC      │ 🎯 Critical
└──────────────────┘

┌───────────────┐
│ 4. Config     │ ⚡
│   Schema      │
└───────────────┘

Phase 1: Core Components
────────────────────────
         ┌──────────────┐
         │ 7. Data      │ 🎯
         │   Models     │
         └──┬─────┬─────┘
            │     │
     ┌──────▼──┐  └──────┬──────────┬──────────┐
     │ 8.Config│         │          │          │
     │  Loader │    ┌────▼───┐ ┌────▼────┐ ┌──▼────┐
     └─────────┘    │9. Base │ │11.Spread│ │12. UI │
                    │Adapter │ │  Calc   │ │Output │
                    └────┬───┘ └─────────┘ └───────┘
                         │
                    ┌────▼─────┐
                    │10. V2    │ 🎯
                    │ Adapter  │
                    └──────────┘
                         │
                    ┌────▼─────┐
                    │13. Tests │
                    └──────────┘

Phase 2: Integration
────────────────────
     ┌──────────────┐
     │ 14. Monitor  │ 🎯 Critical
     │   Manager    │
     └──────┬───────┘
            │
     ┌──────▼───────┐
     │ 15. Main     │ 🎯 Critical
     │   Entry      │
     └──┬───────┬───┘
        │       │
  ┌─────▼──┐ ┌─▼──────┐
  │16.Error│ │17.Logs │ ⚡
  │Handling│ └────────┘
  └────┬───┘
       │
  ┌────▼─────────┐
  │18.Integration│ 🎯 Critical
  │    Tests     │
  └──────────────┘

Phase 3: Polish
───────────────
  ┌────────────┬──────────┬─────────┬──────────┐
  │19. Real    │20. More  │21. Perf │22. Better│
  │  Configs   │ Adapters │ Optimize│   UI     │
  └────────────┴──────────┴─────────┴──────────┘
                     │
            ┌────────┴────────┐
            │23. User Docs    │
            └────┬────────────┘
                 │
            ┌────▼────────────┐
            │24. Deploy Docs  │
            └─────────────────┘
```

---

## Critical Path

The minimum sequence of tasks to achieve a working MVP:

```
1. Research DEXes
   ↓
2. Project Structure
   ↓
3. Dependencies
   ↓
5. Test RPC ──────────────────┐
   ↓                          │
6. Collect ABIs               │
   ↓                          │
7. Data Models ───────────────┤
   ↓                          │
9. Base Adapter Interface     │
   ↓                          │
10. Uniswap V2 Adapter ◄──────┘
   ↓
14. Monitor Manager
   ↓
15. Main Entry Point
   ↓
18. Integration Testing
   ↓
MVP COMPLETE ✅
```

**Estimated Critical Path Duration**:
- With focused effort: 3-5 days
- With research unknowns: 5-7 days

---

## Parallel Work Streams

To maximize efficiency, work can be split into these independent streams:

### Stream A: Research & Discovery 🔍
```
1. Research DEXes
   ↓
6. Collect ABIs
   ↓
19. Real Configs
```
**Can run independently** - No code dependencies

---

### Stream B: Infrastructure 🏗️
```
2. Project Structure
   ↓
3. Dependencies
   ↓
4. Config Schema
   ↓
5. Test RPC
   ↓
17. Logging System
```
**Minimal dependencies** - Can start immediately

---

### Stream C: Data & Models 📊
```
7. Data Models
   ↓
11. Spread Calculator
   ↓
8. Config Loader
```
**Depends on Stream B** (dependencies), then independent

---

### Stream D: DEX Integration 🔌
```
9. Base Adapter
   ↓
10. Uniswap V2 Adapter
   ↓
20. More Adapters
```
**Depends on Stream A** (ABIs) and Stream C (models)

---

### Stream E: User Interface 🖥️
```
12. Console Output
   ↓
22. Improve UI
   ↓
23. User Docs
```
**Depends on Stream C** (models), then independent

---

### Stream F: Integration 🔗
```
14. Monitor Manager
   ↓
15. Main Entry
   ↓
16. Error Handling
   ↓
18. Integration Tests
```
**Depends on all other streams** - Final integration

---

## Risk & Blockers

### High Risk 🔴 → ✅ MITIGATED

**DEXes don't exist or lack liquidity** - ✅ **RESOLVED**
- Risk: Research reveals DEXes aren't active or FXRP pairs don't exist
- Status: **Task 1 complete** - All 4 DEXes verified active with documented contract addresses
- Result: SparkDEX ($5.2M volume), BlazeSwap ($73K), Pangolin, Enosys all operational

**RPC rate limiting** - ✅ **RESOLVED**
- Risk: Public RPC endpoints too restrictive for our polling frequency
- Status: **Task 5 complete** - All 3 RPC endpoints tested successfully
- Result: No rate limiting observed, public RPC sufficient for MVP (0.427s avg response)

### Medium Risk 🟡 → ✅ MITIGATED

**DEXes use non-standard interfaces** - ✅ **RESOLVED**
- Risk: DEXes aren't pure Uniswap forks, require custom adapters
- Status: **Task 1 research** - Confirmed all are Uniswap V2 forks (V3 deferred)
- Result: Standard Uniswap V2 adapter will work for all 4 DEXes

**Token decimals and precision issues** - ✅ **MITIGATED**
- Risk: Incorrect decimal handling leads to wrong price calculations
- Status: **Task 7 complete** - All models use Decimal type with comprehensive validation
- Result: FXRP (18 decimals), USDT0 (6 decimals), WFLR (18 decimals) all documented and validated

### Low Risk 🟢

**Performance insufficient** - **LOW PRIORITY**
- Risk: Python too slow for desired update frequency
- Mitigation: Async I/O should handle, can optimize later
- Impact: Minor - can optimize or rewrite hot paths
- Status: Will validate during integration testing

**Dependency conflicts** - ✅ **RESOLVED**
- Risk: Library version incompatibilities
- Status: **Task 3 complete** - All dependencies installed successfully in venv
- Result: No conflicts, all tools operational (web3 7.14.0, aiohttp 3.13.2, pydantic 2.12.4)

---

## Next Actions

### Current Status 📍

**Phase 0: COMPLETE** ✅ (6/6 tasks)
**Phase 1: 71% COMPLETE** (5/7 tasks)

### Immediate Priority (Critical Path) 🚀

1. **Implement Uniswap V2 Adapter** (Task #10) - **NEXT**
   - All dependencies complete (RPC tested, ABIs collected, base adapter ready)
   - Critical for MVP functionality
   - Enables price fetching from all 4 DEXes
   - Deliverable: Working adapter that fetches real prices from Flare Network

2. **Write Unit Tests** (Task #13) - After Task 10
   - Test all components (models, config, adapters, calculator, output)
   - Ensure quality before integration
   - Can be done in parallel with early Phase 2 work
   - Deliverable: >80% test coverage

### Phase 2: Integration (Ready After Task 10) 🔗

3. **Implement Monitor Manager** (Task #14)
   - Orchestrates all DEX adapters
   - Spawns concurrent price fetching tasks
   - Aggregates results
   - Deliverable: Coordinated multi-DEX monitoring

4. **Create Application Entry Point** (Task #15)
   - Main application loop
   - Initializes all components
   - Handles lifecycle
   - Deliverable: Runnable `python -m flare_monitor`

5. **Add Error Handling & Logging** (Tasks #16, #17)
   - Robust error recovery
   - Comprehensive logging
   - Graceful degradation
   - Deliverable: Production-ready error handling

6. **Integration Testing** (Task #18)
   - End-to-end testing against live Flare Network
   - Validate all 4 DEXes work
   - Performance validation
   - Deliverable: **MVP COMPLETE**

### Recommended Next Steps 🎯

**Immediate**:
- Day 1-2: Tasks #1, #2, #3 (Research + Setup)
- Day 3: Tasks #4, #5, #6 (Config, RPC, ABIs)
- Day 4-5: Tasks #7, #9 (Models, Base Adapter)
- Day 6: Task #10 (Uniswap V2 Adapter - first working integration)

**If multiple developers**:
- Developer A: Tasks #1, #6, #19 (Research stream)
- Developer B: Tasks #2, #3, #4, #5 (Infrastructure stream)
- Then converge for implementation tasks

---

## Success Metrics

### Phase 0 Complete
- ✅ Can connect to Flare RPC
- ✅ Have all DEX contract addresses
- ✅ Project structure created
- ✅ Dependencies installed

### Phase 1 Complete
- ✅ All models defined and validated
- ✅ Can fetch price from one DEX
- ✅ Can calculate spread between two prices
- ✅ Unit tests passing

### Phase 2 Complete (MVP)
- ✅ Application runs and displays prices
- ✅ Monitors multiple DEXes concurrently
- ✅ Shows real-time spreads
- ✅ Handles errors gracefully
- ✅ Integration tests pass

### Phase 3 Complete (Production Ready)
- ✅ All Flare DEXes monitored
- ✅ Performance optimized
- ✅ Documentation complete
- ✅ Can run 24/7 reliably

---

## Notes

- This plan assumes Python expertise and familiarity with async programming
- Research unknowns could extend timeline by 50-100%
- Plan will be updated as implementation reveals new requirements
- Focus on getting to working MVP quickly, then iterate
- Parallelization most effective with 2+ developers
- Critical path items marked with 🎯 should be prioritized
- Tasks marked ⚡ can be parallelized with others
- Tasks marked 🔗 have dependencies that must be completed first
