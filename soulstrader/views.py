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
    AIAdvisor, AIAdvisorRecommendation, ConsensusRecommendation,
    SmartRecommendation, SmartAnalysisSession, RiskProfile
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
    
    # Get URL parameters for pre-filling forms
    prefill_symbol = request.GET.get('symbol', '').upper()
    prefill_action = request.GET.get('action', '').upper()
    prefill_quantity = request.GET.get('quantity', '')
    
    # Validate prefill data
    if prefill_action and prefill_action not in ['BUY', 'SELL']:
        prefill_action = ''
    
    context = {
        'portfolio': portfolio,
        'recent_trades': recent_trades,
        'pending_orders': pending_orders,
        'trading_summary': trading_summary,
        'order_types': Trade.ORDER_TYPES,
        'trade_types': Trade.TRADE_TYPES,
        'current_page': 'trading',
        'prefill_symbol': prefill_symbol,
        'prefill_action': prefill_action,
        'prefill_quantity': prefill_quantity,
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
                notes=notes,
                trade_source='MANUAL',
                source_reference='Trading Form'
            )
            
            if result['success']:
                trade = result['trade']
                
                # Check if this trade matches any pending Smart Recommendations
                from .models import SmartRecommendation
                from django.utils import timezone
                
                matching_recommendations = SmartRecommendation.objects.filter(
                    user=request.user,
                    stock=stock,
                    recommendation_type=trade_type,
                    status='PENDING'
                ).order_by('-priority_score', '-created_at')
                
                # Mark the highest priority matching recommendation as executed
                if matching_recommendations.exists():
                    recommendation = matching_recommendations.first()
                    recommendation.status = 'EXECUTED'
                    recommendation.executed_trade = trade
                    recommendation.executed_at = timezone.now()
                    recommendation.save()
                
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
    
    # Get URL parameters for pre-filling forms
    prefill_symbol = request.GET.get('symbol', '').upper()
    prefill_action = request.GET.get('action', '').upper()
    prefill_quantity = request.GET.get('quantity', '')
    
    # Validate prefill data
    if prefill_action and prefill_action not in ['BUY', 'SELL']:
        prefill_action = ''
    
    context = {
        'stocks': stocks,
        'order_types': Trade.ORDER_TYPES,
        'trade_types': Trade.TRADE_TYPES,
        'current_page': 'trading',
        'prefill_symbol': prefill_symbol,
        'prefill_action': prefill_action,
        'prefill_quantity': prefill_quantity,
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
                notes=f'Manual sell order from portfolio for {quantity} shares',
                trade_source='MANUAL',
                source_reference='Portfolio Holdings'
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
                notes=f'Trade based on AI recommendation for {quantity} shares',
                trade_source='AI_RECOMMENDATION',
                source_reference='Recommendations Page'
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
                notes=f'Trade based on AI recommendation for {quantity} shares',
                trade_source='AI_RECOMMENDATION',
                source_reference='Recommendations Page'
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
    """Display stored Smart Analysis recommendations"""
    from django.http import JsonResponse
    from datetime import timedelta
    
    if request.method == 'POST':
        try:
            # Get user's Smart Analysis sessions
            sessions = SmartAnalysisSession.objects.filter(
                user=request.user
            ).order_by('-started_at')[:5]  # Last 5 sessions
            
            # Get user's Smart Recommendations - PENDING first, then by priority and date
            from django.db.models import Case, When, IntegerField
            recommendations = SmartRecommendation.objects.filter(
                user=request.user
            ).select_related('stock').annotate(
                status_order=Case(
                    When(status='PENDING', then=0),
                    When(status='EXECUTED', then=1),
                    default=2,
                    output_field=IntegerField(),
                )
            ).order_by('status_order', '-priority_score', '-created_at')[:20]  # Last 20 recommendations
            
            # Get user's risk profile
            risk_profile, created = RiskProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'max_purchase_percentage': Decimal('5.00'),
                    'min_confidence_score': Decimal('0.70'),
                    'cash_spend_percentage': Decimal('20.00'),
                }
            )
            
            # Generate HTML for the results
            analysis_html = render_smart_analysis_stored_html(sessions, recommendations, risk_profile)
            
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


