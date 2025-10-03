from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


# =============================================================================
# USER PROFILE & RISK MANAGEMENT MODELS
# =============================================================================

class UserProfile(models.Model):
    """Extended user profile with investment preferences and risk settings"""
    
    RISK_LEVELS = [
        ('CONSERVATIVE', 'Conservative'),
        ('MODERATE', 'Moderate'),
        ('AGGRESSIVE', 'Aggressive'),
    ]
    
    INVESTMENT_GOALS = [
        ('GROWTH', 'Growth'),
        ('INCOME', 'Income'),
        ('PRESERVATION', 'Capital Preservation'),
        ('BALANCED', 'Balanced'),
    ]
    
    TIME_HORIZONS = [
        ('SHORT', 'Short Term (1-3 years)'),
        ('MEDIUM', 'Medium Term (3-7 years)'),
        ('LONG', 'Long Term (7+ years)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='MODERATE')
    investment_goal = models.CharField(max_length=20, choices=INVESTMENT_GOALS, default='BALANCED')
    time_horizon = models.CharField(max_length=10, choices=TIME_HORIZONS, default='MEDIUM')
    
    # Portfolio settings
    initial_capital = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100000.00'))
    max_positions = models.IntegerField(default=20, validators=[MinValueValidator(1), MaxValueValidator(50)])
    max_position_size = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))  # Max % per position
    
    # Investment preferences
    preferred_sectors = models.JSONField(default=list, blank=True)  # ['Technology', 'Healthcare', etc.]
    preferred_market_cap = models.CharField(max_length=20, default='LARGE_CAP', choices=[
        ('LARGE_CAP', 'Large Cap'),
        ('MID_CAP', 'Mid Cap'),
        ('SMALL_CAP', 'Small Cap'),
        ('MIXED', 'Mixed'),
    ])
    
    # ESG preferences
    esg_focused = models.BooleanField(default=False)
    esg_score_minimum = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0'), 
                                          validators=[MinValueValidator(0), MaxValueValidator(10)])
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    daily_summary = models.BooleanField(default=True)
    recommendation_alerts = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.risk_level} ({self.investment_goal})"


