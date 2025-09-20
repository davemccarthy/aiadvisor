"""
Market Screening Service for SOULTRADER
Provides proactive stock recommendations from market screening APIs
"""

import requests
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import Stock, AIAdvisor, AIAdvisorRecommendation

logger = logging.getLogger(__name__)


class MarketScreeningService:
    """Service for proactive market screening and stock discovery"""
    
    ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, alpha_vantage_key: str = None):
        """Initialize with Alpha Vantage API key"""
        self.alpha_vantage_key = alpha_vantage_key or getattr(settings, 'ALPHA_VANTAGE_API_KEY', None)
        if not self.alpha_vantage_key:
            raise ValueError("Alpha Vantage API key required for market screening")
    
    def get_market_movers(self) -> Dict:
        """
        Get top gainers, losers, and most active stocks from Alpha Vantage
        
        Returns:
            Dictionary with 'top_gainers', 'top_losers', 'most_actively_traded' lists
        """
        cache_key = "market_movers_alpha_vantage"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            params = {
                'function': 'TOP_GAINERS_LOSERS',
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(self.ALPHA_VANTAGE_BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache for 5 minutes (market data updates frequently)
            cache.set(cache_key, data, 300)
            
            logger.info("Successfully retrieved market movers from Alpha Vantage")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market movers: {e}")
            return {}
    
    def get_top_gainers(self, limit: int = 10) -> List[Dict]:
        """Get top gaining stocks"""
        market_data = self.get_market_movers()
        gainers = market_data.get('top_gainers', [])
        return gainers[:limit]
    
    def get_top_losers(self, limit: int = 10) -> List[Dict]:
        """Get top losing stocks"""
        market_data = self.get_market_movers()
        losers = market_data.get('top_losers', [])
        return losers[:limit]
    
    def get_most_active(self, limit: int = 10) -> List[Dict]:
        """Get most actively traded stocks"""
        market_data = self.get_market_movers()
        most_active = market_data.get('most_actively_traded', [])
        return most_active[:limit]
    
    def create_proactive_recommendations(self, category: str = 'gainers', limit: int = 5) -> List[Dict]:
        """
        Create proactive stock recommendations based on market screening
        
        Args:
            category: 'gainers', 'losers', or 'active'
            limit: Maximum number of recommendations
            
        Returns:
            List of recommendation dictionaries
        """
        try:
            # Get market data
            if category == 'gainers':
                stocks = self.get_top_gainers(limit)
                recommendation_type = 'BUY'
                confidence = 'MEDIUM'
                reasoning_prefix = "Top market gainer"
            elif category == 'losers':
                stocks = self.get_top_losers(limit)
                recommendation_type = 'STRONG_SELL'  # Or could be BUY for contrarian strategy
                confidence = 'LOW'
                reasoning_prefix = "Top market loser - potential contrarian opportunity"
            elif category == 'active':
                stocks = self.get_most_active(limit)
                recommendation_type = 'HOLD'
                confidence = 'MEDIUM'
                reasoning_prefix = "High trading volume - market attention"
            else:
                logger.error(f"Invalid category: {category}")
                return []
            
            recommendations = []
            
            for stock_data in stocks:
                try:
                    symbol = stock_data.get('ticker', '').upper()
                    if not symbol:
                        continue
                    
                    # Get or create stock in database
                    stock, created = Stock.objects.get_or_create(
                        symbol=symbol,
                        defaults={'name': symbol + ' Corporation'}
                    )
                    
                    # If stock was created, try to get additional info
                    if created:
                        try:
                            from .yahoo_finance_service import YahooMarketDataManager
                            YahooMarketDataManager.update_stock_quote(symbol)
                        except Exception as e:
                            logger.warning(f"Could not update stock info for {symbol}: {e}")
                    
                    # Build recommendation data
                    price = stock_data.get('price', '0').replace('$', '')
                    change_percent = stock_data.get('change_percentage', '0%').replace('%', '')
                    volume = stock_data.get('volume', '0')
                    
                    try:
                        price_decimal = Decimal(price)
                        change_percent_decimal = Decimal(change_percent)
                    except (ValueError, TypeError):
                        price_decimal = Decimal('0')
                        change_percent_decimal = Decimal('0')
                    
                    recommendation = {
                        'stock': stock,
                        'symbol': symbol,
                        'recommendation_type': recommendation_type,
                        'confidence_level': confidence,
                        'confidence_score': 0.6,
                        'current_price': price_decimal,
                        'change_percent': change_percent_decimal,
                        'volume': volume,
                        'reasoning': f"{reasoning_prefix}: {symbol} - {change_percent}% change, volume: {volume}",
                        'source': 'Market Screening',
                        'category': category
                    }
                    
                    recommendations.append(recommendation)
                    
                except Exception as e:
                    logger.error(f"Error processing stock {stock_data}: {e}")
                    continue
            
            logger.info(f"Created {len(recommendations)} proactive {category} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to create proactive recommendations: {e}")
            return []
    
    def save_proactive_recommendations(self, category: str = 'gainers', limit: int = 5) -> int:
        """
        Save proactive recommendations to database
        
        Returns:
            Number of recommendations saved
        """
        try:
            # Get market screening advisor
            advisor, created = AIAdvisor.objects.get_or_create(
                advisor_type='MARKET_SCREENING',
                defaults={
                    'name': 'Market Screening Service',
                    'description': 'Proactive recommendations from market screening APIs',
                    'is_enabled': True
                }
            )
            
            if created:
                logger.info("Created Market Screening advisor")
            
            # Get recommendations
            recommendations = self.create_proactive_recommendations(category, limit)
            
            saved_count = 0
            
            for rec_data in recommendations:
                try:
                    # Check if recommendation already exists for today
                    existing = AIAdvisorRecommendation.objects.filter(
                        advisor=advisor,
                        stock=rec_data['stock'],
                        created_at__date=timezone.now().date()
                    ).exists()
                    
                    if existing:
                        logger.debug(f"Recommendation for {rec_data['symbol']} already exists today")
                        continue
                    
                    # Create recommendation
                    recommendation = AIAdvisorRecommendation.objects.create(
                        advisor=advisor,
                        stock=rec_data['stock'],
                        recommendation_type=rec_data['recommendation_type'],
                        confidence_level=rec_data['confidence_level'],
                        confidence_score=Decimal(str(rec_data['confidence_score'])),
                        price_at_recommendation=rec_data['current_price'],
                        reasoning=rec_data['reasoning'],
                        key_factors=[
                            f"Change: {rec_data['change_percent']}%",
                            f"Volume: {rec_data['volume']}",
                            f"Category: {rec_data['category']}"
                        ],
                        raw_response={
                            'source': rec_data['source'],
                            'category': rec_data['category'],
                            'volume': rec_data['volume'],
                            'change_percent': str(rec_data['change_percent'])
                        }
                    )
                    
                    saved_count += 1
                    logger.info(f"Saved proactive recommendation: {rec_data['symbol']} - {rec_data['recommendation_type']}")
                    
                except Exception as e:
                    logger.error(f"Failed to save recommendation for {rec_data.get('symbol', 'unknown')}: {e}")
                    continue
            
            # Update advisor usage
            advisor.daily_api_calls += 1
            advisor.last_api_call = timezone.now()
            advisor.save()
            
            logger.info(f"Saved {saved_count} proactive {category} recommendations")
            return saved_count
            
        except Exception as e:
            logger.error(f"Failed to save proactive recommendations: {e}")
            return 0
    
    def get_market_summary(self) -> Dict:
        """Get a summary of current market conditions"""
        try:
            market_data = self.get_market_movers()
            
            if not market_data:
                return {}
            
            # Analyze market sentiment
            gainers = market_data.get('top_gainers', [])
            losers = market_data.get('top_losers', [])
            
            # Calculate average changes
            gainer_changes = []
            loser_changes = []
            
            for gainer in gainers[:10]:
                try:
                    change = float(gainer.get('change_percentage', '0%').replace('%', ''))
                    gainer_changes.append(change)
                except ValueError:
                    continue
            
            for loser in losers[:10]:
                try:
                    change = float(loser.get('change_percentage', '0%').replace('%', ''))
                    loser_changes.append(abs(change))  # Use absolute value
                except ValueError:
                    continue
            
            avg_gainer_change = sum(gainer_changes) / len(gainer_changes) if gainer_changes else 0
            avg_loser_change = sum(loser_changes) / len(loser_changes) if loser_changes else 0
            
            # Determine market sentiment
            if avg_gainer_change > avg_loser_change:
                sentiment = 'BULLISH'
            elif avg_loser_change > avg_gainer_change:
                sentiment = 'BEARISH'
            else:
                sentiment = 'NEUTRAL'
            
            return {
                'sentiment': sentiment,
                'avg_gainer_change': avg_gainer_change,
                'avg_loser_change': avg_loser_change,
                'top_gainer': gainers[0]['ticker'] if gainers else None,
                'top_loser': losers[0]['ticker'] if losers else None,
                'last_updated': market_data.get('last_updated', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            return {}


# Convenience function
def get_market_screening_service() -> MarketScreeningService:
    """Get market screening service instance"""
    return MarketScreeningService()
