"""
API Views for SOULTRADER iOS App
Provides REST API endpoints for mobile clients
"""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal

from soulstrader.models import (
    Portfolio, Holding, Trade, SmartRecommendation, 
    SmartAnalysisSession, UserProfile, RiskProfile
)
from .serializers import (
    HoldingSerializer, PortfolioSummarySerializer, TradeSerializer,
    SmartRecommendationSerializer, SmartAnalysisSessionSerializer,
    UserSerializer
)


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom login endpoint that returns user info along with tokens
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Add user info to response
            from django.contrib.auth.models import User
            user = User.objects.get(username=request.data.get('username'))
            user_serializer = UserSerializer(user)
            response.data['user'] = user_serializer.data
        
        return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current authenticated user information
    GET /api/auth/user/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# =============================================================================
# PORTFOLIO ENDPOINTS (iOS Tab 1)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_portfolio_holdings(request):
    """
    Get user's portfolio holdings
    GET /api/portfolio/holdings/
    
    Returns:
        {
            "portfolio_summary": {...},
            "holdings": [...]
        }
    """
    # Get user's portfolio
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get all holdings
    holdings = portfolio.holdings.select_related('stock').order_by('-last_updated', '-purchase_date')
    
    # Calculate portfolio metrics (matching web version)
    total_invested = sum(holding.quantity * holding.average_price for holding in holdings)
    total_current_value = sum(holding.current_value for holding in holdings)
    
    # Total portfolio return (matching web version)
    total_unrealized_pnl = portfolio.total_value - portfolio.initial_capital
    total_unrealized_pnl_percent = portfolio.total_return
    
    # Portfolio summary
    portfolio_summary = {
        'total_value': portfolio.total_value,
        'available_cash': portfolio.current_capital,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_unrealized_pnl_percent': total_unrealized_pnl_percent,
        'holdings_count': holdings.count()
    }
    
    # Serialize holdings
    holdings_serializer = HoldingSerializer(holdings, many=True)
    
    return Response({
        'portfolio_summary': portfolio_summary,
        'holdings': holdings_serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_portfolio_summary(request):
    """
    Get portfolio summary only (without holdings)
    GET /api/portfolio/summary/
    """
    portfolio = get_object_or_404(Portfolio, user=request.user)
    serializer = PortfolioSummarySerializer(portfolio)
    return Response(serializer.data)


# =============================================================================
# TRADES ENDPOINTS (iOS Tab 2)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_trades(request):
    """
    Get user's recent trades
    GET /api/trades/recent/
    
    Query Parameters:
        limit: Number of trades to return (default: 20)
    """
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get limit from query params (default 20)
    limit = int(request.query_params.get('limit', 20))
    
    # Get recent trades
    trades = portfolio.trades.select_related('stock').order_by('-created_at')[:limit]
    
    serializer = TradeSerializer(trades, many=True)
    
    return Response({
        'count': trades.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_trades(request):
    """
    Get all trades with pagination
    GET /api/trades/
    """
    portfolio = get_object_or_404(Portfolio, user=request.user)
    trades = portfolio.trades.select_related('stock').order_by('-created_at')
    
    # Use DRF pagination
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginated_trades = paginator.paginate_queryset(trades, request)
    
    serializer = TradeSerializer(paginated_trades, many=True)
    return paginator.get_paginated_response(serializer.data)


# =============================================================================
# SMART ANALYSIS ENDPOINTS (iOS Tab 3)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_smart_analysis(request):
    """
    Get latest smart analysis results
    GET /api/analysis/smart/
    
    Returns:
        {
            "latest_session": {...},
            "recommendations": [...]
        }
    """
    user = request.user
    
    # Get latest smart analysis session
    latest_session = SmartAnalysisSession.objects.filter(
        user=user,
        status='COMPLETED'
    ).order_by('-completed_at').first()
    
    if not latest_session:
        return Response({
            'message': 'No smart analysis sessions found. Run analysis first.',
            'latest_session': None,
            'recommendations': []
        })
    
    # Get recommendations from latest session
    recommendations = SmartRecommendation.objects.filter(
        user=user,
        created_at__gte=latest_session.started_at
    ).select_related('stock').order_by('-priority_score')
    
    # Serialize data
    session_serializer = SmartAnalysisSessionSerializer(latest_session)
    recommendations_serializer = SmartRecommendationSerializer(recommendations, many=True)
    
    return Response({
        'latest_session': session_serializer.data,
        'recommendations': recommendations_serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_sessions(request):
    """
    Get smart analysis session history
    GET /api/analysis/sessions/
    """
    sessions = SmartAnalysisSession.objects.filter(
        user=request.user
    ).order_by('-started_at')[:10]
    
    serializer = SmartAnalysisSessionSerializer(sessions, many=True)
    
    return Response({
        'count': sessions.count(),
        'results': serializer.data
    })


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_health_check(request):
    """
    Health check endpoint
    GET /api/health/
    """
    return Response({
        'status': 'healthy',
        'user': request.user.username,
        'timestamp': str(timezone.now())
    })