class RiskAssessment(models.Model):
    """User's risk assessment questionnaire results"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='risk_assessment')
    
    # Risk tolerance questions (0-10 scale)
    age = models.IntegerField(validators=[MinValueValidator(18), MaxValueValidator(100)])
    investment_experience = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    risk_tolerance = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    volatility_comfort = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    loss_tolerance = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    
    # Calculated risk score
    risk_score = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    recommended_risk_level = models.CharField(max_length=20, choices=UserProfile.RISK_LEVELS)
    
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Risk Score: {self.risk_score}"


# =============================================================================
# STOCK & MARKET DATA MODELS
# =============================================================================

class Stock(models.Model):
    """Stock information and metadata"""
    
    SECTORS = [
        ('TECHNOLOGY', 'Technology'),
        ('HEALTHCARE', 'Healthcare'),
        ('FINANCIAL', 'Financial Services'),
        ('CONSUMER_DISCRETIONARY', 'Consumer Discretionary'),
        ('INDUSTRIALS', 'Industrials'),
        ('CONSUMER_STAPLES', 'Consumer Staples'),
        ('ENERGY', 'Energy'),
        ('UTILITIES', 'Utilities'),
        ('REAL_ESTATE', 'Real Estate'),
        ('MATERIALS', 'Materials'),
        ('COMMUNICATION', 'Communication Services'),
        ('OTHER', 'Other'),
    ]
    
    MARKET_CAP_CATEGORIES = [
        ('LARGE_CAP', 'Large Cap ($10B+)'),
        ('MID_CAP', 'Mid Cap ($2B-$10B)'),
        ('SMALL_CAP', 'Small Cap ($300M-$2B)'),
        ('MICRO_CAP', 'Micro Cap (<$300M)'),
    ]
    
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    sector = models.CharField(max_length=30, choices=SECTORS, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    market_cap = models.BigIntegerField(null=True, blank=True)
    market_cap_category = models.CharField(max_length=20, choices=MARKET_CAP_CATEGORIES, blank=True)
    
    # International market support
    currency = models.CharField(max_length=3, default='USD', help_text="Trading currency (USD, EUR, GBP, CHF, etc.)")
    exchange = models.CharField(max_length=20, blank=True, help_text="Stock exchange (NYSE, LSE, SIX, etc.)")
    
    # Current pricing
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    previous_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    day_change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    day_change_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Fundamental data
    pe_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pb_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dividend_yield = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # ESG data
    esg_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
                                  validators=[MinValueValidator(0), MaxValueValidator(10)])
    
    # FMP API specific fields
    logo_url = models.URLField(blank=True, null=True, help_text="Company logo URL from FMP API")
    fmp_grade = models.CharField(max_length=20, blank=True, null=True, help_text="FMP consensus grade (A+, A, B+, etc.)")
    fmp_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="FMP numerical score")
    analyst_target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    analyst_rating_strong_buy = models.IntegerField(default=0)
    analyst_rating_buy = models.IntegerField(default=0)
    analyst_rating_hold = models.IntegerField(default=0)
    analyst_rating_sell = models.IntegerField(default=0)
    analyst_rating_strong_sell = models.IntegerField(default=0)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['symbol']
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"


class StockPrice(models.Model):
    """Historical stock price data"""
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='prices')
    date = models.DateField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()
    adjusted_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ['stock', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.stock.symbol} - {self.date} - ${self.close_price}"


# =============================================================================
# PORTFOLIO & TRADING MODELS
# =============================================================================

class Portfolio(models.Model):
    """User's personal trading portfolio"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='portfolio')
    name = models.CharField(max_length=100, default="My Portfolio")
    
    # Capital management
    initial_capital = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100000.00'))
    current_capital = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100000.00'))
    total_invested = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Portfolio settings
    is_active = models.BooleanField(default=True)
    auto_rebalance = models.BooleanField(default=False)
    rebalance_frequency = models.CharField(max_length=20, default='MONTHLY', choices=[
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('MANUAL', 'Manual'),
    ])
    
    # Sell aggressiveness setting
    sell_weight = models.IntegerField(
        default=5,
        help_text="Portfolio-level sell aggressiveness (1=conservative, 10=aggressive). Overrides risk profile setting."
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Portfolio"
    
    @property
    def total_value(self):
        """Calculate total portfolio value (cash + holdings)"""
        holdings_value = sum(holding.current_value for holding in self.holdings.all())
        return self.current_capital + holdings_value
    
    @property
    def total_return(self):
        """Calculate total return percentage"""
        if self.initial_capital > 0:
            return ((self.total_value - self.initial_capital) / self.initial_capital) * 100
        return 0


class Holding(models.Model):
    """User's stock holdings in their portfolio"""
    
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='holdings')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['portfolio', 'stock']
    
    def __str__(self):
        return f"{self.portfolio.user.username} - {self.stock.symbol} x{self.quantity}"
    
    @property
    def current_value(self):
        """Calculate current value of holding"""
        if self.stock.current_price:
            return self.quantity * self.stock.current_price
        return 0
    
    @property
    def unrealized_pnl(self):
        """Calculate unrealized profit/loss"""
        current_value = self.current_value
        cost_basis = self.quantity * self.average_price
        return current_value - cost_basis
    
    @property
    def unrealized_pnl_percent(self):
        """Calculate unrealized P&L percentage"""
        cost_basis = self.quantity * self.average_price
        if cost_basis > 0:
            return (self.unrealized_pnl / cost_basis) * 100
        return 0


