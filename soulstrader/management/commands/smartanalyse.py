"""
Management command for Smart Analysis - Automated Portfolio Optimization

Usage:
    python manage.py smartanalyse <username>         # Analyze specific user
    python manage.py smartanalyse --all              # Analyze all users
    python manage.py smartanalyse --batch-optimize   # Force batch optimization

Options:
    --auto-execute    Automatically execute recommended trades
    --dry-run         Show what would be done without making changes
    --force           Force analysis even if recent analysis exists
    --bestbuyonly     Only analyze best buy opportunities
    --min-cash N      Minimum cash required (default: 1000)
    --max-users N     Maximum number of users (default: 10)

Note: All analysis uses batch optimization to minimize API calls.
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
        parser.add_argument(
            '--bestbuyonly',
            action='store_true',
            help='Only analyze best buy opportunities, skip existing holdings analysis'
        )
        parser.add_argument(
            '--batch-optimize',
            action='store_true',
            help='Force batch optimization to minimize API calls'
        )
    
    def handle(self, *args, **options):
        """Handle the smartanalyse command"""
        
        # Check if no options provided - show usage
        if not any([options['username'], options['all'], options['batch_optimize']]):
            self.stdout.write(
                self.style.ERROR('Error: No analysis target specified')
            )
            self.stdout.write('\nUsage:')
            self.stdout.write('  python manage.py smartanalyse <username>     # Analyze specific user')
            self.stdout.write('  python manage.py smartanalyse --all          # Analyze all users')
            self.stdout.write('  python manage.py smartanalyse --batch-optimize # Force batch optimization')
            self.stdout.write('\nOptions:')
            self.stdout.write('  --auto-execute    Automatically execute recommended trades')
            self.stdout.write('  --dry-run         Show what would be done without making changes')
            self.stdout.write('  --force           Force analysis even if recent analysis exists')
            self.stdout.write('  --bestbuyonly     Only analyze best buy opportunities')
            self.stdout.write('  --min-cash N      Minimum cash required (default: 1000)')
            self.stdout.write('  --max-users N     Maximum number of users (default: 10)')
            return
        
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
        
        # Always use batch optimization (removed individual processing)
        successful_analyses = 0
        failed_analyses = 0
        
        if len(users_to_analyze) > 1:
            # Use batch optimization for multiple users
            self.stdout.write(
                self.style.SUCCESS('Using batch optimization to minimize API calls...')
            )
            
            try:
                sessions = smart_service.batch_analyze_users(
                    users_to_analyze,
                    auto_execute=options['auto_execute'],
                    bestbuyonly=options['bestbuyonly']
                )
                
                successful_analyses = len(sessions)
                failed_analyses = len(users_to_analyze) - successful_analyses
                
                # Display results for each session
                for session in sessions:
                    self._display_analysis_results(session)
                    
            except Exception as e:
                logger.error(f"Batch analysis failed: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f'Batch analysis failed: {str(e)}')
                )
                failed_analyses = len(users_to_analyze)
        else:
            # Single user - still use batch optimization for consistency
            try:
                sessions = smart_service.batch_analyze_users(
                    users_to_analyze,
                    auto_execute=options['auto_execute'],
                    bestbuyonly=options['bestbuyonly']
                )
                
                successful_analyses = len(sessions)
                failed_analyses = len(users_to_analyze) - successful_analyses
                
                # Display results for each session
                for session in sessions:
                    self._display_analysis_results(session)
                    
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f'Analysis failed: {str(e)}')
                )
                failed_analyses = len(users_to_analyze)
        
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
            
        elif options['batch_optimize']:
            # Force batch optimization - analyze all users
            users = User.objects.filter(is_active=True)
        
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
        
        # Display candidate information
        if hasattr(session, 'candidate_info') and session.candidate_info:
            self._display_candidate_info(session.candidate_info)
        
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
    
    def _display_candidate_info(self, candidate_info):
        """Display candidate information for analysis"""
        self.stdout.write(f'\n  📊 Analysis Candidates:')
        
        # Current holdings
        if candidate_info.get('current_holdings'):
            holdings_str = ', '.join(candidate_info['current_holdings'])
            self.stdout.write(f'    Current Holdings ({len(candidate_info["current_holdings"])}): {holdings_str}')
        else:
            self.stdout.write(f'    Current Holdings: Skipped (best-buy-only mode)')
        
        # Best buy candidates from market screening
        if candidate_info.get('best_buy_candidates'):
            best_buys_str = ', '.join(candidate_info['best_buy_candidates'])
            self.stdout.write(f'    Market Screening Candidates ({len(candidate_info["best_buy_candidates"])}): {best_buys_str}')
        else:
            self.stdout.write(f'    Market Screening Candidates: None (using fallback list)')
        
        # High confidence buy candidates
        if candidate_info.get('high_confidence_buys'):
            high_conf_str = ', '.join(candidate_info['high_confidence_buys'])
            self.stdout.write(f'    High Confidence BUYs ({len(candidate_info["high_confidence_buys"])}): {high_conf_str}')
        
        # Sell candidates
        if candidate_info.get('sell_candidates'):
            sell_str = ', '.join(candidate_info['sell_candidates'])
            self.stdout.write(f'    Sell Candidates ({len(candidate_info["sell_candidates"])}): {sell_str}')
        else:
            self.stdout.write(f'    Sell Candidates: Skipped (best-buy-only mode)')
        
        # Total unique tickers analyzed
        all_tickers = set()
        for ticker_list in candidate_info.values():
            all_tickers.update(ticker_list)
        self.stdout.write(f'    Total Unique Tickers Analyzed: {len(all_tickers)}')
