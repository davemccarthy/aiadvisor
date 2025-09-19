from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from soulstrader.models import (
    Stock, StockPrice, UserProfile, Portfolio, Holding, Trade,
    AIRecommendation, UserNotification
)
from soulstrader.trading_service import TradingService
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Create sample data for SOULTRADER'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data for SOULTRADER...')
        
        # Create sample stocks
        self.create_sample_stocks()
        
        # Create sample stock prices
        self.create_sample_prices()
        
        # Create sample user if doesn't exist
        sample_user = self.create_sample_user()
        
        # Create sample recommendations
        self.create_sample_recommendations(sample_user)
        
        # Create sample notifications
        self.create_sample_notifications(sample_user)
        
        # Create sample trades
        self.create_sample_trades(sample_user)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )

    def create_sample_stocks(self):
        """Create sample stocks"""
        stocks_data = [
            {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'sector': 'TECHNOLOGY',
                'industry': 'Consumer Electronics',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('175.50'),
                'pe_ratio': Decimal('28.5'),
                'esg_score': Decimal('8.2')
            },
            {
                'symbol': 'MSFT',
                'name': 'Microsoft Corporation',
                'sector': 'TECHNOLOGY',
                'industry': 'Software',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('378.85'),
                'pe_ratio': Decimal('32.1'),
                'esg_score': Decimal('8.7')
            },
            {
                'symbol': 'TSLA',
                'name': 'Tesla Inc.',
                'sector': 'CONSUMER_DISCRETIONARY',
                'industry': 'Electric Vehicles',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('248.42'),
                'pe_ratio': Decimal('65.2'),
                'esg_score': Decimal('9.1')
            },
            {
                'symbol': 'JNJ',
                'name': 'Johnson & Johnson',
                'sector': 'HEALTHCARE',
                'industry': 'Pharmaceuticals',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('158.73'),
                'pe_ratio': Decimal('15.8'),
                'esg_score': Decimal('7.9')
            },
            {
                'symbol': 'AMZN',
                'name': 'Amazon.com Inc.',
                'sector': 'CONSUMER_DISCRETIONARY',
                'industry': 'E-commerce',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('151.94'),
                'pe_ratio': Decimal('45.3'),
                'esg_score': Decimal('6.8')
            },
            {
                'symbol': 'GOOGL',
                'name': 'Alphabet Inc.',
                'sector': 'COMMUNICATION',
                'industry': 'Internet Services',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('142.56'),
                'pe_ratio': Decimal('25.4'),
                'esg_score': Decimal('7.5')
            },
            {
                'symbol': 'NVDA',
                'name': 'NVIDIA Corporation',
                'sector': 'TECHNOLOGY',
                'industry': 'Semiconductors',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('875.28'),
                'pe_ratio': Decimal('68.9'),
                'esg_score': Decimal('8.9')
            },
            {
                'symbol': 'JPM',
                'name': 'JPMorgan Chase & Co.',
                'sector': 'FINANCIAL',
                'industry': 'Banking',
                'market_cap_category': 'LARGE_CAP',
                'current_price': Decimal('172.45'),
                'pe_ratio': Decimal('11.2'),
                'esg_score': Decimal('6.2')
            }
        ]
        
        for stock_data in stocks_data:
            stock, created = Stock.objects.get_or_create(
                symbol=stock_data['symbol'],
                defaults=stock_data
            )
            if created:
                self.stdout.write(f'Created stock: {stock.symbol}')
            else:
                self.stdout.write(f'Stock already exists: {stock.symbol}')

    def create_sample_prices(self):
        """Create sample historical prices for stocks"""
        stocks = Stock.objects.all()
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        for stock in stocks:
            current_price = stock.current_price
            if not current_price:
                continue
                
            # Generate 30 days of price data
            for i in range(30):
                price_date = start_date + timedelta(days=i)
                
                # Skip weekends
                if price_date.weekday() >= 5:
                    continue
                
                # Generate realistic price movement
                daily_change = Decimal(str(random.uniform(-0.05, 0.05)))  # ±5% daily change
                price = current_price * (Decimal('1') + daily_change)
                
                # Create price data
                StockPrice.objects.get_or_create(
                    stock=stock,
                    date=price_date,
                    defaults={
                        'open_price': price * Decimal(str(random.uniform(0.98, 1.02))),
                        'high_price': price * Decimal(str(random.uniform(1.01, 1.05))),
                        'low_price': price * Decimal(str(random.uniform(0.95, 0.99))),
                        'close_price': price,
                        'volume': random.randint(1000000, 10000000),
                        'adjusted_close': price
                    }
                )
        
        self.stdout.write('Created sample price data')

    def create_sample_user(self):
        """Create a sample user for testing"""
        username = 'testuser'
        email = 'test@example.com'
        password = 'testpass123'
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f'Created test user: {username}')
        else:
            self.stdout.write(f'Test user already exists: {username}')
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'risk_level': 'MODERATE',
                'investment_goal': 'BALANCED',
                'time_horizon': 'MEDIUM',
                'initial_capital': Decimal('100000.00'),
                'max_positions': 20,
                'preferred_sectors': ['TECHNOLOGY', 'HEALTHCARE'],
                'esg_focused': True,
                'esg_score_minimum': Decimal('7.0')
            }
        )
        
        # Create portfolio
        portfolio, created = Portfolio.objects.get_or_create(
            user=user,
            defaults={
                'name': f"{user.username}'s Portfolio",
                'initial_capital': Decimal('100000.00'),
                'current_capital': Decimal('100000.00')
            }
        )
        
        return user

    def create_sample_recommendations(self, user):
        """Create sample AI recommendations"""
        stocks = Stock.objects.all()[:5]  # Get first 5 stocks
        
        recommendations_data = [
            {
                'stock': stocks[0],  # AAPL
                'recommendation_type': 'BUY',
                'confidence_level': 'HIGH',
                'confidence_score': Decimal('0.85'),
                'target_price': Decimal('185.00'),
                'reasoning': 'Strong technical indicators show bullish momentum. Apple\'s services revenue growth and iPhone 15 sales are exceeding expectations. RSI indicates oversold conditions with potential for rebound.',
                'technical_analysis': {'trend': 'bullish', 'rsi': 35, 'macd': 'positive'},
                'fundamental_analysis': {'pe_ratio': 'reasonable', 'growth': 'strong'},
                'sentiment_analysis': {'news_sentiment': 0.7, 'social_sentiment': 0.6}
            },
            {
                'stock': stocks[1],  # MSFT
                'recommendation_type': 'STRONG_BUY',
                'confidence_level': 'VERY_HIGH',
                'confidence_score': Decimal('0.92'),
                'target_price': Decimal('400.00'),
                'reasoning': 'Microsoft\'s Azure cloud growth continues to accelerate. AI integration across Office 365 and enterprise solutions driving strong revenue. Technical analysis shows clear uptrend with strong support levels.',
                'technical_analysis': {'trend': 'very_bullish', 'rsi': 45, 'macd': 'strong_positive'},
                'fundamental_analysis': {'pe_ratio': 'fair', 'growth': 'exceptional'},
                'sentiment_analysis': {'news_sentiment': 0.8, 'social_sentiment': 0.7}
            },
            {
                'stock': stocks[2],  # TSLA
                'recommendation_type': 'HOLD',
                'confidence_level': 'MEDIUM',
                'confidence_score': Decimal('0.65'),
                'target_price': Decimal('260.00'),
                'reasoning': 'Mixed signals from technical analysis. Strong EV market position but valuation concerns persist. Wait for clearer direction before making significant moves.',
                'technical_analysis': {'trend': 'neutral', 'rsi': 55, 'macd': 'mixed'},
                'fundamental_analysis': {'pe_ratio': 'high', 'growth': 'moderate'},
                'sentiment_analysis': {'news_sentiment': 0.3, 'social_sentiment': 0.4}
            },
            {
                'stock': stocks[3],  # JNJ
                'recommendation_type': 'BUY',
                'confidence_level': 'HIGH',
                'confidence_score': Decimal('0.78'),
                'target_price': Decimal('170.00'),
                'reasoning': 'Defensive healthcare stock with strong dividend yield. Recent pharmaceutical pipeline developments show promise. Technical indicators suggest accumulation phase.',
                'technical_analysis': {'trend': 'bullish', 'rsi': 42, 'macd': 'positive'},
                'fundamental_analysis': {'pe_ratio': 'attractive', 'growth': 'stable'},
                'sentiment_analysis': {'news_sentiment': 0.6, 'social_sentiment': 0.5}
            },
            {
                'stock': stocks[4],  # AMZN
                'recommendation_type': 'BUY',
                'confidence_level': 'MEDIUM',
                'confidence_score': Decimal('0.72'),
                'target_price': Decimal('165.00'),
                'reasoning': 'Amazon Web Services growth remains strong despite retail headwinds. AWS margins improving and AI services gaining traction. Technical analysis shows potential breakout pattern.',
                'technical_analysis': {'trend': 'bullish', 'rsi': 48, 'macd': 'positive'},
                'fundamental_analysis': {'pe_ratio': 'reasonable', 'growth': 'good'},
                'sentiment_analysis': {'news_sentiment': 0.5, 'social_sentiment': 0.6}
            }
        ]
        
        for rec_data in recommendations_data:
            recommendation, created = AIRecommendation.objects.get_or_create(
                user=user,
                stock=rec_data['stock'],
                created_at__date=date.today(),
                defaults={
                    **rec_data,
                    'user_risk_level': user.profile.risk_level,
                    'risk_adjusted': True,
                    'portfolio_fit': Decimal('0.8')
                }
            )
            if created:
                self.stdout.write(f'Created recommendation for {rec_data["stock"].symbol}')
        
        self.stdout.write('Created sample recommendations')

    def create_sample_notifications(self, user):
        """Create sample notifications"""
        notifications_data = [
            {
                'notification_type': 'RECOMMENDATION',
                'title': 'New AI Recommendation Available',
                'message': 'Apple Inc. (AAPL) has received a BUY recommendation with HIGH confidence. Target price: $185.00'
            },
            {
                'notification_type': 'PORTFOLIO_ALERT',
                'title': 'Portfolio Performance Update',
                'message': 'Your portfolio has gained 2.3% this week. Check your dashboard for detailed performance metrics.'
            },
            {
                'notification_type': 'MARKET_UPDATE',
                'title': 'Market Analysis Complete',
                'message': 'Daily market analysis completed. 3 new opportunities identified in the Technology sector.'
            }
        ]
        
        for notif_data in notifications_data:
            UserNotification.objects.get_or_create(
                user=user,
                title=notif_data['title'],
                created_at__date=date.today(),
                defaults=notif_data
            )
        
        self.stdout.write('Created sample notifications')

    def create_sample_trades(self, user):
        """Create sample trading history"""
        portfolio = user.portfolio
        stocks = Stock.objects.all()[:5]  # Get first 5 stocks
        
        # Create some sample trades
        sample_trades = [
            {
                'stock': stocks[0],  # AAPL
                'trade_type': 'BUY',
                'quantity': 10,
                'order_type': 'MARKET',
                'notes': 'Initial position in Apple'
            },
            {
                'stock': stocks[1],  # MSFT
                'trade_type': 'BUY',
                'quantity': 5,
                'order_type': 'LIMIT',
                'price': Decimal('375.00'),
                'notes': 'Limit order for Microsoft'
            },
            {
                'stock': stocks[2],  # TSLA
                'trade_type': 'BUY',
                'quantity': 3,
                'order_type': 'MARKET',
                'notes': 'Small position in Tesla'
            }
        ]
        
        for trade_data in sample_trades:
            # Use the trading service to place orders
            result = TradingService.place_order(
                portfolio=portfolio,
                stock=trade_data['stock'],
                trade_type=trade_data['trade_type'],
                quantity=trade_data['quantity'],
                order_type=trade_data['order_type'],
                price=trade_data.get('price'),
                notes=trade_data['notes']
            )
            
            if result['success']:
                trade = result['trade']
                self.stdout.write(f'Created trade: {trade}')
            else:
                self.stdout.write(f'Failed to create trade: {result["error"]}')
        
        self.stdout.write('Created sample trades')
