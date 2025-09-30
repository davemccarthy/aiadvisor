"""
AI Advisor Service for SOULTRADER
Manages multiple AI advisors and aggregates their recommendations
"""

from openai import OpenAI
import google.generativeai as genai
import requests
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import (
    AIAdvisor, AIAdvisorRecommendation, ConsensusRecommendation, 
    Stock, Trade, Portfolio
)
from .yahoo_finance_service import YahooFinanceService
import logging

logger = logging.getLogger(__name__)


class BaseAIAdvisor:
    """Base class for AI advisor implementations"""
    
    def __init__(self, advisor_model):
        self.advisor = advisor_model
        self.api_key = advisor_model.api_key
    
    def can_make_request(self):
        """Check if advisor can make a request"""
        return self.advisor.can_make_request()
    
    def get_recommendation(self, stock):
        """Get recommendation for a stock - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_recommendation")
    
    def update_usage(self):
        """Update API usage statistics"""
        self.advisor.daily_api_calls += 1
        self.advisor.monthly_api_calls += 1
        self.advisor.last_api_call = timezone.now()
        self.advisor.save()
    
    def parse_recommendation_response(self, response_text):
        """Parse AI response into structured recommendation"""
        # This would be implemented differently for each AI service
        # For now, return a basic structure
        return {
            'recommendation_type': 'HOLD',
            'confidence_level': 'MEDIUM',
            'confidence_score': 0.5,
            'target_price': None,
            'reasoning': response_text,
            'key_factors': [],
            'risk_factors': []
        }


class OpenAIAdvisor(BaseAIAdvisor):
    """OpenAI GPT advisor implementation"""
    
    def __init__(self, advisor_model):
        super().__init__(advisor_model)
    
    def get_recommendation(self, stock):
        """Get stock recommendation from OpenAI GPT"""
        if not self.can_make_request():
            return None
        
        try:
            # Get current stock data
            company_info = YahooFinanceService.get_company_info(stock.symbol)
            historical_data = YahooFinanceService.get_historical_data(stock.symbol, period="1mo")
            
            # Build prompt
            prompt = self.build_analysis_prompt(stock, company_info, historical_data)
            
            start_time = time.time()
            
            # Make API call
            client = OpenAI(api_key=self.advisor.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional stock analyst providing investment recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            processing_time = time.time() - start_time
            
            # Update usage
            self.update_usage()
            
            # Parse response
            recommendation_data = self.parse_gpt_response(response.choices[0].message.content)
            
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
                raw_response=response.model_dump(),
                processing_time=Decimal(str(processing_time))
            )
            
            logger.info(f"OpenAI recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"OpenAI API error for {stock.symbol}: {e}")
            self.advisor.status = 'ERROR'
            self.advisor.save()
            return None
    
    def build_analysis_prompt(self, stock, company_info, historical_data):
        """Build analysis prompt for OpenAI"""
        
        # Calculate recent performance
        if historical_data and len(historical_data) > 1:
            recent_change = ((historical_data[-1]['close'] - historical_data[0]['close']) / historical_data[0]['close']) * 100
        else:
            recent_change = 0
        
        prompt = f"""
Analyze {stock.symbol} ({company_info.get('name', stock.name)}) and provide an investment recommendation.

COMPANY INFO:
- Sector: {company_info.get('sector', 'Unknown')}
- Industry: {company_info.get('industry', 'Unknown')}
- Market Cap: ${company_info.get('market_cap', 0):,}
- Current Price: ${stock.current_price}
- P/E Ratio: {company_info.get('pe_ratio', 'N/A')}
- Beta: {company_info.get('beta', 'N/A')}

RECENT PERFORMANCE:
- 30-day change: {recent_change:.2f}%
- 52-week high: ${company_info.get('52_week_high', 'N/A')}
- 52-week low: ${company_info.get('52_week_low', 'N/A')}

Please provide your analysis in this EXACT format:

RECOMMENDATION: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL]
CONFIDENCE: [LOW/MEDIUM/HIGH/VERY_HIGH]
CONFIDENCE_SCORE: [0.0 to 1.0]
TARGET_PRICE: [price or NONE]
STOP_LOSS: [price or NONE]

REASONING:
[Your detailed analysis here]

KEY_FACTORS:
- [Factor 1]
- [Factor 2]
- [Factor 3]

