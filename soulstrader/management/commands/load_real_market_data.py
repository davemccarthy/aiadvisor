from django.core.management.base import BaseCommand
from django.db import transaction
from soulstrader.market_data_service import MarketDataManager
from soulstrader.models import Stock, StockPrice
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load real market data from Alpha Vantage to replace sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing stock and price data before loading',
        )
        parser.add_argument(
            '--symbols',
            type=str,
            default='AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,NFLX,AMD,INTC',
            help='Comma-separated list of stock symbols to load (default: major tech stocks)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Loading real market data from Alpha Vantage...')
        
        symbols = [s.strip().upper() for s in options['symbols'].split(',')]
        
        if options['clear_existing']:
            self.clear_existing_data()
        
        try:
            with transaction.atomic():
                self.load_stocks(symbols)
                self.load_historical_data(symbols)
                
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded real market data!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to load market data: {e}')
            )
            raise

    def clear_existing_data(self):
        """Clear existing stock and price data"""
        self.stdout.write('Clearing existing stock and price data...')
        
        # Delete price data first (foreign key constraint)
        price_count = StockPrice.objects.count()
        StockPrice.objects.all().delete()
        
        # Delete stocks
        stock_count = Stock.objects.count()
        Stock.objects.all().delete()
        
        self.stdout.write(f'Cleared {stock_count} stocks and {price_count} price records')

    def load_stocks(self, symbols):
        """Load stock data from Alpha Vantage"""
        self.stdout.write(f'Loading data for {len(symbols)} stocks...')
        
        loaded_count = 0
        
        for i, symbol in enumerate(symbols):
            try:
                self.stdout.write(f'Loading {symbol} ({i+1}/{len(symbols)})...')
                
                # Update stock quote (this will create the stock if it doesn't exist)
                stock = MarketDataManager.update_stock_quote(symbol)
                
                if stock:
                    self.stdout.write(
                        f'  ✓ {stock.symbol}: {stock.name} - ${stock.current_price}'
                    )
                    loaded_count += 1
                else:
                    self.stdout.write(f'  ✗ Failed to load {symbol}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error loading {symbol}: {e}')
                )
                continue
        
        self.stdout.write(f'Successfully loaded {loaded_count} stocks')

    def load_historical_data(self, symbols):
        """Load historical price data"""
        self.stdout.write('Loading historical price data...')
        
        total_records = 0
        
        for symbol in symbols:
            try:
                # Check if stock exists
                if not Stock.objects.filter(symbol=symbol).exists():
                    self.stdout.write(f'  Skipping {symbol} - stock not found')
                    continue
                
                self.stdout.write(f'  Loading historical data for {symbol}...')
                
                # Update historical prices
                count = MarketDataManager.update_historical_prices(symbol)
                total_records += count
                
                self.stdout.write(f'    ✓ {count} price records loaded')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Error loading historical data for {symbol}: {e}')
                )
                continue
        
        self.stdout.write(f'Total historical records loaded: {total_records}')

    def get_popular_stocks(self):
        """Get list of popular stocks for default loading"""
        return [
            # Tech Giants
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
            # Semiconductor
            'AMD', 'INTC', 'QCOM', 'AVGO',
            # Streaming/Entertainment
            'NFLX', 'DIS', 'ROKU',
            # Financial
            'JPM', 'BAC', 'WFC', 'GS',
            # Healthcare
            'JNJ', 'PFE', 'UNH', 'ABBV',
            # Consumer
            'KO', 'PEP', 'WMT', 'HD',
            # Energy
            'XOM', 'CVX', 'COP',
            # Industrial
            'BA', 'CAT', 'GE', 'MMM'
        ]
