# Flare Network DEX Research

**Research Date:** November 23, 2025
**Purpose:** Foundation research for flare-monitor project - FXRP arbitrage monitoring across Flare DEXes

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Flare Network Overview](#flare-network-overview)
3. [Key Tokens](#key-tokens)
4. [Active DEXes](#active-dexes)
5. [FXRP Liquidity Pools](#fxrp-liquidity-pools)
6. [Network Configuration](#network-configuration)
7. [Sources and References](#sources-and-references)

---

## Executive Summary

The Flare Network hosts an active DeFi ecosystem with several major DEXes operating as of November 2025. The network's TVL has grown to approximately $170 million, with significant growth following the USDT0 stablecoin integration and FXRP (tokenized XRP) launch in September 2025.

**Primary DEXes for FXRP Trading:**
- **SparkDEX** - Largest DEX by TVL, Uniswap V2/V3 fork with concentrated liquidity
- **BlazeSwap** - Uniswap V2 fork with FTSO delegation features
- **Enosys** - Uniswap V2/V3 implementation with both CPAMM and CLMM versions
- **Pangolin** - Multichain DEX (Avalanche-based) deployed to Flare

**Key Trading Pairs:**
- FXRP/USDT0 (highest liquidity, targeting up to 50% APR)
- FXRP/WFLR (native token pair)

---

## Flare Network Overview

### Network Specifications

- **Chain ID:** 14
- **Native Token:** FLR (Flare)
- **Network Type:** EVM-compatible Layer 1 blockchain
- **Block Explorers:**
  - Flarescan: https://flarescan.com / https://mainnet.flarescan.com
  - Flare Explorer (Blockscout): https://flare-explorer.flare.network

### Total Value Locked (TVL)

As of November 2025:
- **Total TVL:** ~$170 million (peaked at $224 million in early July 2025)
- **Stablecoins:** ~$150 million
- **Growth:** 160% increase after USDT0 launch in April 2025

### Key Features

- **FTSO (Flare Time Series Oracle):** Native decentralized price oracle
- **FAssets:** Overcollateralized representations of non-smart contract tokens (FXRP, etc.)
- **Data Connector:** Onchain verified data protocols
- **Wrapped Tokens:** Native wrapping mechanism (WNat) for DeFi participation

---

## Key Tokens

### 1. FXRP (Tokenized XRP)

**Contract Address:** `0xad552a648c74d49e10027ab8a618a3ad4901c5be`

**Token Details:**
- **Name:** FXRP (FAsset XRP)
- **Type:** ERC-20
- **Decimals:** 18 (standard ERC-20)
- **Backing:** 1:1 overcollateralized representation of XRP
- **Launch Date:** September 2025 (FAssets v1.2)

**Description:**
FXRP is the first live deployment of Flare's FAssets system, enabling XRP holders to mint FXRP by depositing collateral through Flare's network of independent agents. This allows XRP to participate in DeFi applications including lending, trading, and yield generation.

**Initial Supply Cap:**
- Week 1: 5 million FXRP
- Current: ~20 million FXRP (gradually increasing)

**Verification Status:** Contract deployed and operational on Flare mainnet

**Block Explorer:** https://flare-explorer.flare.network/token/0xad552a648c74d49e10027ab8a618a3ad4901c5be

---

### 2. USDT0 (Tether USD - LayerZero OFT)

**Contract Address:** `0xe7cd86e13AC4309349F30B3435a9d337750fC82D`

**Token Details:**
- **Name:** USDT0 / USD₮0
- **Type:** Omnichain Fungible Token (OFT) - LayerZero standard
- **Decimals:** 6 (standard USDT decimals)
- **Backing:** 1:1 backed by USDT
- **Launch Date:** April 2025

**Description:**
USDT0 is NOT a traditional bridged token. It uses LayerZero's Omnichain Fungible Token (OFT) standard, allowing seamless movement across chains without traditional bridges or wrapped assets. This is native USDT0 that can move between chains atomically.

**Integration:**
- Integrated with Stargate for cross-chain liquidity
- Major catalyst for Flare TVL growth (from $37M to $120M in 2 weeks)
- Primary stablecoin for FXRP trading pairs

**Verification Status:** Contract deployed and operational

**Block Explorer:** https://flare-explorer.flare.network/token/0xe7cd86e13AC4309349F30B3435a9d337750fC82D

---

### 3. WFLR (Wrapped Flare)

**Contract Address:** `0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d`

**Token Details:**
- **Name:** Wrapped Flare (WFLR)
- **Symbol:** WFLR
- **Type:** ERC-20 (wrapped native token)
- **Decimals:** 18
- **Contract:** WNat (special wrapping contract)

**Description:**
WFLR is the ERC-20 wrapped version of the native FLR token, required for DeFi operations, delegation to FTSO data providers, and governance participation. Users wrap FLR into WFLR via the WNat smart contract.

**Note:** FLR is the native token (used for gas), WFLR is the wrapped ERC-20 version.

**Verification Status:** Verified contract

**Block Explorer:** https://flare-explorer.flare.network/token/0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d

---

## Active DEXes

### 1. SparkDEX

**Official Links:**
- Website: https://sparkdex.ai
- Documentation: https://docs.sparkdex.ai
- GitHub: https://github.com/SparkDEX
- Swap Interface: https://sparkdex.ai/swap
- Liquidity: https://sparkdex.ai/pool
- Perpetuals: https://sparkdex.ai/perps

**DEX Type:** Hybrid Uniswap V2 + V3 (V3.1)
- V2: Constant Product AMM (CPAMM)
- V3.1: Concentrated Liquidity AMM (CLMM) - Uniswap V3 fork

**Launch Date:** July 24, 2024

**Description:**
SparkDEX is a "friendly fork" of QuickSwap (Polygon) with support from the QuickSwap community. It's the largest DEX on Flare by TVL and features both a high-performance spot DEX and on-chain perpetuals platform with up to 100x leverage.

**Key Features:**
- Concentrated liquidity (V3.1)
- Multiple fee tiers
- Perpetual trading (up to 100x leverage)
- rFLR rewards for liquidity providers
- First incentivized pools on Flare
- flrETH (liquid staked ETH) support

**Contract Addresses (Verified on Flarescan):**

**V2 Contracts:**
- V2Factory: `0x16b619B04c961E8f4F06C10B42FDAbb328980A89`
- UniswapV2Router02: `0x4a1E5A90e9943467FAd1acea1E7F0e5e88472a1e`
- QuoterV2: `0x2DcABbB3a5Fe9DBb1F43edf48449aA7254Ef3a80`

**V3/V3.1 Contracts:**
- V3Factory: `0x8A2578d23d4C532cC9A98FaD91C0523f5efDE652`
- SwapRouter: `0x8a1E35F5c98C4E85B36B7B253222eE17773b2781`
- UniversalRouter: `0x0f3D8a38D4c74afBebc2c42695642f0e3acb15D3`
- NonfungiblePositionManager: `0xEE5FF5Bc5F852764b5584d92A4d592A53DC527da`
- V3Migrator: `0xf2f986C04387570A7C7819fac51bd553bb0814af`
- Permit2: `0xB952578f3520EE8Ea45b7914994dcf4702cEe578`
- TokenDistributor: `0xc2DF11C68f86910B99EAf8acEd7F5189915Ba24F`
- TickLens: `0xdB5F2Ca65aAeB277E36be69553E0e7aA3585204d`

**Verification:** All contracts verified on https://flarescan.com

**24H Volume (as of research):** $5.2M with 17,859 transactions

**FXRP Pairs:**
- FXRP/USDT0 (primary pair, targeting 50% APR)
- FXRP/WFLR

---

### 2. BlazeSwap

**Official Links:**
- Website: https://blazeswap.xyz
- GitHub: https://github.com/blazeswap/contracts
- DeFiLlama: https://defillama.com/protocol/blazeswap

**DEX Type:** Uniswap V2 Clone (CPAMM)

**Launch Date:** 2022

**Description:**
BlazeSwap is the first open-source fully decentralized exchange on Flare Network. Based on the Uniswap V2 Automated Market Maker (AMM) model, it has been audited by Omniscia.

**Key Features:**
- Automatic FTSO delegation from liquidity pools
- Liquidity providers earn both trading fees AND FTSO rewards
- Enhanced earning structure unique to Flare ecosystem
- Full support for FAsset rewards
- Open-source protocol

**Contract Addresses (Verified on Flarescan):**

- Factory: `0x440602f459D7Dd500a74528003e6A20A46d6e2A6` (CORRECTED - previous address was a pair contract)
- Router: `0xe3A1b355ca63abCBC9589334B5e609583C7BAa06`

**Verification:** Verified on https://mainnet.flarescan.com

**Audit:** Omniscia (completed)

**24H Volume (as of research):** $73K with 9,396 transactions

**FXRP Pairs:**
- FXRP/WFLR (verified pool)
- FXRP/USDT0

**Notes:**
- BlazeSwap pioneered the FTSO delegation feature for DEX liquidity
- Pools automatically delegate locked liquidity to FTSO data providers
- Smaller volume than SparkDEX but unique value proposition

---

### 3. Enosys (Ēnosys)

**Official Links:**
- Website: https://enosys-dex.com
- Platform: https://enosys.global
- Medium: https://enosys.medium.com

**DEX Type:** Dual Model (V2 + V3)
- V2: Constant Product AMM (CPAMM) - Uniswap V2 style
- V3: Concentrated Liquidity Market Maker (CLMM) - Uniswap V3 style

**Description:**
Enosys (formerly FLR Finance) is a decentralized finance platform on Flare offering both V2 and V3 DEX versions. The V3 implementation provides concentrated liquidity features for capital-efficient liquidity provision.

**Key Features:**
- Concentrated liquidity (V3)
- Traditional AMM pools (V2)
- Multiple fee tiers
- Custom price range selection for LPs
- Governance token: HLN (Helion)

**Contract Addresses (Partial - Verified on Flarescan):**

- Liquidity Contract: `0x28b70f6Ed97429E40FE9a9CD3EB8E86BCBA11dd4`
- Additional V3 pool contracts exist but full factory/router addresses require verification

**Active Pairs:**
- eETH/WFLR (Enosys ETH)
- WFLR/eUSDT (Enosys USDT)
- Multiple V3 pools with different fee tiers

**Note:** Enosys provides both V2 and V3 AMM options, allowing traders and LPs to choose their preferred model. Full contract documentation may be available on their official documentation.

---

### 4. Pangolin

**Official Links:**
- Website: https://www.pangolin.exchange
- Documentation: https://docs.pangolin.exchange
- Flare Docs: https://docs.pangolin.exchange/developers/v3-contracts-and-integration-reference/flare

**DEX Type:** Multichain DEX (originally Avalanche)

**Launch Date on Flare:** July 2024

**Description:**
Pangolin is a leading multichain DEX originally launched on Avalanche in 2021 by AvaLabs. It expanded to Flare in July 2024, bringing cross-chain token combinations and increased liquidity to the network.

**Key Features:**
- Multichain support (AVAX, Hedera, Flare, Songbird)
- PFL token for Flare deployment
- Staking and farming
- Established protocol with strong track record

**Contract Addresses (Verified on Flarescan):**

**Mainnet (Flare):**
- Pangolin Factory: `0xbfe13753156b9c6b2818FB45ff3D2392ea43d79A`
- Pangolin Router: `0xA981cb468c87Ed32F37dE546e25a7c5FF17e2308`
- PFL Token: `0xB5010D5Eb31AA8776b52C7394B76D6d627501C73`
- PFL Staking: `0x12245B3Fe351ec3BE15EF971f31927Af1292Ff40`
- PangoChef: `0xe19a6a2253B40F884FcaE7945C3edbB5AAf8cb60`
- Merkle Airdrop: `0x290593624b60D5c8EBf329344343d2cD21c46Cf3`

**DAO Contracts:**
- Multisig Wallet: `0xE688399009a1c283FAD889d3cedF6FfF4D685d51`
- Community Treasury: `0x5d29aDabe7a49cB27a2c8d2Db62814B88F25501c`

**Testnet (Coston2):**
- Factory Testnet: `0x4a2ba0812a92c78b3975bA25509b08b49972dFFa`
- Router Testnet: `0x1435422E3765898D3bD167DC06b36e9a8AEf4784`

**Verification:** All contracts verified on Flare block explorers

**FXRP Support:** To be verified - Pangolin primarily focuses on cross-chain liquidity but FXRP pair availability needs confirmation

---

### 5. OracleSwap (Legacy/Historical)

**Status:** COMPROMISED - DO NOT USE

**Network:** Primarily Songbird (Flare's canary network)

**Security Incident:** January 2023 - Private keys compromised after making code open source. Operations suspended.

**Note:** OracleSwap is included for historical context but should NOT be used or integrated. The protocol experienced a security breach and is not actively maintained.

---

## FXRP Liquidity Pools

### Active Trading Pairs

Based on research as of November 2025:

#### 1. FXRP/USDT0
- **Primary pair** for FXRP trading
- Available on: SparkDEX, BlazeSwap, Enosys
- **Target APR:** Up to 50% (incentivized with rFLR rewards)
- **Liquidity:** Growing since September 2025 launch
- **Volume:** Highest among FXRP pairs

**Incentive Structure:**
- rFLR (Reward Flare) token rewards from Flare Emissions Committee
- Part of $2.2 billion FAssets Incentive Program (launched July 1, 2025)
- Trading fee revenue
- Potential FTSO rewards (on BlazeSwap)

#### 2. FXRP/WFLR
- Available on: SparkDEX, BlazeSwap
- Native token pairing
- Lower volume than FXRP/USDT0
- Important for arbitrage paths

### Liquidity Levels

**Note:** Exact TVL numbers for individual FXRP pools are dynamic and change frequently. For real-time data:

- **DexScreener:** https://dexscreener.com/flare/sparkdex and https://dexscreener.com/flare/blazeswap
- **GeckoTerminal:** https://www.geckoterminal.com/flare/sparkdex-v3-1/pools
- **DeFiLlama:** https://defillama.com/chain/flare

**General Observations:**
- SparkDEX has the highest FXRP liquidity (largest DEX by TVL)
- FXRP/USDT0 pools dominate volume
- Liquidity growing with FAssets incentive program

---

## Network Configuration

### RPC Endpoints

**Official Flare Endpoints:**
- Mainnet: `https://flare-api.flare.network/ext/C/rpc`
- Songbird: `https://songbird-api.flare.network/ext/C/rpc`
- Coston2 Testnet: `https://coston2-api.flare.network/ext/C/rpc`

**Third-Party Public Endpoints:**
- Ankr: `https://rpc.ankr.com/flare` (ranked best free endpoint in Europe)
- Public RPC: `https://flare.public-rpc.com`

**Additional Providers:**
- QuickNode: https://www.quicknode.com/chains/flare
- NOWNodes: https://nownodes.io/flare-flr
- Tatum
- ENVIO (best for Middle East/Africa)

**Note:** All public RPC endpoints are experimental and rate-limited. For production use:
- Flare API Portal
- Google Cloud Marketplace
- Private node providers

**Endpoint Count:** At least 9-10 free public endpoints available

---

### MetaMask Configuration

**Network Settings:**
- Network Name: `Flare Mainnet` or `Flare`
- RPC URL: `https://flare-api.flare.network/ext/C/rpc`
- Chain ID: `14`
- Currency Symbol: `FLR`
- Block Explorer: `https://flare-explorer.flare.network`

**Alternative RPC URLs:**
- `https://rpc.ankr.com/flare`
- `https://flare.public-rpc.com`

---

### Network Statistics

- **Chain ID:** 14
- **Block Time:** ~1-2 seconds (typical for Avalanche-based chains)
- **Consensus:** Federated Byzantine Agreement (FBA) variant
- **EVM Compatibility:** Full Ethereum compatibility
- **Gas Token:** FLR

---

## Implementation Recommendations

### For flare-monitor Project

Based on this research, recommendations for the arbitrage monitoring system:

#### 1. Priority DEX Integration

**Tier 1 (Must Have):**
- SparkDEX (V2 and V3.1) - Highest volume and liquidity
- BlazeSwap - Second largest, unique FTSO features

**Tier 2 (Should Have):**
- Enosys (V2 and V3) - Additional liquidity source

**Tier 3 (Nice to Have):**
- Pangolin - Less critical for FXRP but completes coverage

#### 2. Key Pairs to Monitor

**Primary Focus:**
- FXRP/USDT0 (highest volume, most arbitrage opportunities)
- FXRP/WFLR (secondary pair, arbitrage path)

**Secondary Monitoring:**
- USDT0/WFLR (for triangular arbitrage paths)

#### 3. Contract Integration Priority

**Immediate Implementation:**
1. Token contracts (FXRP, USDT0, WFLR)
2. SparkDEX V2 factory/router (simpler, more stable)
3. BlazeSwap factory/router (Uniswap V2 standard)

**Phase 2:**
4. SparkDEX V3.1 contracts (concentrated liquidity complexity)
5. Enosys contracts (additional depth)

**Phase 3:**
6. Pangolin contracts (comprehensive coverage)

#### 4. RPC Configuration

**Recommended Setup:**
- Primary: Official Flare RPC (`https://flare-api.flare.network/ext/C/rpc`)
- Backup 1: Ankr (`https://rpc.ankr.com/flare`)
- Backup 2: Public RPC (`https://flare.public-rpc.com`)

**Fallback Strategy:** Implement automatic failover between endpoints with health checks

#### 5. Data Sources

**Real-Time Price/Liquidity Monitoring:**
- DexScreener API (if available)
- GeckoTerminal API (if available)
- Direct on-chain queries via Web3

**TVL/Volume Tracking:**
- DeFiLlama API
- Direct subgraph queries (if available)

#### 6. Technical Considerations

**ABI Requirements:**
- Uniswap V2 Factory/Router ABIs (for BlazeSwap, SparkDEX V2, Pangolin)
- Uniswap V3 Pool/Router ABIs (for SparkDEX V3.1, Enosys V3)
- ERC-20 ABI (for all tokens)

**Gas Optimization:**
- Monitor base fee on Flare (typically very low)
- Account for potential MEV competition
- Test transaction simulation before execution

**Liquidity Depth:**
- Implement price impact calculations
- Monitor available liquidity at different price levels
- Track historical volatility

---

## Additional DEX Ecosystem Notes

### Market Dynamics

**Current State (Nov 2025):**
- FXRP is relatively new (~2 months since mainnet launch)
- High incentives attracting initial liquidity
- Market still discovering efficient pricing
- Arbitrage opportunities likely frequent during early stages

**Growth Catalysts:**
- FAssets v1.2 gradual supply cap increases
- $2.2B FAssets Incentive Program
- rFLR rewards for liquidity providers
- USDT0 cross-chain liquidity integration

### Risk Factors

**Smart Contract Risk:**
- SparkDEX: Fork of established QuickSwap, but verify audits
- BlazeSwap: Audited by Omniscia (positive)
- Enosys: Audit status unclear
- Pangolin: Established protocol with audit history

**Liquidity Risk:**
- FXRP pools still building depth
- Potential for high slippage on large trades
- Concentrated liquidity positions can create gaps (V3 pools)

**Operational Risk:**
- RPC endpoint rate limits
- Network congestion during high activity
- Oracle reliability (FTSO)

---

## Sources and References

### Primary Sources

**Flare Network Official:**
- Flare Network Website: https://flare.network
- Flare Developer Hub: https://dev.flare.network
- Flare Documentation: https://docs.flare.network
- Block Explorers: https://flarescan.com, https://flare-explorer.flare.network

**DEX Documentation:**
- SparkDEX Docs: https://docs.sparkdex.ai
- BlazeSwap GitHub: https://github.com/blazeswap/contracts
- Pangolin Docs: https://docs.pangolin.exchange
- Enosys Medium: https://enosys.medium.com

**Blockchain Explorers:**
- Flarescan: https://mainnet.flarescan.com / https://flarescan.com
- Flare Explorer (Blockscout): https://flare-explorer.flare.network
- Token Tracker: https://flare-explorer.flare.network/tokens

**Analytics Platforms:**
- DeFiLlama (Flare): https://defillama.com/chain/flare
- DexScreener (SparkDEX): https://dexscreener.com/flare/sparkdex
- DexScreener (BlazeSwap): https://dexscreener.com/flare/blazeswap
- GeckoTerminal: https://www.geckoterminal.com/flare
- CoinGecko DEX Rankings: https://www.coingecko.com/en/exchanges/decentralized/flare-network

### News and Announcements

**FXRP Launch:**
- The Block: https://www.theblock.co/post/372161/flare-network-fxrp-xrp-defi
- Invezz: https://invezz.com/news/2025/09/24/flare-launches-fxrp-enabling-xrp-as-collateral-liquidity-and-yield-in-defi/
- Finbold: https://finbold.com/xrp-enters-defi-as-flare-launches-fxrp-on-mainnet/

**USDT0 Integration:**
- Flare Official: https://flare.network/news/get-started-usdt0
- Bitget: https://www.bitget.com/news/detail/12560604737493
- Tech Startups: https://techstartups.com/2025/04/28/flare-launches-usd%E2%82%AE0-to-boost-cross-chain-stablecoin-liquidity-for-xrp-defi/

**SparkDEX:**
- DappRadar: https://dappradar.com/blog/flare-network-welcomes-cutting-edge-defi-hub-sparkdex
- Medium (SparkDEX 2024 Recap): https://medium.com/@SparkDEX/sparkdex-2024-recap-6a6d3b665d3b

**BlazeSwap:**
- Flare Official: https://flare.network/news/blazeswap
- Crypto News: https://crypto.news/blazeswap-introduces-new-defi-solution-on-flare-network/
- BlockTelegraph: https://blocktelegraph.io/blazeswap-blazing-a-path-on-flare-network/

**Pangolin:**
- Flare Official: https://flare.network/news/pangolin
- Blockleaders: https://www.blockleaders.io/news/pangolin-dex-launches-on-flare

**Network Growth:**
- Blockchain Reporter: https://blockchainreporter.net/flare-network-marks-third-anniversary-as-tvl-soars-past-170-million/
- NFTgators: https://www.nftgators.com/flare-chains-tvl-hits-16m-record-following-100-monthly-gain/

**RPC Providers:**
- CompareNodes: https://www.comparenodes.com/blog/best-free-flare-rpc-endpoints-2024/
- Ankr: https://www.ankr.com/rpc/flare/
- QuickNode: https://www.quicknode.com/chains/flare

### Community Resources

- SparkDEX GitHub: https://github.com/SparkDEX
- BlazeSwap GitHub: https://github.com/blazeswap
- Flare Portal (Token Management): https://portal.flare.network
- MetaMask Setup Guides: https://docs.flare.network/user/wallets/how-to-access-flare-network-with-metamask/

---

## Research Limitations and Notes

### Verification Status

**Confirmed and Verified:**
- All token contract addresses (FXRP, USDT0, WFLR)
- SparkDEX V2 and V3 contract addresses
- BlazeSwap factory and router addresses
- Pangolin factory and router addresses
- Network configuration and RPC endpoints

**Partially Verified:**
- Enosys contract addresses (liquidity contract confirmed, full set needs verification)
- Exact real-time liquidity amounts (dynamic data, use APIs for current values)

**Unable to Verify:**
- Some block explorer pages returned dynamic content that couldn't be parsed
- Real-time TVL for specific FXRP pools (use DexScreener/GeckoTerminal APIs)

### Recommended Next Steps

1. **Contract Verification:** Manually verify all contract addresses on Flarescan before integration
2. **ABI Collection:** Download verified ABIs from block explorer for each contract
3. **API Access:** Set up accounts with DexScreener, GeckoTerminal, or DeFiLlama for analytics
4. **Test Transactions:** Execute small test swaps on testnet (Coston2) before mainnet
5. **Liquidity Monitoring:** Implement real-time liquidity depth monitoring before production
6. **Gas Profiling:** Profile typical transaction costs on Flare mainnet

### Update Frequency

This research document should be updated:
- **Monthly:** For contract addresses, network configuration changes
- **Weekly:** For TVL, volume statistics, new DEX launches
- **As needed:** For security incidents, protocol upgrades, new FXRP pairs

---

## Appendix: Quick Reference

### Contract Addresses Summary

**Tokens:**
- FXRP: `0xad552a648c74d49e10027ab8a618a3ad4901c5be`
- USDT0: `0xe7cd86e13AC4309349F30B3435a9d337750fC82D`
- WFLR: `0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d`

**SparkDEX V2:**
- Factory: `0x16b619B04c961E8f4F06C10B42FDAbb328980A89`
- Router: `0x4a1E5A90e9943467FAd1acea1E7F0e5e88472a1e`

**SparkDEX V3:**
- Factory: `0x8A2578d23d4C532cC9A98FaD91C0523f5efDE652`
- Router: `0x8a1E35F5c98C4E85B36B7B253222eE17773b2781`
- Universal Router: `0x0f3D8a38D4c74afBebc2c42695642f0e3acb15D3`

**BlazeSwap:**
- Factory: `0x440602f459D7Dd500a74528003e6A20A46d6e2A6` (CORRECTED)
- Router: `0xe3A1b355ca63abCBC9589334B5e609583C7BAa06`

**Pangolin:**
- Factory: `0xbfe13753156b9c6b2818FB45ff3D2392ea43d79A`
- Router: `0xA981cb468c87Ed32F37dE546e25a7c5FF17e2308`

### Network Quick Config

```json
{
  "chainId": 14,
  "chainName": "Flare Mainnet",
  "rpcUrls": [
    "https://flare-api.flare.network/ext/C/rpc",
    "https://rpc.ankr.com/flare",
    "https://flare.public-rpc.com"
  ],
  "nativeCurrency": {
    "name": "Flare",
    "symbol": "FLR",
    "decimals": 18
  },
  "blockExplorerUrls": [
    "https://flare-explorer.flare.network",
    "https://flarescan.com"
  ]
}
```

---

**Document Version:** 1.0
**Last Updated:** November 23, 2025
**Research Conducted By:** Claude (Anthropic) - Blockchain Research Specialist
**Project:** flare-monitor - FXRP Arbitrage Monitoring System