RISK_FACTORS:
- [Risk 1]
- [Risk 2]
- [Risk 3]
"""
        return prompt
    
    def parse_gpt_response(self, response_text):
        """Parse GPT response into structured data"""
        try:
            lines = response_text.strip().split('\n')
            data = {
                'recommendation_type': 'HOLD',
                'confidence_level': 'MEDIUM',
                'confidence_score': 0.5,
                'reasoning': response_text,
                'key_factors': [],
                'risk_factors': []
            }
            
            # Parse structured response
            current_section = None
            for line in lines:
                line = line.strip()
                
                if line.startswith('RECOMMENDATION:'):
                    rec = line.split(':', 1)[1].strip()
                    if rec in ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']:
                        data['recommendation_type'] = rec
                
                elif line.startswith('CONFIDENCE:'):
                    conf = line.split(':', 1)[1].strip()
                    if conf in ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']:
                        data['confidence_level'] = conf
                
                elif line.startswith('CONFIDENCE_SCORE:'):
                    try:
                        score = float(line.split(':', 1)[1].strip())
                        data['confidence_score'] = max(0.0, min(1.0, score))
                    except:
                        pass
                
                elif line.startswith('TARGET_PRICE:'):
                    try:
                        price_str = line.split(':', 1)[1].strip()
                        if price_str != 'NONE':
                            data['target_price'] = Decimal(price_str.replace('$', ''))
                    except:
                        pass
                
                elif line.startswith('STOP_LOSS:'):
                    try:
                        price_str = line.split(':', 1)[1].strip()
                        if price_str != 'NONE':
                            data['stop_loss'] = Decimal(price_str.replace('$', ''))
                    except:
                        pass
                
                elif line.startswith('REASONING:'):
                    current_section = 'reasoning'
                    data['reasoning'] = ''
                
                elif line.startswith('KEY_FACTORS:'):
                    current_section = 'key_factors'
                
                elif line.startswith('RISK_FACTORS:'):
                    current_section = 'risk_factors'
                
                elif line.startswith('- ') and current_section == 'key_factors':
                    data['key_factors'].append(line[2:])
                
                elif line.startswith('- ') and current_section == 'risk_factors':
                    data['risk_factors'].append(line[2:])
                
                elif current_section == 'reasoning' and line:
                    if data['reasoning']:
                        data['reasoning'] += '\n'
                    data['reasoning'] += line
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing GPT response: {e}")
            return {
                'recommendation_type': 'HOLD',
                'confidence_level': 'LOW',
                'confidence_score': 0.3,
                'reasoning': response_text,
                'key_factors': [],
                'risk_factors': []
            }


class GeminiAdvisor(BaseAIAdvisor):
    """Google Gemini advisor implementation"""
    
    def get_recommendation(self, stock):
        """Get stock recommendation from Google Gemini"""
        if not self.can_make_request():
            return None
        
        try:
            # Configure Gemini
            genai.configure(api_key=self.advisor.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Get current stock data
            from .yahoo_finance_service import YahooFinanceService
            company_info = YahooFinanceService.get_company_info(stock.symbol)
            historical_data = YahooFinanceService.get_historical_data(stock.symbol, period="1mo")
            
            # Build prompt
            prompt = self.build_analysis_prompt(stock, company_info, historical_data)
            
            start_time = time.time()
            
            # Make API call
            response = model.generate_content(prompt)
            
            processing_time = time.time() - start_time
            
            # Update usage
            self.update_usage()
            
            # Parse response
            recommendation_data = self.parse_gemini_response(response.text)
            
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
                raw_response={'text': response.text},
                processing_time=Decimal(str(processing_time))
            )
            
            logger.info(f"Gemini recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Gemini API error for {stock.symbol}: {e}")
            self.advisor.status = 'ERROR'
            self.advisor.save()
            return None
    
    def build_analysis_prompt(self, stock, company_info, historical_data):
        """Build analysis prompt for Gemini"""
        
        # Calculate recent performance
        if historical_data and len(historical_data) > 1:
            recent_change = ((historical_data[-1]['close'] - historical_data[0]['close']) / historical_data[0]['close']) * 100
        else:
            recent_change = 0
        
        prompt = f"""
Analyze {stock.symbol} ({company_info.get('name', stock.name)}) and provide an investment recommendation.

Current Stock Information:
- Symbol: {stock.symbol}
- Current Price: ${stock.current_price}
- Sector: {stock.sector}
- Market Cap: {company_info.get('market_cap', 'N/A')}
- Recent 1-month performance: {recent_change:.2f}%

Company Overview:
- Name: {company_info.get('name', stock.name)}
- Industry: {company_info.get('industry', 'N/A')}
- Description: {company_info.get('description', 'N/A')[:500]}

Please provide your analysis in this exact format:

RECOMMENDATION: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL]
CONFIDENCE: [LOW/MEDIUM/HIGH/VERY_HIGH]
CONFIDENCE_SCORE: [0.0-1.0]
TARGET_PRICE: $[price or N/A]
STOP_LOSS: $[price or N/A]

KEY_FACTORS:
- [Factor 1]
- [Factor 2]
- [Factor 3]

RISK_FACTORS:
- [Risk 1]
- [Risk 2]
- [Risk 3]

REASONING:
[Detailed analysis explaining your recommendation]

