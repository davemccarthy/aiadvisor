"""
Management command to add stocks discovered through market screening to the database
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from soulstrader.models import Stock
from soulstrader.market_screening_service import MarketScreeningService
from soulstrader.yahoo_finance_service import YahooMarketDataManager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Add stocks discovered through market screening to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of stocks to add from each category (default: 20)'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing stocks with fresh data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be added without actually adding'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        update_existing = options['update_existing']
        dry_run = options['dry_run']

        self.stdout.write('🔍 Discovering stocks from market screening...')

        try:
            # Initialize market screening service
            screening_service = MarketScreeningService()
            
            # Get market data
            market_data = screening_service.get_market_movers()
            
            if not market_data:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to retrieve market data from Alpha Vantage')
                )
                return

            # Collect all unique symbols
            all_symbols = set()
            
            # Add symbols from top gainers
            for stock in market_data.get('top_gainers', [])[:limit]:
                symbol = stock.get('ticker', '').upper()
                if symbol:
                    all_symbols.add(symbol)
            
            # Add symbols from most active
            for stock in market_data.get('most_actively_traded', [])[:limit]:
                symbol = stock.get('ticker', '').upper()
                if symbol:
                    all_symbols.add(symbol)
            
            # Add symbols from top losers (for contrarian opportunities)
            for stock in market_data.get('top_losers', [])[:limit//2]:
                symbol = stock.get('ticker', '').upper()
                if symbol:
                    all_symbols.add(symbol)

            self.stdout.write(f'📊 Found {len(all_symbols)} unique symbols from market screening')

            # Check which stocks are already in database
            existing_symbols = set(Stock.objects.values_list('symbol', flat=True))
            new_symbols = all_symbols - existing_symbols
            existing_in_screening = all_symbols & existing_symbols

            self.stdout.write(f'✅ Already in database: {len(existing_in_screening)} stocks')
            self.stdout.write(f'🆕 New stocks to add: {len(new_symbols)} stocks')

            if existing_in_screening:
                self.stdout.write('\n📋 Existing stocks found in screening:')
                for symbol in sorted(existing_in_screening):
                    stock = Stock.objects.get(symbol=symbol)
                    self.stdout.write(f'  {symbol}: {stock.name}')

            if new_symbols:
                self.stdout.write(f'\n🆕 New stocks to add:')
                for symbol in sorted(new_symbols):
                    self.stdout.write(f'  {symbol}')

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('\n🔍 DRY RUN - No stocks were actually added')
                )
                return

            # Add new stocks
            added_count = 0
            failed_count = 0

            for symbol in sorted(new_symbols):
                try:
                    with transaction.atomic():
                        # Create basic stock entry
                        stock, created = Stock.objects.get_or_create(
                            symbol=symbol,
                            defaults={
                                'name': f'{symbol} Corporation',  # Will be updated with real data
                                'sector': 'OTHER',  # Will be updated with real data
                            }
                        )

                        if created:
                            self.stdout.write(f'✅ Added {symbol} to database')
                            added_count += 1

                            # Try to get real stock data from Yahoo Finance
                            try:
                                YahooMarketDataManager.update_stock_quote(symbol)
                                self.stdout.write(f'  📈 Updated {symbol} with Yahoo Finance data')
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f'  ⚠️  Could not update {symbol} data: {e}')
                                )

                        else:
                            self.stdout.write(f'ℹ️  {symbol} already exists')

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Failed to add {symbol}: {e}')
                    )
                    failed_count += 1
                    logger.error(f"Failed to add stock {symbol}: {e}")

            # Update existing stocks if requested
            if update_existing and existing_in_screening:
                self.stdout.write(f'\n🔄 Updating existing stocks...')
                updated_count = 0
                
                for symbol in sorted(existing_in_screening):
                    try:
                        YahooMarketDataManager.update_stock_quote(symbol)
                        updated_count += 1
                        self.stdout.write(f'  📈 Updated {symbol}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠️  Could not update {symbol}: {e}')
                        )

                self.stdout.write(f'✅ Updated {updated_count} existing stocks')

            # Summary
            self.stdout.write(f'\n📊 Summary:')
            self.stdout.write(f'  ✅ Added: {added_count} new stocks')
            self.stdout.write(f'  ❌ Failed: {failed_count} stocks')
            if update_existing:
                self.stdout.write(f'  🔄 Updated: {updated_count} existing stocks')
            
            total_stocks = Stock.objects.count()
            self.stdout.write(f'  📈 Total stocks in database: {total_stocks}')

            if added_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\n🎉 Successfully added {added_count} new stocks!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('\n⚠️  No new stocks were added')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Command failed: {e}')
            )
            logger.error(f"Add market stocks command failed: {e}")
            raise
