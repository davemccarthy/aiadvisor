from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta
from soulstrader.models import Stock, AIAdvisor, AIAdvisorRecommendation, ConsensusRecommendation
from soulstrader.demo_ai_advisor import DemoAIAdvisor
from soulstrader.ai_advisor_service import AIAdvisorManager


class Command(BaseCommand):
    help = 'Generate demo AI recommendations for testing (no API keys required)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Stock symbol to analyze',
        )
        parser.add_argument(
            '--all-stocks',
            action='store_true',
            help='Get demo recommendations for all active stocks',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Generating Demo AI Recommendations...'))
        
        # Get advisors (we'll use demo mode for all)
        advisors = AIAdvisor.objects.all()[:3]  # Use first 3 for demo
        
        if not advisors.exists():
            self.stdout.write(
                self.style.ERROR('No AI advisors found! Run: python manage.py setup_ai_advisors')
            )
            return
        
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
            stocks = Stock.objects.filter(is_active=True)[:5]  # Limit to 5
        else:
            # Default to your current holdings
            symbols = ['AAPL', 'TSLA', 'MSFT']
            stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
        
        if not stocks:
            self.stdout.write(
                self.style.ERROR('No stocks found to analyze')
            )
            return
        
        total_recommendations = 0
        
        # Generate demo recommendations for each stock
        for i, stock in enumerate(stocks):
            self.stdout.write(f'\n📊 Analyzing {stock.symbol} ({i+1}/{len(stocks)})...')
            
            stock_recommendations = []
            
            # Get recommendations from each advisor (demo mode)
            for advisor in advisors:
                try:
                    demo_advisor = DemoAIAdvisor(advisor)
                    recommendation = demo_advisor.get_recommendation(stock)
                    
                    if recommendation:
                        self.stdout.write(
                            f'  ✓ {advisor.name}: {recommendation.recommendation_type} '
                            f'({recommendation.confidence_level}, {recommendation.confidence_score:.2f})'
                        )
                        if recommendation.target_price:
                            self.stdout.write(f'    Target: ${recommendation.target_price}')
                        
                        # Show key factors
                        if recommendation.key_factors:
                            self.stdout.write(f'    Factors: {", ".join(recommendation.key_factors[:2])}')
                        
                        stock_recommendations.append(recommendation)
                        total_recommendations += 1
                    
                except Exception as e:
                    self.stdout.write(f'  ✗ {advisor.name}: Error - {e}')
                    continue
            
            # Create consensus recommendation
            if stock_recommendations:
                try:
                    consensus = AIAdvisorManager.create_consensus_recommendation(
                        stock, stock_recommendations
                    )
                    if consensus:
                        self.stdout.write(
                            f'  📊 Consensus: {consensus.consensus_type} '
                            f'(strength: {consensus.consensus_strength:.2f}, '
                            f'score: {consensus.weighted_score:.1f})'
                        )
                        if consensus.auto_trade_eligible:
                            self.stdout.write(f'  🤖 Auto-trade eligible!')
                        
                        # Show vote breakdown
                        votes = []
                        if consensus.strong_buy_votes: votes.append(f"{consensus.strong_buy_votes} Strong Buy")
                        if consensus.buy_votes: votes.append(f"{consensus.buy_votes} Buy")
                        if consensus.hold_votes: votes.append(f"{consensus.hold_votes} Hold")
                        if consensus.sell_votes: votes.append(f"{consensus.sell_votes} Sell")
                        if consensus.strong_sell_votes: votes.append(f"{consensus.strong_sell_votes} Strong Sell")
                        
                        if votes:
                            self.stdout.write(f'    Votes: {", ".join(votes)}')
                
                except Exception as e:
                    self.stdout.write(f'  ✗ Consensus error: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Demo Complete! Generated {total_recommendations} recommendations.')
        )
        
        # Show summary
        self.stdout.write('\n📈 Recent Recommendations Summary:')
        recent_recs = AIAdvisorRecommendation.objects.filter(
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).values('recommendation_type').annotate(count=models.Count('id'))
        
        for rec in recent_recs:
            self.stdout.write(f'  {rec["recommendation_type"]}: {rec["count"]}')
        
        # Show consensus summary
        recent_consensus = ConsensusRecommendation.objects.filter(
            created_at__gte=timezone.now() - timedelta(minutes=5)
        )
        
        if recent_consensus.exists():
            self.stdout.write('\n🤝 Consensus Recommendations:')
            for consensus in recent_consensus:
                auto_status = "🤖 Auto-trade eligible" if consensus.auto_trade_eligible else ""
                self.stdout.write(
                    f'  {consensus.stock.symbol}: {consensus.consensus_type} '
                    f'({consensus.participating_advisors} advisors) {auto_status}'
                )
        
        self.stdout.write(
            self.style.SUCCESS('\n✨ Visit the AI Advisors dashboard to see all recommendations!')
        )