Focus on fundamental analysis, technical indicators, market conditions, and company-specific factors.
"""
        return prompt
    
    def parse_gemini_response(self, response_text):
        """Parse Gemini response into structured data"""
        try:
            lines = response_text.strip().split('\n')
            data = {
                'recommendation_type': 'HOLD',
                'confidence_level': 'MEDIUM',
                'confidence_score': 0.5,
                'reasoning': response_text,
                'key_factors': [],
                'risk_factors': []
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith('RECOMMENDATION:'):
                    rec = line.split(':', 1)[1].strip()
                    if rec in ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']:
                        data['recommendation_type'] = rec
                elif line.startswith('CONFIDENCE:'):
                    conf = line.split(':', 1)[1].strip()
                    if conf in ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']:
                        data['confidence_level'] = conf
                elif line.startswith('CONFIDENCE_SCORE:'):
                    try:
                        score = float(line.split(':', 1)[1].strip())
                        if 0 <= score <= 1:
                            data['confidence_score'] = score
                    except:
                        pass
                elif line.startswith('TARGET_PRICE:'):
                    try:
                        price_str = line.split(':', 1)[1].strip().replace('$', '').replace('N/A', '')
                        if price_str:
                            data['target_price'] = Decimal(price_str)
                    except:
                        pass
                elif line.startswith('STOP_LOSS:'):
                    try:
                        price_str = line.split(':', 1)[1].strip().replace('$', '').replace('N/A', '')
                        if price_str:
                            data['stop_loss'] = Decimal(price_str)
                    except:
                        pass
                elif line.startswith('KEY_FACTORS:'):
                    current_section = 'key_factors'
                elif line.startswith('RISK_FACTORS:'):
                    current_section = 'risk_factors'
                elif line.startswith('REASONING:'):
                    current_section = 'reasoning'
                    data['reasoning'] = ''
                elif line.startswith('- ') and current_section in ['key_factors', 'risk_factors']:
                    data[current_section].append(line[2:])
                elif current_section == 'reasoning' and line:
                    if data['reasoning']:
                        data['reasoning'] += '\n' + line
                    else:
                        data['reasoning'] = line
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return {
                'recommendation_type': 'HOLD',
                'confidence_level': 'MEDIUM',
                'confidence_score': 0.5,
                'reasoning': response_text,
                'key_factors': [],
                'risk_factors': []
            }


class FMPAdvisor(BaseAIAdvisor):
    """Financial Modeling Prep advisor implementation"""
    
    BASE_URL = "https://financialmodelingprep.com/stable"  # Use stable endpoints (v3 deprecated)
    
    def get_recommendation(self, stock):
        """Get stock recommendation from FMP analysis"""
        if not self.can_make_request():
            return None
        
        try:
            # Get comprehensive data from FMP
            company_data = self.get_company_data(stock.symbol)
            analyst_estimates = self.get_analyst_estimates(stock.symbol)
            financial_ratios = self.get_financial_ratios(stock.symbol)
            
            start_time = time.time()
            
            # Analyze the data and create recommendation
            recommendation_data = self.analyze_fmp_data(
                stock, company_data, analyst_estimates, financial_ratios
            )
            
            processing_time = time.time() - start_time
            
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
                stop_loss=recommendation_data.get('stop_loss'),
                price_at_recommendation=stock.current_price,
                reasoning=recommendation_data['reasoning'],
                key_factors=recommendation_data.get('key_factors', []),
                risk_factors=recommendation_data.get('risk_factors', []),
                technical_indicators=recommendation_data.get('technical_indicators', {}),
                raw_response={
                    'company_data': company_data,
                    'analyst_estimates': analyst_estimates,
                    'financial_ratios': financial_ratios
                },
                processing_time=Decimal(str(processing_time))
            )
            
            logger.info(f"FMP recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"FMP API error for {stock.symbol}: {e}")
            return None
    
    def get_company_data(self, symbol):
        """Get company profile and key metrics from FMP"""
        url = f"{self.BASE_URL}/profile"
        params = {'symbol': symbol, 'apikey': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_analyst_estimates(self, symbol):
        """Get analyst price targets and recommendations"""
        url = f"{self.BASE_URL}/analyst-estimates"
        params = {'symbol': symbol, 'apikey': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_financial_ratios(self, symbol):
        """Get financial ratios for analysis"""
        url = f"{self.BASE_URL}/ratios"
        params = {'symbol': symbol, 'apikey': self.api_key, 'limit': 1}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def analyze_fmp_data(self, stock, company_data, analyst_estimates, financial_ratios):
        """Analyze FMP data and generate recommendation"""
        try:
            if not company_data or not isinstance(company_data, list) or len(company_data) == 0:
                return self.default_recommendation("Insufficient company data")
            
            company = company_data[0]
            current_price = stock.current_price
            
            # Fundamental Analysis
            pe_ratio = company.get('pe', 0)
            market_cap = company.get('mktCap', 0)
            debt_to_equity = company.get('debtToEquity', 0)
            roe = company.get('roe', 0)
            
            # Analyst consensus (if available)
            analyst_target = None
            if analyst_estimates and len(analyst_estimates) > 0:
                analyst_target = analyst_estimates[0].get('estimatedRevenueLow', 0)
            
            # Scoring system
            score = 0
            factors = []
            risks = []
            
            # P/E Ratio Analysis
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 15:
                    score += 2
                    factors.append(f"Attractive P/E ratio of {pe_ratio:.1f}")
                elif pe_ratio < 25:
                    score += 1
                    factors.append(f"Reasonable P/E ratio of {pe_ratio:.1f}")
                else:
                    score -= 1
                    risks.append(f"High P/E ratio of {pe_ratio:.1f} suggests overvaluation")
            
            # Debt Analysis
            if debt_to_equity and debt_to_equity > 0:
                if debt_to_equity < 0.3:
                    score += 1
                    factors.append(f"Low debt-to-equity ratio of {debt_to_equity:.2f}")
                elif debt_to_equity > 1.0:
                    score -= 1
                    risks.append(f"High debt-to-equity ratio of {debt_to_equity:.2f}")
            
            # ROE Analysis
            if roe and roe > 0:
                if roe > 0.15:
                    score += 2
                    factors.append(f"Strong ROE of {roe:.1%}")
                elif roe > 0.10:
                    score += 1
                    factors.append(f"Good ROE of {roe:.1%}")
            
            # Market Cap Analysis
            if market_cap:
                if market_cap > 10000000000:  # $10B+
                    factors.append("Large-cap stability")
                elif market_cap < 2000000000:  # <$2B
                    risks.append("Small-cap volatility risk")
            
            # Determine recommendation based on score
            if score >= 3:
                recommendation_type = 'STRONG_BUY'
                confidence_level = 'HIGH'
                confidence_score = 0.8
            elif score >= 1:
                recommendation_type = 'BUY'
                confidence_level = 'MEDIUM'
                confidence_score = 0.65
            elif score >= -1:
                recommendation_type = 'HOLD'
                confidence_level = 'MEDIUM'
                confidence_score = 0.5
            else:
                recommendation_type = 'SELL'
                confidence_level = 'MEDIUM'
                confidence_score = 0.6
            
            # Calculate target price (simple DCF approximation)
            target_price = None
            if analyst_target and analyst_target > 0:
                target_price = Decimal(str(analyst_target))
            elif pe_ratio and pe_ratio > 0:
                # Simple target based on industry average P/E
                industry_pe = 20  # Assumption
                target_price = current_price * Decimal(str(industry_pe / pe_ratio))
            
            reasoning = f"""
