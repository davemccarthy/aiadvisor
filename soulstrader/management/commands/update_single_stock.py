from django.core.management.base import BaseCommand
from soulstrader.market_data_service import MarketDataManager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update a single stock to conserve API calls'

    def add_arguments(self, parser):
        parser.add_argument('symbol', type=str, help='Stock symbol to update')

    def handle(self, *args, **options):
        symbol = options['symbol'].upper()
        
        self.stdout.write(f'Updating {symbol} (using 1 API call)...')
        
        try:
            stock = MarketDataManager.update_stock_quote(symbol)
            self.stdout.write(
                self.style.SUCCESS(f'✓ {stock.symbol}: ${stock.current_price} ({stock.day_change_percent:+.2f}%)')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed to update {symbol}: {e}')
            )
