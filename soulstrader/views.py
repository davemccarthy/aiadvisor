from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import json
from .models import (
    UserProfile, RiskAssessment, Stock, Portfolio, Trade, OrderBook,
    AIRecommendation, PerformanceMetrics, UserNotification,
    AIAdvisor, AIAdvisorRecommendation, ConsensusRecommendation
)
from .trading_service import TradingService
from .market_data_service import MarketDataManager, AlphaVantageService
from .yahoo_finance_service import YahooMarketDataManager, YahooFinanceService


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
        'current_page': 'home',
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
    
    return render(request, 'soulstrader/register.html', {'form': form, 'current_page': 'register'})


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
        'current_page': 'dashboard',
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
        'current_page': 'portfolio',
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
        'current_page': 'recommendations',
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
        'current_page': 'stock_detail',
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
        'current_page': 'profile',
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
        'current_page': 'notifications',
    }
    
    return render(request, 'soulstrader/notifications.html', context)


# =============================================================================
# TRADING VIEWS
# =============================================================================

@login_required
def trading_view(request):
    """Main trading interface"""
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get recent trades
    recent_trades = portfolio.trades.select_related('stock').order_by('-created_at')[:10]
    
    # Get pending orders
    pending_orders = portfolio.trades.filter(
        status__in=['PENDING', 'PARTIALLY_FILLED']
    ).select_related('stock').order_by('-created_at')
    
    # Get trading summary
    trading_summary = TradingService.get_trade_summary(portfolio)
    
    context = {
        'portfolio': portfolio,
        'recent_trades': recent_trades,
        'pending_orders': pending_orders,
        'trading_summary': trading_summary,
        'order_types': Trade.ORDER_TYPES,
        'trade_types': Trade.TRADE_TYPES,
        'current_page': 'trading',
    }
    
    return render(request, 'soulstrader/trading.html', context)


@login_required
def place_order_view(request):
    """Place a new trading order"""
    if request.method == 'POST':
        try:
            # Get form data
            stock_symbol = request.POST.get('stock_symbol', '').upper()
            trade_type = request.POST.get('trade_type')
            quantity = int(request.POST.get('quantity', 0))
            order_type = request.POST.get('order_type', 'MARKET')
            price = request.POST.get('price')
            notes = request.POST.get('notes', '')
            
            # Get stock and portfolio
            stock = get_object_or_404(Stock, symbol=stock_symbol, is_active=True)
            portfolio = get_object_or_404(Portfolio, user=request.user)
            
            # Convert price to Decimal if provided
            limit_price = Decimal(price) if price else None
            
            # Place the order
            trade = TradingService.place_order(
                portfolio=portfolio,
                stock=stock,
                trade_type=trade_type,
                quantity=quantity,
                order_type=order_type,
                price=limit_price,
                notes=notes
            )
            
            if trade:
                if order_type == 'MARKET':
                    messages.success(request, f'Market order executed successfully! {trade.trade_type} {trade.quantity} shares of {stock.symbol} at ${trade.average_fill_price:.2f}')
                else:
                    messages.success(request, f'Limit order placed successfully! {trade.trade_type} {trade.quantity} shares of {stock.symbol} at ${trade.price:.2f}')
                return redirect('soulstrader:trading')
            else:
                messages.error(request, 'Failed to place order. Please check your inputs and try again.')
                
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid input. Please check your values and try again.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    # Get available stocks for the form
    stocks = Stock.objects.filter(is_active=True).order_by('symbol')
    
    context = {
        'stocks': stocks,
        'order_types': Trade.ORDER_TYPES,
        'trade_types': Trade.TRADE_TYPES,
        'current_page': 'trading',
    }
    
    return render(request, 'soulstrader/place_order.html', context)