FMP Fundamental Analysis for {stock.symbol}:

Company Profile:
- Market Cap: ${market_cap:,} ({company.get('sector', 'N/A')} sector)
- P/E Ratio: {pe_ratio:.1f}
- Debt/Equity: {debt_to_equity:.2f}
- ROE: {roe:.1%}

Analysis Score: {score}/5

The recommendation is based on fundamental analysis of financial ratios, 
debt levels, profitability metrics, and market position.
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
                    'roe': roe,
                    'market_cap': market_cap,
                    'analysis_score': score
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing FMP data: {e}")
            return self.default_recommendation("Analysis error occurred")
    
    def default_recommendation(self, reason):
        """Return default recommendation when analysis fails"""
        return {
            'recommendation_type': 'HOLD',
            'confidence_level': 'LOW',
            'confidence_score': 0.3,
            'reasoning': f"Unable to generate recommendation: {reason}",
            'key_factors': [],
            'risk_factors': ['Insufficient data for analysis']
        }


class FinnhubAdvisor(BaseAIAdvisor):
    """Finnhub advisor implementation"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def get_recommendation(self, stock):
        """Get stock recommendation from Finnhub analysis"""
        if not self.can_make_request():
            return None
        
        try:
            # Get data from Finnhub
            recommendation_trends = self.get_recommendation_trends(stock.symbol)
            price_target = self.get_price_target(stock.symbol)
            company_news = self.get_company_news(stock.symbol)
            basic_financials = self.get_basic_financials(stock.symbol)
            
            start_time = time.time()
            
            # Analyze the data
            recommendation_data = self.analyze_finnhub_data(
                stock, recommendation_trends, price_target, company_news, basic_financials
            )
            
            processing_time = time.time() - start_time
            
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
                raw_response={
                    'recommendation_trends': recommendation_trends,
                    'price_target': price_target,
                    'company_news': company_news[:5] if company_news else [],  # Limit news
                    'basic_financials': basic_financials
                },
                processing_time=Decimal(str(processing_time))
            )
            
            logger.info(f"Finnhub recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Finnhub API error for {stock.symbol}: {e}")
            return None
    
    def get_recommendation_trends(self, symbol):
        """Get analyst recommendation trends"""
        url = f"{self.BASE_URL}/stock/recommendation"
        params = {'symbol': symbol, 'token': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_price_target(self, symbol):
        """Get analyst price targets - using recommendation endpoint as fallback"""
        try:
            # Try price-target endpoint first (requires paid plan)
            url = f"{self.BASE_URL}/stock/price-target"
            params = {'symbol': symbol, 'token': self.api_key}
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to recommendation data for free tier
                logger.warning(f"Price target endpoint failed ({response.status_code}), using recommendation data")
                return None
        except Exception as e:
            logger.warning(f"Price target endpoint error: {e}, using recommendation data")
            return None
    
    def get_company_news(self, symbol):
        """Get recent company news for sentiment analysis"""
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        url = f"{self.BASE_URL}/company-news"
        params = {
            'symbol': symbol,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'token': self.api_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_basic_financials(self, symbol):
        """Get basic financial metrics"""
        url = f"{self.BASE_URL}/stock/metric"
        params = {'symbol': symbol, 'metric': 'all', 'token': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def analyze_finnhub_data(self, stock, rec_trends, price_target, news, financials):
        """Analyze Finnhub data and generate recommendation"""
        try:
            current_price = stock.current_price
            factors = []
            risks = []
            score = 0
            
            # Analyst Recommendation Analysis
            if rec_trends and len(rec_trends) > 0:
                latest_rec = rec_trends[0]  # Most recent
                
                strong_buy = latest_rec.get('strongBuy', 0)
                buy = latest_rec.get('buy', 0)
                hold = latest_rec.get('hold', 0)
                sell = latest_rec.get('sell', 0)
                strong_sell = latest_rec.get('strongSell', 0)
                
                total_recs = strong_buy + buy + hold + sell + strong_sell
                
                if total_recs > 0:
                    buy_percentage = (strong_buy + buy) / total_recs
                    sell_percentage = (sell + strong_sell) / total_recs
                    
                    if buy_percentage > 0.6:
                        score += 2
                        factors.append(f"Strong analyst support: {buy_percentage:.1%} buy ratings")
                    elif buy_percentage > 0.4:
                        score += 1
                        factors.append(f"Moderate analyst support: {buy_percentage:.1%} buy ratings")
                    elif sell_percentage > 0.4:
                        score -= 2
                        risks.append(f"Analyst concern: {sell_percentage:.1%} sell ratings")
            
            # Price Target Analysis (if available)
            if price_target:
                target_mean = price_target.get('targetMean')
                if target_mean and current_price:
                    upside = (target_mean - float(current_price)) / float(current_price)
                    
                    if upside > 0.15:  # >15% upside
                        score += 2
                        factors.append(f"Strong upside potential: {upside:.1%} to target ${target_mean:.2f}")
                    elif upside > 0.05:  # >5% upside
                        score += 1
                        factors.append(f"Moderate upside: {upside:.1%} to target ${target_mean:.2f}")
                    elif upside < -0.10:  # >10% downside
                        score -= 1
                        risks.append(f"Price above target: {upside:.1%} to ${target_mean:.2f}")
            else:
                # No price target data available (free tier limitation)
                factors.append("Price target data not available (free tier limitation)")
            
            # News Sentiment Analysis (basic)
            if news and len(news) > 0:
                positive_news = sum(1 for article in news if article.get('sentiment', 0) > 0.1)
                negative_news = sum(1 for article in news if article.get('sentiment', 0) < -0.1)
                
                if positive_news > negative_news * 2:
                    score += 1
                    factors.append(f"Positive news sentiment ({positive_news} positive vs {negative_news} negative)")
                elif negative_news > positive_news * 2:
                    score -= 1
                    risks.append(f"Negative news sentiment ({negative_news} negative vs {positive_news} positive)")
            else:
                factors.append("News sentiment data not available")
            
            # Financial Metrics
            if financials and 'metric' in financials:
                metrics = financials['metric']
                
                # P/E ratio
                pe_ratio = metrics.get('peNormalizedAnnual')
                if pe_ratio:
                    if pe_ratio < 15:
                        score += 1
                        factors.append(f"Attractive P/E ratio: {pe_ratio:.1f}")
                    elif pe_ratio > 30:
                        score -= 1
                        risks.append(f"High P/E ratio: {pe_ratio:.1f}")
                
                # ROE
                roe = metrics.get('roeRfy')
                if roe and roe > 0.15:
                    score += 1
                    factors.append(f"Strong ROE: {roe:.1%}")
            else:
                factors.append("Financial metrics not available")
            
            # Determine recommendation
            if score >= 4:
                recommendation_type = 'STRONG_BUY'
                confidence_level = 'VERY_HIGH'
                confidence_score = 0.9
            elif score >= 2:
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
            
            # Set target price
            target_price = None
            if price_target and price_target.get('targetMean'):
                target_price = Decimal(str(price_target['targetMean']))
            else:
                # No price target available (free tier limitation)
                target_price = None
            
            reasoning = f"""
