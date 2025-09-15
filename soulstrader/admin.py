from django.contrib import admin
from .models import (
    UserProfile, RiskAssessment, Stock, StockPrice, Portfolio, 
    Holding, Trade, AIRecommendation, PerformanceMetrics, UserNotification
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'risk_level', 'investment_goal', 'time_horizon', 'initial_capital', 'created_at']
    list_filter = ['risk_level', 'investment_goal', 'time_horizon', 'esg_focused', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'risk_score', 'recommended_risk_level', 'age', 'investment_experience', 'completed_at']
    list_filter = ['recommended_risk_level', 'completed_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['completed_at']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'sector', 'market_cap_category', 'current_price', 'esg_score', 'is_active']
    list_filter = ['sector', 'market_cap_category', 'is_active', 'created_at']
    search_fields = ['symbol', 'name', 'industry']
    readonly_fields = ['created_at', 'last_updated']


@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    list_display = ['stock', 'date', 'close_price', 'volume', 'open_price', 'high_price', 'low_price']
    list_filter = ['date', 'stock__sector']
    search_fields = ['stock__symbol', 'stock__name']
    date_hierarchy = 'date'


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'initial_capital', 'current_capital', 'total_value', 'is_active', 'created_at']
    list_filter = ['is_active', 'auto_rebalance', 'rebalance_frequency', 'created_at']
    search_fields = ['user__username', 'name']
    readonly_fields = ['created_at', 'last_updated', 'total_value', 'total_return']


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'stock', 'quantity', 'average_price', 'current_value', 'unrealized_pnl_percent']
    list_filter = ['stock__sector', 'purchase_date']
    search_fields = ['portfolio__user__username', 'stock__symbol', 'stock__name']
    readonly_fields = ['purchase_date', 'last_updated', 'current_value', 'unrealized_pnl', 'unrealized_pnl_percent']


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'stock', 'trade_type', 'quantity', 'price', 'total_amount', 'status', 'created_at']
    list_filter = ['trade_type', 'status', 'created_at']
    search_fields = ['portfolio__user__username', 'stock__symbol', 'stock__name']
    readonly_fields = ['id', 'total_amount', 'created_at', 'executed_at']
    date_hierarchy = 'created_at'


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'stock', 'recommendation_type', 'confidence_level', 'confidence_score', 'user_risk_level', 'created_at']
    list_filter = ['recommendation_type', 'confidence_level', 'user_risk_level', 'risk_adjusted', 'is_active', 'created_at']
    search_fields = ['user__username', 'stock__symbol', 'stock__name', 'reasoning']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(PerformanceMetrics)
class PerformanceMetricsAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'date', 'total_value', 'total_return', 'daily_return', 'sharpe_ratio']
    list_filter = ['date']
    search_fields = ['portfolio__user__username']
    readonly_fields = ['date']
    date_hierarchy = 'date'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'is_sent', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_sent', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
