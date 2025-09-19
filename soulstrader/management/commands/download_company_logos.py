"""
Management command to download and store company logos locally
"""

import os
import requests
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.storage import default_storage
from soulstrader.models import Stock
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Download company logos from FMP and store them locally'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific stock symbols to download logos for (e.g., AAPL MSFT GOOGL)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Download logos for all active stocks',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-download logos even if they already exist locally',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be downloaded without actually downloading',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of logos to download in each batch (default: 10)',
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Validate arguments
        if not options['symbols'] and not options['all']:
            raise CommandError('You must specify either --symbols or --all')
        
        if options['symbols'] and options['all']:
            raise CommandError('You cannot use both --symbols and --all')
        
        # Create logos directory if it doesn't exist
        self.logos_dir = self.ensure_logos_directory()
        
        # Get stocks to process
        if options['all']:
            stocks = Stock.objects.filter(is_active=True).order_by('symbol')
            self.stdout.write(f'Found {stocks.count()} active stocks to process')
        else:
            symbols = [s.upper() for s in options['symbols']]
            stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
            missing_symbols = set(symbols) - set(stocks.values_list('symbol', flat=True))
            if missing_symbols:
                self.stdout.write(
                    self.style.WARNING(f'Warning: These symbols were not found: {", ".join(missing_symbols)}')
                )
        
        if not stocks.exists():
            self.stdout.write(self.style.WARNING('No stocks found to process'))
            return
        
        # Process stocks
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No logos will be downloaded'))
            self.dry_run_download(stocks, options['force'])
        else:
            self.download_logos(stocks, options['force'], options['batch_size'])
    
    def ensure_logos_directory(self):
        """Create logos directory in static files"""
        # Use static directory
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root:
            logos_dir = Path(static_root) / 'soulstrader' / 'images' / 'logos'
        else:
            # Fallback to app static directory during development
            logos_dir = Path(settings.BASE_DIR) / 'soulstrader' / 'static' / 'soulstrader' / 'images' / 'logos'
        
        # Create directory if it doesn't exist
        logos_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write(f'✓ Logos directory: {logos_dir}')
        return logos_dir
    
    def get_logo_path(self, symbol: str) -> Path:
        """Get local path for a logo file"""
        return self.logos_dir / f'{symbol.upper()}.png'
    
    def get_logo_url(self, symbol: str) -> str:
        """Get static URL for a logo"""
        return f'/static/soulstrader/images/logos/{symbol.upper()}.png'
    
    def logo_exists_locally(self, symbol: str) -> bool:
        """Check if logo exists locally"""
        return self.get_logo_path(symbol).exists()
    
    def download_single_logo(self, symbol: str, force: bool = False) -> bool:
        """Download a single logo from FMP"""
        logo_path = self.get_logo_path(symbol)
        
        # Skip if already exists and not forcing
        if not force and self.logo_exists_locally(symbol):
            return True
        
        try:
            # FMP logo URL
            fmp_url = f'https://financialmodelingprep.com/image-stock/{symbol.upper()}.png'
            
            # Download with timeout
            response = requests.get(fmp_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check if we got an actual image (not an error page)
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type.lower():
                self.stdout.write(f'  ⚠ {symbol}: Not a valid image (got {content_type})')
                return False
            
            # Save the logo
            with open(logo_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file was created and has content
            if logo_path.exists() and logo_path.stat().st_size > 0:
                return True
            else:
                self.stdout.write(f'  ✗ {symbol}: Downloaded file is empty')
                return False
                
        except requests.exceptions.RequestException as e:
            self.stdout.write(f'  ✗ {symbol}: Download failed - {e}')
            return False
        except Exception as e:
            self.stdout.write(f'  ✗ {symbol}: Error - {e}')
            return False
    
    def dry_run_download(self, stocks, force: bool):
        """Show what would be downloaded"""
        self.stdout.write(f'Would process {stocks.count()} stocks:')
        
        for stock in stocks[:10]:  # Show first 10 as example
            exists = self.logo_exists_locally(stock.symbol)
            if exists and not force:
                self.stdout.write(f'  • {stock.symbol}: ⏭️ Skip (already exists)')
            else:
                action = 'Re-download' if exists and force else 'Download'
                self.stdout.write(f'  • {stock.symbol}: 📥 {action}')
        
        if stocks.count() > 10:
            self.stdout.write(f'  ... and {stocks.count() - 10} more stocks')
    
    def download_logos(self, stocks, force: bool, batch_size: int):
        """Download logos for stocks"""
        total_stocks = stocks.count()
        downloaded_count = 0
        skipped_count = 0
        failed_count = 0
        
        self.stdout.write(f'Processing {total_stocks} stocks in batches of {batch_size}...')
        
        # Process in batches
        for i in range(0, total_stocks, batch_size):
            batch = stocks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_stocks + batch_size - 1) // batch_size
            
            self.stdout.write(f'\nProcessing batch {batch_num}/{total_batches}...')
            
            for stock in batch:
                symbol = stock.symbol
                
                # Check if already exists
                if not force and self.logo_exists_locally(symbol):
                    skipped_count += 1
                    self.stdout.write(f'  ⏭️ Skipped {symbol} (already exists)')
                    continue
                
                # Download logo
                success = self.download_single_logo(symbol, force)
                
                if success:
                    downloaded_count += 1
                    # Update stock model with local URL
                    stock.logo_url = self.get_logo_url(symbol)
                    stock.save(update_fields=['logo_url'])
                    self.stdout.write(f'  ✓ Downloaded {symbol}')
                else:
                    failed_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Logo download completed:')
        self.stdout.write(f'  • Successfully downloaded: {downloaded_count} logos')
        self.stdout.write(f'  • Skipped (already exist): {skipped_count} logos')
        self.stdout.write(f'  • Failed to download: {failed_count} logos')
        self.stdout.write(f'  • Total processed: {downloaded_count + skipped_count + failed_count} stocks')
        
        if downloaded_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully downloaded {downloaded_count} company logos')
            )
            self.stdout.write(f'📁 Logos stored in: {self.logos_dir}')
        
        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠ {failed_count} logos failed to download')
            )
        
        # Update all stocks that now have local logos
        updated_stocks = Stock.objects.filter(
            symbol__in=[s.symbol for s in stocks if self.logo_exists_locally(s.symbol)]
        )
        
        for stock in updated_stocks:
            if not stock.logo_url or 'financialmodelingprep.com' in stock.logo_url:
                stock.logo_url = self.get_logo_url(stock.symbol)
                stock.save(update_fields=['logo_url'])
        
        self.stdout.write(f'✓ Updated {updated_stocks.count()} stock records with local logo URLs')
    
    def get_logo_stats(self):
        """Get statistics about existing logos"""
        total_stocks = Stock.objects.filter(is_active=True).count()
        stocks_with_local_logos = 0
        
        for stock in Stock.objects.filter(is_active=True):
            if self.logo_exists_locally(stock.symbol):
                stocks_with_local_logos += 1
        
        return {
            'total_stocks': total_stocks,
            'with_local_logos': stocks_with_local_logos,
            'missing_logos': total_stocks - stocks_with_local_logos
        }
