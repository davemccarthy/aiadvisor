"""
IEX Cloud Advisor for SOULTRADER
Provides real market data and fundamental analysis from IEX Cloud
"""

import requests
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from .models import AIAdvisorRecommendation
from .ai_advisor_service import BaseAIAdvisor
import logging

logger = logging.getLogger(__name__)


class IEXCloudAdvisor(BaseAIAdvisor):
    """IEX Cloud advisor implementation"""
    
    BASE_URL = "https://cloud.iexapis.com/stable"
    SANDBOX_URL = "https://sandbox.iexapis.com/stable"
    
    def get_recommendation(self, stock):
        """Get stock recommendation from IEX Cloud analysis"""
        if not self.can_make_request():
            return None
        
        try:
            # Get comprehensive data from IEX Cloud
            quote_data = self.get_quote(stock.symbol)
            stats_data = self.get_key_stats(stock.symbol)
            financials_data = self.get_financials(stock.symbol)
            
            # Analyze the data
            recommendation_data = self.analyze_iex_data(
                stock, quote_data, stats_data, financials_data
            )
            
            # Update usage
            self.update_usage()
            
            # Create recommendation record
            recommendation = AIAdvisorRecommendation.objects.create(
                advisor=self.advisor,
                stock=stock,
                recommendation_type=recommendation_data['recommendation_type'],
                confidence_level=recommendation_data['confidence_level'],
                confidence_score=recommendation_data['confidence_score'],
                target_price=recommendation_data.get('target_price'),
                price_at_recommendation=stock.current_price,
                reasoning=recommendation_data['reasoning'],
                key_factors=recommendation_data.get('key_factors', []),
                risk_factors=recommendation_data.get('risk_factors', []),
                technical_indicators=recommendation_data.get('technical_indicators', {}),
                raw_response={
                    'quote': quote_data,
                    'stats': stats_data,
                    'financials': financials_data
                },
                processing_time=Decimal('1.0')
            )
            
            logger.info(f"IEX Cloud recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"IEX Cloud API error for {stock.symbol}: {e}")
            return None
    
    def get_quote(self, symbol):
        """Get real-time quote from IEX Cloud"""
        url = f"{self.BASE_URL}/stock/{symbol}/quote"
        params = {'token': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_key_stats(self, symbol):
        """Get key statistics from IEX Cloud"""
        url = f"{self.BASE_URL}/stock/{symbol}/stats"
        params = {'token': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_financials(self, symbol):
        """Get financial data from IEX Cloud"""
        url = f"{self.BASE_URL}/stock/{symbol}/financials"
        params = {'token': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def analyze_iex_data(self, stock, quote, stats, financials):
        """Analyze IEX Cloud data and generate recommendation"""
        try:
            current_price = float(stock.current_price) if stock.current_price else quote.get('latestPrice', 100)
            
            score = 0
            factors = []
            risks = []
            
            # 1. MOMENTUM ANALYSIS
            change_percent = quote.get('changePercent', 0)
            if change_percent > 0.02:  # >2%
                score += 2
                factors.append(f"Strong daily momentum: +{change_percent:.1%}")
            elif change_percent > 0:
                score += 1
                factors.append(f"Positive momentum: +{change_percent:.1%}")
            elif change_percent < -0.02:
                score -= 1
                risks.append(f"Negative momentum: {change_percent:.1%}")
            
            # 2. VALUATION ANALYSIS
            pe_ratio = stats.get('peRatio')
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 15:
                    score += 2
                    factors.append(f"Attractive P/E ratio: {pe_ratio:.1f}")
                elif pe_ratio < 25:
                    score += 1
                    factors.append(f"Reasonable P/E ratio: {pe_ratio:.1f}")
                elif pe_ratio > 35:
                    score -= 1
                    risks.append(f"High P/E ratio: {pe_ratio:.1f}")
            
            # 3. MARKET PERFORMANCE
            week52_high = stats.get('week52high')
            week52_low = stats.get('week52low')
            if week52_high and week52_low:
                position_in_range = (current_price - week52_low) / (week52_high - week52_low)
                
                if position_in_range > 0.8:  # Near 52-week high
                    factors.append(f"Near 52-week high ({position_in_range:.1%} of range)")
                elif position_in_range < 0.2:  # Near 52-week low
                    score += 1
                    factors.append(f"Near 52-week low - potential value ({position_in_range:.1%} of range)")
            
            # 4. FINANCIAL HEALTH
            debt_to_equity = stats.get('debtToEquity')
            if debt_to_equity is not None:
                if debt_to_equity < 0.5:
                    score += 1
                    factors.append(f"Low debt-to-equity: {debt_to_equity:.2f}")
                elif debt_to_equity > 1.5:
                    score -= 1
                    risks.append(f"High debt-to-equity: {debt_to_equity:.2f}")
            
            # 5. PROFITABILITY
            profit_margin = stats.get('profitMargin')
            if profit_margin and profit_margin > 0:
                if profit_margin > 0.2:  # >20% margin
                    score += 2
                    factors.append(f"Excellent profit margin: {profit_margin:.1%}")
                elif profit_margin > 0.1:  # >10% margin
                    score += 1
                    factors.append(f"Good profit margin: {profit_margin:.1%}")
            
            # 6. GROWTH METRICS
            revenue_per_share = stats.get('revenuePerShare')
            revenue_per_employee = stats.get('revenuePerEmployee')
            
            if revenue_per_employee and revenue_per_employee > 500000:  # >$500k per employee
                score += 1
                factors.append(f"High revenue efficiency: ${revenue_per_employee:,.0f} per employee")
            
            # 7. MARKET CAP ANALYSIS
            market_cap = stats.get('marketcap')
            if market_cap:
                if market_cap > 500_000_000_000:  # >$500B
                    factors.append("Mega-cap market leader")
                elif market_cap > 10_000_000_000:  # >$10B
                    factors.append("Large-cap stability")
                elif market_cap < 2_000_000_000:  # <$2B
                    risks.append("Small-cap volatility")
            
            # 8. DIVIDEND ANALYSIS
            dividend_yield = stats.get('dividendYield')
            if dividend_yield and dividend_yield > 0:
                if dividend_yield > 0.03:  # >3%
                    score += 1
                    factors.append(f"Attractive dividend yield: {dividend_yield:.1%}")
            
            # DETERMINE RECOMMENDATION
            if score >= 5:
                recommendation_type = 'STRONG_BUY'
                confidence_level = 'VERY_HIGH'
                confidence_score = 0.85
            elif score >= 3:
                recommendation_type = 'BUY'
                confidence_level = 'HIGH'
                confidence_score = 0.75
            elif score >= 0:
                recommendation_type = 'HOLD'
                confidence_level = 'MEDIUM'
                confidence_score = 0.5
            elif score >= -2:
                recommendation_type = 'SELL'
                confidence_level = 'MEDIUM'
                confidence_score = 0.6
            else:
                recommendation_type = 'STRONG_SELL'
                confidence_level = 'HIGH'
                confidence_score = 0.8
            
            # Calculate target price
            target_price = None
            if recommendation_type in ['STRONG_BUY', 'BUY']:
                upside = 0.15 if recommendation_type == 'STRONG_BUY' else 0.10
                target_price = Decimal(str(current_price * (1 + upside)))
            elif recommendation_type in ['SELL', 'STRONG_SELL']:
                downside = 0.10 if recommendation_type == 'SELL' else 0.15
                target_price = Decimal(str(current_price * (1 - downside)))
            
            reasoning = f"""
IEX Cloud Professional Analysis for {stock.symbol}:

MARKET DATA:
- Current Price: ${current_price:.2f}
- Daily Change: {change_percent:.1%}
- 52-Week Range: ${week52_low:.2f if week52_low else 'N/A'} - ${week52_high:.2f if week52_high else 'N/A'}
- Volume: {quote.get('latestVolume', 'N/A'):,}

VALUATION:
- P/E Ratio: {pe_ratio:.1f if pe_ratio else 'N/A'}
- Market Cap: ${market_cap:,.0f if market_cap else 'N/A'}
- Debt/Equity: {debt_to_equity:.2f if debt_to_equity else 'N/A'}

PROFITABILITY:
- Profit Margin: {profit_margin:.1% if profit_margin else 'N/A'}
- Revenue/Share: ${revenue_per_share:.2f if revenue_per_share else 'N/A'}
- Revenue/Employee: ${revenue_per_employee:,.0f if revenue_per_employee else 'N/A'}

Analysis Score: {score}/8
Professional market data analysis using IEX Cloud's institutional-grade data.
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
                    'pe_ratio': pe_ratio,
                    'debt_to_equity': debt_to_equity,
                    'profit_margin': profit_margin,
                    'market_cap': market_cap,
                    'change_percent': change_percent,
                    'analysis_score': score,
                    'data_source': 'iex_cloud_professional'
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing IEX Cloud data: {e}")
            return {
                'recommendation_type': 'HOLD',
                'confidence_level': 'LOW',
                'confidence_score': 0.3,
                'reasoning': f"IEX Cloud analysis error: {str(e)}",
                'key_factors': [],
                'risk_factors': ['Data analysis failed']
            }
