"""
Demo AI Advisor Service for SOULTRADER
Simulates AI advisor recommendations for testing without API keys
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from .models import AIAdvisorRecommendation
from .ai_advisor_service import BaseAIAdvisor
import logging

logger = logging.getLogger(__name__)


class DemoAIAdvisor(BaseAIAdvisor):
    """Demo AI advisor that generates realistic recommendations without API calls"""
    
    def get_recommendation(self, stock):
        """Generate a demo recommendation based on stock characteristics"""
        try:
            # Simulate processing time
            import time
            time.sleep(0.5)  # Simulate API call delay
            
            # Generate recommendation based on stock price movement and characteristics
            recommendation_data = self.generate_demo_recommendation(stock)
            
            # Update usage (simulate API call)
            self.update_usage()
            
            # Create recommendation record
            recommendation = AIAdvisorRecommendation.objects.create(
                advisor=self.advisor,
                stock=stock,
                recommendation_type=recommendation_data['recommendation_type'],
                confidence_level=recommendation_data['confidence_level'],
                confidence_score=recommendation_data['confidence_score'],
                target_price=recommendation_data.get('target_price'),
                stop_loss=recommendation_data.get('stop_loss'),
                price_at_recommendation=stock.current_price,
                reasoning=recommendation_data['reasoning'],
                key_factors=recommendation_data.get('key_factors', []),
                risk_factors=recommendation_data.get('risk_factors', []),
                technical_indicators=recommendation_data.get('technical_indicators', {}),
                raw_response={'demo_mode': True, 'generated_at': str(timezone.now())},
                processing_time=Decimal('0.5')
            )
            
            logger.info(f"Demo recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Demo advisor error for {stock.symbol}: {e}")
            return None
    
    def generate_demo_recommendation(self, stock):
        """Generate realistic demo recommendation based on stock data"""
        
        # Get stock characteristics
        current_price = float(stock.current_price) if stock.current_price else 100.0
        day_change_percent = float(stock.day_change_percent) if stock.day_change_percent else 0.0
        
        # Simulate different advisor personalities
        advisor_profiles = {
            'Financial Modeling Prep': {
                'focus': 'fundamental',
                'conservative': True,
                'weight_pe': 0.3,
                'weight_growth': 0.4,
                'weight_debt': 0.3
            },
            'Finnhub Market Intelligence': {
                'focus': 'analyst_consensus',
                'conservative': False,
                'weight_momentum': 0.4,
                'weight_target': 0.4,
                'weight_sentiment': 0.2
            },
            'OpenAI GPT-3.5': {
                'focus': 'comprehensive',
                'conservative': False,
                'weight_technical': 0.3,
                'weight_fundamental': 0.3,
                'weight_sentiment': 0.4
            }
        }
        
        profile = advisor_profiles.get(self.advisor.name, advisor_profiles['OpenAI GPT-3.5'])
        
        # Generate recommendation based on advisor profile and stock data
        score = 0
        factors = []
        risks = []
        
        # Price momentum analysis
        if day_change_percent > 2:
            score += 2
            factors.append(f"Strong positive momentum: +{day_change_percent:.2f}% today")
        elif day_change_percent > 0:
            score += 1
            factors.append(f"Positive momentum: +{day_change_percent:.2f}% today")
        elif day_change_percent < -2:
            score -= 2
            risks.append(f"Negative momentum: {day_change_percent:.2f}% today")
        elif day_change_percent < 0:
            score -= 1
            factors.append(f"Minor decline: {day_change_percent:.2f}% today")
        
        # Simulate sector analysis
        sector_strength = {
            'TECHNOLOGY': 2,
            'HEALTHCARE': 1,
            'FINANCIAL': 0,
            'CONSUMER_DISCRETIONARY': -1,
            'ENERGY': -2
        }
        
        sector_score = sector_strength.get(stock.sector, 0)
        score += sector_score
        
        if sector_score > 0:
            factors.append(f"{stock.get_sector_display()} sector showing strength")
        elif sector_score < 0:
            risks.append(f"{stock.get_sector_display()} sector facing headwinds")
        
        # Simulate market cap analysis
        if stock.market_cap_category == 'LARGE_CAP':
            factors.append("Large-cap stability and liquidity")
        elif stock.market_cap_category == 'SMALL_CAP':
            factors.append("Small-cap growth potential")
            risks.append("Higher volatility risk")
        
        # Add advisor-specific analysis
        if profile['focus'] == 'fundamental':
            # FMP-style fundamental analysis
            pe_estimate = random.uniform(15, 30)
            if pe_estimate < 20:
                score += 1
                factors.append(f"Attractive estimated P/E ratio: {pe_estimate:.1f}")
            else:
                risks.append(f"High estimated P/E ratio: {pe_estimate:.1f}")
            
            debt_ratio = random.uniform(0.1, 0.8)
            if debt_ratio < 0.4:
                factors.append(f"Conservative debt levels: {debt_ratio:.2f}")
            else:
                risks.append(f"Elevated debt ratio: {debt_ratio:.2f}")
                
        elif profile['focus'] == 'analyst_consensus':
            # Finnhub-style analyst consensus
            buy_percentage = random.uniform(0.3, 0.9)
            if buy_percentage > 0.6:
                score += 2
                factors.append(f"Strong analyst support: {buy_percentage:.1%} buy ratings")
            else:
                score -= 1
                risks.append(f"Mixed analyst sentiment: {buy_percentage:.1%} buy ratings")
            
            target_upside = random.uniform(-0.1, 0.25)
            if target_upside > 0.1:
                factors.append(f"Analyst price targets suggest {target_upside:.1%} upside")
            elif target_upside < 0:
                risks.append(f"Price above analyst targets by {abs(target_upside):.1%}")
        
        else:
            # Comprehensive AI analysis
            factors.extend([
                "Technical indicators showing consolidation",
                "Market sentiment remains cautiously optimistic",
                "Institutional buying activity detected"
            ])
            
            if random.random() > 0.5:
                risks.append("General market volatility concerns")
        
        # Add some randomness for realism
        score += random.randint(-1, 1)
        
        # Determine recommendation
        if score >= 3:
            recommendation_type = 'STRONG_BUY'
            confidence_level = 'HIGH'
            confidence_score = random.uniform(0.75, 0.95)
        elif score >= 1:
            recommendation_type = 'BUY'
            confidence_level = 'MEDIUM' if score == 1 else 'HIGH'
            confidence_score = random.uniform(0.6, 0.8)
        elif score >= -1:
            recommendation_type = 'HOLD'
            confidence_level = 'MEDIUM'
            confidence_score = random.uniform(0.4, 0.6)
        elif score >= -3:
            recommendation_type = 'SELL'
            confidence_level = 'MEDIUM'
            confidence_score = random.uniform(0.55, 0.75)
        else:
            recommendation_type = 'STRONG_SELL'
            confidence_level = 'HIGH'
            confidence_score = random.uniform(0.7, 0.9)
        
        # Calculate target price
        target_price = None
        if recommendation_type in ['STRONG_BUY', 'BUY']:
            upside = random.uniform(0.05, 0.25)
            target_price = Decimal(str(current_price * (1 + upside)))
        elif recommendation_type in ['SELL', 'STRONG_SELL']:
            downside = random.uniform(0.05, 0.20)
            target_price = Decimal(str(current_price * (1 - downside)))
        
        # Generate reasoning
        reasoning = f"""
{self.advisor.name} Analysis for {stock.symbol}:

Current Price: ${current_price:.2f}
Sector: {stock.get_sector_display() if stock.sector else 'Unknown'}
Market Cap: {stock.get_market_cap_category_display() if stock.market_cap_category else 'Unknown'}

Analysis Focus: {profile['focus'].replace('_', ' ').title()}
Overall Score: {score}/5

This {recommendation_type.lower().replace('_', ' ')} recommendation is based on 
{profile['focus'].replace('_', ' ')} analysis considering current market conditions,
sector trends, and company-specific factors.

Note: This is a demo recommendation for testing purposes.
        """.strip()
        
        return {
            'recommendation_type': recommendation_type,
            'confidence_level': confidence_level,
            'confidence_score': confidence_score,
            'target_price': target_price,
            'reasoning': reasoning,
            'key_factors': factors,
            'risk_factors': risks,
            'technical_indicators': {
                'analysis_score': score,
                'day_change_percent': day_change_percent,
                'advisor_focus': profile['focus']
            }
        }
