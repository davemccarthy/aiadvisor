"""
Management command to test Yahoo Finance discovery
"""

from django.core.management.base import BaseCommand
from soulstrader.yahoo_finance_discovery_service import YahooFinanceDiscoveryService


class Command(BaseCommand):
    help = 'Test Yahoo Finance stock discovery'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=15,
            help='Maximum number of stocks to discover (default: 15)'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        
        self.stdout.write('🔍 Testing Yahoo Finance Stock Discovery')
        self.stdout.write('=' * 50)
        
        try:
            discovery_service = YahooFinanceDiscoveryService()
            
            # Test comprehensive discovery
            symbols = discovery_service.discover_stocks(limit=limit)
            
            self.stdout.write(f'📊 Discovery Results:')
            self.stdout.write(f'Total stocks found: {len(symbols)}')
            
            # Get detailed summary
            summary = discovery_service.get_discovery_summary(symbols)
            
            self.stdout.write(f'\n📈 Discovery Summary:')
            self.stdout.write(f'Source: {summary["source"]}')
            self.stdout.write(f'Methods: {", ".join(summary["methods"])}')
            self.stdout.write(f'Total: {summary["total_discovered"]} stocks')
            
            self.stdout.write(f'\n🎯 Discovered Stocks:')
            for i, symbol in enumerate(symbols, 1):
                self.stdout.write(f'{i:2d}. {symbol}')
            
            self.stdout.write('\n✅ Yahoo Finance discovery test completed successfully!')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Yahoo Finance discovery test failed: {e}')
            )
            raise



