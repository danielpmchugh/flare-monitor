"""
DEX adapter modules for interacting with different decentralized exchanges.

This package contains adapters for various DEX protocols including:
- Uniswap V2 style DEXes (SparkDEX, Blazeswap, etc.)
- Uniswap V3 style DEXes (if applicable)

Each adapter implements the base DEX adapter interface for consistent
price and liquidity fetching across different exchange types.
"""

from flare_monitor.adapters.base import DEXAdapter

__all__ = ["DEXAdapter"]