@login_required
def order_history_view(request):
    """View order history"""
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get all trades with filtering
    trades = portfolio.trades.select_related('stock').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    trade_type_filter = request.GET.get('trade_type')
    stock_filter = request.GET.get('stock')
    
    if status_filter:
        trades = trades.filter(status=status_filter)
    if trade_type_filter:
        trades = trades.filter(trade_type=trade_type_filter)
    if stock_filter:
        trades = trades.filter(stock__symbol__icontains=stock_filter)
    
    # Get trading summary
    trading_summary = TradingService.get_trade_summary(portfolio)
    
    context = {
        'trades': trades,
        'trading_summary': trading_summary,
        'status_choices': Trade.TRADE_STATUS,
        'trade_types': Trade.TRADE_TYPES,
        'current_filters': {
            'status': status_filter,
            'trade_type': trade_type_filter,
            'stock': stock_filter,
        },
        'current_page': 'trading',
    }
    
    return render(request, 'soulstrader/order_history.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_order_view(request, trade_id):
    """Cancel a pending order"""
    try:
        trade = get_object_or_404(Trade, id=trade_id, portfolio__user=request.user)
        
        if TradingService.cancel_order(trade):
            messages.success(request, f'Order cancelled successfully.')
        else:
            messages.error(request, 'Cannot cancel this order.')
            
    except Exception as e:
        messages.error(request, f'Error cancelling order: {str(e)}')
    
    return redirect('soulstrader:trading')


@login_required
def quick_trade_view(request, symbol):
    """Quick trade interface for a specific stock"""
    stock = get_object_or_404(Stock, symbol=symbol.upper(), is_active=True)
    portfolio = get_object_or_404(Portfolio, user=request.user)
    
    # Get user's current holding for this stock
    try:
        holding = portfolio.holdings.get(stock=stock)
    except:
        holding = None
    
    # Get recent recommendations for this stock
    recommendations = AIRecommendation.objects.filter(
        user=request.user,
        stock=stock,
        is_active=True
    ).order_by('-created_at')[:3]
    
    # Check if coming from a specific recommendation
    from_rec_id = request.GET.get('from_rec')
    source_recommendation = None
    if from_rec_id:
        try:
            source_recommendation = AIRecommendation.objects.get(
                id=from_rec_id,
                user=request.user,
                stock=stock,
                is_active=True
            )
        except AIRecommendation.DoesNotExist:
            pass
    
    context = {
        'stock': stock,
        'portfolio': portfolio,
        'holding': holding,
        'recommendations': recommendations,
        'source_recommendation': source_recommendation,
        'order_types': Trade.ORDER_TYPES,
        'trade_types': Trade.TRADE_TYPES,
        'current_page': 'trading',
    }
    
    return render(request, 'soulstrader/quick_trade.html', context)


@login_required
def get_stock_info(request, symbol):
    """AJAX endpoint to get stock information"""
    try:
        stock = get_object_or_404(Stock, symbol=symbol.upper(), is_active=True)
        
        data = {
            'symbol': stock.symbol,
            'name': stock.name,
            'current_price': float(stock.current_price) if stock.current_price else None,
            'day_change': float(stock.day_change) if stock.day_change else None,
            'day_change_percent': float(stock.day_change_percent) if stock.day_change_percent else None,
            'sector': stock.sector,
            'market_cap_category': stock.market_cap_category,
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def simulate_market(request):
    """Simulate market price movements (for testing)"""
    if request.method == 'POST':
        try:
            # Simulate price movements for all stocks
            stocks = Stock.objects.filter(is_active=True, current_price__isnull=False)
            
            for stock in stocks:
                TradingService.simulate_price_movement(stock)
            
            # Process pending orders
            TradingService.process_pending_orders()
            
            messages.success(request, 'Market simulation completed!')
            
        except Exception as e:
            messages.error(request, f'Simulation error: {str(e)}')
    
    return redirect('soulstrader:trading')


@login_required
def quick_buy_from_recommendation(request, recommendation_id):
    """Quick buy action from AI recommendation"""
    try:
        recommendation = get_object_or_404(
            AIRecommendation, 
            id=recommendation_id, 
            user=request.user,
            is_active=True
        )
        
        # Only allow buy actions for buy recommendations
        if recommendation.recommendation_type not in ['BUY', 'STRONG_BUY']:
            messages.error(request, 'This recommendation is not a buy recommendation.')
            return redirect('soulstrader:recommendations')
        
        # Pre-fill the trading form with recommendation data
        return redirect(f"{reverse('soulstrader:quick_trade', args=[recommendation.stock.symbol])}?from_rec={recommendation_id}")
        
    except Exception as e:
        messages.error(request, f'Error processing recommendation: {str(e)}')
        return redirect('soulstrader:recommendations')


@login_required
def quick_sell_from_recommendation(request, recommendation_id):
    """Quick sell action from AI recommendation"""
    try:
        recommendation = get_object_or_404(
            AIRecommendation, 
            id=recommendation_id, 
            user=request.user,
            is_active=True
        )
        
        # Only allow sell actions for sell recommendations
        if recommendation.recommendation_type not in ['SELL', 'STRONG_SELL']:
            messages.error(request, 'This recommendation is not a sell recommendation.')
            return redirect('soulstrader:recommendations')
        
        # Pre-fill the trading form with recommendation data
        return redirect(f"{reverse('soulstrader:quick_trade', args=[recommendation.stock.symbol])}?from_rec={recommendation_id}")
        
    except Exception as e:
        messages.error(request, f'Error processing recommendation: {str(e)}')
        return redirect('soulstrader:recommendations')


@login_required
def search_stocks(request):
    """Search for stocks using Yahoo Finance"""
    if request.method == 'POST':
        keywords = request.POST.get('keywords', '').strip()
        if keywords:
            try:
                # Search for stocks using Yahoo Finance
                symbols = YahooFinanceService.search_symbols(keywords)
                
                # Add results to database
                added_stocks = []
                for symbol_data in symbols:
                    symbol = symbol_data['symbol']
                    if not Stock.objects.filter(symbol=symbol).exists():
                        try:
                            # Create stock and update with real data
                            stock = YahooMarketDataManager.update_stock_quote(symbol)
                            if stock:
                                added_stocks.append(stock)
                        except Exception as e:
                            messages.warning(request, f'Could not add {symbol}: {str(e)}')
                            continue
                
                if added_stocks:
                    messages.success(request, f'Added {len(added_stocks)} new stocks to your watchlist!')
                else:
                    messages.info(request, 'No new stocks found or all results already exist.')
                    
            except Exception as e:
                messages.error(request, f'Search failed: {str(e)}')
        
        return redirect('soulstrader:trading')
    
    return render(request, 'soulstrader/search_stocks.html', {'current_page': 'trading'})


@login_required
def update_stock_data(request, symbol):
    """Update real-time data for a specific stock using Yahoo Finance"""
    try:
        stock = YahooMarketDataManager.update_stock_quote(symbol.upper())
        messages.success(request, f'Updated {symbol} - Current price: ${stock.current_price}')
    except Exception as e:
        messages.error(request, f'Failed to update {symbol}: {str(e)}')
    
    return redirect('soulstrader:stock_detail', symbol=symbol)


@login_required
def market_data_status(request):
    """Show market data status and last update times"""
    stocks = Stock.objects.filter(is_active=True).order_by('-last_updated')
    
    context = {
        'stocks': stocks,
        'current_page': 'trading',
    }
    
    return render(request, 'soulstrader/market_data_status.html', context)


# =============================================================================
# AI ADVISOR VIEWS
# =============================================================================

@login_required
def ai_advisors_dashboard(request):
    """AI Advisors dashboard showing all advisors and their performance"""
    advisors = AIAdvisor.objects.all().order_by('-success_rate', '-weight')
    
    # Get recent recommendations
    recent_recommendations = AIAdvisorRecommendation.objects.select_related(
        'advisor', 'stock'
    ).order_by('-created_at')[:20]
    
    # Get recent consensus recommendations
    recent_consensus = ConsensusRecommendation.objects.select_related(
        'stock'
    ).order_by('-created_at')[:10]
    
    # Calculate overall statistics
    total_recommendations = AIAdvisorRecommendation.objects.count()
    active_advisors = advisors.filter(is_enabled=True, status='ACTIVE').count()
    
    # Performance stats
    successful_recs = AIAdvisorRecommendation.objects.filter(is_successful=True).count()
    overall_success_rate = (successful_recs / total_recommendations * 100) if total_recommendations > 0 else 0
    
    context = {
        'advisors': advisors,
        'recent_recommendations': recent_recommendations,
        'recent_consensus': recent_consensus,
        'total_recommendations': total_recommendations,
        'active_advisors': active_advisors,
        'overall_success_rate': overall_success_rate,
        'current_page': 'ai_advisors',
    }
    
    return render(request, 'soulstrader/ai_advisors_dashboard.html', context)


@login_required
def advisor_detail(request, advisor_id):
    """Detailed view of a specific AI advisor"""
    advisor = get_object_or_404(AIAdvisor, id=advisor_id)
    
    # Get advisor's recommendations
    recommendations = advisor.recommendations.select_related('stock').order_by('-created_at')
    
    # Apply filters
    rec_type = request.GET.get('type')
    if rec_type:
        recommendations = recommendations.filter(recommendation_type=rec_type)
    
    status_filter = request.GET.get('status')
    if status_filter:
        recommendations = recommendations.filter(status=status_filter)
    
    # Performance metrics
    total_recs = recommendations.count()
    successful_recs = recommendations.filter(is_successful=True).count()
    
    # Recent performance (last 30 days)
    from datetime import timedelta
    recent_recs = recommendations.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    )
    
    context = {
        'advisor': advisor,
        'recommendations': recommendations[:50],  # Limit for page load
        'total_recommendations': total_recs,
        'successful_recommendations': successful_recs,
        'recent_recommendations_count': recent_recs.count(),
        'recommendation_types': AIAdvisorRecommendation.RECOMMENDATION_TYPES,
        'recommendation_statuses': AIAdvisorRecommendation.RECOMMENDATION_STATUS,
        'current_filters': {
            'type': rec_type,
            'status': status_filter,
        },
        'current_page': 'ai_advisors',
    }
    
    return render(request, 'soulstrader/advisor_detail.html', context)


@login_required
def consensus_recommendations(request):
    """View consensus recommendations from all advisors"""
    consensus_recs = ConsensusRecommendation.objects.select_related(
        'stock'
    ).prefetch_related('advisor_recommendations__advisor').order_by('-created_at')
    
    # Filter by consensus type
    consensus_type = request.GET.get('type')
    if consensus_type:
        consensus_recs = consensus_recs.filter(consensus_type=consensus_type)
    
    # Filter by auto-trade eligibility
    auto_trade = request.GET.get('auto_trade')
    if auto_trade == 'eligible':
        consensus_recs = consensus_recs.filter(auto_trade_eligible=True)
    elif auto_trade == 'executed':
        consensus_recs = consensus_recs.filter(auto_trade_executed=True)
    
    context = {
        'consensus_recommendations': consensus_recs[:50],
        'consensus_types': ConsensusRecommendation.CONSENSUS_TYPES,
        'current_filters': {
            'type': consensus_type,
            'auto_trade': auto_trade,
        },
        'current_page': 'ai_advisors',
    }
    
    return render(request, 'soulstrader/consensus_recommendations.html', context)


@login_required
def get_stock_recommendations(request, symbol):
    """Get AI recommendations for a specific stock"""
    from .ai_advisor_service import AIAdvisorManager
    
    if request.method == 'POST':
        try:
            stock = get_object_or_404(Stock, symbol=symbol.upper(), is_active=True)
            
            # Get recommendations from all active advisors
            recommendations = AIAdvisorManager.get_recommendations_for_stock(stock)
            
            if recommendations:
                # Create consensus
                consensus = AIAdvisorManager.create_consensus_recommendation(stock, recommendations)
                
                messages.success(
                    request, 
                    f'Got {len(recommendations)} AI recommendations for {symbol}. '
                    f'Consensus: {consensus.consensus_type if consensus else "No consensus"}'
                )
            else:
                messages.warning(request, f'No AI recommendations available for {symbol}')
                
        except Exception as e:
            messages.error(request, f'Error getting recommendations: {str(e)}')
    
    return redirect('soulstrader:stock_detail', symbol=symbol)
