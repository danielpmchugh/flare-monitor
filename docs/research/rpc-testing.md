# Flare Network RPC Testing Results

**Date:** 2025-11-23
**Test Script:** `scripts/test_rpc.py`
**Python Version:** 3.10.12
**web3.py Version:** 6.0.0+

## Executive Summary

All three tested Flare Network RPC endpoints are **fully operational** and suitable for use in the Flare Monitor MVP. Testing revealed:

- **100% success rate** across all endpoints
- **Chain ID validation passed**: All endpoints correctly report chain ID 14 (Flare mainnet)
- **Network synchronization**: All endpoints report identical block heights (51,10X,XXX)
- **Response times**: Range from 0.247s to 0.888s (async mode)
- **Concurrent request handling**: All endpoints successfully handled 10 concurrent requests

### Recommended Configuration

**Primary RPC:** `https://flare.public-rpc.com` (fastest, 0.427s avg async)
**Fallback RPC 1:** `https://rpc.ankr.com/flare` (second fastest, 0.490s avg async)
**Fallback RPC 2:** `https://flare-api.flare.network/ext/C/rpc` (official, 0.888s avg async)

## Test Methodology

### Test Configuration

- **Iterations per endpoint:** 5 sync + 5 async tests
- **Request timeout:** 10 seconds
- **Concurrent request test:** 10 simultaneous requests
- **Sample address tested:** `0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d` (WFLR contract)

### Tests Performed

For each RPC endpoint, the following tests were executed:

1. **Connection Test**: Verify endpoint is reachable and responds
2. **Chain ID Validation**: Confirm chain ID is 14 (Flare mainnet)
3. **Block Height Query**: Retrieve latest block number
4. **Gas Price Query**: Get current network gas price
5. **Balance Query**: Test account balance retrieval
6. **Concurrent Load Test**: 10 simultaneous requests
7. **Sync vs Async Performance**: Compare synchronous and asynchronous request times

## Detailed Test Results

### 1. Official Flare RPC

**Endpoint:** `https://flare-api.flare.network/ext/C/rpc`

| Metric | Value |
|--------|-------|
| Status | ✓ Online |
| Chain ID | 14 (Correct) |
| Latest Block | 51,10X,XXX |
| Success Rate | 100.0% |
| Avg Sync Response Time | 0.656s |
| Avg Async Response Time | 0.888s |
| Min Async Response | 0.829s |
| Max Async Response | 1.084s |
| Concurrent Requests | 10/10 successful (0.212s avg) |
| Current Gas Price | 25.00 Gwei |

**Analysis:**
- Official Flare RPC is stable and reliable
- Slowest of the three tested endpoints
- Suitable for fallback/redundancy
- Known to be rate-limited for public use
- Best for development/testing, not high-frequency production

**Recommendation:** Use as tertiary/fallback endpoint

---

### 2. Ankr Flare RPC

**Endpoint:** `https://rpc.ankr.com/flare`

| Metric | Value |
|--------|-------|
| Status | ✓ Online |
| Chain ID | 14 (Correct) |
| Latest Block | 51,10X,XXX |
| Success Rate | 100.0% |
| Avg Sync Response Time | 0.283s |
| Avg Async Response Time | 0.490s |
| Min Async Response | 0.378s |
| Max Async Response | 0.592s |
| Concurrent Requests | 10/10 successful (0.141s avg) |
| Current Gas Price | 25.00 Gwei |

**Analysis:**
- Second fastest endpoint tested
- Excellent reliability (100% success rate)
- Very consistent response times (low variance)
- Ankr is a reputable infrastructure provider
- Good for Europe-based deployments (as advertised)

**Recommendation:** Use as secondary/fallback endpoint

---

### 3. Public RPC (flare.public-rpc.com)

**Endpoint:** `https://flare.public-rpc.com`

| Metric | Value |
|--------|-------|
| Status | ✓ Online |
| Chain ID | 14 (Correct) |
| Latest Block | 51,10X,XXX |
| Success Rate | 100.0% |
| Avg Sync Response Time | 0.247s |
| Avg Async Response Time | 0.427s |
| Min Async Response | 0.384s |
| Max Async Response | 0.541s |
| Concurrent Requests | 10/10 successful (0.127s avg) |
| Current Gas Price | 25.00 Gwei |

**Analysis:**
- **Fastest endpoint tested** (0.427s avg async)
- Excellent concurrent request handling
- Very low response time variance
- Best performance for both sync and async operations
- Unknown rate limits (needs monitoring in production)

**Recommendation:** Use as primary endpoint for MVP

---

## Performance Comparison

### Response Time Summary (Async Mode)

| Endpoint | Average | Min | Max | Variance |
|----------|---------|-----|-----|----------|
| Public RPC | 0.427s | 0.384s | 0.541s | 0.157s |
| Ankr RPC | 0.490s | 0.378s | 0.592s | 0.214s |
| Official Flare | 0.888s | 0.829s | 1.084s | 0.255s |

**Key Findings:**
- Public RPC is **2.1x faster** than Official Flare RPC
- All endpoints show sub-second response times
- Public RPC has the lowest variance (most consistent)
- Concurrent requests are handled efficiently by all endpoints

### Sync vs Async Performance

All endpoints showed **faster synchronous response times** than async times, which is expected due to async overhead. However, async mode is still recommended for the Flare Monitor because:

1. Enables concurrent polling of multiple DEXes
2. Non-blocking I/O for better resource utilization
3. Required for real-time monitoring architecture
4. Scales better with increasing number of requests

## Network Information Validated

All endpoints returned consistent network data:

- **Chain ID:** 14 (Flare Mainnet) ✓
- **Gas Price:** 25.00 Gwei (consistent across all RPCs) ✓
- **Block Height:** Synchronized (all reported same block) ✓
- **WFLR Contract Balance:** 55,136,739,327.29 FLR ✓

