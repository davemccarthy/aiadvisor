from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone
from soulstrader.models import Stock, AIAdvisor, AIAdvisorRecommendation
from soulstrader.ai_advisor_service import AIAdvisorManager
import time


class Command(BaseCommand):
    help = 'Get AI recommendations for stocks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Stock symbol to analyze',
        )
        parser.add_argument(
            '--all-stocks',
            action='store_true',
            help='Get recommendations for all active stocks',
        )
        parser.add_argument(
            '--create-consensus',
            action='store_true',
            help='Create consensus recommendations after getting individual recommendations',
        )

    def handle(self, *args, **options):
        self.stdout.write('Getting AI recommendations...')
        
        # Check active advisors
        active_advisors = AIAdvisor.objects.filter(is_enabled=True, status='ACTIVE')
        if not active_advisors.exists():
            self.stdout.write(
                self.style.ERROR('No active AI advisors found! Set up advisors first.')
            )
            return
        
        self.stdout.write(f'Active advisors: {active_advisors.count()}')
        for advisor in active_advisors:
            self.stdout.write(f'  - {advisor.name} (calls remaining: {advisor.daily_calls_remaining})')
        
        # Determine stocks to analyze
        if options['symbol']:
            try:
                stocks = [Stock.objects.get(symbol=options['symbol'].upper())]
            except Stock.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Stock {options["symbol"]} not found')
                )
                return
        elif options['all_stocks']:
            stocks = Stock.objects.filter(is_active=True)[:5]  # Limit to 5 for testing
        else:
            # Default to a few popular stocks
            symbols = ['AAPL', 'MSFT', 'GOOGL']
            stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
        
        if not stocks:
            self.stdout.write(
                self.style.ERROR('No stocks found to analyze')
            )
            return
        
        total_recommendations = 0
        
        # Get recommendations for each stock
        for i, stock in enumerate(stocks):
            self.stdout.write(f'\nAnalyzing {stock.symbol} ({i+1}/{len(stocks)})...')
            
            try:
                recommendations = AIAdvisorManager.get_recommendations_for_stock(stock)
                
                if recommendations:
                    self.stdout.write(f'  ✓ Got {len(recommendations)} recommendations:')
                    for rec in recommendations:
                        self.stdout.write(
                            f'    - {rec.advisor.name}: {rec.recommendation_type} '
                            f'({rec.confidence_level}, {rec.confidence_score:.2f})'
                        )
                        if rec.target_price:
                            self.stdout.write(f'      Target: ${rec.target_price}')
                        if rec.reasoning:
                            # Show first line of reasoning
                            first_line = rec.reasoning.split('\n')[0][:100]
                            self.stdout.write(f'      Reason: {first_line}...')
                    
                    total_recommendations += len(recommendations)
                    
                    # Create consensus if requested
                    if options['create_consensus']:
                        consensus = AIAdvisorManager.create_consensus_recommendation(
                            stock, recommendations
                        )
                        if consensus:
                            self.stdout.write(
                                f'  📊 Consensus: {consensus.consensus_type} '
                                f'(strength: {consensus.consensus_strength:.2f}, '
                                f'score: {consensus.weighted_score:.1f})'
                            )
                            if consensus.auto_trade_eligible:
                                self.stdout.write(f'  🤖 Auto-trade eligible!')
                else:
                    self.stdout.write(f'  ✗ No recommendations received')
                
                # Small delay between stocks
                if i < len(stocks) - 1:
                    time.sleep(2)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error analyzing {stock.symbol}: {e}')
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'\nCompleted! Got {total_recommendations} total recommendations.')
        )
        
        # Show summary
        recent_recommendations = AIAdvisorRecommendation.objects.filter(
            created_at__date=timezone.now().date()
        ).values('recommendation_type').annotate(count=models.Count('id'))
        
        if recent_recommendations:
            self.stdout.write('\nToday\'s recommendations summary:')
            for rec in recent_recommendations:
                self.stdout.write(f'  {rec["recommendation_type"]}: {rec["count"]}')
        
        # Show advisor performance
        self.stdout.write('\nAdvisor performance:')
        for advisor in active_advisors:
            self.stdout.write(
                f'  {advisor.name}: {advisor.success_rate:.1f}% success rate, '
                f'{advisor.total_recommendations} total recommendations'
            )
