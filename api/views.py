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
        'bank_balance': float(getattr(portfolio, 'safety_bank_balance', Decimal('0.00'))),
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
def get_stock_trades(request, symbol):
    """
    Get all trades for a specific stock
    GET /api/trades/stock/{symbol}/
    
    Returns all trades for the specified stock symbol
    """
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get trades for this stock
    trades = portfolio.trades.filter(
        stock__symbol=symbol.upper()
    ).select_related('stock').order_by('-created_at')
    
    serializer = TradeSerializer(trades, many=True)
    
    return Response({
        'symbol': symbol.upper(),
        'count': trades.count(),
        'trades': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trade_summary(request):
    """
    Get trade summary statistics for the user
    GET /api/trades/summary/
    """
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get all trades for calculations
    trades = portfolio.trades.all()
    
    # Get all holdings for current value calculations
    holdings = portfolio.holdings.all()
    
    # Calculate summary statistics
    total_invested = float(sum(trade.total_amount for trade in trades))
    total_current_value = float(sum(holding.current_value for holding in holdings))
    total_unrealized_pnl = total_current_value - total_invested
    total_unrealized_pnl_percent = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
    
    # Get total shares across all holdings (current positions)
    total_shares = sum(holding.quantity for holding in holdings)
    
    # Get available cash and bank balance from portfolio
    available_cash = float(portfolio.current_capital)
    bank_balance = float(getattr(portfolio, 'safety_bank_balance', Decimal('0.00')))
    
    # Calculate total value (current value + available cash + bank balance)
    total_value = total_current_value + available_cash + bank_balance
    
    summary_data = {
        'total_value': float(total_value),
        'available_cash': float(available_cash),
        'bank_balance': bank_balance,
        'total_invested': float(total_invested),
        'total_current_value': float(total_current_value),
        'total_unrealized_pnl': float(total_unrealized_pnl),
        'total_unrealized_pnl_percent': float(total_unrealized_pnl_percent),
        'trades_count': trades.count(),
        'shares_count': total_shares
    }
    
    return Response(summary_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_trades(request):
    """
    Get all trades with pagination
    GET /api/trades/
    
    Query Parameters:
        symbol: Filter by stock symbol (optional)
    """
    portfolio = get_object_or_404(Portfolio, user=request.user)
    trades = portfolio.trades.select_related('stock').order_by('-created_at')
    
    # Filter by symbol if provided
    symbol = request.query_params.get('symbol', None)
    if symbol:
        trades = trades.filter(stock__symbol=symbol.upper())
    
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trade_analysis(request, trade_id):
    """
    Get detailed analysis for a specific trade
    GET /api/analysis/trade/{trade_id}/
    
    Returns detailed analysis including:
    - Trade summary
    - Individual advisor recommendations
    - Algorithm steps
    - Technical details
    """
    user = request.user
    
    # Get the trade
    try:
        trade = Trade.objects.get(id=trade_id, portfolio__user=user)
    except Trade.DoesNotExist:
        return Response({
            'error': 'Trade not found'
        }, status=404)
    
    # Get the smart recommendation that led to this trade
    smart_recommendation = None
    if trade.trade_source == 'SMART_ANALYSIS':
        # Try to find the smart recommendation that led to this trade
        smart_recommendation = SmartRecommendation.objects.filter(
            user=user,
            stock=trade.stock,
            recommendation_type=trade.trade_type,
            created_at__lte=trade.created_at
        ).order_by('-created_at').first()
    
    # Prepare response data
    response_data = {
        'trade': {
            'id': str(trade.id),
            'stock': {
                'symbol': trade.stock.symbol,
                'name': trade.stock.name,
                'logo_url': trade.stock.logo_url,
                'current_price': float(trade.stock.current_price or 0),
            },
            'trade_type': trade.trade_type,
            'quantity': trade.quantity,
            'total_amount': float(trade.total_amount),
            'executed_at': trade.executed_at,
            'trade_source': trade.trade_source,
        },
        'advisor_recommendations': [],
        'algorithm_steps': [],
        'technical_details': {}
    }
    
    # Get individual advisor recommendations if smart recommendation exists
    if smart_recommendation:
        advisor_recs = smart_recommendation.advisor_recommendations.select_related('advisor').all()
        
        for rec in advisor_recs:
            # Clean up reasoning text by replacing newlines with spaces
            cleaned_reasoning = rec.reasoning.replace('\n', ' ').replace('\r', ' ').strip()
            # Remove multiple spaces
            cleaned_reasoning = ' '.join(cleaned_reasoning.split())
            
            # Improve readability by creating a more natural summary
            # Extract key information and create a concise summary
            summary_parts = []
            
            # Look for key phrases and extract them
            if 'Analyst Consensus' in cleaned_reasoning:
                summary_parts.append("Strong analyst consensus")
            if 'Price Target' in cleaned_reasoning:
                summary_parts.append("positive price targets")
            if 'News' in cleaned_reasoning:
                summary_parts.append("favorable news sentiment")
            if 'Analysis Score' in cleaned_reasoning:
                summary_parts.append("solid analysis metrics")
            
            # Create a natural summary if we found key parts
            if summary_parts:
                cleaned_reasoning = f"Analysis shows {', '.join(summary_parts)} with strong market intelligence support."
            else:
                # Fallback: ensure proper sentence structure
                if not cleaned_reasoning.endswith('.'):
                    cleaned_reasoning += '.'
                # Capitalize first letter
                if cleaned_reasoning:
                    cleaned_reasoning = cleaned_reasoning[0].upper() + cleaned_reasoning[1:]
            
            # Include ALL advisor recommendations for this stock (not just matching trade type)
            response_data['advisor_recommendations'].append({
                'advisor_name': rec.advisor.name,
                'recommendation_type': rec.recommendation_type,
                'confidence_score': float(rec.confidence_score),
                'reasoning': cleaned_reasoning,
                'target_price': float(rec.target_price) if rec.target_price else None,
            })
        
        # Add algorithm steps (placeholder for now)
        response_data['algorithm_steps'] = [
            f"Stock {trade.stock.symbol} chosen for consideration from market movers",
            f"{len(advisor_recs)} advisors gave combined confidence score of {float(smart_recommendation.confidence_score):.2f}",
            f"${float(trade.total_amount):.0f} allocated to {trade.trade_type.lower()} {trade.quantity} shares based on confidence"
        ]
        
        # Add technical details
        response_data['technical_details'] = {
            'priority_score': float(smart_recommendation.priority_score),
            'confidence_score': float(smart_recommendation.confidence_score),
            'recommendation_type': smart_recommendation.recommendation_type,
            'current_price': float(smart_recommendation.current_price),
            'target_price': float(smart_recommendation.target_price) if smart_recommendation.target_price else None,
            'stop_loss': float(smart_recommendation.stop_loss) if smart_recommendation.stop_loss else None,
            'key_factors': smart_recommendation.key_factors,
            'risk_factors': smart_recommendation.risk_factors,
            'reasoning': smart_recommendation.reasoning,
        }
    
    return Response(response_data)


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
