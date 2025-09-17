from django.contrib import admin
from .models import (
    UserProfile, RiskAssessment, Stock, StockPrice, Portfolio, 
    Holding, Trade, OrderBook, AIRecommendation, PerformanceMetrics, UserNotification,
    AIAdvisor, AIAdvisorRecommendation, ConsensusRecommendation
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
    list_display = ['portfolio', 'stock', 'trade_type', 'order_type', 'quantity', 'price', 'status', 'created_at']
    list_filter = ['trade_type', 'order_type', 'status', 'created_at']
    search_fields = ['portfolio__user__username', 'stock__symbol', 'stock__name']
    readonly_fields = ['id', 'total_amount', 'created_at', 'executed_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(OrderBook)
class OrderBookAdmin(admin.ModelAdmin):
    list_display = ['trade', 'priority', 'is_active']
    list_filter = ['is_active', 'priority']
    search_fields = ['trade__portfolio__user__username', 'trade__stock__symbol']


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


# =============================================================================
# AI ADVISOR ADMIN
# =============================================================================

@admin.register(AIAdvisor)
class AIAdvisorAdmin(admin.ModelAdmin):
    list_display = ['name', 'advisor_type', 'status', 'is_enabled', 'success_rate', 'weight', 'daily_calls_remaining', 'last_api_call']
    list_filter = ['advisor_type', 'status', 'is_enabled', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['total_recommendations', 'successful_recommendations', 'success_rate', 'daily_api_calls', 'monthly_api_calls', 'last_api_call', 'last_reset_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'advisor_type', 'description')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'api_endpoint', 'rate_limit_per_day', 'rate_limit_per_minute'),
            'description': 'Configure API access and rate limits'
        }),
        ('Status & Performance', {
            'fields': ('status', 'is_enabled', 'weight', 'total_recommendations', 'successful_recommendations', 'success_rate', 'average_confidence')
        }),
        ('Usage Tracking', {
            'fields': ('daily_api_calls', 'monthly_api_calls', 'last_api_call', 'last_reset_date'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('prompt_template', 'analysis_parameters'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def daily_calls_remaining(self, obj):
        return obj.daily_calls_remaining
    daily_calls_remaining.short_description = 'Daily Calls Remaining'


@admin.register(AIAdvisorRecommendation)
class AIAdvisorRecommendationAdmin(admin.ModelAdmin):
    list_display = ['advisor', 'stock', 'recommendation_type', 'confidence_level', 'confidence_score', 'target_price', 'current_return', 'status', 'created_at']
    list_filter = ['advisor', 'recommendation_type', 'confidence_level', 'status', 'created_at']
    search_fields = ['advisor__name', 'stock__symbol', 'stock__name', 'reasoning']
    readonly_fields = ['id', 'current_return', 'created_at', 'processing_time']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('advisor', 'stock', 'recommendation_type', 'confidence_level', 'confidence_score')
        }),
        ('Price Information', {
            'fields': ('target_price', 'stop_loss', 'price_at_recommendation', 'current_return')
        }),
        ('Analysis', {
            'fields': ('reasoning', 'key_factors', 'technical_indicators', 'risk_factors')
        }),
        ('Performance', {
            'fields': ('status', 'is_successful', 'actual_return', 'expires_at', 'evaluated_at')
        }),
        ('Metadata', {
            'fields': ('raw_response', 'processing_time', 'created_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ConsensusRecommendation)
class ConsensusRecommendationAdmin(admin.ModelAdmin):
    list_display = ['stock', 'consensus_type', 'consensus_strength', 'participating_advisors', 'weighted_score', 'auto_trade_eligible', 'auto_trade_executed', 'created_at']
    list_filter = ['consensus_type', 'auto_trade_eligible', 'auto_trade_executed', 'created_at']
    search_fields = ['stock__symbol', 'stock__name']
    readonly_fields = ['id', 'consensus_percentage', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Consensus Details', {
            'fields': ('stock', 'consensus_type', 'consensus_strength', 'total_advisors', 'participating_advisors')
        }),
        ('Vote Breakdown', {
            'fields': ('strong_buy_votes', 'buy_votes', 'hold_votes', 'sell_votes', 'strong_sell_votes')
        }),
        ('Weighted Analysis', {
            'fields': ('weighted_score', 'average_confidence', 'average_target_price')
        }),
        ('Auto-Trading', {
            'fields': ('auto_trade_eligible', 'auto_trade_executed', 'auto_trade')
        }),
        ('Performance', {
            'fields': ('price_at_consensus', 'is_successful', 'actual_return')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def consensus_percentage(self, obj):
        return f"{obj.consensus_percentage:.1f}%"
    consensus_percentage.short_description = 'Consensus %'
