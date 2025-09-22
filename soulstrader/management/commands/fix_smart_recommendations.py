from django.core.management.base import BaseCommand
from django.utils import timezone
from soulstrader.models import SmartRecommendation, Trade, User


class Command(BaseCommand):
    help = 'Fix Smart Recommendations that should be marked as executed based on existing trades'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to fix recommendations for (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        dry_run = options.get('dry_run', False)
        
        # Get users to process
        if username:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
                return
        else:
            users = User.objects.all()
        
        total_fixed = 0
        
        for user in users:
            self.stdout.write(f'\nProcessing user: {user.username}')
            
            # Get all pending Smart Recommendations for this user
            pending_recommendations = SmartRecommendation.objects.filter(
                user=user,
                status='PENDING'
            )
            
            user_fixed = 0
            
            for recommendation in pending_recommendations:
                # Look for matching trades
                matching_trades = Trade.objects.filter(
                    portfolio__user=user,
                    stock=recommendation.stock,
                    trade_type=recommendation.recommendation_type,
                    status='FILLED'
                ).order_by('-created_at')
                
                if matching_trades.exists():
                    trade = matching_trades.first()
                    
                    if dry_run:
                        self.stdout.write(
                            f'  Would mark recommendation {recommendation.id} as executed '
                            f'(matches trade {trade.id} for {trade.stock.symbol})'
                        )
                    else:
                        recommendation.status = 'EXECUTED'
                        recommendation.executed_trade = trade
                        recommendation.executed_at = trade.executed_at or trade.created_at
                        recommendation.save()
                        
                        self.stdout.write(
                            f'  ✓ Marked recommendation {recommendation.id} as executed '
                            f'(matches trade {trade.id} for {trade.stock.symbol})'
                        )
                    
                    user_fixed += 1
            
            if user_fixed == 0:
                self.stdout.write(f'  No recommendations to fix for {user.username}')
            else:
                total_fixed += user_fixed
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nDry run complete. Would fix {total_fixed} recommendations.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nFixed {total_fixed} Smart Recommendations.')
            )
