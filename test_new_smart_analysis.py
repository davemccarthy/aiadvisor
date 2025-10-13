#!/usr/bin/env python3
"""
Test script to compare new Smart Analysis algorithm with existing user7 data.

This script will:
1. Run the new Smart Analysis algorithm on user7's existing recommendations
2. Compare results with previous analysis
3. Show the differences in confidence scores and recommendations
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append('/Users/davidmccarthy/Development/CursorAI/Django/aiadvisor')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiadvisor.settings')
django.setup()

from django.contrib.auth.models import User
from soulstrader.models import AIAdvisorRecommendation, RiskProfile, Portfolio, Holding
from soulstrader.smart_analysis_service import SmartAnalysisService
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_new_analysis_algorithm():
    """Test the new Smart Analysis algorithm against user7's data"""
    
    try:
        # Get user7
        user = User.objects.get(username='user7')
        logger.info(f"Testing with user: {user.username}")
        
        # Get user's risk profile
        try:
            risk_profile = user.risk_profile
            logger.info(f"Risk Profile: min_confidence={risk_profile.min_confidence_score}, "
                       f"sell_weight={risk_profile.sell_weight}")
        except:
            logger.error("No risk profile found for user7")
            return
        
        # Get user's portfolio and holdings
        try:
            portfolio = user.portfolio
            holdings = {h.stock.symbol: h for h in Holding.objects.filter(portfolio=portfolio)}
            logger.info(f"Portfolio: {len(holdings)} holdings, total_value=${portfolio.total_value}")
        except:
            logger.error("No portfolio found for user7")
            return
        
        # Get recommendations from September 29th (testing different date)
        from datetime import date
        sep_29 = date(2025, 9, 29)
        recent_recommendations = AIAdvisorRecommendation.objects.filter(
            created_at__date=sep_29,
            status='ACTIVE'
        ).select_related('stock', 'advisor').order_by('stock__symbol', 'advisor__name')
        
        logger.info(f"Found {recent_recommendations.count()} recent recommendations")
        
        if not recent_recommendations.exists():
            logger.warning("No recent recommendations found")
            return
        
        # Initialize Smart Analysis Service
        smart_service = SmartAnalysisService()
        
        # Run new analysis
        logger.info("Running new Smart Analysis algorithm...")
        consolidated = smart_service._consolidate_recommendations(
            user=user,
            advisor_recommendations=list(recent_recommendations),
            holdings=holdings,
            risk_profile=risk_profile
        )
        
        # Display results
        logger.info(f"\n=== NEW ANALYSIS RESULTS ===")
        logger.info(f"Total recommendations: {len(consolidated)}")
        
        sell_count = sum(1 for r in consolidated if r['recommendation_type'] == 'SELL')
        buy_count = sum(1 for r in consolidated if r['recommendation_type'] == 'BUY')
        
        logger.info(f"SELL recommendations: {sell_count}")
        logger.info(f"BUY recommendations: {buy_count}")
        
        # Show detailed results
        logger.info(f"\n=== DETAILED RECOMMENDATIONS ===")
        for i, rec in enumerate(consolidated[:10], 1):  # Show first 10
            stock = rec['stock']
            logger.info(f"{i}. {stock.symbol} - {rec['recommendation_type']}")
            logger.info(f"   Confidence: {rec['confidence_score']:.3f}")
            logger.info(f"   Buy Avg: {rec['buy_avg']:.3f}, Sell Avg: {rec['sell_avg']:.3f}")
            logger.info(f"   Net Signal: {rec['net_signal']:.3f}")
            logger.info(f"   Price: ${rec['current_price']:.2f}")
            if rec['existing_shares'] > 0:
                logger.info(f"   Owned: {rec['existing_shares']} shares (${rec['position_value']:.2f})")
            logger.info("")
        
        # Show HOLD range thresholds
        lower_threshold, upper_threshold = smart_service._get_hold_range_thresholds(risk_profile)
        logger.info(f"\n=== HOLD RANGE THRESHOLDS ===")
        logger.info(f"Lower threshold (SELL): {lower_threshold:.2f}")
        logger.info(f"Upper threshold (BUY): {upper_threshold:.2f}")
        logger.info(f"HOLD range: [{lower_threshold:.2f}, {upper_threshold:.2f}]")
        
        # Compare with old algorithm (if we can find previous results)
        logger.info(f"\n=== COMPARISON WITH PREVIOUS ALGORITHM ===")
        logger.info("New algorithm uses:")
        logger.info("- Average confidence scores instead of totals")
        logger.info("- HOLD range logic instead of bidirectional offset")
        logger.info("- Two-pass analysis (SELL first, then BUY)")
        logger.info("- Market Sentiment + Risk Level for thresholds")
        
        return consolidated
        
    except User.DoesNotExist:
        logger.error("user7 not found")
    except Exception as e:
        logger.error(f"Error running test: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_confidence_score_changes():
    """Analyze how confidence scores changed with the new algorithm"""
    
    logger.info(f"\n=== CONFIDENCE SCORE ANALYSIS ===")
    
    # Example scenarios to demonstrate the difference
    scenarios = [
        {
            'name': 'Weak Consensus (Old vs New)',
            'old_total': Decimal('0.90'),  # 3 × 30%
            'new_avg': Decimal('0.30'),    # Average of 30%
            'description': '3 advisors @ 30% each'
        },
        {
            'name': 'Strong Consensus (Old vs New)', 
            'old_total': Decimal('0.90'),  # 1 × 90%
            'new_avg': Decimal('0.90'),    # Average of 90%
            'description': '1 advisor @ 90%'
        },
        {
            'name': 'Mixed Signals (Old vs New)',
            'old_total': Decimal('1.20'),  # 2 × 60%
            'new_avg': Decimal('0.60'),    # Average of 60%
            'description': '2 advisors @ 60% each'
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"\n{scenario['name']}: {scenario['description']}")
        logger.info(f"  Old algorithm (totals): {scenario['old_total']:.2f}")
        logger.info(f"  New algorithm (averages): {scenario['new_avg']:.2f}")
        logger.info(f"  Difference: {scenario['new_avg'] - scenario['old_total']:.2f}")

if __name__ == "__main__":
    logger.info("Starting Smart Analysis Algorithm Test")
    logger.info("=" * 50)
    
    # Run the test
    results = test_new_analysis_algorithm()
    
    # Analyze confidence score changes
    analyze_confidence_score_changes()
    
    logger.info("\nTest completed!")