class Trade(models.Model):
    """Trade execution records"""
    
    TRADE_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    ORDER_TYPES = [
        ('MARKET', 'Market Order'),
        ('LIMIT', 'Limit Order'),
        ('STOP', 'Stop Order'),
        ('STOP_LIMIT', 'Stop Limit Order'),
    ]
    
    TRADE_STATUS = [
        ('PENDING', 'Pending'),
        ('PARTIALLY_FILLED', 'Partially Filled'),
        ('FILLED', 'Filled'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    
    TRADE_SOURCES = [
        ('MANUAL', 'Manual Trade'),
        ('AI_RECOMMENDATION', 'AI Recommendation'),
        ('SMART_ANALYSIS', 'Smart Analysis'),
        ('MARKET_SCREENING', 'Market Screening'),
        ('AUTOMATED_STRATEGY', 'Automated Strategy'),
        ('REBALANCING', 'Portfolio Rebalancing'),
        ('STOP_LOSS', 'Stop Loss Trigger'),
        ('TAKE_PROFIT', 'Take Profit Trigger'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='trades')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default='MARKET')
    
    # Order details
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Limit price
    stop_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Stop price
    
    # Execution details
    filled_quantity = models.IntegerField(default=0)
    average_fill_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    commission = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    status = models.CharField(max_length=20, choices=TRADE_STATUS, default='PENDING')
    
    # Time-based fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Trade source and explanation
    trade_source = models.CharField(max_length=20, choices=TRADE_SOURCES, default='MANUAL')
    source_reference = models.CharField(max_length=200, blank=True, help_text="Reference to source (e.g., advisor name, recommendation ID)")
    
    # Additional fields (expanded notes for detailed explanations)
    notes = models.TextField(blank=True, help_text="Detailed explanation of trade reasoning")
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.portfolio.user.username} - {self.trade_type} {self.quantity} {self.stock.symbol} @ ${self.price or 'Market'}"
    
    @property
    def remaining_quantity(self):
        """Calculate remaining quantity to be filled"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_completely_filled(self):
        """Check if order is completely filled"""
        return self.filled_quantity >= self.quantity
    
    @property
    def is_active(self):
        """Check if order is still active"""
        return self.status in ['PENDING', 'PARTIALLY_FILLED']
    
    @property
    def is_automated(self):
        """Check if trade was automated"""
        return self.trade_source != 'MANUAL'
    
    def get_source_display_with_icon(self):
        """Get trade source with appropriate icon"""
        source_icons = {
            'MANUAL': '👤',
            'AI_RECOMMENDATION': '🤖',
            'SMART_ANALYSIS': '🧠',
            'MARKET_SCREENING': '📈',
            'AUTOMATED_STRATEGY': '⚙️',
            'REBALANCING': '⚖️',
            'STOP_LOSS': '🛑',
            'TAKE_PROFIT': '🎯',
        }
        icon = source_icons.get(self.trade_source, '📊')
        display = self.get_trade_source_display()
        return f"{icon} {display}"
    
    def save(self, *args, **kwargs):
        # Calculate total amount based on filled quantity and average price
        if self.average_fill_price and self.filled_quantity:
            self.total_amount = self.filled_quantity * self.average_fill_price
        elif self.price and self.quantity and not self.total_amount:
            # For pending orders, calculate based on order price and quantity
            self.total_amount = self.quantity * self.price
        super().save(*args, **kwargs)


class OrderBook(models.Model):
    """Simulated order book for tracking pending orders"""
    
    trade = models.OneToOneField(Trade, on_delete=models.CASCADE, related_name='order_book_entry')
    priority = models.IntegerField(default=0)  # For order matching priority
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['priority', 'created_at']
    
    def __str__(self):
        return f"Order: {self.trade}"


# =============================================================================
# AI ADVISOR MODELS
# =============================================================================

class AIAdvisor(models.Model):
    """AI Advisor services that provide stock recommendations"""
    
    ADVISOR_TYPES = [
        ('OPENAI_GPT', 'OpenAI GPT'),
        ('CLAUDE', 'Anthropic Claude'),
        ('GEMINI', 'Google Gemini'),
        ('PERPLEXITY', 'Perplexity AI'),
        ('FMP', 'Financial Modeling Prep'),
        ('FINNHUB', 'Finnhub'),
        ('YAHOO_ENHANCED', 'Yahoo Finance Enhanced'),
        ('POLYGON', 'Polygon.io'),
        ('IEX_CLOUD', 'IEX Cloud'),
        ('MARKET_SCREENING', 'Market Screening Service'),
        ('CUSTOM', 'Custom AI Service'),
    ]
    
    ADVISOR_STATUS = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('LIMITED', 'Limited (Trial/Rate Limited)'),
        ('ERROR', 'Error State'),
    ]
    
    name = models.CharField(max_length=100)
    advisor_type = models.CharField(max_length=20, choices=ADVISOR_TYPES)
    description = models.TextField(blank=True)
    
    # API Configuration
    api_key = models.CharField(max_length=500, blank=True, null=True)
    api_endpoint = models.URLField(blank=True, null=True)
    rate_limit_per_day = models.IntegerField(default=100)
    rate_limit_per_minute = models.IntegerField(default=10)
    
    # Status and Performance
    status = models.CharField(max_length=20, choices=ADVISOR_STATUS, default='ACTIVE')
    is_enabled = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('1.00'))  # Voting weight
    
    # Performance Metrics
    total_recommendations = models.IntegerField(default=0)
    successful_recommendations = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_confidence = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    
    # Usage Tracking
    daily_api_calls = models.IntegerField(default=0)
    monthly_api_calls = models.IntegerField(default=0)
    last_api_call = models.DateTimeField(null=True, blank=True)
    last_reset_date = models.DateField(auto_now_add=True)
    
    # Configuration
    prompt_template = models.TextField(blank=True)
    analysis_parameters = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-success_rate', '-weight', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_advisor_type_display()}) - {self.success_rate}%"
    
    @property
    def daily_calls_remaining(self):
        """Calculate remaining daily API calls"""
        return max(0, self.rate_limit_per_day - self.daily_api_calls)
    
    def can_make_request(self):
        """Check if advisor can make a request"""
        return (self.is_enabled and 
                self.status == 'ACTIVE' and 
                self.daily_calls_remaining > 0)
    
    def update_success_rate(self):
        """Update success rate based on recommendations"""
        if self.total_recommendations > 0:
            self.success_rate = (self.successful_recommendations / self.total_recommendations) * 100
        else:
            self.success_rate = 0
        self.save()


class AIAdvisorRecommendation(models.Model):
    """Individual recommendations from AI advisors"""
    
    RECOMMENDATION_TYPES = [
        ('STRONG_BUY', 'Strong Buy'),
        ('BUY', 'Buy'),
        ('HOLD', 'Hold'),
        ('SELL', 'Sell'),
        ('STRONG_SELL', 'Strong Sell'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('VERY_HIGH', 'Very High'),
    ]
    
    RECOMMENDATION_STATUS = [
        ('ACTIVE', 'Active'),
        ('EXECUTED', 'Executed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advisor = models.ForeignKey(AIAdvisor, on_delete=models.CASCADE, related_name='recommendations')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='ai_recommendations')
    
    # Recommendation Details
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVELS)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Price Targets
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_at_recommendation = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Analysis
    reasoning = models.TextField()
    key_factors = models.JSONField(default=list, blank=True)  # List of key factors
    technical_indicators = models.JSONField(default=dict, blank=True)
    risk_factors = models.JSONField(default=list, blank=True)
    
    # Performance Tracking
    status = models.CharField(max_length=20, choices=RECOMMENDATION_STATUS, default='ACTIVE')
    is_successful = models.BooleanField(null=True, blank=True)  # Determined later
    actual_return = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    # API Response
    raw_response = models.JSONField(default=dict, blank=True)
    processing_time = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['advisor', 'stock', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['recommendation_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.advisor.name} - {self.stock.symbol} - {self.recommendation_type} ({self.confidence_level})"
    
    @property
    def current_return(self):
        """Calculate current return since recommendation"""
        if self.stock.current_price and self.price_at_recommendation:
            return ((self.stock.current_price - self.price_at_recommendation) / self.price_at_recommendation) * 100
        return 0
    
    @property
    def is_expired(self):
        """Check if recommendation has expired"""
        return self.expires_at and timezone.now() > self.expires_at


class ConsensusRecommendation(models.Model):
    """Aggregated recommendations from multiple AI advisors"""
    
    CONSENSUS_TYPES = [
        ('STRONG_BUY', 'Strong Buy'),
        ('BUY', 'Buy'),
        ('HOLD', 'Hold'),
        ('SELL', 'Sell'),
        ('STRONG_SELL', 'Strong Sell'),
        ('NO_CONSENSUS', 'No Consensus'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='consensus_recommendations')
    
    # Consensus Details
    consensus_type = models.CharField(max_length=20, choices=CONSENSUS_TYPES)
    consensus_strength = models.DecimalField(max_digits=3, decimal_places=2)  # 0.0 to 1.0
    total_advisors = models.IntegerField()
    participating_advisors = models.IntegerField()
    
    # Vote Breakdown
    strong_buy_votes = models.IntegerField(default=0)
    buy_votes = models.IntegerField(default=0)
    hold_votes = models.IntegerField(default=0)
    sell_votes = models.IntegerField(default=0)
    strong_sell_votes = models.IntegerField(default=0)
    
    # Weighted Scores
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2)  # -100 to +100
    average_confidence = models.DecimalField(max_digits=3, decimal_places=2)
    average_target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Related Recommendations
    advisor_recommendations = models.ManyToManyField(AIAdvisorRecommendation, related_name='consensus_recommendations')
    
    # Auto-trading
    auto_trade_eligible = models.BooleanField(default=False)
    auto_trade_executed = models.BooleanField(default=False)
    auto_trade = models.ForeignKey(Trade, on_delete=models.SET_NULL, null=True, blank=True, related_name='consensus_recommendation')
    
    # Performance
    price_at_consensus = models.DecimalField(max_digits=10, decimal_places=2)
    is_successful = models.BooleanField(null=True, blank=True)
    actual_return = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stock', '-created_at']),
            models.Index(fields=['consensus_type', '-created_at']),
            models.Index(fields=['auto_trade_eligible', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.stock.symbol} - {self.consensus_type} ({self.participating_advisors}/{self.total_advisors} advisors)"
    
    @property
    def consensus_percentage(self):
        """Calculate consensus percentage"""
        if self.total_advisors > 0:
            return (self.participating_advisors / self.total_advisors) * 100
        return 0


# =============================================================================
# LEGACY AI RECOMMENDATION MODELS (keeping for backward compatibility)
# =============================================================================

class AIRecommendation(models.Model):
    """AI-generated stock recommendations personalized for each user"""
    
    RECOMMENDATION_TYPES = [
        ('STRONG_BUY', 'Strong Buy'),
        ('BUY', 'Buy'),
        ('HOLD', 'Hold'),
        ('SELL', 'Sell'),
        ('STRONG_SELL', 'Strong Sell'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('VERY_HIGH', 'Very High'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='recommendations')
    
    # Recommendation details
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVELS)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Price targets
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Analysis details
    reasoning = models.TextField()
    technical_analysis = models.JSONField(default=dict, blank=True)
    fundamental_analysis = models.JSONField(default=dict, blank=True)
    sentiment_analysis = models.JSONField(default=dict, blank=True)
    risk_assessment = models.JSONField(default=dict, blank=True)
    
    # User-specific factors
    risk_adjusted = models.BooleanField(default=True)
    user_risk_level = models.CharField(max_length=20, choices=UserProfile.RISK_LEVELS)
    portfolio_fit = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)  # How well it fits user's portfolio
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'stock', 'created_at']  # One recommendation per user per stock per day
    
    def __str__(self):
        return f"{self.user.username} - {self.stock.symbol} - {self.recommendation_type} ({self.confidence_level})"


# =============================================================================
# PERFORMANCE & ANALYTICS MODELS
# =============================================================================

class PerformanceMetrics(models.Model):
    """Portfolio performance tracking per user"""
    
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='performance_metrics')
    date = models.DateField()
    
    # Portfolio values
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    total_return = models.DecimalField(max_digits=8, decimal_places=2)  # Percentage
    daily_return = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Risk metrics
    sharpe_ratio = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    volatility = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    beta = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    # Portfolio composition
    cash_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sector_diversification = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['portfolio', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.portfolio.user.username} - {self.date} - {self.total_return}%"


class UserNotification(models.Model):
    """User notifications and alerts"""
    
    NOTIFICATION_TYPES = [
        ('RECOMMENDATION', 'New Recommendation'),
        ('TRADE_EXECUTED', 'Trade Executed'),
        ('PORTFOLIO_ALERT', 'Portfolio Alert'),
        ('MARKET_UPDATE', 'Market Update'),
        ('REBALANCE_REMINDER', 'Rebalance Reminder'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Notification status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.title}"


# =============================================================================
# SMART ANALYSIS & PORTFOLIO OPTIMIZATION MODELS
# =============================================================================

class RiskProfile(models.Model):
    """User's risk profile settings for automated portfolio optimization"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='risk_profile')
    
    # Portfolio optimization settings
    max_purchase_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('5.00'),
        help_text="Maximum percentage of portfolio value that can be invested in a single stock"
    )
    min_confidence_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.70'),
        help_text="Minimum confidence score threshold for recommendations"
    )
    cash_spend_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('20.00'),
        help_text="Percentage of available cash to spend on new positions"
    )
    
    # Anti-repetition settings
    cooldown_period_days = models.IntegerField(
        default=7,
        help_text="Minimum days between purchases of the same stock"
    )
    max_rebuy_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('50.00'),
        help_text="Maximum percentage of existing position that can be added in a single buy"
    )
    
    # Diversification rules
    max_sector_allocation = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('30.00'),
        help_text="Maximum percentage of portfolio in any single sector"
    )
    min_diversification_stocks = models.IntegerField(
        default=5,
        help_text="Minimum number of different stocks to maintain"
    )
    
    # Risk tolerance settings
    allow_penny_stocks = models.BooleanField(
        default=False,
        help_text="Allow penny stocks (price < $5) and micro-cap stocks (market cap < $100M) in recommendations"
    )
    min_stock_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('5.00'),
        help_text="Minimum stock price threshold (penny stock filter)"
    )
    min_market_cap = models.BigIntegerField(
        default=100_000_000,
        help_text="Minimum market cap threshold in USD (micro-cap filter)"
    )
    
    # Sell aggressiveness settings
    sell_weight = models.IntegerField(
        default=5,
        help_text="Sell aggressiveness multiplier (1=conservative, 10=aggressive). Multiplies sell confidence scores."
    )
    sell_hold_threshold = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.30'),
        help_text="Minimum adjusted confidence to consider HOLD as partial SELL"
    )
    
    # Profit-taking settings
    profit_taking_enabled = models.BooleanField(
        default=True,
        help_text="Enable automated profit-taking on volatile stocks with significant gains"
    )
    profit_taking_threshold = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('10.00'),
        help_text="Minimum gain percentage to trigger profit-taking recommendation"
    )
    volatility_threshold = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('20.00'),
        help_text="Minimum annual volatility percentage to consider stock for profit-taking"
    )
    
    # Automation settings
    auto_execute_trades = models.BooleanField(
        default=False,
        help_text="Automatically execute recommended trades"
    )
    auto_rebalance_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic portfolio rebalancing"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Risk Profile"


