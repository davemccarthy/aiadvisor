from django.core.management.base import BaseCommand
from django.db import transaction
from soulstrader.yahoo_finance_service import YahooMarketDataManager
from soulstrader.models import Stock, StockPrice
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load popular stocks using Yahoo Finance (unlimited, free)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            type=str,
            help='Comma-separated list of stock symbols to load',
        )
        parser.add_argument(
            '--popular',
            action='store_true',
            help='Load popular stocks (default set)',
        )
        parser.add_argument(
            '--tech',
            action='store_true',
            help='Load technology stocks',
        )
        parser.add_argument(
            '--financial',
            action='store_true',
            help='Load financial stocks',
        )
        parser.add_argument(
            '--healthcare',
            action='store_true',
            help='Load healthcare stocks',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing stock data before loading',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading stocks using Yahoo Finance...'))
        
        if options['clear_existing']:
            self.clear_existing_data()
        
        # Determine which stocks to load
        symbols = []
        
        if options['symbols']:
            symbols = [s.strip().upper() for s in options['symbols'].split(',')]
        elif options['tech']:
            symbols = self.get_tech_stocks()
        elif options['financial']:
            symbols = self.get_financial_stocks()
        elif options['healthcare']:
            symbols = self.get_healthcare_stocks()
        else:
            # Default to popular stocks
            symbols = self.get_popular_stocks()
        
        try:
            self.load_stocks(symbols)
            self.load_historical_data(symbols)
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded Yahoo Finance data!')
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
        """Load stock data from Yahoo Finance"""
        self.stdout.write(f'Loading data for {len(symbols)} stocks...')
        
        loaded_count = 0
        
        for i, symbol in enumerate(symbols):
            try:
                self.stdout.write(f'Loading {symbol} ({i+1}/{len(symbols)})...')
                
                # Update stock quote (this will create the stock if it doesn't exist)
                stock = YahooMarketDataManager.update_stock_quote(symbol)
                
                if stock:
                    self.stdout.write(
                        f'  ✓ {stock.symbol}: {stock.name} - ${stock.current_price} '
                        f'({stock.day_change_percent:+.2f}%)'
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
                
                # Update historical prices (3 months by default)
                count = YahooMarketDataManager.update_historical_prices(symbol, period="3mo")
                total_records += count
                
                self.stdout.write(f'    ✓ {count} price records loaded')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Error loading historical data for {symbol}: {e}')
                )
                continue
        
        self.stdout.write(f'Total historical records loaded: {total_records}')

    def get_popular_stocks(self):
        """Get list of popular stocks across sectors"""
        return [
            # Mega-cap tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA',
            # Other major tech
            'NFLX', 'ADBE', 'CRM', 'ORCL', 'INTC', 'AMD', 'AVGO',
            # Financial
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'V', 'MA',
            # Healthcare
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'LLY',
            # Consumer/Retail
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'DIS',
            # Industrial
            'BA', 'CAT', 'GE', 'MMM',
            # Energy
            'XOM', 'CVX',
        ]

    def get_tech_stocks(self):
        """Get technology stocks"""
        return [
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA',
            'NFLX', 'ADBE', 'CRM', 'ORCL', 'INTC', 'AMD', 'AVGO', 'QCOM',
            'TXN', 'INTU', 'CSCO', 'ACN', 'IBM', 'UBER', 'LYFT', 'SPOT',
            'ZOOM', 'DOCU', 'SHOP', 'SQ', 'PYPL', 'ROKU'
        ]

    def get_financial_stocks(self):
        """Get financial sector stocks"""
        return [
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC',
            'TFC', 'COF', 'AXP', 'BLK', 'SCHW', 'CB', 'V', 'MA',
            'PYPL', 'SQ', 'AFRM', 'SOFI'
        ]

    def get_healthcare_stocks(self):
        """Get healthcare sector stocks"""
        return [
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT',
            'DHR', 'BMY', 'AMGN', 'GILD', 'CVS', 'MDT', 'CI', 'HUM',
            'ANTM', 'ISRG', 'VRTX', 'REGN'
        ]