@login_required
@require_http_methods(["POST"])
def execute_smart_recommendation(request):
    """Execute a Smart Recommendation (place actual trades)"""
    try:
        import json
        data = json.loads(request.body)
        recommendation_id = data.get('recommendation_id')
        
        if not recommendation_id:
            return JsonResponse({'success': False, 'error': 'Recommendation ID required'})
        
        # Get the recommendation
        recommendation = get_object_or_404(
            SmartRecommendation, 
            id=recommendation_id, 
            user=request.user,
            status='PENDING'
        )
        
        # Get portfolio
        portfolio = get_object_or_404(Portfolio, user=request.user)
        
        # Execute the recommendation using the Smart Analysis Service
        from .smart_analysis_service import SmartAnalysisService
        service = SmartAnalysisService()
        
        # Execute the specific recommendation
        result = service._execute_single_recommendation(recommendation, portfolio)
        
        if result['success']:
            return JsonResponse({
                'success': True, 
                'message': f'Successfully executed {recommendation.recommendation_type} for {recommendation.stock.symbol}'
            })
        else:
            return JsonResponse({'success': False, 'error': result['error']})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Execution failed: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def mark_smart_recommendation_executed(request):
    """Mark a Smart Recommendation as executed without placing trades"""
    try:
        import json
        data = json.loads(request.body)
        recommendation_id = data.get('recommendation_id')
        
        if not recommendation_id:
            return JsonResponse({'success': False, 'error': 'Recommendation ID required'})
        
        # Get the recommendation
        recommendation = get_object_or_404(
            SmartRecommendation, 
            id=recommendation_id, 
            user=request.user,
            status='PENDING'
        )
        
        # Mark as executed
        recommendation.status = 'EXECUTED'
        recommendation.executed_at = timezone.now()
        recommendation.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Marked {recommendation.recommendation_type} for {recommendation.stock.symbol} as executed'
        })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to mark as executed: {str(e)}'})


