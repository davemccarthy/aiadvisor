"""
Management command to get proactive stock recommendations from market screening
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from soulstrader.market_screening_service import MarketScreeningService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Get proactive stock recommendations from market screening APIs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            choices=['gainers', 'losers', 'active', 'all'],
            default='gainers',
            help='Category of stocks to screen (default: gainers)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Maximum number of recommendations per category (default: 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show recommendations without saving to database'
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show market summary only'
        )
    
    def handle(self, *args, **options):
        try:
            # Initialize market screening service
            screening_service = MarketScreeningService()
            
            # Show market summary if requested
            if options['summary']:
                self.show_market_summary(screening_service)
                return
            
            category = options['category']
            limit = options['limit']
            dry_run = options['dry_run']
            
            self.stdout.write(
                self.style.SUCCESS(f'Getting proactive recommendations: {category} (limit: {limit})')
            )
            
            if category == 'all':
                categories = ['gainers', 'losers', 'active']
            else:
                categories = [category]
            
            total_saved = 0
            
            for cat in categories:
                self.stdout.write(f'\n📊 Processing {cat}...')
                
                if dry_run:
                    # Just show the recommendations
                    recommendations = screening_service.create_proactive_recommendations(cat, limit)
                    self.show_recommendations(recommendations, cat)
                else:
                    # Save to database
                    saved_count = screening_service.save_proactive_recommendations(cat, limit)
                    total_saved += saved_count
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Saved {saved_count} {cat} recommendations')
                    )
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'\n🎯 Total recommendations saved: {total_saved}')
                )
            
        except Exception as e:
            logger.error(f"Market screening command failed: {e}")
            raise CommandError(f'Failed to get market recommendations: {e}')
    
    def show_recommendations(self, recommendations, category):
        """Display recommendations in a formatted table"""
        if not recommendations:
            self.stdout.write(self.style.WARNING(f'No {category} recommendations found'))
            return
        
        self.stdout.write(f'\n{category.upper()} RECOMMENDATIONS:')
        self.stdout.write('-' * 80)
        self.stdout.write(f'{"Symbol":>8} | {"Price":>10} | {"Change":>8} | {"Recommendation":>12} | {"Reasoning"}')
        self.stdout.write('-' * 80)
        
        for rec in recommendations:
            symbol = rec['symbol']
            price = f"${rec['current_price']}"
            change = f"{rec['change_percent']}%"
            rec_type = rec['recommendation_type']
            reasoning = rec['reasoning'][:40] + '...' if len(rec['reasoning']) > 40 else rec['reasoning']
            
            # Color code based on recommendation
            if rec_type in ['BUY', 'STRONG_BUY']:
                color_style = self.style.SUCCESS
            elif rec_type in ['SELL', 'STRONG_SELL']:
                color_style = self.style.ERROR
            else:
                color_style = self.style.WARNING
            
            line = f'{symbol:>8} | {price:>10} | {change:>8} | {rec_type:>12} | {reasoning}'
            self.stdout.write(color_style(line))
    
    def show_market_summary(self, screening_service):
        """Display market summary"""
        self.stdout.write(self.style.SUCCESS('📈 MARKET SUMMARY'))
        self.stdout.write('=' * 50)
        
        try:
            summary = screening_service.get_market_summary()
            
            if not summary:
                self.stdout.write(self.style.WARNING('No market data available'))
                return
            
            # Display sentiment with colors
            sentiment = summary.get('sentiment', 'UNKNOWN')
            if sentiment == 'BULLISH':
                sentiment_style = self.style.SUCCESS(f'🟢 {sentiment}')
            elif sentiment == 'BEARISH':
                sentiment_style = self.style.ERROR(f'🔴 {sentiment}')
            else:
                sentiment_style = self.style.WARNING(f'🟡 {sentiment}')
            
            self.stdout.write(f'Market Sentiment: {sentiment_style}')
            self.stdout.write(f'Avg Gainer Change: {summary.get("avg_gainer_change", 0):.2f}%')
            self.stdout.write(f'Avg Loser Change: {summary.get("avg_loser_change", 0):.2f}%')
            self.stdout.write(f'Top Gainer: {summary.get("top_gainer", "N/A")}')
            self.stdout.write(f'Top Loser: {summary.get("top_loser", "N/A")}')
            self.stdout.write(f'Last Updated: {summary.get("last_updated", "Unknown")}')
            
            # Show top movers
            self.stdout.write('\n📊 TOP MOVERS:')
            
            gainers = screening_service.get_top_gainers(3)
            losers = screening_service.get_top_losers(3)
            
            self.stdout.write('\nTop Gainers:')
            for gainer in gainers:
                symbol = gainer.get('ticker', 'N/A')
                change = gainer.get('change_percentage', 'N/A')
                price = gainer.get('price', 'N/A')
                self.stdout.write(self.style.SUCCESS(f'  {symbol}: {price} ({change})'))
            
            self.stdout.write('\nTop Losers:')
            for loser in losers:
                symbol = loser.get('ticker', 'N/A')
                change = loser.get('change_percentage', 'N/A')
                price = loser.get('price', 'N/A')
                self.stdout.write(self.style.ERROR(f'  {symbol}: {price} ({change})'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting market summary: {e}'))
