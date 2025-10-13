"""
Yahoo Finance Stock Discovery Service for SOULTRADER
Uses Yahoo Finance screener for better stock discovery
"""

import yfinance as yf
import logging
from typing import List, Dict
from django.core.cache import cache

logger = logging.getLogger(__name__)


class YahooFinanceDiscoveryService:
    """Service for Yahoo Finance stock discovery using predefined screeners"""
    
    def __init__(self):
        self.cache_timeout = 3600  # 1 hour cache
    
    def discover_stocks(self, limit: int = 20) -> List[str]:
        """
        Discover stocks using Yahoo Finance screeners
        
        Args:
            limit: Maximum number of stocks to return
            
        Returns:
            List of stock symbols discovered
        """
        all_symbols = set()
        
        # Method 1: Undervalued Growth Stocks (best quality)
        growth_stocks = self._get_undervalued_growth_stocks(limit=8)
        all_symbols.update(growth_stocks)
        
        # Method 2: Undervalued Large Caps (stability)
        large_caps = self._get_undervalued_large_caps(limit=6)
        all_symbols.update(large_caps)
        
        # Method 3: Most Active Stocks (liquidity)
        active_stocks = self._get_most_active_stocks(limit=6)
        all_symbols.update(active_stocks)
        
        # Convert to list and limit
        discovered_symbols = list(all_symbols)[:limit]
        
        logger.info(f"Yahoo Finance discovery found {len(discovered_symbols)} unique stocks")
        return discovered_symbols
    
    def _get_undervalued_growth_stocks(self, limit: int = 8) -> List[str]:
        """Get undervalued growth stocks (P/E 0-20, PEG <1, Growth >25%)"""
        cache_key = f"yahoo_growth_stocks_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            query = yf.PREDEFINED_SCREENER_QUERIES['undervalued_growth_stocks']['query']
            data = yf.screen(query)
            
            symbols = []
            if isinstance(data, dict) and 'quotes' in data:
                for quote in data['quotes'][:limit]:
                    if 'symbol' in quote:
                        symbols.append(quote['symbol'])
            
            # Cache for 1 hour
            cache.set(cache_key, symbols, self.cache_timeout)
            
            logger.info(f"Found {len(symbols)} undervalued growth stocks")
            return symbols
            
        except Exception as e:
            logger.warning(f"Yahoo Finance growth stocks failed: {e}")
            return []
    
    def _get_undervalued_large_caps(self, limit: int = 6) -> List[str]:
        """Get undervalued large cap stocks (P/E 0-20, PEG <1, Market cap $10B-$100B)"""
        cache_key = f"yahoo_large_caps_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            query = yf.PREDEFINED_SCREENER_QUERIES['undervalued_large_caps']['query']
            data = yf.screen(query)
            
            symbols = []
            if isinstance(data, dict) and 'quotes' in data:
                for quote in data['quotes'][:limit]:
                    if 'symbol' in quote:
                        symbols.append(quote['symbol'])
            
            # Cache for 1 hour
            cache.set(cache_key, symbols, self.cache_timeout)
            
            logger.info(f"Found {len(symbols)} undervalued large cap stocks")
            return symbols
            
        except Exception as e:
            logger.warning(f"Yahoo Finance large caps failed: {e}")
            return []
    
    def _get_most_active_stocks(self, limit: int = 6) -> List[str]:
        """Get most active stocks (high volume >5M shares/day)"""
        cache_key = f"yahoo_active_stocks_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            query = yf.PREDEFINED_SCREENER_QUERIES['most_actives']['query']
            data = yf.screen(query)
            
            symbols = []
            if isinstance(data, dict) and 'quotes' in data:
                for quote in data['quotes'][:limit]:
                    if 'symbol' in quote:
                        symbols.append(quote['symbol'])
            
            # Cache for 1 hour
            cache.set(cache_key, symbols, self.cache_timeout)
            
            logger.info(f"Found {len(symbols)} most active stocks")
            return symbols
            
        except Exception as e:
            logger.warning(f"Yahoo Finance active stocks failed: {e}")
            return []
    
    def get_discovery_summary(self, symbols: List[str]) -> Dict:
        """Get summary of discovered stocks"""
        return {
            'total_discovered': len(symbols),
            'source': 'Yahoo Finance Screener',
            'methods': ['undervalued_growth', 'undervalued_large_caps', 'most_active'],
            'symbols': symbols
        }



