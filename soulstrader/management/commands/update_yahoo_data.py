from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from soulstrader.yahoo_finance_service import YahooMarketDataManager
from soulstrader.models import Stock
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update market data from Yahoo Finance (unlimited, free)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            type=str,
            help='Comma-separated list of stock symbols to update (e.g., AAPL,MSFT,GOOGL)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all active stocks in the database',
        )
        parser.add_argument(
            '--historical',
            action='store_true',
            help='Also update historical price data',
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Search for and add new stocks by keywords',
        )
        parser.add_argument(
            '--period',
            type=str,
            default='3mo',
            help='Historical data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Yahoo Finance data update...'))
        
        try:
            if options['search']:
                self.handle_search(options['search'])
            elif options['all']:
                self.handle_update_all(options['historical'], options['period'])
            elif options['symbols']:
                self.handle_update_symbols(options['symbols'], options['historical'], options['period'])
            else:
                self.stdout.write(
                    self.style.WARNING('Please specify --symbols, --all, or --search')
                )
                return
                
        except Exception as e:
            raise CommandError(f'Yahoo Finance data update failed: {e}')

    def handle_search(self, keywords):
        """Search for and add new stocks"""
        self.stdout.write(f'Searching for stocks with keywords: {keywords}')
        
        try:
            added_stocks = YahooMarketDataManager.search_and_add_stock(keywords)
            
            if added_stocks:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully added {len(added_stocks)} stocks:')
                )
                for stock in added_stocks:
                    self.stdout.write(f'  - {stock.symbol}: {stock.name} - ${stock.current_price}')
            else:
                self.stdout.write(
                    self.style.WARNING('No new stocks found or added')
                )
                
        except Exception as e:
            raise CommandError(f'Stock search failed: {e}')

    def handle_update_all(self, include_historical, period):
        """Update all active stocks"""
        active_stocks = Stock.objects.filter(is_active=True)
        
        if not active_stocks.exists():
            self.stdout.write(
                self.style.WARNING('No active stocks found in database')
            )
            return
        
        symbols = [stock.symbol for stock in active_stocks]
        self.stdout.write(f'Updating {len(symbols)} active stocks...')
        
        try:
            updated_stocks = YahooMarketDataManager.update_multiple_stocks(symbols)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {len(updated_stocks)} stocks')
            )
            
            # Show updated stock details
            for stock in updated_stocks:
                self.stdout.write(
                    f'  - {stock.symbol}: ${stock.current_price} '
                    f'({stock.day_change_percent:+.2f}%)'
                )
            
            # Update historical data if requested
            if include_historical:
                self.stdout.write(f'Updating historical price data (period: {period})...')
                for stock in updated_stocks:
                    try:
                        count = YahooMarketDataManager.update_historical_prices(stock.symbol, period)
                        self.stdout.write(f'  - {stock.symbol}: {count} price records updated')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  - {stock.symbol}: Failed to update historical data - {e}')
                        )
                        
        except Exception as e:
            raise CommandError(f'Bulk update failed: {e}')

    def handle_update_symbols(self, symbols_str, include_historical, period):
        """Update specific stock symbols"""
        symbols = [s.strip().upper() for s in symbols_str.split(',')]
        self.stdout.write(f'Updating {len(symbols)} stocks: {", ".join(symbols)}')
        
        try:
            updated_stocks = YahooMarketDataManager.update_multiple_stocks(symbols)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {len(updated_stocks)} stocks')
            )
            
            # Show updated stock details
            for stock in updated_stocks:
                self.stdout.write(
                    f'  - {stock.symbol}: ${stock.current_price} '
                    f'({stock.day_change_percent:+.2f}%)'
                )
            
            # Update historical data if requested
            if include_historical:
                self.stdout.write(f'Updating historical price data (period: {period})...')
                for stock in updated_stocks:
                    try:
                        count = YahooMarketDataManager.update_historical_prices(stock.symbol, period)
                        self.stdout.write(f'  - {stock.symbol}: {count} price records updated')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  - {stock.symbol}: Failed to update historical data - {e}')
                        )
                        
        except Exception as e:
            raise CommandError(f'Update failed: {e}')
