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
    
    # Additional fields
    notes = models.TextField(blank=True)
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
# AI RECOMMENDATION MODELS
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
