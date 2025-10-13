#!/usr/bin/env python3
"""
Discovery Source Performance Analysis Script
Analyzes the performance of stocks discovered from different sources
to identify patterns like Alpha Vantage "bounce" behavior
"""

import os
import sys
import django
from decimal import Decimal
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q

# Setup Django
sys.path.append('/Users/davidmccarthy/Development/CursorAI/Django/aiadvisor')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiadvisor.settings')
django.setup()

from django.contrib.auth.models import User
from soulstrader.models import (
    Stock, Portfolio, Holding, AIAdvisorRecommendation, 
    SmartAnalysisSession, SmartRecommendation, RiskProfile
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

def analyze_discovery_sources():
    """Analyze performance patterns by discovery source"""
    logger.info("=== DISCOVERY SOURCE PERFORMANCE ANALYSIS ===")
    
    # Get all stocks with discovery source information using raw SQL to avoid decimal issues
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('''
        SELECT symbol, 
               COALESCE(discovery_source, 'alpha_vantage') as discovery_source,
               COALESCE(discovery_method, 'market_movers') as discovery_method,
               current_price, market_cap, sector, day_change_percent
        FROM soulstrader_stock 
        WHERE is_active = 1
    ''')
    stocks_data = cursor.fetchall()
    
    logger.info(f"Found {len(stocks_data)} stocks with discovery source tracking")
    
    # Group by discovery source
    source_stats = {}
    for symbol, discovery_source, discovery_method, current_price, market_cap, sector, day_change_percent in stocks_data:
        source = discovery_source
        
        if source not in source_stats:
            source_stats[source] = {
                'stocks': [],
                'methods': set(),
                'total_count': 0,
                'avg_price': 0,
                'avg_market_cap': 0,
                'sector_distribution': {},
                'recommendations': [],
                'smart_recommendations': []
            }
        
        source_stats[source]['stocks'].append({
            'symbol': symbol,
            'discovery_method': discovery_method,
            'current_price': current_price,
            'market_cap': market_cap,
            'sector': sector,
            'day_change_percent': day_change_percent
        })
        source_stats[source]['methods'].add(discovery_method)
        source_stats[source]['total_count'] += 1
        
        # Track sector distribution
        sector = sector or 'UNKNOWN'
        if sector not in source_stats[source]['sector_distribution']:
            source_stats[source]['sector_distribution'][sector] = 0
        source_stats[source]['sector_distribution'][sector] += 1
    
    # Analyze each source
    for source, stats in source_stats.items():
        logger.info(f"\n=== {source.upper()} ANALYSIS ===")
        logger.info(f"Total stocks: {stats['total_count']}")
        logger.info(f"Discovery methods: {', '.join(stats['methods'])}")
        
        # Calculate averages
        prices = [float(s['current_price']) for s in stats['stocks'] if s['current_price']]
        market_caps = [float(s['market_cap']) for s in stats['stocks'] if s['market_cap']]
        
        if prices:
            avg_price = sum(prices) / len(prices)
            logger.info(f"Average price: ${avg_price:.2f}")
        
        if market_caps:
            avg_market_cap = sum(market_caps) / len(market_caps)
            logger.info(f"Average market cap: ${avg_market_cap:,.0f}")
        
        # Sector distribution
        logger.info("Sector distribution:")
        for sector, count in sorted(stats['sector_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats['total_count']) * 100
            logger.info(f"  {sector}: {count} ({percentage:.1f}%)")
        
        # Get recommendations for these stocks
        stock_symbols = [s['symbol'] for s in stats['stocks']]
        recommendations = AIAdvisorRecommendation.objects.filter(
            stock__symbol__in=stock_symbols,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('stock', 'advisor')
        
        logger.info(f"Recent recommendations (30 days): {recommendations.count()}")
        
        if recommendations.exists():
            # Analyze recommendation types
            rec_types = recommendations.values('recommendation_type').annotate(count=Count('id'))
            logger.info("Recommendation breakdown:")
            for rec_type in rec_types:
                logger.info(f"  {rec_type['recommendation_type']}: {rec_type['count']}")
            
            # Analyze confidence scores
            avg_confidence = recommendations.aggregate(avg=Avg('confidence_score'))['avg']
            if avg_confidence:
                logger.info(f"Average confidence score: {avg_confidence:.3f}")
        
        # Get Smart Analysis recommendations
        smart_recs = SmartRecommendation.objects.filter(
            stock__symbol__in=stock_symbols,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('stock')
        
        logger.info(f"Smart Analysis recommendations (30 days): {smart_recs.count()}")
        
        if smart_recs.exists():
            smart_types = smart_recs.values('recommendation_type').annotate(count=Count('id'))
            logger.info("Smart Analysis breakdown:")
            for smart_type in smart_types:
                logger.info(f"  {smart_type['recommendation_type']}: {smart_type['count']}")
    
    # Analyze "bounce" patterns for Alpha Vantage
    logger.info(f"\n=== ALPHA VANTAGE 'BOUNCE' ANALYSIS ===")
    
    # Get Alpha Vantage stocks using raw SQL
    cursor.execute('''
        SELECT symbol, current_price, day_change_percent, market_cap
        FROM soulstrader_stock 
        WHERE discovery_source = 'alpha_vantage'
    ''')
    alpha_stocks_data = cursor.fetchall()
    
    if alpha_stocks_data:
        logger.info(f"Analyzing {len(alpha_stocks_data)} Alpha Vantage stocks for bounce patterns...")
        
        # Look for stocks with high volatility (price changes)
        volatile_stocks = []
        for symbol, current_price, day_change_percent, market_cap in alpha_stocks_data:
            if current_price and day_change_percent:
                # High volatility = large daily changes
                if abs(float(day_change_percent)) > 5.0:  # >5% daily change
                    volatile_stocks.append({
                        'symbol': symbol,
                        'price': current_price,
                        'day_change': day_change_percent,
                        'market_cap': market_cap
                    })
        
        logger.info(f"Found {len(volatile_stocks)} highly volatile Alpha Vantage stocks (>5% daily change)")
        
        # Sort by volatility
        volatile_stocks.sort(key=lambda x: abs(float(x['day_change'])), reverse=True)
        
        logger.info("Top 10 most volatile Alpha Vantage stocks:")
        for i, stock in enumerate(volatile_stocks[:10]):
            logger.info(f"  {i+1}. {stock['symbol']}: ${stock['price']:.2f} "
                       f"({stock['day_change']:+.2f}%)")
        
        # Analyze if these volatile stocks tend to have lower confidence scores
        volatile_symbols = [s['symbol'] for s in volatile_stocks]
        volatile_recs = AIAdvisorRecommendation.objects.filter(
            stock__symbol__in=volatile_symbols,
            created_at__gte=timezone.now() - timedelta(days=7)
        )
        
        if volatile_recs.exists():
            avg_volatile_confidence = volatile_recs.aggregate(avg=Avg('confidence_score'))['avg']
            logger.info(f"Average confidence for volatile Alpha Vantage stocks: {avg_volatile_confidence:.3f}")
            
            # Compare with non-volatile Alpha Vantage stocks
            non_volatile_symbols = [s.symbol for s in alpha_stocks if s.symbol not in volatile_symbols]
            if non_volatile_symbols:
                non_volatile_recs = AIAdvisorRecommendation.objects.filter(
                    stock__symbol__in=non_volatile_symbols,
                    created_at__gte=timezone.now() - timedelta(days=7)
                )
                if non_volatile_recs.exists():
                    avg_non_volatile_confidence = non_volatile_recs.aggregate(avg=Avg('confidence_score'))['avg']
                    logger.info(f"Average confidence for stable Alpha Vantage stocks: {avg_non_volatile_confidence:.3f}")
                    
                    if avg_volatile_confidence and avg_non_volatile_confidence:
                        diff = avg_non_volatile_confidence - avg_volatile_confidence
                        logger.info(f"Confidence difference (stable - volatile): {diff:.3f}")
                        if diff > 0.1:
                            logger.info("⚠️  Volatile Alpha Vantage stocks tend to have LOWER confidence scores!")
                        elif diff < -0.1:
                            logger.info("✅ Volatile Alpha Vantage stocks tend to have HIGHER confidence scores!")
                        else:
                            logger.info("📊 No significant difference in confidence between volatile and stable stocks")
    
    # Summary recommendations
    logger.info(f"\n=== SUMMARY & RECOMMENDATIONS ===")
    
    if 'alpha_vantage' in source_stats and 'yahoo_finance' in source_stats:
        alpha_count = source_stats['alpha_vantage']['total_count']
        yahoo_count = source_stats['yahoo_finance']['total_count']
        
        logger.info(f"Discovery source distribution:")
        logger.info(f"  Alpha Vantage: {alpha_count} stocks")
        logger.info(f"  Yahoo Finance: {yahoo_count} stocks")
        
        if alpha_count > yahoo_count * 2:
            logger.info("⚠️  Alpha Vantage dominates discovery - consider balancing sources")
        elif yahoo_count > alpha_count * 2:
            logger.info("⚠️  Yahoo Finance dominates discovery - consider balancing sources")
        else:
            logger.info("✅ Good balance between discovery sources")
    
    logger.info("\nAnalysis completed!")

if __name__ == '__main__':
    analyze_discovery_sources()