Finnhub Market Intelligence Analysis for {stock.symbol}:

Analyst Consensus: {len(rec_trends) if rec_trends else 0} recommendation periods analyzed
Price Target: ${price_target.get('targetMean', 'N/A') if price_target else 'N/A'} (mean)
Recent News: {len(news) if news else 0} articles analyzed
Analysis Score: {score}/6

This recommendation combines analyst consensus, price targets, 
news sentiment, and fundamental metrics from Finnhub's market intelligence.
            """.strip()
            
            return {
                'recommendation_type': recommendation_type,
                'confidence_level': confidence_level,
                'confidence_score': confidence_score,
                'target_price': target_price,
                'reasoning': reasoning,
                'key_factors': factors,
                'risk_factors': risks
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Finnhub data: {e}")
            return {
                'recommendation_type': 'HOLD',
                'confidence_level': 'LOW',
                'confidence_score': 0.3,
                'reasoning': f"Analysis error: {str(e)}",
                'key_factors': [],
                'risk_factors': ['Data analysis failed']
            }


class PolygonAdvisor(BaseAIAdvisor):
    """Polygon.io advisor implementation"""
    
    BASE_URL = "https://api.polygon.io/v2"
    
    def get_recommendation(self, stock):
        """Get stock recommendation from Polygon.io analysis"""
        if not self.can_make_request():
            return None
        
        try:
            start_time = time.time()
            
            # Get stock data from Polygon
            stock_data = self.get_polygon_stock_data(stock.symbol)
            
            if not stock_data:
                return None
            
            # Analyze the data
            recommendation_data = self.analyze_polygon_data(stock, stock_data)
            
            processing_time = time.time() - start_time
            
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
                raw_response=stock_data,
                processing_time=Decimal(str(processing_time))
            )
            
            logger.info(f"Polygon recommendation for {stock.symbol}: {recommendation.recommendation_type}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Polygon API error for {stock.symbol}: {e}")
            self.advisor.status = 'ERROR'
            self.advisor.save()
            return None
    
    def get_polygon_stock_data(self, symbol):
        """Get stock data from Polygon API"""
        try:
            # Get current stock price and basic info
            ticker_url = f"{self.BASE_URL}/aggs/ticker/{symbol}/prev"
            ticker_params = {"apikey": self.api_key}
            
            ticker_response = requests.get(ticker_url, params=ticker_params, timeout=10)
            ticker_response.raise_for_status()
            ticker_data = ticker_response.json()
            
            # Get technical indicators (SMA)
            sma_url = f"{self.BASE_URL}/aggs/ticker/{symbol}/range/1/day/2024-01-01/2024-12-31"
            sma_params = {"apikey": self.api_key, "limit": 50}
            
            sma_response = requests.get(sma_url, params=sma_params, timeout=10)
            sma_response.raise_for_status()
            sma_data = sma_response.json()
            
            return {
                'ticker_data': ticker_data,
                'price_history': sma_data,
                'symbol': symbol
            }
            
        except Exception as e:
            logger.error(f"Error fetching Polygon data for {symbol}: {e}")
            return None
    
    def analyze_polygon_data(self, stock, polygon_data):
        """Analyze Polygon data to generate recommendation"""
        try:
            ticker_data = polygon_data.get('ticker_data', {})
            price_history = polygon_data.get('price_history', {})
            
            # Get current price info
            results = ticker_data.get('results', [])
            if not results:
                return self.default_recommendation("No price data available")
            
            current_data = results[0]
            current_price = current_data.get('c', 0)  # Close price
            volume = current_data.get('v', 0)
            high = current_data.get('h', 0)
            low = current_data.get('l', 0)
            
            # Calculate technical indicators
            price_range = high - low if high and low else 0
            volatility = (price_range / current_price * 100) if current_price else 0
            
            # Get historical data for trend analysis
            historical_results = price_history.get('results', [])
            if len(historical_results) >= 10:
                recent_prices = [r.get('c', 0) for r in historical_results[-10:]]
                sma_10 = sum(recent_prices) / len(recent_prices)
                trend = "bullish" if current_price > sma_10 else "bearish"
            else:
                trend = "neutral"
                sma_10 = current_price
            
            # Generate recommendation based on analysis
            if trend == "bullish" and volatility < 5:
                recommendation_type = "BUY"
                confidence_level = "HIGH"
                confidence_score = 0.75
                target_price = current_price * 1.1
            elif trend == "bullish":
                recommendation_type = "BUY"
                confidence_level = "MEDIUM"
                confidence_score = 0.65
                target_price = current_price * 1.05
            elif trend == "bearish" and volatility > 8:
                recommendation_type = "SELL"
                confidence_level = "MEDIUM"
                confidence_score = 0.60
                target_price = current_price * 0.95
            else:
                recommendation_type = "HOLD"
                confidence_level = "MEDIUM"
                confidence_score = 0.50
                target_price = current_price
            
            key_factors = [
                f"Current price trend: {trend}",
                f"Volatility: {volatility:.1f}%",
                f"Trading volume: {volume:,}" if volume else "Volume data available"
            ]
            
            risk_factors = []
            if volatility > 10:
                risk_factors.append("High volatility detected")
            if volume < 100000:
                risk_factors.append("Low trading volume")
            
            reasoning = f"""
