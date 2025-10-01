"""
API Serializers for SOULTRADER iOS App
Converts Django models to JSON format
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from soulstrader.models import (
    Stock, Portfolio, Holding, Trade, 
    SmartRecommendation, SmartAnalysisSession, 
    UserProfile, RiskProfile
)


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock model"""
    # Convert Decimal fields to Float for proper JSON encoding
    current_price = serializers.FloatField(read_only=True)
    previous_close = serializers.FloatField(read_only=True, allow_null=True)
    day_change = serializers.FloatField(read_only=True, allow_null=True)
    day_change_percent = serializers.FloatField(read_only=True, allow_null=True)
    
    class Meta:
        model = Stock
        fields = [
            'symbol', 'name', 'logo_url', 'current_price', 
            'previous_close', 'day_change', 'day_change_percent',
            'fmp_grade', 'currency', 'exchange', 'sector'
        ]


class HoldingSerializer(serializers.ModelSerializer):
    """Serializer for Holding model - for Portfolio view"""
    stock = StockSerializer(read_only=True)
    # Convert Decimal fields to Float
    average_price = serializers.FloatField(read_only=True)
    current_value = serializers.FloatField(read_only=True)
    unrealized_pnl = serializers.FloatField(read_only=True)
    unrealized_pnl_percent = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Holding
        fields = [
            'id', 'stock', 'quantity', 'average_price', 
            'current_value', 'unrealized_pnl', 'unrealized_pnl_percent',
            'purchase_date', 'last_updated'
        ]


class PortfolioSummarySerializer(serializers.ModelSerializer):
    """Serializer for Portfolio summary"""
    # Convert Decimal fields to Float
    initial_capital = serializers.FloatField(read_only=True)
    current_capital = serializers.FloatField(read_only=True)
    total_value = serializers.FloatField(read_only=True)
    total_invested = serializers.FloatField(read_only=True)
    total_return = serializers.FloatField(read_only=True)
    total_return_percent = serializers.FloatField(read_only=True)
    holdings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'name', 'initial_capital', 'current_capital',
            'total_value', 'total_invested', 'total_return', 
            'total_return_percent', 'holdings_count', 'created_at'
        ]
    
    def get_holdings_count(self, obj):
        return obj.holdings.count()


class TradeSerializer(serializers.ModelSerializer):
    """Serializer for Trade model - for Trades view"""
    stock = StockSerializer(read_only=True)
    # Convert Decimal fields to Float
    price = serializers.FloatField(read_only=True, allow_null=True)
    average_fill_price = serializers.FloatField(read_only=True, allow_null=True)
    total_amount = serializers.FloatField(read_only=True)
    commission = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Trade
        fields = [
            'id', 'stock', 'trade_type', 'order_type', 'quantity',
            'price', 'average_fill_price', 'total_amount', 'commission',
            'status', 'trade_source', 'executed_at', 'created_at', 'notes'
        ]


class SmartRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for Smart Recommendation - for Analysis view"""
    stock = StockSerializer(read_only=True)
    # Convert Decimal fields to Float
    priority_score = serializers.FloatField(read_only=True)
    confidence_score = serializers.FloatField(read_only=True)
    current_price = serializers.FloatField(read_only=True)
    target_price = serializers.FloatField(read_only=True, allow_null=True)
    stop_loss = serializers.FloatField(read_only=True, allow_null=True)
    cash_allocated = serializers.FloatField(read_only=True, allow_null=True)
    
    class Meta:
        model = SmartRecommendation
        fields = [
            'id', 'stock', 'recommendation_type', 'priority_score',
            'confidence_score', 'shares_to_buy', 'cash_allocated',
            'current_price', 'target_price', 'stop_loss',
            'reasoning', 'key_factors', 'risk_factors',
            'status', 'created_at', 'expires_at'
        ]


class SmartAnalysisSessionSerializer(serializers.ModelSerializer):
    """Serializer for Smart Analysis Session"""
    # Convert Decimal and numeric fields to Float
    portfolio_value = serializers.FloatField(read_only=True)
    available_cash = serializers.FloatField(read_only=True)
    total_cash_spend = serializers.FloatField(read_only=True)
    processing_time_seconds = serializers.FloatField(read_only=True, allow_null=True)
    
    class Meta:
        model = SmartAnalysisSession
        fields = [
            'id', 'status', 'started_at', 'completed_at',
            'processing_time_seconds', 'total_recommendations',
            'executed_recommendations', 'portfolio_value',
            'available_cash', 'total_cash_spend',
            'recommendations_summary'
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for User Profile"""
    
    class Meta:
        model = UserProfile
        fields = [
            'risk_level', 'investment_goal', 'time_horizon',
            'max_positions', 'esg_focused'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
