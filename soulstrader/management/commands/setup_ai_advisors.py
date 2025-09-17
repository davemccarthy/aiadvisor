from django.core.management.base import BaseCommand
from soulstrader.models import AIAdvisor
from decimal import Decimal


class Command(BaseCommand):
    help = 'Set up AI advisors with default configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--openai-key',
            type=str,
            help='OpenAI API key',
        )
        parser.add_argument(
            '--claude-key',
            type=str,
            help='Anthropic Claude API key',
        )
        parser.add_argument(
            '--gemini-key',
            type=str,
            help='Google Gemini API key',
        )
        parser.add_argument(
            '--fmp-key',
            type=str,
            help='Financial Modeling Prep API key',
        )
        parser.add_argument(
            '--finnhub-key',
            type=str,
            help='Finnhub API key',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up AI advisors...')
        
        advisors_created = 0
        
        # OpenAI GPT Advisor
        if options.get('openai_key'):
            advisor, created = AIAdvisor.objects.get_or_create(
                name='OpenAI GPT-3.5',
                advisor_type='OPENAI_GPT',
                defaults={
                    'description': 'OpenAI GPT-3.5 Turbo for stock analysis and recommendations',
                    'api_key': options['openai_key'],
                    'rate_limit_per_day': 1000,  # Adjust based on your plan
                    'rate_limit_per_minute': 60,
                    'weight': Decimal('1.00'),
                    'prompt_template': '''
Analyze the stock {symbol} and provide a detailed investment recommendation.

Consider:
- Current market conditions
- Company fundamentals
- Technical indicators
- Recent news and events
- Risk factors

Provide your recommendation in the specified format.
                    '''.strip(),
                    'analysis_parameters': {
                        'model': 'gpt-3.5-turbo',
                        'temperature': 0.3,
                        'max_tokens': 1000
                    }
                }
            )
            if created:
                self.stdout.write(f'✓ Created OpenAI GPT advisor')
                advisors_created += 1
            else:
                # Update API key if provided
                advisor.api_key = options['openai_key']
                advisor.save()
                self.stdout.write(f'✓ Updated OpenAI GPT advisor API key')
        else:
            # Create without API key for setup
            advisor, created = AIAdvisor.objects.get_or_create(
                name='OpenAI GPT-3.5',
                advisor_type='OPENAI_GPT',
                defaults={
                    'description': 'OpenAI GPT-3.5 Turbo for stock analysis and recommendations (API key needed)',
                    'rate_limit_per_day': 1000,
                    'rate_limit_per_minute': 60,
                    'weight': Decimal('1.00'),
                    'is_enabled': False,  # Disabled until API key is added
                    'status': 'INACTIVE'
                }
            )
            if created:
                self.stdout.write(f'⚠ Created OpenAI GPT advisor (disabled - no API key)')
                advisors_created += 1
        
        # Claude Advisor (placeholder for future implementation)
        advisor, created = AIAdvisor.objects.get_or_create(
            name='Anthropic Claude',
            advisor_type='CLAUDE',
            defaults={
                'description': 'Anthropic Claude for detailed stock analysis (coming soon)',
                'api_key': options.get('claude_key', ''),
                'rate_limit_per_day': 500,
                'rate_limit_per_minute': 30,
                'weight': Decimal('1.20'),  # Slightly higher weight
                'is_enabled': False,  # Not implemented yet
                'status': 'INACTIVE'
            }
        )
        if created:
            self.stdout.write(f'⚠ Created Claude advisor (not implemented yet)')
            advisors_created += 1
        
        # Gemini Advisor (placeholder for future implementation)
        advisor, created = AIAdvisor.objects.get_or_create(
            name='Google Gemini',
            advisor_type='GEMINI',
            defaults={
                'description': 'Google Gemini for stock recommendations (coming soon)',
                'api_key': options.get('gemini_key', ''),
                'rate_limit_per_day': 1500,
                'rate_limit_per_minute': 100,
                'weight': Decimal('0.90'),
                'is_enabled': False,  # Not implemented yet
                'status': 'INACTIVE'
            }
        )
        if created:
            self.stdout.write(f'⚠ Created Gemini advisor (not implemented yet)')
            advisors_created += 1
        
        # Perplexity Advisor (placeholder for future implementation)
        advisor, created = AIAdvisor.objects.get_or_create(
            name='Perplexity AI',
            advisor_type='PERPLEXITY',
            defaults={
                'description': 'Perplexity AI for real-time market analysis (coming soon)',
                'rate_limit_per_day': 200,
                'rate_limit_per_minute': 20,
                'weight': Decimal('0.80'),
                'is_enabled': False,  # Not implemented yet
                'status': 'INACTIVE'
            }
        )
        if created:
            self.stdout.write(f'⚠ Created Perplexity advisor (not implemented yet)')
            advisors_created += 1
        
        # FMP Advisor
        if options.get('fmp_key'):
            advisor, created = AIAdvisor.objects.get_or_create(
                name='Financial Modeling Prep',
                advisor_type='FMP',
                defaults={
                    'description': 'Financial Modeling Prep for fundamental analysis and recommendations',
                    'api_key': options['fmp_key'],
                    'rate_limit_per_day': 250,  # Free tier limit
                    'rate_limit_per_minute': 10,
                    'weight': Decimal('1.10'),  # Higher weight for fundamental analysis
                    'prompt_template': 'Analyze fundamental metrics and provide investment recommendation',
                    'analysis_parameters': {
                        'focus': 'fundamental_analysis',
                        'metrics': ['pe_ratio', 'debt_to_equity', 'roe', 'market_cap']
                    }
                }
            )
            if created:
                self.stdout.write(f'✓ Created FMP advisor')
                advisors_created += 1
            else:
                advisor.api_key = options['fmp_key']
                advisor.save()
                self.stdout.write(f'✓ Updated FMP advisor API key')
        else:
            advisor, created = AIAdvisor.objects.get_or_create(
                name='Financial Modeling Prep',
                advisor_type='FMP',
                defaults={
                    'description': 'Financial Modeling Prep for fundamental analysis (API key needed)',
                    'rate_limit_per_day': 250,
                    'rate_limit_per_minute': 10,
                    'weight': Decimal('1.10'),
                    'is_enabled': False,
                    'status': 'INACTIVE'
                }
            )
            if created:
                self.stdout.write(f'⚠ Created FMP advisor (disabled - no API key)')
                advisors_created += 1
        
        # Finnhub Advisor
        if options.get('finnhub_key'):
            advisor, created = AIAdvisor.objects.get_or_create(
                name='Finnhub Market Intelligence',
                advisor_type='FINNHUB',
                defaults={
                    'description': 'Finnhub for analyst consensus, price targets, and market intelligence',
                    'api_key': options['finnhub_key'],
                    'rate_limit_per_day': 3600,  # 60 calls/min * 60 minutes
                    'rate_limit_per_minute': 60,
                    'weight': Decimal('1.20'),  # High weight for analyst consensus
                    'prompt_template': 'Analyze market intelligence and analyst consensus',
                    'analysis_parameters': {
                        'focus': 'market_intelligence',
                        'data_sources': ['analyst_recommendations', 'price_targets', 'news_sentiment']
                    }
                }
            )
            if created:
                self.stdout.write(f'✓ Created Finnhub advisor')
                advisors_created += 1
            else:
                advisor.api_key = options['finnhub_key']
                advisor.save()
                self.stdout.write(f'✓ Updated Finnhub advisor API key')
        else:
            advisor, created = AIAdvisor.objects.get_or_create(
                name='Finnhub Market Intelligence',
                advisor_type='FINNHUB',
                defaults={
                    'description': 'Finnhub for analyst consensus and market intelligence (API key needed)',
                    'rate_limit_per_day': 3600,
                    'rate_limit_per_minute': 60,
                    'weight': Decimal('1.20'),
                    'is_enabled': False,
                    'status': 'INACTIVE'
                }
            )
            if created:
                self.stdout.write(f'⚠ Created Finnhub advisor (disabled - no API key)')
                advisors_created += 1
        
        # Enhanced Yahoo Finance Advisor (no API key needed!)
        advisor, created = AIAdvisor.objects.get_or_create(
            name='Yahoo Finance Enhanced',
            advisor_type='YAHOO_ENHANCED',
            defaults={
                'description': 'Enhanced Yahoo Finance fundamental analysis (free, no API key needed)',
                'rate_limit_per_day': 10000,  # Very generous since it's free
                'rate_limit_per_minute': 100,
                'weight': Decimal('1.00'),
                'is_enabled': True,  # Enable by default since no API key needed
                'status': 'ACTIVE',
                'prompt_template': 'Comprehensive fundamental analysis using Yahoo Finance data',
                'analysis_parameters': {
                    'focus': 'fundamental_analysis',
                    'data_sources': ['financials', 'ratios', 'analyst_targets', 'momentum'],
                    'free_service': True
                }
            }
        )
        if created:
            self.stdout.write(f'✅ Created Enhanced Yahoo advisor (active - no API key needed)')
            advisors_created += 1
        
        # Polygon.io Advisor
        if options.get('polygon_key'):
            advisor, created = AIAdvisor.objects.get_or_create(
                name='Polygon.io Market Data',
                advisor_type='POLYGON',
                defaults={
                    'description': 'Polygon.io for professional market data and analysis',
                    'api_key': options['polygon_key'],
                    'rate_limit_per_day': 1000,  # Free tier
                    'rate_limit_per_minute': 5,
                    'weight': Decimal('1.15'),
                    'prompt_template': 'Professional market data analysis',
                    'analysis_parameters': {
                        'focus': 'market_data',
                        'data_sources': ['real_time_quotes', 'aggregates', 'technical_indicators']
                    }
                }
            )
            if created:
                self.stdout.write(f'✓ Created Polygon.io advisor')
                advisors_created += 1
        else:
            advisor, created = AIAdvisor.objects.get_or_create(
                name='Polygon.io Market Data',
                advisor_type='POLYGON',
                defaults={
                    'description': 'Polygon.io for professional market data (API key needed)',
                    'rate_limit_per_day': 1000,
                    'rate_limit_per_minute': 5,
                    'weight': Decimal('1.15'),
                    'is_enabled': False,
                    'status': 'INACTIVE'
                }
            )
            if created:
                self.stdout.write(f'⚠ Created Polygon.io advisor (disabled - no API key)')
                advisors_created += 1
        
        self.stdout.write(f'\nSetup complete! Created {advisors_created} new advisors.')
        
        # Show status
        active_advisors = AIAdvisor.objects.filter(is_enabled=True, status='ACTIVE').count()
        total_advisors = AIAdvisor.objects.count()
        
        self.stdout.write(f'Active advisors: {active_advisors}/{total_advisors}')
        
        if active_advisors == 0:
            self.stdout.write(
                self.style.WARNING('\nNo active advisors! Add API keys to enable them:')
            )
            self.stdout.write('python manage.py setup_ai_advisors --openai-key YOUR_KEY')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n{active_advisors} advisors ready to provide recommendations!')
            )
