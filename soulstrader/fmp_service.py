"""
Financial Modeling Prep (FMP) API Service
Provides integration with FMP API for stock data, grades, and company logos.
"""

import requests
import logging
from typing import Dict, List, Optional, Union
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from .models import Stock, AIAdvisor, AIAdvisorRecommendation

logger = logging.getLogger(__name__)


class FMPAPIService:
    """Service class for Financial Modeling Prep API integration"""
    
    BASE_URL = "https://financialmodelingprep.com/stable"  # Use stable endpoints (v3 deprecated)
    STABLE_URL = "https://financialmodelingprep.com/stable"
    IMAGE_URL = "https://financialmodelingprep.com/image-stock"
    
    def __init__(self, api_key: str = None):
        """
        Initialize FMP API service
        
        Args:
            api_key: FMP API key. If None, will try to get from settings or AIAdvisor model
        """
        self.api_key = api_key or self._get_api_key()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AIAdvisor-Django-App/1.0'
        })
    
    def _get_api_key(self) -> str:
        """Get API key from settings or AIAdvisor model"""
        # First try Django settings
        if hasattr(settings, 'FMP_API_KEY') and settings.FMP_API_KEY:
            return settings.FMP_API_KEY
        
        # Then try AIAdvisor model
        try:
            advisor = AIAdvisor.objects.filter(
                advisor_type='FMP',
                is_enabled=True,
                api_key__isnull=False
            ).first()
            if advisor and advisor.api_key:
                return advisor.api_key
        except Exception as e:
            logger.warning(f"Could not retrieve FMP API key from AIAdvisor model: {e}")
        
        raise ValueError("FMP API key not found. Please set FMP_API_KEY in settings or create an FMP AIAdvisor with API key.")
    
    def _make_request(self, endpoint: str, params: Dict = None, base_url: str = None) -> Dict:
        """
        Make HTTP request to FMP API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            base_url: Base URL to use (defaults to BASE_URL)
        
        Returns:
            JSON response data
        """
        if base_url is None:
            base_url = self.BASE_URL
        
        # FMP stable API uses query parameters, not URL paths
        # Format: https://financialmodelingprep.com/stable/profile?symbol=AAPL&apikey=KEY
        url = f"{base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to parameters
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        try:
            # Add rate limiting to respect 10 calls/minute limit
            import time
            time.sleep(6)  # 6 second delay = 10 calls per minute
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Log API usage
            self._log_api_usage()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API request failed: {url} - {e}")
            raise
        except ValueError as e:
            logger.error(f"FMP API response parsing failed: {url} - {e}")
            raise
    
    def _log_api_usage(self):
        """Log API usage for rate limiting tracking"""
        try:
            advisor = AIAdvisor.objects.filter(advisor_type='FMP').first()
            if advisor:
                advisor.daily_api_calls += 1
                advisor.save(update_fields=['daily_api_calls'])
        except Exception as e:
            logger.warning(f"Could not log FMP API usage: {e}")
    
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for stocks using FMP search endpoint
        
        Args:
            query: Search query (symbol or company name)
            limit: Maximum number of results
        
        Returns:
            List of stock information dictionaries
        """
        cache_key = f"fmp_search_{query}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            params = {
                'query': query,
                'limit': limit
            }
            
            # Use stable endpoint for search
            data = self._make_request('search-symbol', params, self.STABLE_URL)
            
            # Cache results for 1 hour
            cache.set(cache_key, data, 3600)
            
            return data
            
        except Exception as e:
            logger.error(f"FMP stock search failed for query '{query}': {e}")
            return []
    
    def get_stock_grade(self, symbol: str) -> Dict:
        """
        Get stock grade and consensus from FMP
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
        
        Returns:
            Dictionary containing grade information
        """
        cache_key = f"fmp_grade_{symbol}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            params = {'symbol': symbol}
            data = self._make_request('grades-consensus', params, self.STABLE_URL)
            
            # Cache results for 4 hours
            cache.set(cache_key, data, 14400)
            
            return data
            
        except Exception as e:
            logger.error(f"FMP grade retrieval failed for {symbol}: {e}")
            return {}
    
    def get_company_logo_url(self, symbol: str, prefer_local: bool = True) -> str:
        """
        Get company logo URL - prefer local static files if available
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            prefer_local: If True, return local static URL if logo exists locally
        
        Returns:
            URL to company logo image (local static or FMP URL)
        """
        if prefer_local:
            # Check if local logo exists
            local_logo_url = self.get_local_logo_url(symbol)
            if local_logo_url:
                return local_logo_url
        
        # Fallback to FMP URL
        return f"{self.IMAGE_URL}/{symbol.upper()}.png"
    
    def get_local_logo_url(self, symbol: str) -> str:
        """
        Get local static URL for logo if it exists
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Local static URL if logo exists, empty string otherwise
        """
        from pathlib import Path
        from django.conf import settings
        
        # Check in static directory
        static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
        base_dir = getattr(settings, 'BASE_DIR', None)
        
        # Possible logo locations
        possible_paths = []
        
        # Add STATIC_ROOT if it exists
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root:
            possible_paths.append(Path(static_root) / 'soulstrader' / 'images' / 'logos' / f'{symbol.upper()}.png')
        
        # Add app static directory
        if base_dir:
            possible_paths.append(Path(base_dir) / 'soulstrader' / 'static' / 'soulstrader' / 'images' / 'logos' / f'{symbol.upper()}.png')
        
        # Add STATICFILES_DIRS
        for static_dir in static_dirs:
            possible_paths.append(Path(static_dir) / 'soulstrader' / 'images' / 'logos' / f'{symbol.upper()}.png')
        
        # Check if any of these paths exist
        for path in possible_paths:
            if path.exists():
                return f'/static/soulstrader/images/logos/{symbol.upper()}.png'
        
        return ""
    
    def get_analyst_estimates(self, symbol: str) -> Dict:
        """
        Get analyst estimates for a stock
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary containing analyst estimates
        """
        cache_key = f"fmp_estimates_{symbol}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Use v3 endpoint for analyst estimates (stable doesn't have this endpoint)
            data = self._make_request(f'analyst-estimates/{symbol}')
            
            # Cache results for 6 hours
            cache.set(cache_key, data, 21600)
            
            return data
            
        except Exception as e:
            logger.error(f"FMP analyst estimates failed for {symbol}: {e}")
            return {}
    
    def get_price_target(self, symbol: str) -> Dict:
        """
        Get price target consensus for a stock
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary containing price target information
        """
        cache_key = f"fmp_price_target_{symbol}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Use v3 endpoint for price target consensus (stable doesn't have this endpoint)
            data = self._make_request(f'price-target-consensus')
            
            # Filter for specific symbol if data is a list
            if isinstance(data, list):
                data = [item for item in data if item.get('symbol') == symbol.upper()]
                data = data[0] if data else {}
            
            # Cache results for 4 hours
            cache.set(cache_key, data, 14400)
            
            return data
            
        except Exception as e:
            logger.error(f"FMP price target failed for {symbol}: {e}")
            return {}
    
    def update_stock_with_fmp_data(self, stock: Stock) -> bool:
        """
        Update a Stock instance with FMP API data
        
        Args:
            stock: Stock model instance to update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = stock.symbol
            
            # Get grade data
            grade_data = self.get_stock_grade(symbol)
            if grade_data:
                # Parse grade data (structure may vary)
                if isinstance(grade_data, list) and grade_data:
                    grade_info = grade_data[0]
                elif isinstance(grade_data, dict):
                    grade_info = grade_data
                else:
                    grade_info = {}
                
                # Update fields based on available data
                if 'grade' in grade_info:
                    stock.fmp_grade = grade_info['grade']
                if 'score' in grade_info:
                    stock.fmp_score = Decimal(str(grade_info['score']))
            
            # Get price target data
            price_target_data = self.get_price_target(symbol)
            if price_target_data and 'targetHigh' in price_target_data:
                stock.analyst_target_price = Decimal(str(price_target_data['targetHigh']))
            
            # Set logo URL
            stock.logo_url = self.get_company_logo_url(symbol)
            
            # Save the updated stock
            stock.save()
            
            logger.info(f"Successfully updated {symbol} with FMP data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update stock {stock.symbol} with FMP data: {e}")
            return False
    
    def create_recommendation_from_grade(self, stock: Stock, advisor: AIAdvisor) -> Optional[AIAdvisorRecommendation]:
        """
        Create an AI recommendation based on FMP grade data
        
        Args:
            stock: Stock instance
            advisor: AIAdvisor instance (should be FMP type)
        
        Returns:
            AIAdvisorRecommendation instance or None
        """
        try:
            grade_data = self.get_stock_grade(stock.symbol)
            if not grade_data:
                return None
            
            # Parse grade data
            if isinstance(grade_data, list) and grade_data:
                grade_info = grade_data[0]
            elif isinstance(grade_data, dict):
                grade_info = grade_data
            else:
                return None
            
            # Map FMP grade to recommendation type
            grade = grade_info.get('grade', '').upper()
            recommendation_mapping = {
                'A+': 'STRONG_BUY',
                'A': 'STRONG_BUY',
                'A-': 'BUY',
                'B+': 'BUY',
                'B': 'HOLD',
                'B-': 'HOLD',
                'C+': 'SELL',
                'C': 'SELL',
                'C-': 'STRONG_SELL',
                'D': 'STRONG_SELL',
                'F': 'STRONG_SELL',
            }
            
            recommendation_type = recommendation_mapping.get(grade, 'HOLD')
            
            # Calculate confidence based on grade
            confidence_mapping = {
                'STRONG_BUY': ('VERY_HIGH', 0.9),
                'BUY': ('HIGH', 0.75),
                'HOLD': ('MEDIUM', 0.5),
                'SELL': ('HIGH', 0.75),
                'STRONG_SELL': ('VERY_HIGH', 0.9),
            }
            
            confidence_level, confidence_score = confidence_mapping.get(recommendation_type, ('MEDIUM', 0.5))
            
            # Create recommendation
            recommendation = AIAdvisorRecommendation.objects.create(
                advisor=advisor,
                stock=stock,
                recommendation_type=recommendation_type,
                confidence_level=confidence_level,
                confidence_score=Decimal(str(confidence_score)),
                price_at_recommendation=stock.current_price or Decimal('0'),
                reasoning=f"FMP Grade: {grade}. " + grade_info.get('description', 'Grade-based recommendation from Financial Modeling Prep.'),
                key_factors=[f"FMP Grade: {grade}"],
                raw_response=grade_info
            )
            
            logger.info(f"Created FMP recommendation for {stock.symbol}: {recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to create FMP recommendation for {stock.symbol}: {e}")
            return None
    
    def bulk_update_stocks(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Update multiple stocks with FMP data
        
        Args:
            symbols: List of stock symbols to update
        
        Returns:
            Dictionary mapping symbol to success status
        """
        results = {}
        
        for symbol in symbols:
            try:
                stock = Stock.objects.get(symbol=symbol.upper())
                results[symbol] = self.update_stock_with_fmp_data(stock)
            except Stock.DoesNotExist:
                logger.warning(f"Stock {symbol} not found in database")
                results[symbol] = False
            except Exception as e:
                logger.error(f"Error updating stock {symbol}: {e}")
                results[symbol] = False
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test FMP API connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Simple search test
            result = self.search_stocks("AAPL", limit=1)
            return len(result) > 0
        except Exception as e:
            logger.error(f"FMP API connection test failed: {e}")
            return False


# Convenience function for easy import
def get_fmp_service(api_key: str = None) -> FMPAPIService:
    """Get FMP API service instance"""
    return FMPAPIService(api_key=api_key)
