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
    # Count both legacy and new advisor recommendations
    legacy_recommendations = AIRecommendation.objects.filter(is_active=True).count()
    advisor_recommendations = AIAdvisorRecommendation.objects.filter(status='ACTIVE').count()
    total_recommendations = legacy_recommendations + advisor_recommendations
    
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
    """AI recommendations view - shows both legacy and new advisor recommendations"""
    
    # Get legacy user-specific recommendations
    legacy_recommendations = AIRecommendation.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('stock').order_by('-created_at')
    
    # Get new AI advisor recommendations (not user-specific, but general market recommendations)
    advisor_recommendations = AIAdvisorRecommendation.objects.filter(
        status='ACTIVE'
    ).select_related('stock', 'advisor').order_by('-created_at')
    
    # Filter by recommendation type if specified
    rec_type = request.GET.get('type')
    if rec_type:
        legacy_recommendations = legacy_recommendations.filter(recommendation_type=rec_type)
        advisor_recommendations = advisor_recommendations.filter(recommendation_type=rec_type)
    
    # Filter by confidence level if specified
    confidence = request.GET.get('confidence')
    if confidence:
        legacy_recommendations = legacy_recommendations.filter(confidence_level=confidence)
        advisor_recommendations = advisor_recommendations.filter(confidence_level=confidence)
    
    # Combine and sort recommendations by date
    all_recommendations = []
    
    # Add legacy recommendations
    for rec in legacy_recommendations:
        all_recommendations.append({
            'type': 'legacy',
            'recommendation': rec,
            'created_at': rec.created_at,
            'stock': rec.stock,
            'recommendation_type': rec.recommendation_type,
            'confidence_level': rec.confidence_level,
            'confidence_score': rec.confidence_score,
            'reasoning': rec.reasoning,
            'advisor_name': 'Personal AI',
        })
    
    # Add advisor recommendations
    for rec in advisor_recommendations:
        all_recommendations.append({
            'type': 'advisor',
            'recommendation': rec,
            'created_at': rec.created_at,
            'stock': rec.stock,
            'recommendation_type': rec.recommendation_type,
            'confidence_level': rec.confidence_level,
            'confidence_score': rec.confidence_score,
            'reasoning': rec.reasoning,
            'advisor_name': rec.advisor.name,
        })
    
    # Sort by creation date (newest first)
    all_recommendations.sort(key=lambda x: x['created_at'], reverse=True)
    
    context = {
        'all_recommendations': all_recommendations,
        'legacy_count': legacy_recommendations.count(),
        'advisor_count': advisor_recommendations.count(),
        'total_count': len(all_recommendations),
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
            result = TradingService.place_order(
                portfolio=portfolio,
                stock=stock,
                trade_type=trade_type,
                quantity=quantity,
                order_type=order_type,
                price=limit_price,
                notes=notes
            )
            
            if result['success']:
                trade = result['trade']
                if order_type == 'MARKET':
                    messages.success(request, f'Market order executed successfully! {trade.trade_type} {trade.quantity} shares of {stock.symbol} at ${trade.average_fill_price:.2f}')
                else:
                    messages.success(request, f'Limit order placed successfully! {trade.trade_type} {trade.quantity} shares of {stock.symbol} at ${trade.price:.2f}')
                return redirect('soulstrader:trading')
            else:
                messages.error(request, f'Order failed: {result["error"]}')
                
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


@login_required
def sell_shares_view(request):
    """Handle sell orders from portfolio"""
    if request.method == 'POST':
        try:
            # Get form data
            stock_symbol = request.POST.get('symbol', '').upper()
            quantity = int(request.POST.get('quantity', 0))
            
            # Get stock and portfolio
            stock = get_object_or_404(Stock, symbol=stock_symbol, is_active=True)
            portfolio = get_object_or_404(Portfolio, user=request.user)
            
            # Verify user owns the stock
            try:
                holding = portfolio.holdings.get(stock=stock)
            except Holding.DoesNotExist:
                messages.error(request, f'You do not own any {stock_symbol} shares.')
                return redirect('soulstrader:portfolio')
            
            # Validate quantity
            if quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0.')
                return redirect('soulstrader:portfolio')
                
            if quantity > holding.quantity:
                messages.error(request, f'You only own {holding.quantity} shares of {stock_symbol}.')
                return redirect('soulstrader:portfolio')
            
            # Place the sell order
            result = TradingService.place_order(
                portfolio=portfolio,
                stock=stock,
                trade_type='SELL',
                quantity=quantity,
                order_type='MARKET',
                notes=f'Sell order from portfolio for {quantity} shares'
            )
            
            if result['success']:
                trade = result['trade']
                proceeds = trade.total_amount - trade.commission if trade.total_amount else 0
                messages.success(request, 
                    f'Successfully sold {quantity} shares of {stock_symbol} for ${proceeds:.2f} '
                    f'(after ${trade.commission:.2f} commission)')
            else:
                messages.error(request, f'Sell order failed: {result["error"]}')
                
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid input. Please check your values and try again.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('soulstrader:portfolio')


@login_required
def buy_from_recommendations_view(request):
    """Handle buy orders from recommendations page"""
    if request.method == 'POST':
        try:
            # Get form data
            stock_symbol = request.POST.get('symbol', '').upper()
            quantity = int(request.POST.get('quantity', 0))
            
            # Get stock and portfolio
            stock = get_object_or_404(Stock, symbol=stock_symbol, is_active=True)
            portfolio = get_object_or_404(Portfolio, user=request.user)
            
            # Validate quantity
            if quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0.')
                return redirect('soulstrader:recommendations')
            
            # Place the buy order
            result = TradingService.place_order(
                portfolio=portfolio,
                stock=stock,
                trade_type='BUY',
                quantity=quantity,
                order_type='MARKET',
                notes=f'Buy order from AI recommendation for {quantity} shares'
            )
            
            if result['success']:
                trade = result['trade']
                total_cost = trade.total_amount + trade.commission if trade.total_amount else 0
                messages.success(request, 
                    f'Successfully bought {quantity} shares of {stock_symbol} for ${total_cost:.2f} '
                    f'(including ${trade.commission:.2f} commission)')
            else:
                messages.error(request, f'Buy order failed: {result["error"]}')
                
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid input. Please check your values and try again.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('soulstrader:recommendations')


@login_required
def sell_from_recommendations_view(request):
    """Handle sell orders from recommendations page"""
    if request.method == 'POST':
        try:
            # Get form data
            stock_symbol = request.POST.get('symbol', '').upper()
            quantity = int(request.POST.get('quantity', 0))
            
            # Get stock and portfolio
            stock = get_object_or_404(Stock, symbol=stock_symbol, is_active=True)
            portfolio = get_object_or_404(Portfolio, user=request.user)
            
            # Verify user owns the stock
            try:
                holding = portfolio.holdings.get(stock=stock)
            except Holding.DoesNotExist:
                messages.error(request, f'You do not own any {stock_symbol} shares.')
                return redirect('soulstrader:recommendations')
            
            # Validate quantity
            if quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0.')
                return redirect('soulstrader:recommendations')
                
            if quantity > holding.quantity:
                messages.error(request, f'You only own {holding.quantity} shares of {stock_symbol}.')
                return redirect('soulstrader:recommendations')
            
            # Place the sell order
            result = TradingService.place_order(
                portfolio=portfolio,
                stock=stock,
                trade_type='SELL',
                quantity=quantity,
                order_type='MARKET',
                notes=f'Sell order from AI recommendation for {quantity} shares'
            )
            
            if result['success']:
                trade = result['trade']
                proceeds = trade.total_amount - trade.commission if trade.total_amount else 0
                messages.success(request, 
                    f'Successfully sold {quantity} shares of {stock_symbol} for ${proceeds:.2f} '
                    f'(after ${trade.commission:.2f} commission)')
            else:
                messages.error(request, f'Sell order failed: {result["error"]}')
                
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid input. Please check your values and try again.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('soulstrader:recommendations')
# Smart Analysis Functions for SOULTRADER
# These will be added to views.py

@login_required
def smart_analysis_view(request):
    """Generate portfolio-aware smart analysis"""
    from django.http import JsonResponse
    from datetime import timedelta
    
    if request.method == 'POST':
        try:
            portfolio = get_object_or_404(Portfolio, user=request.user)
            
            # Get all recent AI recommendations
            recent_recommendations = AIAdvisorRecommendation.objects.filter(
                status='ACTIVE',
                created_at__gte=timezone.now() - timedelta(days=7)  # Last 7 days
            ).select_related('stock', 'advisor')
            
            # Get user's current holdings
            user_holdings = {
                holding.stock.symbol: holding 
                for holding in portfolio.holdings.select_related('stock').all()
            }
            
            # Process recommendations with portfolio awareness
            smart_analysis = process_smart_analysis(recent_recommendations, user_holdings, portfolio)
            
            # Generate HTML for the results
            analysis_html = render_smart_analysis_html(smart_analysis, user_holdings)
            
            return JsonResponse({
                'success': True,
                'html': analysis_html
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def process_smart_analysis(recommendations, user_holdings, portfolio):
    """Process AI recommendations with portfolio awareness"""
    stock_analysis = {}
    
    for rec in recommendations:
        symbol = rec.stock.symbol
        
        # Initialize stock analysis if not exists
        if symbol not in stock_analysis:
            stock_analysis[symbol] = {
                'stock': rec.stock,
                'recommendations': [],
                'user_holding': user_holdings.get(symbol),
                'consensus_score': 0,
                'action_priority': 0,
                'reasoning': []
            }
        
        # Apply portfolio-aware filtering
        holding = user_holdings.get(symbol)
        
        # Filter SELL recommendations for stocks not owned
        if rec.recommendation_type in ['SELL', 'STRONG_SELL'] and not holding:
            continue  # Skip SELL recommendations for stocks not owned
        
        # Add recommendation to analysis
        stock_analysis[symbol]['recommendations'].append(rec)
    
    # Calculate consensus and ranking for each stock
    for symbol, analysis in stock_analysis.items():
        if not analysis['recommendations']:
            continue
            
        # Calculate consensus score
        total_score = 0
        total_weight = 0
        buy_votes = 0
        sell_votes = 0
        
        for rec in analysis['recommendations']:
            # Convert recommendation to numeric score
            score_map = {
                'STRONG_SELL': -2, 'SELL': -1, 'HOLD': 0, 'BUY': 1, 'STRONG_BUY': 2
            }
            confidence_weight = {
                'LOW': 0.5, 'MEDIUM': 1.0, 'HIGH': 1.5, 'VERY_HIGH': 2.0
            }
            
            rec_score = score_map.get(rec.recommendation_type, 0)
            weight = confidence_weight.get(rec.confidence_level, 1.0)
            
            total_score += rec_score * weight
            total_weight += weight
            
            if rec_score > 0:
                buy_votes += 1
            elif rec_score < 0:
                sell_votes += 1
        
        # Calculate weighted consensus
        analysis['consensus_score'] = total_score / total_weight if total_weight > 0 else 0
        analysis['buy_votes'] = buy_votes
        analysis['sell_votes'] = sell_votes
        analysis['total_advisors'] = len(analysis['recommendations'])
        
        # Calculate action priority based on consensus strength and portfolio context
        holding = analysis['user_holding']
        consensus = float(analysis['consensus_score'])  # Convert to float for calculations
        
        if holding and consensus < -0.5:  # Strong sell consensus for owned stock
            analysis['action_priority'] = abs(consensus) * 100  # High priority to sell
            analysis['action_type'] = 'SELL'
        elif not holding and consensus > 0.5:  # Strong buy consensus for unowned stock
            analysis['action_priority'] = consensus * 100  # High priority to buy
            analysis['action_type'] = 'BUY'
        elif holding and consensus > 0.5:  # Buy more of owned stock
            # Factor in current performance
            current_price = float(holding.stock.current_price)
            avg_price = float(holding.average_price)
            current_return = ((current_price - avg_price) / avg_price) * 100
            if current_return > 10:  # Already profitable
                analysis['action_priority'] = consensus * 50  # Lower priority
            else:
                analysis['action_priority'] = consensus * 75  # Medium priority
            analysis['action_type'] = 'BUY_MORE'
        else:
            analysis['action_priority'] = 0
            analysis['action_type'] = 'HOLD'
    
    # Sort by action priority (highest first)
    sorted_analysis = sorted(
        [(symbol, data) for symbol, data in stock_analysis.items() if data['recommendations']],
        key=lambda x: x[1]['action_priority'],
        reverse=True
    )
    
    return sorted_analysis


def render_smart_analysis_html(analysis_data, user_holdings):
    """Render smart analysis results as HTML"""
    if not analysis_data:
        return """
        <div style="text-align: center; padding: 3rem; color: #6c757d;">
            <h3>No Actionable Recommendations</h3>
            <p>No portfolio-relevant recommendations found in recent AI analysis.</p>
        </div>
        """
    
    html = f"""
    <div style="margin-bottom: 1rem; padding: 1rem; background-color: #e8f4fd; border-radius: 4px;">
        <h3 style="color: #667eea; margin-bottom: 0.5rem;">📊 Smart Analysis Results</h3>
        <p style="color: #6c757d; margin: 0;">
            Analyzed {len(analysis_data)} stocks with portfolio context. 
            Ranked by action priority and filtered for relevance.
        </p>
    </div>
    
    <div class="table">
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Stock</th>
                    <th>Your Position</th>
                    <th>AI Consensus</th>
                    <th>Priority Score</th>
                    <th>Advisors</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for rank, (symbol, analysis) in enumerate(analysis_data, 1):
        stock = analysis['stock']
        holding = analysis['user_holding']
        consensus = analysis['consensus_score']
        action_type = analysis['action_type']
        priority = analysis['action_priority']
        
        # Position info
        if holding:
            position_info = f"{holding.quantity} shares @ ${holding.average_price:.2f}"
            current_price = float(stock.current_price)
            avg_price = float(holding.average_price)
            current_return = ((current_price - avg_price) / avg_price) * 100
            position_color = "positive" if current_return >= 0 else "negative"
            position_return = f"({current_return:+.1f}%)"
        else:
            position_info = "Not owned"
            position_color = "neutral"
            position_return = ""
        
        # Action styling
        action_colors = {
            'BUY': '#28a745', 'BUY_MORE': '#17a2b8', 'SELL': '#dc3545', 'HOLD': '#6c757d'
        }
        action_color = action_colors.get(action_type, '#6c757d')
        
        # Consensus display
        if consensus > 0.5:
            consensus_text = f"Strong Buy ({consensus:.2f})"
            consensus_color = "#28a745"
        elif consensus > 0:
            consensus_text = f"Buy ({consensus:.2f})"
            consensus_color = "#28a745"
        elif consensus < -0.5:
            consensus_text = f"Strong Sell ({consensus:.2f})"
            consensus_color = "#dc3545"
        elif consensus < 0:
            consensus_text = f"Sell ({consensus:.2f})"
            consensus_color = "#dc3545"
        else:
            consensus_text = f"Hold ({consensus:.2f})"
            consensus_color = "#6c757d"
        
        # Generate action button based on recommendation
        current_price_float = float(stock.current_price)
        target_price_buy = current_price_float * 1.05
        target_price_sell = current_price_float * 0.95
        
        # Create action buttons with Details button
        details_button = f'''
            <button class="btn" 
                    style="padding: 0.5rem 1rem; font-size: 0.9rem; background-color: #667eea; border: none; cursor: pointer; color: white; margin-right: 0.5rem;"
                    onclick="showAdvisorDetails('{symbol}')">
                Details
            </button>
        '''
        
        if action_type == 'BUY':
            action_button = f'''
                {details_button}
                <button class="btn" 
                        style="padding: 0.5rem 1rem; font-size: 0.9rem; background-color: #28a745; border: none; cursor: pointer; color: white;"
                        onclick="openBuyModal('{symbol}', '{stock.name}', {current_price_float}, {target_price_buy})">
                    Buy Now
                </button>
            '''
        elif action_type == 'BUY_MORE':
            action_button = f'''
                {details_button}
                <button class="btn" 
                        style="padding: 0.5rem 1rem; font-size: 0.9rem; background-color: #17a2b8; border: none; cursor: pointer; color: white;"
                        onclick="openBuyModal('{symbol}', '{stock.name}', {current_price_float}, {target_price_buy})">
                    Buy More
                </button>
            '''
        elif action_type == 'SELL':
            action_button = f'''
                {details_button}
                <button class="btn" 
                        style="padding: 0.5rem 1rem; font-size: 0.9rem; background-color: #dc3545; border: none; cursor: pointer; color: white;"
                        onclick="openSellFromRecommendationsModal('{symbol}', '{stock.name}', {current_price_float}, {target_price_sell})">
                    Sell Now
                </button>
            '''
        else:
            action_button = f'''
                {details_button}
                <span style="color: #6c757d; font-style: italic;">Hold</span>
            '''
        
        html += f"""
                <tr>
                    <td><strong>#{rank}</strong></td>
                    <td>
                        <strong>{symbol}</strong><br>
                        <small>{stock.name[:30]}</small><br>
                        <small style="color: #6c757d;">${stock.current_price:.2f}</small>
                    </td>
                    <td>
                        <span class="{position_color}">{position_info}</span><br>
                        <small class="{position_color}">{position_return}</small>
                    </td>
                    <td>
                        <span style="color: {consensus_color}; font-weight: bold;">{consensus_text}</span><br>
                        <small>{analysis['buy_votes']} buy, {analysis['sell_votes']} sell</small>
                    </td>
                    <td>
                        <span style="color: #667eea; font-weight: bold;">{priority:.0f}</span>
                    </td>
                    <td>{analysis['total_advisors']} advisors</td>
                    <td>{action_button}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    </div>
    
    <div style="margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-radius: 4px;">
        <h4 style="color: #333; margin-bottom: 1rem;">💡 How to Read This Analysis:</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; font-size: 0.9rem; color: #555;">
            <div><strong>Rank:</strong> Priority order for action</div>
            <div><strong>Your Position:</strong> Current holdings and performance</div>
            <div><strong>AI Consensus:</strong> Weighted advisor agreement</div>
            <div><strong>Action:</strong> Recommended next step</div>
            <div><strong>Priority Score:</strong> Urgency/importance rating</div>
        </div>
    </div>
    """
    
    return html


@login_required
def advisor_details_view(request, symbol):
    """Get detailed advisor breakdown for a specific stock"""
    from django.http import JsonResponse
    from datetime import timedelta
    import traceback
    
    try:
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        portfolio = get_object_or_404(Portfolio, user=request.user)
        
        # Get recent recommendations for this stock
        recommendations = AIAdvisorRecommendation.objects.filter(
            stock=stock,
            status='ACTIVE',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('advisor').order_by('-confidence_score')
        
        # Get user's holding if any
        user_holding = None
        try:
            user_holding = portfolio.holdings.get(stock=stock)
        except Holding.DoesNotExist:
            pass
        
        # Generate detailed HTML
        try:
            details_html = render_advisor_details_html(stock, recommendations, user_holding)
        except Exception as html_error:
            return JsonResponse({
                'success': False,
                'error': f'HTML generation error: {str(html_error)}'
            })
        
        return JsonResponse({
            'success': True,
            'html': details_html
        })
        
    except Exception as e:
        # Get full traceback for debugging
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error loading advisor details: {str(e)}',
            'traceback': error_details
        })


def render_advisor_details_html(stock, recommendations, user_holding):
    """Render detailed advisor analysis as HTML"""
    
    # Stock and position info
    position_info = ""
    if user_holding:
        current_price = float(stock.current_price)
        avg_price = float(user_holding.average_price)
        current_return = ((current_price - avg_price) / avg_price) * 100
        position_color = "positive" if current_return >= 0 else "negative"
        position_info = f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 4px; margin-bottom: 1.5rem;">
            <h4 style="color: #333; margin-bottom: 0.5rem;">💼 Your Position</h4>
            <p style="margin: 0;">
                <strong>{user_holding.quantity} shares</strong> @ ${avg_price:.2f} average
                <span class="{position_color}" style="margin-left: 1rem;">({current_return:+.1f}%)</span>
            </p>
            <p style="margin: 0.5rem 0 0 0; color: #6c757d;">
                Current value: ${user_holding.current_value:.2f}
            </p>
        </div>
        """
    else:
        position_info = f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 4px; margin-bottom: 1.5rem;">
            <h4 style="color: #333; margin-bottom: 0.5rem;">💼 Your Position</h4>
            <p style="margin: 0; color: #6c757d;">
                You do not currently own {stock.symbol} shares
            </p>
        </div>
        """
    
    html = f"""
    <div style="margin-bottom: 1.5rem;">
        <h3 style="color: #667eea; margin-bottom: 0.5rem;">{stock.symbol} - {stock.name}</h3>
        <p style="color: #6c757d; margin: 0;">
            Current Price: <strong>${stock.current_price:.2f}</strong> | 
            Sector: {stock.sector} | 
            {recommendations.count()} advisor recommendations
        </p>
    </div>
    
    {position_info}
    
    <h4 style="color: #333; margin-bottom: 1rem;">🤖 Individual Advisor Recommendations</h4>
    """
    
    if recommendations:
        for rec in recommendations:
            # Recommendation styling
            rec_colors = {
                'STRONG_BUY': '#28a745', 'BUY': '#28a745', 'HOLD': '#6c757d', 
                'SELL': '#dc3545', 'STRONG_SELL': '#dc3545'
            }
            rec_color = rec_colors.get(rec.recommendation_type, '#6c757d')
            
            confidence_colors = {
                'VERY_HIGH': '#28a745', 'HIGH': '#28a745', 'MEDIUM': '#ffc107', 'LOW': '#dc3545'
            }
            conf_color = confidence_colors.get(rec.confidence_level, '#6c757d')
            
            html += f"""
            <div style="border: 1px solid #e9ecef; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; background-color: #fafafa;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h5 style="margin: 0; color: #333;">{rec.advisor.name}</h5>
                        <small style="color: #6c757d;">{rec.advisor.get_advisor_type_display()}</small>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.1rem; font-weight: bold; color: {rec_color};">
                            {rec.get_recommendation_type_display()}
                        </div>
                        <div style="font-size: 0.9rem; color: {conf_color};">
                            {rec.get_confidence_level_display()} ({rec.confidence_score:.2f})
                        </div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                    <div>
                        <strong>Target Price:</strong><br>
                        <span style="color: #28a745;">{'$' + str(rec.target_price) if rec.target_price else 'N/A'}</span>
                    </div>
                    <div>
                        <strong>Stop Loss:</strong><br>
                        <span style="color: #dc3545;">{'$' + str(rec.stop_loss) if rec.stop_loss else 'N/A'}</span>
                    </div>
                    <div>
                        <strong>Processing Time:</strong><br>
                        <span style="color: #6c757d;">{float(rec.processing_time or 0):.2f}s</span>
                    </div>
                    <div>
                        <strong>Created:</strong><br>
                        <span style="color: #6c757d;">{rec.created_at.strftime('%m/%d %H:%M')}</span>
                    </div>
                </div>
                
                <div>
                    <strong>AI Reasoning:</strong>
                    <div style="margin-top: 0.5rem; padding: 1rem; background-color: white; border-radius: 4px; border-left: 4px solid {rec_color};">
                        <p style="margin: 0; color: #555; line-height: 1.5; font-size: 0.95rem;">
                            {rec.reasoning[:500]}{'...' if len(rec.reasoning) > 500 else ''}
                        </p>
                    </div>
                </div>
            </div>
            """
        
        # Add consensus summary
        total_recs = recommendations.count()
        buy_count = recommendations.filter(recommendation_type__in=['BUY', 'STRONG_BUY']).count()
        sell_count = recommendations.filter(recommendation_type__in=['SELL', 'STRONG_SELL']).count()
        hold_count = recommendations.filter(recommendation_type='HOLD').count()
        
        html += f"""
        <div style="margin-top: 2rem; padding: 1.5rem; background-color: #e8f4fd; border-radius: 8px;">
            <h4 style="color: #667eea; margin-bottom: 1rem;">📊 Consensus Summary</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 1rem; text-align: center;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #28a745;">{buy_count}</div>
                    <div style="font-size: 0.9rem; color: #6c757d;">Buy Votes</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #6c757d;">{hold_count}</div>
                    <div style="font-size: 0.9rem; color: #6c757d;">Hold Votes</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #dc3545;">{sell_count}</div>
                    <div style="font-size: 0.9rem; color: #6c757d;">Sell Votes</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;">{total_recs}</div>
                    <div style="font-size: 0.9rem; color: #6c757d;">Total Advisors</div>
                </div>
            </div>
        </div>
        """
    else:
        html += """
        <div style="text-align: center; padding: 3rem; color: #6c757d;">
            <h4>No Recent Recommendations</h4>
            <p>No advisor recommendations found for this stock in the last 7 days.</p>
        </div>
        """
    
    return html
