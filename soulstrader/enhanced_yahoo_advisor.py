"""
Enhanced Yahoo Finance Advisor for SOULTRADER
Uses Yahoo Finance data to create comprehensive fundamental analysis
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from .models import AIAdvisorRecommendation
from .ai_advisor_service import BaseAIAdvisor
import logging

logger = logging.getLogger(__name__)


class EnhancedYahooAdvisor(BaseAIAdvisor):
    """Enhanced Yahoo Finance advisor with comprehensive fundamental analysis"""
    
    def get_recommendation(self, stock):
        """Get recommendation based on Yahoo Finance fundamental data"""
        if not self.can_make_request():
            return None
        
        try:
            # Get comprehensive data from Yahoo Finance
            ticker = yf.Ticker(stock.symbol)
            info = ticker.info
            history = ticker.history(period="3mo")
            financials = ticker.financials
            
            # Analyze the data
            recommendation_data = self.analyze_yahoo_data(stock, info, history, financials)
            
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
                raw_response={'yahoo_info': self.sanitize_info(info)},
                processing_time=Decimal('1.0')
            )
            
            logger.info(f"Enhanced Yahoo recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Enhanced Yahoo error for {stock.symbol}: {e}")
            return None
    
    def sanitize_info(self, info):
        """Remove non-serializable data from Yahoo info"""
        sanitized = {}
        for key, value in info.items():
            try:
                # Test if value is JSON serializable
                import json
                json.dumps(value)
                sanitized[key] = value
            except (TypeError, ValueError):
                sanitized[key] = str(value)
        return sanitized
    
    def analyze_yahoo_data(self, stock, info, history, financials):
        """Comprehensive analysis using Yahoo Finance data"""
        try:
            current_price = float(stock.current_price) if stock.current_price else info.get('currentPrice', 100)
            
            # Initialize scoring
            score = 0
            factors = []
            risks = []
            
            # 1. VALUATION ANALYSIS
            pe_ratio = info.get('trailingPE')
            if pe_ratio:
                if pe_ratio < 15:
                    score += 2
                    factors.append(f"Attractive P/E ratio: {pe_ratio:.1f}")
                elif pe_ratio < 25:
                    score += 1
                    factors.append(f"Reasonable P/E ratio: {pe_ratio:.1f}")
                elif pe_ratio > 35:
                    score -= 1
                    risks.append(f"High P/E ratio: {pe_ratio:.1f} suggests overvaluation")
            
            # 2. PROFITABILITY ANALYSIS
            roe = info.get('returnOnEquity')
            if roe:
                if roe > 0.2:  # >20% ROE
                    score += 2
                    factors.append(f"Excellent ROE: {roe:.1%}")
                elif roe > 0.15:  # >15% ROE
                    score += 1
                    factors.append(f"Strong ROE: {roe:.1%}")
                elif roe < 0.05:  # <5% ROE
                    score -= 1
                    risks.append(f"Low ROE: {roe:.1%}")
            
            # 3. FINANCIAL HEALTH
            debt_to_equity = info.get('debtToEquity')
            if debt_to_equity is not None:
                debt_ratio = debt_to_equity / 100  # Convert percentage
                if debt_ratio < 0.3:
                    score += 1
                    factors.append(f"Low debt-to-equity: {debt_ratio:.2f}")
                elif debt_ratio > 1.0:
                    score -= 1
                    risks.append(f"High debt-to-equity: {debt_ratio:.2f}")
            
            # 4. GROWTH ANALYSIS
            revenue_growth = info.get('revenueGrowth')
            if revenue_growth:
                if revenue_growth > 0.15:  # >15% growth
                    score += 2
                    factors.append(f"Strong revenue growth: {revenue_growth:.1%}")
                elif revenue_growth > 0.05:  # >5% growth
                    score += 1
                    factors.append(f"Positive revenue growth: {revenue_growth:.1%}")
                elif revenue_growth < -0.05:  # Declining revenue
                    score -= 2
                    risks.append(f"Declining revenue: {revenue_growth:.1%}")
            
            # 5. MOMENTUM ANALYSIS (from history)
            if not history.empty and len(history) >= 20:
                # 20-day momentum
                current_close = history['Close'].iloc[-1]
                twenty_day_ago = history['Close'].iloc[-20]
                momentum_20d = (current_close - twenty_day_ago) / twenty_day_ago
                
                if momentum_20d > 0.1:  # >10% in 20 days
                    score += 1
                    factors.append(f"Strong 20-day momentum: {momentum_20d:.1%}")
                elif momentum_20d < -0.1:  # <-10% in 20 days
                    score -= 1
                    risks.append(f"Negative 20-day momentum: {momentum_20d:.1%}")
                
                # Volatility analysis
                returns = history['Close'].pct_change().dropna()
                volatility = returns.std() * (252 ** 0.5)  # Annualized volatility
                
                if volatility > 0.4:  # >40% annual volatility
                    risks.append(f"High volatility: {volatility:.1%} annually")
                elif volatility < 0.2:  # <20% annual volatility
                    factors.append(f"Low volatility: {volatility:.1%} annually")
            
            # 6. DIVIDEND ANALYSIS
            dividend_yield = info.get('dividendYield')
            if dividend_yield and dividend_yield > 0:
                if dividend_yield > 0.03:  # >3% yield
                    score += 1
                    factors.append(f"Attractive dividend yield: {dividend_yield:.1%}")
                else:
                    factors.append(f"Dividend yield: {dividend_yield:.1%}")
            
            # 7. MARKET POSITION
            market_cap = info.get('marketCap')
            if market_cap:
                if market_cap > 500_000_000_000:  # >$500B mega-cap
                    factors.append("Mega-cap market leader")
                elif market_cap > 10_000_000_000:  # >$10B large-cap
                    factors.append("Large-cap stability")
                elif market_cap < 2_000_000_000:  # <$2B small-cap
                    risks.append("Small-cap volatility risk")
            
            # 8. ANALYST TARGETS (if available)
            target_high = info.get('targetHighPrice')
            target_mean = info.get('targetMeanPrice')
            target_low = info.get('targetLowPrice')
            
            if target_mean:
                upside = (target_mean - current_price) / current_price
                if upside > 0.15:
                    score += 2
                    factors.append(f"Strong analyst upside: {upside:.1%} to ${target_mean:.2f}")
                elif upside > 0.05:
                    score += 1
                    factors.append(f"Moderate upside: {upside:.1%} to ${target_mean:.2f}")
                elif upside < -0.1:
                    score -= 1
                    risks.append(f"Price above analyst target: {upside:.1%}")
            
            # DETERMINE RECOMMENDATION
            if score >= 6:
                recommendation_type = 'STRONG_BUY'
                confidence_level = 'VERY_HIGH'
                confidence_score = 0.9
            elif score >= 3:
                recommendation_type = 'BUY'
                confidence_level = 'HIGH'
                confidence_score = 0.75
            elif score >= 0:
                recommendation_type = 'HOLD'
                confidence_level = 'MEDIUM'
                confidence_score = 0.5
            elif score >= -3:
                recommendation_type = 'SELL'
                confidence_level = 'MEDIUM'
                confidence_score = 0.65
            else:
                recommendation_type = 'STRONG_SELL'
                confidence_level = 'HIGH'
                confidence_score = 0.8
            
            # Calculate target price
            target_price = None
            if target_mean:
                target_price = Decimal(str(target_mean))
            elif recommendation_type in ['STRONG_BUY', 'BUY']:
                # Estimate based on score
                upside_estimate = 0.15 if recommendation_type == 'STRONG_BUY' else 0.10
                target_price = Decimal(str(current_price * (1 + upside_estimate)))
            
            # Generate comprehensive reasoning
            # Format values safely
            pe_str = f"{pe_ratio:.1f}" if pe_ratio else "N/A"
            market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
            roe_str = f"{roe:.1%}" if roe else "N/A"
            revenue_growth_str = f"{revenue_growth:.1%}" if revenue_growth else "N/A"
            debt_ratio_str = f"{debt_to_equity/100:.2f}" if debt_to_equity else "N/A"
            target_mean_str = f"${target_mean:.2f}" if target_mean else "N/A"
            target_low_str = f"${target_low:.2f}" if target_low else "N/A"
            target_high_str = f"${target_high:.2f}" if target_high else "N/A"
            
            reasoning = f"""
