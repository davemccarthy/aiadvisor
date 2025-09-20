"""
Management command to find and download missing stock logos
"""

import os
import requests
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from soulstrader.models import Stock
from soulstrader.fmp_service import FMPAPIService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Find and download missing stock logos to static folder'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check for missing logos without downloading'
        )
        parser.add_argument(
            '--symbols',
            type=str,
            help='Comma-separated list of specific symbols to process'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-download logos even if they already exist locally'
        )
        parser.add_argument(
            '--source',
            type=str,
            choices=['fmp', 'clearbit', 'both'],
            default='both',
            help='Logo source: fmp (Financial Modeling Prep), clearbit (Clearbit Logo API), or both'
        )
    
    def handle(self, *args, **options):
        try:
            # Setup static directory
            static_dir = self.get_logos_directory()
            
            # Get stocks to process
            if options['symbols']:
                symbols = [s.strip().upper() for s in options['symbols'].split(',')]
                stocks = Stock.objects.filter(symbol__in=symbols)
                if not stocks.exists():
                    raise CommandError(f'No stocks found for symbols: {options["symbols"]}')
            else:
                stocks = Stock.objects.filter(is_active=True).order_by('symbol')
            
            self.stdout.write(f'Processing {stocks.count()} stocks for logo availability...')
            self.stdout.write(f'Static logos directory: {static_dir}')
            
            missing_logos = []
            existing_logos = []
            
            # Check each stock
            for stock in stocks:
                local_logo_path = static_dir / f'{stock.symbol.upper()}.png'
                
                if local_logo_path.exists() and not options['force']:
                    existing_logos.append(stock)
                    if options['check_only']:
                        self.stdout.write(f'✅ {stock.symbol:8} | Logo exists locally')
                else:
                    missing_logos.append(stock)
                    if options['check_only']:
                        self.stdout.write(f'❌ {stock.symbol:8} | Missing logo')
            
            # Summary
            self.stdout.write(f'\n📊 SUMMARY:')
            self.stdout.write(f'   Existing logos: {len(existing_logos)}')
            self.stdout.write(f'   Missing logos:  {len(missing_logos)}')
            
            if options['check_only']:
                return
            
            if not missing_logos:
                self.stdout.write(self.style.SUCCESS('✅ All logos are present!'))
                return
            
            # Download missing logos
            self.stdout.write(f'\n🔄 Downloading {len(missing_logos)} missing logos...')
            
            downloaded = 0
            failed = 0
            
            for stock in missing_logos:
                success = self.download_logo(stock, static_dir, options['source'])
                if success:
                    downloaded += 1
                    self.stdout.write(self.style.SUCCESS(f'✅ {stock.symbol:8} | Downloaded'))
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f'❌ {stock.symbol:8} | Failed'))
            
            # Final summary
            self.stdout.write(f'\n🎯 DOWNLOAD RESULTS:')
            self.stdout.write(f'   Successfully downloaded: {downloaded}')
            self.stdout.write(f'   Failed downloads: {failed}')
            
            if downloaded > 0:
                self.stdout.write(self.style.SUCCESS(f'\n✅ Downloaded {downloaded} new logos to {static_dir}'))
            
        except Exception as e:
            logger.error(f"Logo download command failed: {e}")
            raise CommandError(f'Failed to process logos: {e}')
    
    def get_logos_directory(self):
        """Get the logos static directory, create if needed"""
        # Try to find the static directory
        base_dir = getattr(settings, 'BASE_DIR', Path.cwd())
        
        # Check common static directory locations
        possible_paths = [
            base_dir / 'soulstrader' / 'static' / 'soulstrader' / 'images' / 'logos',
            base_dir / 'static' / 'soulstrader' / 'images' / 'logos',
            base_dir / 'staticfiles' / 'soulstrader' / 'images' / 'logos',
        ]
        
        # Use the first existing path, or create the primary one
        for path in possible_paths:
            if path.exists():
                return path
        
        # Create the primary path
        primary_path = possible_paths[0]
        primary_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f'Created logos directory: {primary_path}')
        return primary_path
    
    def download_logo(self, stock, static_dir, source):
        """Download logo for a stock from specified source(s)"""
        symbol = stock.symbol.upper()
        local_path = static_dir / f'{symbol}.png'
        
        sources_to_try = []
        
        if source in ['fmp', 'both']:
            sources_to_try.append(('FMP', f'https://financialmodelingprep.com/image-stock/{symbol}.png'))
        
        if source in ['clearbit', 'both']:
            # Try to get company domain for Clearbit
            company_name = stock.name.lower().replace(' inc', '').replace(' corp', '').replace(' ltd', '').replace(' plc', '').replace(' ag', '').strip()
            domain_guess = company_name.replace(' ', '').replace('.', '') + '.com'
            sources_to_try.append(('Clearbit', f'https://logo.clearbit.com/{domain_guess}'))
        
        for source_name, url in sources_to_try:
            try:
                response = requests.get(url, timeout=10, stream=True)
                
                # Check if we got a valid image
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'image' in content_type.lower():
                        # Save the image
                        with open(local_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        # Verify the file was created and has content
                        if local_path.exists() and local_path.stat().st_size > 0:
                            # Update the stock's logo_url to point to local file
                            stock.logo_url = f'/static/soulstrader/images/logos/{symbol}.png'
                            stock.save(update_fields=['logo_url'])
                            return True
                        else:
                            # Remove empty file
                            local_path.unlink(missing_ok=True)
                
            except requests.exceptions.RequestException as e:
                logger.debug(f"Failed to download from {source_name} for {symbol}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing {source_name} logo for {symbol}: {e}")
                continue
        
        return False
    
    def get_company_domain_guess(self, stock):
        """Try to guess company domain for Clearbit API"""
        name = stock.name.lower()
        
        # Common domain mappings
        domain_mappings = {
            'apple': 'apple.com',
            'microsoft': 'microsoft.com',
            'google': 'google.com',
            'alphabet': 'google.com',
            'amazon': 'amazon.com',
            'tesla': 'tesla.com',
            'nvidia': 'nvidia.com',
            'meta': 'meta.com',
            'facebook': 'meta.com',
            'netflix': 'netflix.com',
            'adobe': 'adobe.com',
            'salesforce': 'salesforce.com',
            'oracle': 'oracle.com',
            'intel': 'intel.com',
            'amd': 'amd.com',
            'paypal': 'paypal.com',
            'visa': 'visa.com',
            'mastercard': 'mastercard.com',
            'johnson': 'jnj.com',
            'pfizer': 'pfizer.com',
            'coca': 'coca-colacompany.com',
            'pepsi': 'pepsico.com',
            'walmart': 'walmart.com',
            'disney': 'disney.com',
            'boeing': 'boeing.com',
            'goldman': 'goldmansachs.com',
            'jpmorgan': 'jpmorganchase.com',
            'novo nordisk': 'novonordisk.com',
            'kerry group': 'kerrygroup.com',
            'glanbia': 'glanbia.com',
            'holcim': 'holcim.com',
        }
        
        # Check for exact matches first
        for company, domain in domain_mappings.items():
            if company in name:
                return domain
        
        # Fallback: clean up name and add .com
        clean_name = name.replace(' inc', '').replace(' corp', '').replace(' ltd', '').replace(' plc', '').replace(' ag', '').strip()
        return clean_name.replace(' ', '').replace('.', '') + '.com'