class SmartRecommendation(models.Model):
    """Consolidated smart recommendations from automated portfolio optimization"""
    
    RECOMMENDATION_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('HOLD', 'Hold'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('EXECUTED', 'Executed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='smart_recommendations')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='smart_recommendations')
    
    # Recommendation details
    recommendation_type = models.CharField(max_length=10, choices=RECOMMENDATION_TYPES)
    priority_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Consolidated priority score")
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, help_text="Overall confidence score")
    
    # Buy algorithm fields
    initial_weight = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    adjusted_weight = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    shares_to_buy = models.IntegerField(null=True, blank=True)
    cash_allocated = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Portfolio context
    existing_shares = models.IntegerField(default=0, help_text="Current shares owned")
    current_position_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    position_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Price information
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Analysis details
    reasoning = models.TextField(help_text="Consolidated reasoning from all advisors")
    key_factors = models.JSONField(default=list, blank=True)
    risk_factors = models.JSONField(default=list, blank=True)
    
    # Related recommendations
    advisor_recommendations = models.ManyToManyField(
        AIAdvisorRecommendation, 
        related_name='smart_recommendations',
        blank=True
    )
    
    # Execution tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    executed_trade = models.ForeignKey(
        Trade, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='smart_recommendation'
    )
    
    # Performance tracking
    is_successful = models.BooleanField(null=True, blank=True)
    actual_return = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority_score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['recommendation_type', '-priority_score']),
            models.Index(fields=['stock', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.stock.symbol} - {self.recommendation_type} (PS: {self.priority_score})"
    
    @property
    def is_expired(self):
        """Check if recommendation has expired"""
        from django.utils import timezone
        return self.expires_at and timezone.now() > self.expires_at
    
    @property
    def current_return(self):
        """Calculate current return since recommendation"""
        if self.stock.current_price and self.current_price:
            return ((self.stock.current_price - self.current_price) / self.current_price) * 100
        return 0


class SmartAnalysisSession(models.Model):
    """Track automated portfolio optimization sessions"""
    
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='smart_analysis_sessions')
    
    # Session details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING')
    total_recommendations = models.IntegerField(default=0)
    executed_recommendations = models.IntegerField(default=0)
    
    # Portfolio state at time of analysis
    portfolio_value = models.DecimalField(max_digits=12, decimal_places=2)
    available_cash = models.DecimalField(max_digits=12, decimal_places=2)
    total_cash_spend = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Analysis parameters
    risk_profile_snapshot = models.JSONField(default=dict, help_text="Risk profile settings at time of analysis")
    advisor_weights = models.JSONField(default=dict, help_text="Advisor weights used in analysis")
    
    # Results summary
    recommendations_summary = models.JSONField(default=dict, blank=True)
    execution_summary = models.JSONField(default=dict, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processing_time_seconds = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Smart Analysis - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def success_rate(self):
        """Calculate success rate of executed recommendations"""
        if self.total_recommendations > 0:
            return (self.executed_recommendations / self.total_recommendations) * 100
        return 0
