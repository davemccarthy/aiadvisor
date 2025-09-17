from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta
import requests
from decimal import Decimal
from soulstrader.models import Stock, AIAdvisor, AIAdvisorRecommendation, ConsensusRecommendation
from soulstrader.demo_ai_advisor import DemoAIAdvisor
from soulstrader.ai_advisor_service import AIAdvisorManager


class Command(BaseCommand):
    help = 'Get real AI recommendations using working APIs and demo for others'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Stock symbol to analyze',
        )
        parser.add_argument(
            '--all-stocks',
            action='store_true',
            help='Get recommendations for all active stocks',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Getting Real + Demo AI Recommendations...'))
        
        # Get advisors
        advisors = AIAdvisor.objects.filter(is_enabled=True)
        
        if not advisors.exists():
            self.stdout.write(
                self.style.ERROR('No enabled AI advisors found!')
            )
            return
        
        # Determine stocks to analyze
        if options['symbol']:
            try:
                stocks = [Stock.objects.get(symbol=options['symbol'].upper())]
            except Stock.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Stock {options["symbol"]} not found')
                )
                return
        elif options['all_stocks']:
            stocks = Stock.objects.filter(is_active=True)[:5]
        else:
            # Your portfolio stocks
            symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL']
            stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
        
        total_recommendations = 0
        
        # Analyze each stock
        for i, stock in enumerate(stocks):
            self.stdout.write(f'\n📊 Analyzing {stock.symbol} ({i+1}/{len(stocks)})...')
            
            stock_recommendations = []
            
            # Get recommendations from each advisor
            for advisor in advisors:
                try:
                    if advisor.advisor_type == 'FINNHUB':
                        # Use real Finnhub data
                        recommendation = self.get_real_finnhub_recommendation(advisor, stock)
                    elif advisor.advisor_type == 'YAHOO_ENHANCED':
                        # Use real Yahoo Finance enhanced data
                        from soulstrader.enhanced_yahoo_advisor import EnhancedYahooAdvisor
                        yahoo_advisor = EnhancedYahooAdvisor(advisor)
                        recommendation = yahoo_advisor.get_recommendation(stock)
                    else:
                        # Use demo mode for others (FMP broken, OpenAI needs key)
                        demo_advisor = DemoAIAdvisor(advisor)
                        recommendation = demo_advisor.get_recommendation(stock)
                    
                    if recommendation:
                        mode = "REAL" if advisor.advisor_type in ['FINNHUB', 'YAHOO_ENHANCED'] else "DEMO"
                        self.stdout.write(
                            f'  ✓ {advisor.name} ({mode}): {recommendation.recommendation_type} '
                            f'({recommendation.confidence_level}, {recommendation.confidence_score:.2f})'
                        )
                        if recommendation.target_price:
                            self.stdout.write(f'    Target: ${recommendation.target_price}')
                        
                        stock_recommendations.append(recommendation)
                        total_recommendations += 1
                    
                except Exception as e:
                    self.stdout.write(f'  ✗ {advisor.name}: Error - {e}')
                    continue
            
            # Create consensus
            if stock_recommendations:
                try:
                    consensus = AIAdvisorManager.create_consensus_recommendation(
                        stock, stock_recommendations
                    )
                    if consensus:
                        self.stdout.write(
                            f'  📊 Consensus: {consensus.consensus_type} '
                            f'(strength: {consensus.consensus_strength:.2f})'
                        )
                        if consensus.auto_trade_eligible:
                            self.stdout.write(f'  🤖 Auto-trade eligible!')
                
                except Exception as e:
                    self.stdout.write(f'  ✗ Consensus error: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Complete! Generated {total_recommendations} recommendations.')
        )

    def get_real_finnhub_recommendation(self, advisor, stock):
        """Get real recommendation from Finnhub API"""
        try:
            # Get real analyst recommendations
            rec_url = f'https://finnhub.io/api/v1/stock/recommendation?symbol={stock.symbol}&token={advisor.api_key}'
            rec_response = requests.get(rec_url)
            
            if rec_response.status_code != 200:
                raise Exception(f"Finnhub API error: {rec_response.status_code}")
            
            rec_data = rec_response.json()
            
            if not rec_data:
                raise Exception("No recommendation data available")
            
            # Analyze real analyst data
            latest_rec = rec_data[0]  # Most recent recommendations
            
            strong_buy = latest_rec.get('strongBuy', 0)
            buy = latest_rec.get('buy', 0)
            hold = latest_rec.get('hold', 0)
            sell = latest_rec.get('sell', 0)
            strong_sell = latest_rec.get('strongSell', 0)
            
            total_analysts = strong_buy + buy + hold + sell + strong_sell
            
            if total_analysts == 0:
                raise Exception("No analyst recommendations available")
            
            # Calculate percentages
            buy_percentage = (strong_buy + buy) / total_analysts
            sell_percentage = (sell + strong_sell) / total_analysts
            strong_buy_percentage = strong_buy / total_analysts
            
            # Determine recommendation based on real analyst data
            if strong_buy_percentage > 0.4:  # >40% strong buy
                recommendation_type = 'STRONG_BUY'
                confidence_level = 'VERY_HIGH'
                confidence_score = 0.9
            elif buy_percentage > 0.6:  # >60% buy+strong_buy
                recommendation_type = 'BUY'
                confidence_level = 'HIGH'
                confidence_score = 0.8
            elif buy_percentage > 0.4:  # >40% buy+strong_buy
                recommendation_type = 'BUY'
                confidence_level = 'MEDIUM'
                confidence_score = 0.65
            elif sell_percentage > 0.4:  # >40% sell
                recommendation_type = 'SELL'
                confidence_level = 'MEDIUM'
                confidence_score = 0.7
            else:
                recommendation_type = 'HOLD'
                confidence_level = 'MEDIUM'
                confidence_score = 0.5
            
            # Generate factors based on real data
            factors = [
                f'Real analyst consensus: {total_analysts} analysts',
                f'{strong_buy} Strong Buy, {buy} Buy, {hold} Hold, {sell} Sell ratings',
                f'{buy_percentage:.1%} positive sentiment from analysts'
            ]
            
            risks = []
            if sell_percentage > 0.2:
                risks.append(f'{sell_percentage:.1%} of analysts recommend selling')
            
            # Estimate target price based on current price and recommendation strength
            current_price = float(stock.current_price)
            if recommendation_type in ['STRONG_BUY', 'BUY']:
                upside = 0.15 if recommendation_type == 'STRONG_BUY' else 0.10
                target_price = Decimal(str(current_price * (1 + upside)))
            else:
                target_price = None
            
            reasoning = f'''
Real Finnhub Analyst Consensus for {stock.symbol}:

Total Analysts: {total_analysts}
- Strong Buy: {strong_buy} ({strong_buy_percentage:.1%})
- Buy: {buy} ({buy/total_analysts:.1%})
- Hold: {hold} ({hold/total_analysts:.1%})
- Sell: {sell} ({sell/total_analysts:.1%})
- Strong Sell: {strong_sell}

Overall Sentiment: {buy_percentage:.1%} positive
Period: {latest_rec.get('period', 'Current')}

This recommendation is based on REAL analyst consensus data from Finnhub.
            '''.strip()
            
            # Update advisor usage
            advisor.daily_api_calls += 1
            advisor.last_api_call = timezone.now()
            advisor.save()
            
            # Create recommendation
            recommendation = AIAdvisorRecommendation.objects.create(
                advisor=advisor,
                stock=stock,
                recommendation_type=recommendation_type,
                confidence_level=confidence_level,
                confidence_score=Decimal(str(confidence_score)),
                target_price=target_price,
                price_at_recommendation=stock.current_price,
                reasoning=reasoning,
                key_factors=factors,
                risk_factors=risks,
                technical_indicators={
                    'total_analysts': total_analysts,
                    'strong_buy_count': strong_buy,
                    'buy_count': buy,
                    'hold_count': hold,
                    'sell_count': sell,
                    'buy_percentage': buy_percentage,
                    'data_source': 'real_finnhub_api'
                },
                raw_response=rec_data,
                processing_time=Decimal('0.5')
            )
            
            return recommendation
            
        except Exception as e:
            self.stdout.write(f'    Finnhub API error: {e}')
            # Fallback to demo mode
            demo_advisor = DemoAIAdvisor(advisor)
            return demo_advisor.get_recommendation(stock)
