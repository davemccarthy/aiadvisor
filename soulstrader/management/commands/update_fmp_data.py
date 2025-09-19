"""
Management command to update stock data with Financial Modeling Prep (FMP) API
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from soulstrader.models import Stock, AIAdvisor
from soulstrader.fmp_service import FMPAPIService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update stock data with FMP API (logos, grades, analyst ratings)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific stock symbols to update (e.g., AAPL MSFT GOOGL)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all active stocks in the database',
        )
        parser.add_argument(
            '--create-advisor',
            action='store_true',
            help='Create FMP AI Advisor if it doesn\'t exist',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='FMP API key to use (optional)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of stocks to process in each batch (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Validate arguments
        if not options['symbols'] and not options['all']:
            raise CommandError('You must specify either --symbols or --all')
        
        if options['symbols'] and options['all']:
            raise CommandError('You cannot use both --symbols and --all')
        
        # Create FMP advisor if requested
        if options['create_advisor']:
            self.create_fmp_advisor(options['api_key'])
        
        # Initialize FMP service
        try:
            fmp_service = FMPAPIService(api_key=options['api_key'])
            
            # Test connection
            if not fmp_service.test_connection():
                raise CommandError('FMP API connection test failed. Check your API key.')
            
            self.stdout.write(
                self.style.SUCCESS('✓ FMP API connection successful')
            )
            
        except Exception as e:
            raise CommandError(f'Failed to initialize FMP service: {e}')
        
        # Get stocks to update
        if options['all']:
            stocks = Stock.objects.filter(is_active=True).order_by('symbol')
            self.stdout.write(f'Found {stocks.count()} active stocks to update')
        else:
            symbols = [s.upper() for s in options['symbols']]
            stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
            missing_symbols = set(symbols) - set(stocks.values_list('symbol', flat=True))
            if missing_symbols:
                self.stdout.write(
                    self.style.WARNING(f'Warning: These symbols were not found: {", ".join(missing_symbols)}')
                )
        
        if not stocks.exists():
            self.stdout.write(self.style.WARNING('No stocks found to update'))
            return
        
        # Process stocks
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.dry_run_update(stocks, fmp_service)
        else:
            self.update_stocks(stocks, fmp_service, options['batch_size'])
    
    def create_fmp_advisor(self, api_key: str = None):
        """Create or update FMP AI Advisor"""
        try:
            advisor, created = AIAdvisor.objects.get_or_create(
                advisor_type='FMP',
                defaults={
                    'name': 'Financial Modeling Prep',
                    'description': 'Stock grades and consensus data from Financial Modeling Prep API',
                    'api_key': api_key or '',
                    'api_endpoint': 'https://financialmodelingprep.com/api/v3',
                    'rate_limit_per_day': 250,  # FMP free tier limit
                    'rate_limit_per_minute': 10,
                    'status': 'ACTIVE',
                    'is_enabled': True,
                    'weight': 1.0,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created FMP AI Advisor: {advisor.name}')
                )
            else:
                # Update API key if provided
                if api_key and advisor.api_key != api_key:
                    advisor.api_key = api_key
                    advisor.save(update_fields=['api_key'])
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Updated FMP AI Advisor API key')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'FMP AI Advisor already exists: {advisor.name}')
                    )
            
            return advisor
            
        except Exception as e:
            raise CommandError(f'Failed to create FMP advisor: {e}')
    
    def dry_run_update(self, stocks, fmp_service: FMPAPIService):
        """Show what would be updated without making changes"""
        self.stdout.write(f'Would update {stocks.count()} stocks:')
        
        for stock in stocks[:10]:  # Show first 10 as example
            self.stdout.write(f'  • {stock.symbol} - {stock.name}')
            
            # Check what data would be retrieved
            try:
                grade_data = fmp_service.get_stock_grade(stock.symbol)
                logo_url = fmp_service.get_company_logo_url(stock.symbol)
                
                if grade_data:
                    self.stdout.write(f'    - Would update grade data: {grade_data}')
                else:
                    self.stdout.write(f'    - No grade data available')
                
                self.stdout.write(f'    - Would set logo URL: {logo_url}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'    - Error retrieving data: {e}')
                )
        
        if stocks.count() > 10:
            self.stdout.write(f'  ... and {stocks.count() - 10} more stocks')
    
    def update_stocks(self, stocks, fmp_service: FMPAPIService, batch_size: int):
        """Update stocks with FMP data"""
        total_stocks = stocks.count()
        updated_count = 0
        failed_count = 0
        
        self.stdout.write(f'Updating {total_stocks} stocks in batches of {batch_size}...')
        
        # Process in batches
        for i in range(0, total_stocks, batch_size):
            batch = stocks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_stocks + batch_size - 1) // batch_size
            
            self.stdout.write(f'Processing batch {batch_num}/{total_batches}...')
            
            with transaction.atomic():
                for stock in batch:
                    try:
                        success = fmp_service.update_stock_with_fmp_data(stock)
                        
                        if success:
                            updated_count += 1
                            self.stdout.write(f'  ✓ Updated {stock.symbol}')
                        else:
                            failed_count += 1
                            self.stdout.write(f'  ✗ Failed to update {stock.symbol}')
                    
                    except Exception as e:
                        failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error updating {stock.symbol}: {e}')
                        )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Update completed:')
        self.stdout.write(f'  • Successfully updated: {updated_count} stocks')
        self.stdout.write(f'  • Failed to update: {failed_count} stocks')
        self.stdout.write(f'  • Total processed: {updated_count + failed_count} stocks')
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully updated {updated_count} stocks with FMP data')
            )
        
        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠ {failed_count} stocks failed to update')
            )