Polygon.io Technical Analysis for {stock.symbol}:

Current Price: ${current_price:.2f}
10-day SMA: ${sma_10:.2f}
Daily Range: ${low:.2f} - ${high:.2f}
Volatility: {volatility:.1f}%
Trend: {trend.capitalize()}

Technical indicators suggest a {recommendation_type.lower()} position based on:
- Price momentum relative to moving average
- Current volatility levels
- Trading volume patterns

Target price reflects expected movement based on technical analysis.
"""
            
            return {
                'recommendation_type': recommendation_type,
                'confidence_level': confidence_level,
                'confidence_score': confidence_score,
                'target_price': Decimal(str(target_price)),
                'reasoning': reasoning.strip(),
                'key_factors': key_factors,
                'risk_factors': risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Polygon data: {e}")
            return self.default_recommendation("Technical analysis failed")
    
    def default_recommendation(self, reason):
        """Return default recommendation when analysis fails"""
        return {
            'recommendation_type': 'HOLD',
            'confidence_level': 'LOW',
            'confidence_score': 0.3,
            'reasoning': f'Polygon.io analysis unavailable: {reason}',
            'key_factors': [],
            'risk_factors': ['Technical analysis failed']
        }


class AIAdvisorManager:
    """Manager for coordinating multiple AI advisors"""
    
    @classmethod
    def get_recommendations_for_stock(cls, stock, user_portfolio=None, check_existing=True):
        """
        Get recommendations from all active advisors for a stock
        
        Args:
            stock: Stock object to analyze
            user_portfolio: Optional user portfolio for context
            check_existing: If True, check for existing recent recommendations first
        """
        recommendations = []
        
        # Check for existing recommendations first (API optimization)
        if check_existing:
            existing_recommendations = cls._get_existing_recommendations(stock)
            if existing_recommendations:
                logger.info(f"Using existing recommendations for {stock.symbol} (API optimization)")
                return existing_recommendations
        
        # Get all active advisors
        advisors = AIAdvisor.objects.filter(is_enabled=True, status='ACTIVE')
        
        for advisor in advisors:
            try:
                # Create advisor instance based on type
                if advisor.advisor_type == 'OPENAI_GPT':
                    advisor_instance = OpenAIAdvisor(advisor)
                elif advisor.advisor_type == 'GEMINI':
                    advisor_instance = GeminiAdvisor(advisor)
                elif advisor.advisor_type == 'FMP':
                    advisor_instance = FMPAdvisor(advisor)
                elif advisor.advisor_type == 'FINNHUB':
                    advisor_instance = FinnhubAdvisor(advisor)
                elif advisor.advisor_type == 'POLYGON':
                    advisor_instance = PolygonAdvisor(advisor)
                elif advisor.advisor_type == 'YAHOO_ENHANCED':
                    from .enhanced_yahoo_advisor import EnhancedYahooAdvisor
                    advisor_instance = EnhancedYahooAdvisor(advisor)
                # Add other advisor types here as we implement them
                else:
                    continue
                
                # Get recommendation
                recommendation = advisor_instance.get_recommendation(stock)
                if recommendation:
                    recommendations.append(recommendation)
                    
                # Rate limiting delay
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error getting recommendation from {advisor.name}: {e}")
                continue
        
        return recommendations
    
    @classmethod
    def _get_existing_recommendations(cls, stock):
        """
        Check for existing recent recommendations for a stock to avoid duplicate API calls
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Check for recommendations from the last 6 hours
        recent_date = timezone.now() - timedelta(hours=6)
        
        existing = AIAdvisorRecommendation.objects.filter(
            stock=stock,
            created_at__gte=recent_date,
            status='ACTIVE'
        ).select_related('advisor')
        
        return list(existing)
    
    @classmethod
    def create_consensus_recommendation(cls, stock, recommendations=None):
        """Create consensus recommendation from multiple advisor recommendations"""
        
        if not recommendations:
            # Get recent recommendations for this stock
            recommendations = AIAdvisorRecommendation.objects.filter(
                stock=stock,
                status='ACTIVE',
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).select_related('advisor')
        
        if not recommendations:
            return None
        
        # Calculate vote counts
        vote_counts = {
            'STRONG_BUY': 0,
            'BUY': 0,
            'HOLD': 0,
            'SELL': 0,
            'STRONG_SELL': 0
        }
        
        total_weight = Decimal('0')
        weighted_score = Decimal('0')
        total_confidence = Decimal('0')
        target_prices = []
        
        for rec in recommendations:
            # Count votes
            vote_counts[rec.recommendation_type] += 1
            
            # Calculate weighted score (-100 to +100)
            weight = rec.advisor.weight
            total_weight += weight
            
            score_map = {
                'STRONG_SELL': -100,
                'SELL': -50,
                'HOLD': 0,
                'BUY': 50,
                'STRONG_BUY': 100
            }
            
            weighted_score += score_map[rec.recommendation_type] * weight
            total_confidence += rec.confidence_score * weight
            
            if rec.target_price:
                target_prices.append(rec.target_price)
        
        # Calculate final metrics
        if total_weight > 0:
            final_weighted_score = weighted_score / total_weight
            average_confidence = total_confidence / total_weight
        else:
            final_weighted_score = 0
            average_confidence = 0
        
        # Determine consensus type
        consensus_type = cls.determine_consensus_type(final_weighted_score, vote_counts)
        
        # Calculate consensus strength
        max_votes = max(vote_counts.values())
        total_votes = sum(vote_counts.values())
        consensus_strength = Decimal(str(max_votes / total_votes)) if total_votes > 0 else Decimal('0')
        
        # Create consensus recommendation
        consensus = ConsensusRecommendation.objects.create(
            stock=stock,
            consensus_type=consensus_type,
            consensus_strength=consensus_strength,
            total_advisors=AIAdvisor.objects.filter(is_enabled=True).count(),
            participating_advisors=len(recommendations),
            strong_buy_votes=vote_counts['STRONG_BUY'],
            buy_votes=vote_counts['BUY'],
            hold_votes=vote_counts['HOLD'],
            sell_votes=vote_counts['SELL'],
            strong_sell_votes=vote_counts['STRONG_SELL'],
            weighted_score=final_weighted_score,
            average_confidence=average_confidence,
            average_target_price=sum(target_prices) / len(target_prices) if target_prices else None,
            price_at_consensus=stock.current_price,
            auto_trade_eligible=cls.is_auto_trade_eligible(consensus_strength, final_weighted_score)
        )
        
        # Link advisor recommendations
        consensus.advisor_recommendations.set(recommendations)
        
        logger.info(f"Created consensus for {stock.symbol}: {consensus_type} ({consensus_strength:.2f} strength)")
        return consensus
    
    @classmethod
    def determine_consensus_type(cls, weighted_score, vote_counts):
        """Determine consensus type based on weighted score and votes"""
        if weighted_score >= 75:
            return 'STRONG_BUY'
        elif weighted_score >= 25:
            return 'BUY'
        elif weighted_score <= -75:
            return 'STRONG_SELL'
        elif weighted_score <= -25:
            return 'SELL'
        elif abs(weighted_score) <= 10:
            return 'HOLD'
        else:
            return 'NO_CONSENSUS'
    
    @classmethod
    def is_auto_trade_eligible(cls, consensus_strength, weighted_score):
        """Determine if consensus is eligible for auto-trading"""
        # Require strong consensus (>60%) and significant weighted score
        return (consensus_strength >= Decimal('0.6') and 
                abs(weighted_score) >= 50)
    
    @classmethod
    def execute_auto_trades(cls, user_portfolio):
        """Execute auto trades based on consensus recommendations"""
        from .trading_service import TradingService
        
        # Get eligible consensus recommendations
        eligible_consensus = ConsensusRecommendation.objects.filter(
            auto_trade_eligible=True,
            auto_trade_executed=False,
            created_at__gte=timezone.now() - timedelta(hours=1)  # Only recent consensus
        )
        
        executed_trades = []
        
        for consensus in eligible_consensus:
            try:
                # Determine trade parameters
                if consensus.consensus_type in ['STRONG_BUY', 'BUY']:
                    trade_type = 'BUY'
                    # Calculate position size (e.g., 1% of portfolio)
                    position_size = user_portfolio.current_capital * Decimal('0.01')
                    quantity = int(position_size / consensus.stock.current_price)
                    
                elif consensus.consensus_type in ['STRONG_SELL', 'SELL']:
                    trade_type = 'SELL'
                    # Sell existing position if any
                    try:
                        holding = user_portfolio.holdings.get(stock=consensus.stock)
                        quantity = holding.quantity
                    except:
                        continue  # No position to sell
                
                else:
                    continue  # No action for HOLD or NO_CONSENSUS
                
                if quantity > 0:
                    # Place trade
                    result = TradingService.place_order(
                        portfolio=user_portfolio,
                        stock=consensus.stock,
                        trade_type=trade_type,
                        quantity=quantity,
                        order_type='MARKET',
                        notes=f'Auto-trade based on AI consensus: {consensus.consensus_type}'
                    )
                    
                    if result['success']:
                        trade = result['trade']
                        consensus.auto_trade_executed = True
                        consensus.auto_trade = trade
                        consensus.save()
                        executed_trades.append(trade)
                        
                        logger.info(f"Executed auto-trade: {trade_type} {quantity} {consensus.stock.symbol}")
                    else:
                        logger.warning(f"Auto-trade failed for {consensus.stock.symbol}: {result['error']}")
            
            except Exception as e:
                logger.error(f"Error executing auto-trade for {consensus.stock.symbol}: {e}")
                continue
        
        return executed_trades
