"""
Management command for Smart Analysis - Automated Portfolio Optimization

Usage:
    python manage.py smartanalyse [username]          # Analyze specific user
    python manage.py smartanalyse --all               # Analyze all users
    python manage.py smartanalyse --auto-execute      # Auto-execute trades
    python manage.py smartanalyse --dry-run           # Show what would be done
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
import logging

from soulstrader.smart_analysis_service import SmartAnalysisService
from soulstrader.models import RiskProfile, SmartAnalysisSession

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Smart Analysis for automated portfolio optimization'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            nargs='?',
            type=str,
            help='Username to analyze (optional, defaults to all users)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Analyze all users'
        )
        parser.add_argument(
            '--auto-execute',
            action='store_true',
            help='Automatically execute recommended trades'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force analysis even if recent analysis exists'
        )
        parser.add_argument(
            '--min-cash',
            type=float,
            default=1000.0,
            help='Minimum cash required for analysis (default: 1000)'
        )
        parser.add_argument(
            '--max-users',
            type=int,
            default=10,
            help='Maximum number of users to analyze (default: 10)'
        )
    
    def handle(self, *args, **options):
        """Handle the smartanalyse command"""
        
        # Initialize service
        smart_service = SmartAnalysisService()
        
        # Determine which users to analyze
        users_to_analyze = self._get_users_to_analyze(options)
        
        if not users_to_analyze:
            self.stdout.write(
                self.style.WARNING('No users found to analyze')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting Smart Analysis for {len(users_to_analyze)} user(s)')
        )
        
        # Process each user
        successful_analyses = 0
        failed_analyses = 0
        
        for user in users_to_analyze:
            try:
                self._analyze_user(
                    user, 
                    smart_service, 
                    options
                )
                successful_analyses += 1
                
            except Exception as e:
                logger.error(f"Smart Analysis failed for user {user.username}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f'Failed to analyze {user.username}: {str(e)}')
                )
                failed_analyses += 1
                continue
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSmart Analysis completed:\n'
                f'  Successful: {successful_analyses}\n'
                f'  Failed: {failed_analyses}\n'
                f'  Total: {successful_analyses + failed_analyses}'
            )
        )
    
    def _get_users_to_analyze(self, options):
        """Get list of users to analyze based on options"""
        users = []
        
        if options['username']:
            # Analyze specific user
            try:
                user = User.objects.get(username=options['username'])
                users.append(user)
            except User.DoesNotExist:
                raise CommandError(f'User "{options["username"]}" does not exist')
                
        elif options['all']:
            # Analyze all users
            users = User.objects.filter(is_active=True)
            
        else:
            # Default: analyze users with recent activity
            users = self._get_active_users()
        
        # Filter users based on criteria
        filtered_users = []
        min_cash = Decimal(str(options['min_cash']))
        max_users = options['max_users']
        
        for user in users:
            # Check if user has enough cash
            if hasattr(user, 'portfolio') and user.portfolio.current_capital >= min_cash:
                # Check if recent analysis exists (unless forced)
                if not options['force'] and self._has_recent_analysis(user):
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping {user.username} - recent analysis exists (use --force to override)'
                        )
                    )
                    continue
                
                filtered_users.append(user)
                
                if len(filtered_users) >= max_users:
                    break
        
        return filtered_users
    
    def _get_active_users(self):
        """Get users with recent activity"""
        # Get users who have made trades in the last 30 days
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now() - timedelta(days=30)
        
        users = User.objects.filter(
            is_active=True,
            portfolio__trades__created_at__gte=recent_date
        ).distinct()
        
        return users
    
    def _has_recent_analysis(self, user):
        """Check if user has recent smart analysis"""
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now() - timedelta(hours=6)  # 6 hours cooldown
        
        return SmartAnalysisSession.objects.filter(
            user=user,
            started_at__gte=recent_date,
            status='COMPLETED'
        ).exists()
    
    def _analyze_user(self, user, smart_service, options):
        """Analyze a single user"""
        self.stdout.write(f'\nAnalyzing user: {user.username}')
        
        # Get or create risk profile
        risk_profile, created = RiskProfile.objects.get_or_create(
            user=user,
            defaults={
                'max_purchase_percentage': Decimal('5.00'),
                'min_confidence_score': Decimal('0.70'),
                'cash_spend_percentage': Decimal('20.00'),
            }
        )
        
        if created:
            self.stdout.write(
                self.style.WARNING(f'  Created default risk profile for {user.username}')
            )
        
        # Show current portfolio status
        portfolio = user.portfolio
        self.stdout.write(
            f'  Portfolio Value: ${portfolio.total_value:,.2f}\n'
            f'  Available Cash: ${portfolio.current_capital:,.2f}\n'
            f'  Cash Spend %: {risk_profile.cash_spend_percentage}%\n'
            f'  Max Purchase %: {risk_profile.max_purchase_percentage}%\n'
            f'  Min Confidence: {risk_profile.min_confidence_score}'
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('  DRY RUN - No changes will be made')
            )
            return
        
        # Run smart analysis
        auto_execute = options['auto_execute'] and risk_profile.auto_execute_trades
        
        if auto_execute:
            self.stdout.write(
                self.style.WARNING('  AUTO-EXECUTE ENABLED - Trades will be executed automatically')
            )
        
        try:
            with transaction.atomic():
                session = smart_service.smart_analyse(
                    user=user,
                    auto_execute=auto_execute
                )
                
                # Display results
                self._display_analysis_results(session)
                
        except Exception as e:
            logger.error(f"Smart Analysis failed for user {user.username}: {str(e)}")
            raise
    
    def _display_analysis_results(self, session):
        """Display smart analysis results"""
        self.stdout.write(f'\n  Analysis Results:')
        self.stdout.write(f'    Status: {session.status}')
        self.stdout.write(f'    Total Recommendations: {session.total_recommendations}')
        self.stdout.write(f'    Executed: {session.executed_recommendations}')
        self.stdout.write(f'    Processing Time: {session.processing_time_seconds:.2f}s')
        
        if session.recommendations_summary:
            summary = session.recommendations_summary
            self.stdout.write(f'    Buy Recommendations: {summary.get("buy_recommendations", 0)}')
            self.stdout.write(f'    Total Cash Allocated: ${summary.get("total_cash_allocated", 0):,.2f}')
            self.stdout.write(f'    Avg Priority Score: {summary.get("average_priority_score", 0):.2f}')
            self.stdout.write(f'    Avg Confidence: {summary.get("average_confidence_score", 0):.2f}')
        
        if session.status == 'FAILED':
            self.stdout.write(
                self.style.ERROR(f'    Error: {session.error_message}')
            )
        
        # Show individual recommendations
        recommendations = session.user.smart_recommendations.filter(
            created_at__gte=session.started_at
        ).order_by('-priority_score')[:5]  # Top 5
        
        if recommendations:
            self.stdout.write(f'\n  Top Recommendations:')
            for rec in recommendations:
                self.stdout.write(
                    f'    {rec.stock.symbol}: {rec.recommendation_type} '
                    f'(PS: {rec.priority_score:.2f}, CS: {rec.confidence_score:.2f})'
                )
                if rec.shares_to_buy:
                    self.stdout.write(
                        f'      Shares to Buy: {rec.shares_to_buy}, '
                        f'Cash: ${rec.cash_allocated:,.2f}'
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Analysis completed for {session.user.username}')
        )