def render_smart_analysis_stored_html(sessions, recommendations, risk_profile):
    """Render stored Smart Analysis results as HTML"""
    if not recommendations:
        return """
        <div style="text-align: center; padding: 3rem; color: #6c757d;">
            <h3>No Smart Analysis Results</h3>
            <p>No Smart Analysis recommendations found. Run Smart Analysis to generate recommendations.</p>
        </div>
        """
    
    html = f"""
        <h3 style="color: #667eea; margin-bottom: 0.5rem;">🧠 Smart Analysis Results</h3>
        <p style="color: #6c757d; margin-bottom: 1.5rem; font-size: 0.9rem;">
            Automated portfolio optimization recommendations
        </p>
    """
    
    # Show risk profile settings
    html += f"""
        <div style="
            background: #f8f9fa; 
            border: 1px solid #e9ecef; 
            border-radius: 8px; 
            padding: 1rem; 
            margin-bottom: 1.5rem;
        ">
            <h4 style="color: #495057; margin-bottom: 0.5rem;">⚙️ Risk Profile Settings</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; font-size: 0.9rem;">
                <div>
                    <div style="color: #6c757d;">Max Purchase %</div>
                    <div style="font-weight: bold;">{risk_profile.max_purchase_percentage}%</div>
                </div>
                <div>
                    <div style="color: #6c757d;">Min Confidence</div>
                    <div style="font-weight: bold;">{risk_profile.min_confidence_score}</div>
                </div>
                <div>
                    <div style="color: #6c757d;">Cash Spend %</div>
                    <div style="font-weight: bold;">{risk_profile.cash_spend_percentage}%</div>
                </div>
            </div>
        </div>
    """
    
    # Show recent sessions
    if sessions:
        html += """
        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #495057; margin-bottom: 0.5rem;">📊 Recent Analysis Sessions</h4>
        """
        for session in sessions:
            status_color = '#28a745' if session.status == 'COMPLETED' else '#dc3545' if session.status == 'FAILED' else '#ffc107'
            html += f"""
            <div style="
                background: white; 
                border: 1px solid #e9ecef; 
                border-radius: 6px; 
                padding: 0.75rem; 
                margin-bottom: 0.5rem;
                display: flex; 
                justify-content: space-between; 
                align-items: center;
            ">
                <div>
                    <div style="font-weight: bold;">{session.started_at.strftime('%Y-%m-%d %H:%M')}</div>
                    <div style="font-size: 0.9rem; color: #6c757d;">
                        {session.total_recommendations} recommendations • {session.processing_time_seconds:.1f}s
                    </div>
                </div>
                <div style="color: {status_color}; font-weight: bold;">{session.status}</div>
            </div>
            """
        html += "</div>"
    
    # Show recommendations
    html += """
    <div>
        <h4 style="color: #495057; margin-bottom: 0.5rem;">🎯 Smart Recommendations</h4>
    """
    
    for rec in recommendations:
        # Status styling and icons
        if rec.status == 'EXECUTED':
            status_color = '#28a745'
            status_icon = '✅'
            status_text = 'EXECUTED'
        elif rec.status == 'PENDING':
            status_color = '#ffc107'
            status_icon = '⏳'
            status_text = 'PENDING'
        else:
            status_color = '#6c757d'
            status_icon = '❌'
            status_text = rec.status
        
        # Action icon based on recommendation type
        action_icon = '🛒' if rec.recommendation_type == 'BUY' else '📉' if rec.recommendation_type == 'SELL' else '⏸️'
        
        # Determine if this is an executed recommendation
        is_executed = rec.status == 'EXECUTED'
        
        # Background color for executed recommendations
        bg_color = '#f8fff8' if is_executed else 'white'
        border_color = '#28a745' if is_executed else '#e9ecef'
        
        html += f"""
        <div style="
            background: {bg_color}; 
            border: 2px solid {border_color}; 
            border-radius: 8px; 
            padding: 1rem; 
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            {'opacity: 0.8;' if is_executed else ''}
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.2rem;">{action_icon}</span>
                    <h4 style="margin: 0; color: #2c3e50;">{rec.stock.symbol}</h4>
                    <span style="font-size: 0.9rem; color: #6c757d;">{rec.stock.name}</span>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.1rem; font-weight: bold; color: {status_color}; display: flex; align-items: center; justify-content: flex-end; gap: 0.3rem;">
                        <span>{status_icon}</span>
                        <span>{status_text}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #6c757d;">
                        {rec.created_at.strftime('%m/%d %H:%M')}
                        {f' • Executed: {rec.executed_at.strftime("%m/%d %H:%M")}' if rec.executed_at else ''}
                    </div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                <div>
                    <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.2rem;">Current Price</div>
                    <div style="font-size: 1.1rem; font-weight: bold;">${rec.current_price:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.2rem;">Priority Score</div>
                    <div style="font-size: 1.1rem; font-weight: bold; color: #667eea;">{rec.priority_score:.1f}</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.2rem;">Confidence</div>
                    <div style="font-size: 1.1rem; font-weight: bold; color: #28a745;">{rec.confidence_score:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.2rem;">Shares to Buy</div>
                    <div style="font-size: 1.1rem; font-weight: bold;">
                        {rec.shares_to_buy if rec.shares_to_buy else 'N/A'}
                    </div>
                </div>
            </div>
            
            {f'''
            <div style="margin-bottom: 1rem;">
                <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.2rem;">Cash Allocation</div>
                <div style="font-size: 1.1rem; font-weight: bold; color: #28a745;">${rec.cash_allocated:,.2f}</div>
            </div>
            ''' if rec.cash_allocated else ''}
            
            <div style="margin-bottom: 1rem;">
                <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.5rem;">Reasoning:</div>
                <div style="font-size: 0.9rem; line-height: 1.4; color: #495057;">
                    {rec.reasoning[:200]}{'...' if len(rec.reasoning) > 200 else ''}
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                <div style="display: flex; gap: 0.5rem; font-size: 0.8rem; color: #6c757d;">
                    <span>📊 {rec.existing_shares} existing</span>
                    <span>•</span>
                    <span>🎯 {rec.recommendation_type}</span>
                    {f'<span>•</span><span>💰 ${rec.cash_allocated:,.0f}' if rec.cash_allocated else ''}
                </div>
                
               <div style="display: flex; gap: 0.5rem;">
                   <button style="
                       padding: 0.5rem 1rem; 
                       font-size: 0.9rem; 
                       background-color: #17a2b8; 
                       border: none; 
                       cursor: pointer; 
                       color: white; 
                       border-radius: 4px;
                   " onclick="showSmartRecommendationDetails('{rec.id}')">
                       📋 Details
                   </button>
                   
                   {f'''
                   <button style="
                       padding: 0.5rem 1rem; 
                       font-size: 0.9rem; 
                       background-color: #6c757d; 
                       border: none; 
                       cursor: not-allowed; 
                       color: white; 
                       border-radius: 4px;
                       opacity: 0.6;
                   " disabled>
                       ✅ Already Executed
                   </button>
                   ''' if is_executed else f'''
                   <a href="/trading/place-order/?symbol={rec.stock.symbol}&action={rec.recommendation_type.lower()}&quantity={rec.shares_to_buy or (10 if rec.recommendation_type == 'BUY' else 1)}" style="
                       padding: 0.5rem 1rem; 
                       font-size: 0.9rem; 
                       background-color: {'#28a745' if rec.recommendation_type == 'BUY' else '#dc3545'}; 
                       border: none; 
                       cursor: pointer; 
                       color: white; 
                       border-radius: 4px;
                       text-decoration: none;
                       display: inline-block;
                   ">
                       {'Buy Now' if rec.recommendation_type == 'BUY' else 'Sell Now'}
                   </a>
                   '''}
               </div>
            </div>
        </div>
        """
    
    html += """
    </div>
    
    """
    
    return html


@login_required
@require_http_methods(["GET"])
def smart_recommendation_details(request, recommendation_id):
    """Get detailed information about a smart recommendation"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        recommendation = SmartRecommendation.objects.select_related('stock', 'executed_trade').get(
            id=recommendation_id,
            user=request.user
        )
        
        # Get related advisor recommendations for context
        related_recommendations = AIAdvisorRecommendation.objects.filter(
            stock=recommendation.stock,
            created_at__date=recommendation.created_at.date()
        ).select_related('advisor').order_by('-confidence_score')
        
        context = {
            'recommendation': recommendation,
            'related_recommendations': related_recommendations,
        }
        
        return render(request, 'soulstrader/smart_recommendation_details.html', context)
        
    except SmartRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting recommendation details: {e}")
        return JsonResponse({'error': str(e)}, status=500)

