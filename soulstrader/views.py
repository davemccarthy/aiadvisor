from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum
from .models import (
    UserProfile, RiskAssessment, Stock, Portfolio, 
    AIRecommendation, PerformanceMetrics, UserNotification
)


def home(request):
    """SOULTRADER home page"""
    # Get some basic stats
    total_stocks = Stock.objects.filter(is_active=True).count()
    total_users = UserProfile.objects.count()
    total_recommendations = AIRecommendation.objects.filter(is_active=True).count()
    
    # Get recent recommendations for display
    recent_recommendations = AIRecommendation.objects.filter(
        is_active=True
    ).select_related('user', 'stock').order_by('-created_at')[:5]
    
    context = {
        'total_stocks': total_stocks,
        'total_users': total_users,
        'total_recommendations': total_recommendations,
        'recent_recommendations': recent_recommendations,
    }
    
    return render(request, 'soulstrader/home.html', context)


def register(request):
    """User registration page"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile with default settings
            UserProfile.objects.create(
                user=user,
                risk_level='MODERATE',
                investment_goal='BALANCED',
                time_horizon='MEDIUM'
            )
            # Create portfolio for the user
            Portfolio.objects.create(
                user=user,
                name=f"{user.username}'s Portfolio"
            )
            
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('soulstrader:login')
    else:
        form = UserCreationForm()
    
    return render(request, 'soulstrader/register.html', {'form': form})


def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('soulstrader:home')


@login_required
def dashboard(request):
    """User dashboard - main interface"""
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'risk_level': 'MODERATE',
            'investment_goal': 'BALANCED',
            'time_horizon': 'MEDIUM'
        }
    )
    
    # Get or create portfolio
    portfolio, created = Portfolio.objects.get_or_create(
        user=request.user,
        defaults={'name': f"{request.user.username}'s Portfolio"}
    )
    
    # Get user's recent recommendations
    recent_recommendations = AIRecommendation.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('stock').order_by('-created_at')[:5]
    
    # Get user's recent notifications
    recent_notifications = UserNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Get portfolio performance (last 30 days)
    performance_data = PerformanceMetrics.objects.filter(
        portfolio=portfolio
    ).order_by('-date')[:30]
    
    # Get user's holdings
    holdings = portfolio.holdings.select_related('stock').all()
    
    context = {
        'profile': profile,
        'portfolio': portfolio,
        'recent_recommendations': recent_recommendations,
        'recent_notifications': recent_notifications,
        'performance_data': performance_data,
        'holdings': holdings,
    }
    
    return render(request, 'soulstrader/dashboard.html', context)


@login_required
def portfolio_view(request):
    """Detailed portfolio view"""
    portfolio = get_object_or_404(Portfolio, user=request.user)
    holdings = portfolio.holdings.select_related('stock').all()
    
    # Calculate portfolio metrics
    total_invested = sum(holding.quantity * holding.average_price for holding in holdings)
    total_current_value = sum(holding.current_value for holding in holdings)
    total_unrealized_pnl = total_current_value - total_invested
    
    # Get recent trades
    recent_trades = portfolio.trades.select_related('stock').order_by('-created_at')[:10]
    
    context = {
        'portfolio': portfolio,
        'holdings': holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'recent_trades': recent_trades,
    }
    
    return render(request, 'soulstrader/portfolio.html', context)


@login_required
def recommendations_view(request):
    """AI recommendations view"""
    recommendations = AIRecommendation.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('stock').order_by('-created_at')
    
    # Filter by recommendation type if specified
    rec_type = request.GET.get('type')
    if rec_type:
        recommendations = recommendations.filter(recommendation_type=rec_type)
    
    # Filter by confidence level if specified
    confidence = request.GET.get('confidence')
    if confidence:
        recommendations = recommendations.filter(confidence_level=confidence)
    
    context = {
        'recommendations': recommendations,
        'recommendation_types': AIRecommendation.RECOMMENDATION_TYPES,
        'confidence_levels': AIRecommendation.CONFIDENCE_LEVELS,
    }
    
    return render(request, 'soulstrader/recommendations.html', context)


@login_required
def stock_detail(request, symbol):
    """Individual stock detail view"""
    stock = get_object_or_404(Stock, symbol=symbol.upper())
    
    # Get recent price data
    recent_prices = stock.prices.all()[:30]
    
    # Get user's recommendations for this stock
    user_recommendations = AIRecommendation.objects.filter(
        user=request.user,
        stock=stock,
        is_active=True
    ).order_by('-created_at')[:5]
    
    # Get user's holding for this stock if any
    user_holding = None
    try:
        user_holding = request.user.portfolio.holdings.get(stock=stock)
    except:
        pass
    
    context = {
        'stock': stock,
        'recent_prices': recent_prices,
        'user_recommendations': user_recommendations,
        'user_holding': user_holding,
    }
    
    return render(request, 'soulstrader/stock_detail.html', context)


@login_required
def profile_view(request):
    """User profile and settings"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    # Get risk assessment if exists
    try:
        risk_assessment = request.user.risk_assessment
    except:
        risk_assessment = None
    
    context = {
        'profile': profile,
        'risk_assessment': risk_assessment,
    }
    
    return render(request, 'soulstrader/profile.html', context)


@login_required
def notifications_view(request):
    """User notifications"""
    notifications = UserNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Mark all as read when viewing
    notifications.update(is_read=True)
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'soulstrader/notifications.html', context)
