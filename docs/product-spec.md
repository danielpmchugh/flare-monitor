# Flare Monitor - Product Specification

## Overview

Flare Monitor is a real-time monitoring system for tracking FXRP token prices and trading opportunities across the Flare Network ecosystem.

## MVP Scope

**Goal:** Validate the concept quickly with a functional arbitrage monitoring tool.

**What's IN the MVP:**
- ✅ Monitor all 4 DEXes (SparkDEX, BlazeSwap, Pangolin, Enosys)
- ✅ Track all 3 pairs (FXRP/USDT0, FXRP/WFLR, WFLR/USDT0)
- ✅ Uniswap V2 protocol support only
- ✅ Real-time price fetching via RPC polling
- ✅ Spread calculation and arbitrage opportunity detection
- ✅ Console output with live-updating price table
- ✅ Basic error handling and retry logic

**What's OUT of the MVP (Future Enhancements):**
- ❌ Uniswap V3 support (evaluate after MVP)
- ❌ Historical price storage (SQLite/database)
- ❌ WebSocket real-time feeds
- ❌ Alert webhooks (Discord, Telegram, etc.)
- ❌ Web dashboard / REST API
- ❌ Advanced analytics (VWAP, volume tracking)
- ❌ Automated trading execution

**Success Criteria for MVP:**
1. Successfully fetches prices from all 4 DEXes
2. Calculates spreads accurately with proper decimal precision
3. Displays opportunities in real-time console interface
4. Handles DEX/RPC failures gracefully
5. Runs continuously without crashing

## Core Features

### 1. Real-time Price Monitoring

#### 1.1 DEX Coverage (MVP Requirement)
**All DEXes must be monitored for arbitrage opportunities:**
- **SparkDEX** (Primary - highest volume $5.2M daily)
  - Uniswap V2 pools (MVP)
  - Uniswap V3.1 concentrated liquidity (Future evaluation)
- **BlazeSwap** (Uniswap V2 clone)
- **Pangolin** (Multichain DEX on Flare)
- **Enosys** (Dual V2/V3 implementation - V2 for MVP)

**Protocol Support:**
- MVP: Uniswap V2 protocol only
- Future: Evaluate Uniswap V3 support based on liquidity distribution

#### 1.2 Trading Pair Coverage (MVP Requirement)
**All pairs must be monitored for accurate arbitrage detection:**

1. **FXRP/USDT0** (Primary Pair)
   - Direct USD price tracking
   - Highest volume and liquidity
   - Primary arbitrage opportunities

2. **FXRP/WFLR** (Secondary Pair)
   - FLR-denominated pricing
   - Alternative arbitrage paths
   - Backup when USDT0 liquidity is low

3. **WFLR/USDT0** (Reference Pair)
   - Required for USD conversion of FXRP/WFLR prices
   - Enables triangular arbitrage calculations
   - Cross-validates FXRP/USDT0 pricing

**Token Contracts (Flare Network):**
- FXRP: `0xad552a648c74d49e10027ab8a618a3ad4901c5be` (18 decimals)
- USDT0: `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` (6 decimals)
- WFLR: `0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d` (18 decimals)

#### 1.3 Price Spread Calculator
- Calculate price differences between all monitored DEXes
- Identify arbitrage opportunities across all pairs
- Display spread percentages in real-time
- Alert when spread exceeds configurable thresholds
- Account for gas fees and slippage in profitability calculations
- Support triangular arbitrage detection (FXRP/USDT0 vs FXRP/WFLR + WFLR/USDT0)

## Technical Requirements

### Data Collection
- WebSocket connections for real-time price feeds
- Fallback to polling for DEXes without WebSocket support
- Update frequency: Sub-second for active pairs

## Future Enhancements

### Data Storage
- Time-series database for historical price data
- Support for aggregation and analysis
- Retention policy for historical data

### Alert System
- Configurable alert thresholds
- Multiple notification channels (console, webhook, etc.)
- Rate limiting to prevent alert spam

### Performance
- Low latency data collection (<1 second)
- Efficient concurrent monitoring of multiple pairs
- Scalable architecture for adding new DEXes

### Additional Features
- Additional trading pair support
- Advanced analytics and charting
- Automated trading signal generation
- Mobile notifications
- Web dashboard interface