This confirms all endpoints are properly synchronized with the Flare Network.

## Rate Limiting Observations

**During Testing:**
- No rate limiting observed during 5 iterations + 10 concurrent requests
- Total requests per endpoint: ~15-20 requests
- No 429 (Too Many Requests) errors encountered
- No degraded performance over test duration

**Expected Behavior in Production:**
- Official Flare RPC: Known to have rate limits (undocumented)
- Ankr Public RPC: Likely has rate limits (typical: 30 req/sec)
- Public RPC: Unknown limits, requires monitoring

**Recommendation:** Implement rate limit detection and automatic failover in the monitor.

## Recommendations for MVP Deployment

### Primary Configuration

```yaml
flare:
  rpc_endpoints:
    - https://flare.public-rpc.com              # Primary (fastest)
    - https://rpc.ankr.com/flare                # Fallback 1
    - https://flare-api.flare.network/ext/C/rpc # Fallback 2 (official)
  chain_id: 14
```

### Application Settings

Based on test results, recommended settings for `config.yaml`:

```yaml
monitoring:
  poll_interval_seconds: 2          # 2-second polling is feasible with these response times
  max_concurrent_requests: 10       # All endpoints handle 10 concurrent requests well
  request_timeout_seconds: 5        # Conservative (3x faster than slowest response)
  max_retries: 3                    # Retry with exponential backoff
  retry_backoff_seconds: 2          # Start with 2s, double on each retry
```

### Failover Strategy

1. **Primary Endpoint Failure**: Automatically switch to Ankr RPC
2. **Secondary Failure**: Fall back to Official Flare RPC
3. **All Endpoints Down**: Alert user, retry with exponential backoff
4. **Rate Limiting (429 error)**: Immediately switch to next endpoint
5. **Health Checks**: Periodically test failed endpoints to restore primary

### Production Considerations

**For MVP (Free Tier):**
- ✓ Public RPC endpoints are sufficient for development and testing
- ✓ 2-second polling interval is achievable
- ✓ Monitor for rate limiting and implement failover
- ✗ No SLA or guaranteed uptime
- ✗ Rate limits may impact high-frequency polling

**For Production (Paid Tier):**
Consider upgrading to paid RPC services if encountering:
- Frequent rate limiting (429 errors)
- Need for <1 second polling intervals
- Requirements for guaranteed uptime/SLA
- Need for WebSocket connections (real-time subscriptions)
- High request volume (>100 req/min sustained)

**Recommended Paid RPC Providers:**
1. **Ankr Premium**: $200-500/month for high request limits
2. **QuickNode**: $49-299/month with WebSocket support
3. **Blast API**: $20-100/month for Flare endpoints
4. **Chainstack**: $49-199/month with SLA guarantees

### Gas Price Observations

- Current network gas price: **25 Gwei** (25,000,000,000 Wei)
- This is consistent across all RPCs (good sign)
- For profitability calculations, assume minimum 25 Gwei gas costs
- Gas prices on Flare are relatively stable compared to Ethereum

### Error Handling Requirements

The monitor should implement:

1. **Connection Timeout**: 5-10 second timeout per request
2. **Retry Logic**: Exponential backoff (2s, 4s, 8s)
3. **Endpoint Rotation**: Auto-failover on errors
4. **Rate Limit Detection**: Catch 429 errors, switch endpoints
5. **Health Monitoring**: Log endpoint failures for debugging
6. **Circuit Breaker**: Temporarily disable consistently failing endpoints

## Testing Script Details

The test script (`scripts/test_rpc.py`) provides:

- Automated testing of multiple RPC endpoints
- Performance benchmarking (sync vs async)
- Concurrent request load testing
- Chain ID validation
- Rich console output with color-coded results
- Detailed statistics and recommendations

**Usage:**
```bash
python scripts/test_rpc.py
```

**Future Enhancements:**
- Add WebSocket connectivity testing
- Test multicall contract batching
- Monitor rate limiting thresholds
- Long-duration stress testing
- Measure block finality times

## Conclusions

### Key Takeaways

1. ✓ **All tested RPC endpoints are operational and reliable**
2. ✓ **Public RPC (flare.public-rpc.com) is recommended as primary** (fastest)
3. ✓ **100% success rate across all endpoints** (excellent reliability)
4. ✓ **Async mode is viable** with response times under 1 second
5. ✓ **Concurrent requests work well** (10 simultaneous requests handled)
6. ✓ **Network is properly synchronized** across all endpoints

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rate limiting on public RPCs | Medium | Implement automatic failover, monitor 429 errors |
| No SLA on free tier | Low | Use 3 endpoints for redundancy |
| Undocumented rate limits | Medium | Monitor usage, implement exponential backoff |
| Public RPC downtime | Low | Configure multiple fallback endpoints |
| Network congestion | Low | Set conservative timeouts, retry logic |

### Next Steps

1. ✓ Configure monitor to use recommended endpoint priority
2. Implement robust error handling and failover logic
3. Add rate limit detection (catch 429 status codes)
4. Monitor endpoint health in production
5. Consider paid RPC upgrade if rate limits become an issue

## Appendix: Test Environment

**System Information:**
- OS: Linux (WSL2)
- Kernel: 6.6.87.2-microsoft-standard-WSL2
- Python: 3.10.12
- web3.py: 6.0.0+
- aiohttp: 3.9.0+

**Test Duration:** ~90 seconds (all endpoints)

**Network Conditions:** Standard residential internet connection

---

**Report Generated:** 2025-11-23
**Tested By:** RPC Testing Script v1.0
**Status:** ✓ All tests passed