Enhanced Yahoo Finance Analysis for {stock.symbol}:

VALUATION METRICS:
- P/E Ratio: {pe_str}
- Market Cap: {market_cap_str}
- Price-to-Book: {info.get('priceToBook', 'N/A')}

PROFITABILITY:
- ROE: {roe_str}
- Profit Margin: {info.get('profitMargins', 'N/A')}
- Revenue Growth: {revenue_growth_str}

FINANCIAL HEALTH:
- Debt-to-Equity: {debt_ratio_str}
- Current Ratio: {info.get('currentRatio', 'N/A')}
- Cash per Share: ${info.get('totalCashPerShare', 'N/A')}

ANALYST TARGETS:
- Target Mean: {target_mean_str}
- Target Range: {target_low_str} - {target_high_str}

Analysis Score: {score}/8
Recommendation based on comprehensive fundamental analysis using real Yahoo Finance data.
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
                    'roe': roe,
                    'debt_to_equity': debt_to_equity,
                    'revenue_growth': revenue_growth,
                    'market_cap': market_cap,
                    'analysis_score': score,
                    'data_source': 'yahoo_finance_comprehensive'
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Enhanced Yahoo analysis: {e}")
            return {
                'recommendation_type': 'HOLD',
                'confidence_level': 'LOW',
                'confidence_score': 0.3,
                'reasoning': f"Analysis error: {str(e)}",
                'key_factors': [],
                'risk_factors': ['Analysis failed due to data issues']
            }
