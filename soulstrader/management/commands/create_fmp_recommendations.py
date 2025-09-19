"""
Management command to create AI recommendations based on FMP grades
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from soulstrader.models import Stock, AIAdvisor, AIAdvisorRecommendation
from soulstrader.fmp_service import FMPAPIService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create AI recommendations based on FMP stock grades'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific stock symbols to create recommendations for (e.g., AAPL MSFT GOOGL)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create recommendations for all active stocks with FMP grades',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='FMP API key to use (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what recommendations would be created without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation of new recommendations even if recent ones exist',
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Validate arguments
        if not options['symbols'] and not options['all']:
            raise CommandError('You must specify either --symbols or --all')
        
        if options['symbols'] and options['all']:
            raise CommandError('You cannot use both --symbols and --all')
        
        # Get or create FMP advisor
        try:
            advisor = self.get_or_create_fmp_advisor(options['api_key'])
            self.stdout.write(f"✅ Using FMP advisor: {advisor.name}")
        except Exception as e:
            raise CommandError(f'Failed to get FMP advisor: {e}')
        
        # Initialize FMP service
        try:
            fmp_service = FMPAPIService(api_key=options['api_key'])
            
            # Test connection
            if not fmp_service.test_connection():
                raise CommandError('FMP API connection test failed. Check your API key.')
            
            self.stdout.write(self.style.SUCCESS('✓ FMP API connection successful'))
            
        except Exception as e:
            raise CommandError(f'Failed to initialize FMP service: {e}')
        
        # Get stocks to process
        if options['all']:
            stocks = Stock.objects.filter(is_active=True).exclude(fmp_grade__isnull=True).exclude(fmp_grade='')
            self.stdout.write(f'Found {stocks.count()} active stocks with FMP grades')
        else:
            symbols = [s.upper() for s in options['symbols']]
            stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
            missing_symbols = set(symbols) - set(stocks.values_list('symbol', flat=True))
            if missing_symbols:
                self.stdout.write(
                    self.style.WARNING(f'Warning: These symbols were not found: {", ".join(missing_symbols)}')
                )
        
        if not stocks.exists():
            self.stdout.write(self.style.WARNING('No stocks found to create recommendations for'))
            return
        
        # Process stocks
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No recommendations will be created'))
            self.dry_run_recommendations(stocks, advisor, fmp_service)
        else:
            self.create_recommendations(stocks, advisor, fmp_service, options['force'])
    
    def get_or_create_fmp_advisor(self, api_key: str = None):
        """Get or create FMP AI Advisor"""
        try:
            advisor, created = AIAdvisor.objects.get_or_create(
                advisor_type='FMP',
                defaults={
                    'name': 'Financial Modeling Prep',
                    'description': 'Stock grades and consensus data from Financial Modeling Prep API',
                    'api_key': api_key or '',
                    'api_endpoint': 'https://financialmodelingprep.com/api/v3',
                    'rate_limit_per_day': 250,
                    'rate_limit_per_minute': 10,
                    'status': 'ACTIVE',
                    'is_enabled': True,
                    'weight': 1.0,
                }
            )
            
            if created:
                self.stdout.write(f'✓ Created FMP AI Advisor: {advisor.name}')
            else:
                # Update API key if provided
                if api_key and advisor.api_key != api_key:
                    advisor.api_key = api_key
                    advisor.save(update_fields=['api_key'])
            
            return advisor
            
        except Exception as e:
            raise CommandError(f'Failed to get/create FMP advisor: {e}')
    
    def dry_run_recommendations(self, stocks, advisor, fmp_service: FMPAPIService):
        """Show what recommendations would be created"""
        self.stdout.write(f'Would create recommendations for {stocks.count()} stocks:')
        
        for stock in stocks[:10]:  # Show first 10 as example
            grade = stock.fmp_grade
            recommendation_type = self.get_recommendation_from_grade(grade)
            
            self.stdout.write(f'  • {stock.symbol} (Grade: {grade}) → {recommendation_type}')
        
        if stocks.count() > 10:
            self.stdout.write(f'  ... and {stocks.count() - 10} more stocks')
    
    def create_recommendations(self, stocks, advisor, fmp_service: FMPAPIService, force: bool):
        """Create recommendations for stocks"""
        total_stocks = stocks.count()
        created_count = 0
        skipped_count = 0
        failed_count = 0
        
        self.stdout.write(f'Creating recommendations for {total_stocks} stocks...')
        
        for stock in stocks:
            try:
                # Check if recent recommendation exists
                if not force:
                    from django.utils import timezone
                    from datetime import timedelta
                    
                    recent_recommendation = AIAdvisorRecommendation.objects.filter(
                        advisor=advisor,
                        stock=stock,
                        created_at__gte=timezone.now() - timedelta(days=1)
                    ).first()
                    
                    if recent_recommendation:
                        skipped_count += 1
                        self.stdout.write(f'  ⏭️  Skipped {stock.symbol} (recent recommendation exists)')
                        continue
                
                # Create recommendation
                recommendation = fmp_service.create_recommendation_from_grade(stock, advisor)
                
                if recommendation:
                    created_count += 1
                    self.stdout.write(f'  ✓ Created recommendation for {stock.symbol}: {recommendation.recommendation_type}')
                else:
                    failed_count += 1
                    self.stdout.write(f'  ✗ Failed to create recommendation for {stock.symbol}')
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error creating recommendation for {stock.symbol}: {e}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Recommendation creation completed:')
        self.stdout.write(f'  • Successfully created: {created_count} recommendations')
        self.stdout.write(f'  • Skipped (recent exists): {skipped_count} stocks')
        self.stdout.write(f'  • Failed to create: {failed_count} stocks')
        self.stdout.write(f'  • Total processed: {created_count + skipped_count + failed_count} stocks')
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully created {created_count} FMP-based recommendations')
            )
        
        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠ {failed_count} recommendations failed to create')
            )
        
        # Update advisor statistics
        try:
            advisor.total_recommendations += created_count
            advisor.save(update_fields=['total_recommendations'])
            self.stdout.write(f'✓ Updated advisor statistics')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠ Failed to update advisor statistics: {e}')
            )
    
    def get_recommendation_from_grade(self, grade: str) -> str:
        """Convert FMP grade to recommendation type"""
        grade = grade.upper() if grade else ''
        
        mapping = {
            'A+': 'STRONG_BUY',
            'A': 'STRONG_BUY', 
            'A-': 'BUY',
            'B+': 'BUY',
            'B': 'HOLD',
            'B-': 'HOLD',
            'C+': 'SELL',
            'C': 'SELL',
            'C-': 'STRONG_SELL',
            'D': 'STRONG_SELL',
            'F': 'STRONG_SELL',
        }
        
        return mapping.get(grade, 'HOLD')
