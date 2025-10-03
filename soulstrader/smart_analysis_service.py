"""
Smart Analysis Service - Automated Portfolio Optimization Engine

This service implements the automated portfolio optimization system that:
1. Consolidates recommendations from all active AI advisors
2. Applies portfolio-aware filtering and ranking
3. Implements the revised buy algorithm with anti-repetition logic
4. Stores recommendations in the database for automated execution
"""

import logging
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Tuple, Optional
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

from .models import (
    Stock, Portfolio, Holding, AIAdvisor, AIAdvisorRecommendation,
    SmartRecommendation, SmartAnalysisSession, RiskProfile, Trade
)
from .ai_advisor_service import AIAdvisorManager

logger = logging.getLogger(__name__)


class SmartAnalysisService:
    """Service for automated portfolio optimization and smart recommendations"""
    
    def __init__(self):
        pass  # AIAdvisorManager uses class methods
    
    def batch_analyze_users(self, users: List[User], auto_execute: bool = False, bestbuyonly: bool = False) -> List[SmartAnalysisSession]:
        """
        Optimized batch analysis for multiple users that minimizes API calls
        by analyzing each unique stock only once and reusing recommendations.
        
        Args:
            users: List of users to analyze
            auto_execute: Whether to automatically execute recommended trades
            bestbuyonly: If True, only analyze best buy opportunities, skip existing holdings
            
        Returns:
            List of SmartAnalysisSession objects for each user
        """
        logger.info(f"Starting batch Smart Analysis for {len(users)} users")
        
        # Step 1: Collect all unique stocks from all users
        all_unique_stocks = self._collect_all_unique_stocks(users, bestbuyonly)
        logger.info(f"Found {len(all_unique_stocks)} unique stocks to analyze across all users")
        
        # Step 2: Analyze all unique stocks once and store recommendations
        self._batch_analyze_stocks(all_unique_stocks)
        
        # Step 3: Process each user using the pre-analyzed recommendations
        sessions = []
        for user in users:
            try:
                session = self._analyze_user_with_existing_recommendations(
                    user, auto_execute, bestbuyonly
                )
                sessions.append(session)
            except Exception as e:
                logger.error(f"Failed to analyze user {user.username}: {str(e)}")
                continue
        
        logger.info(f"Batch analysis completed for {len(sessions)} users")
        return sessions
    
    def _collect_all_unique_stocks(self, users: List[User], bestbuyonly: bool = False) -> List[str]:
        """
        Collect all unique stock symbols needed across all users
        """
        all_stocks = set()
        
        for user in users:
            # Get user's portfolio and holdings
            try:
                portfolio = self._get_or_create_portfolio(user)
                holdings = self._get_current_holdings(portfolio)
                
                # Build ticker list for this user (same logic as individual analysis)
                ticker_list, _ = self._build_ticker_list(user, holdings, bestbuyonly)
                all_stocks.update(ticker_list)
                
            except Exception as e:
                logger.warning(f"Failed to collect stocks for user {user.username}: {e}")
                continue
        
        return list(all_stocks)
    
    def _batch_analyze_stocks(self, stock_symbols: List[str]) -> None:
        """
        Analyze all stocks once and store recommendations in database
        """
        logger.info(f"Batch analyzing {len(stock_symbols)} unique stocks")
        
        for symbol in stock_symbols:
            try:
                # Check if we already have recent recommendations for this stock
                if self._has_recent_recommendations(symbol):
                    logger.info(f"Skipping {symbol} - recent recommendations exist")
                    continue
                
                # Validate symbol with Yahoo Finance
                if not self._validate_yahoo_symbol(symbol):
                    logger.warning(f"Skipping {symbol} - not recognized by Yahoo Finance")
                    continue
                
                # Get or create stock
                try:
                    stock = Stock.objects.get(symbol=symbol)
                except Stock.DoesNotExist:
                    stock = self._create_stock_from_market_screening(symbol)
                    if not stock:
                        logger.warning(f"Failed to create stock {symbol}, skipping")
                        continue
                
                # Get recommendations from all advisors for this stock
                logger.info(f"Getting recommendations for {symbol}")
                advisor_recommendations = AIAdvisorManager.get_recommendations_for_stock(
                    stock, check_existing=False  # Force new analysis in batch mode
                )
                
                if advisor_recommendations:
                    logger.info(f"Generated {len(advisor_recommendations)} recommendations for {symbol}")
                else:
                    logger.warning(f"No recommendations generated for {symbol}")
                
            except Exception as e:
                logger.error(f"Error analyzing stock {symbol}: {str(e)}")
                continue
    
    def _has_recent_recommendations(self, symbol: str) -> bool:
        """
        Check if we have recent recommendations for a stock (within last 6 hours)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now() - timedelta(hours=6)
        
        return AIAdvisorRecommendation.objects.filter(
            stock__symbol=symbol,
            created_at__gte=recent_date,
            status='ACTIVE'
        ).exists()
    
    def _analyze_user_with_existing_recommendations(
        self, 
        user: User, 
        auto_execute: bool = False, 
        bestbuyonly: bool = False
    ) -> SmartAnalysisSession:
        """
        Analyze a single user using existing recommendations from the batch analysis
        """
        logger.info(f"Analyzing user {user.username} with existing recommendations")
        
        # Create analysis session
        session = self._create_analysis_session(user)
        
        try:
            # Get or create risk profile
            risk_profile = self._get_or_create_risk_profile(user)
            
            # Get portfolio and current holdings
            portfolio = self._get_or_create_portfolio(user)
            holdings = self._get_current_holdings(portfolio)
            
            # Build ticker list for this user
            ticker_list, candidate_info = self._build_ticker_list(user, holdings, bestbuyonly)
            
            if not ticker_list:
                logger.warning(f"No tickers to analyze for user: {user.username}")
                session.status = 'COMPLETED'
                session.completed_at = timezone.now()
                session.save()
                return session
            
            # Get existing recommendations for this user's stocks
            advisor_recommendations = self._get_existing_recommendations(ticker_list)
            
            # Consolidate and rank recommendations
            smart_recommendations = self._consolidate_recommendations(
                user, advisor_recommendations, holdings, risk_profile
            )
            
            # Apply buy algorithm
            buy_recommendations = self._apply_buy_algorithm(
                smart_recommendations, portfolio, holdings, risk_profile
            )
            
            # Apply sell algorithm (NEW!)
            sell_recommendations = self._apply_sell_algorithm(
                smart_recommendations, portfolio, holdings, risk_profile
            )
            
            # Check for profit-taking opportunities (NEW!)
            profit_taking_recommendations = self._check_profit_taking_opportunities(
                holdings, risk_profile, portfolio
            )
            
            # Combine buy, sell, and profit-taking recommendations
            all_recommendations = buy_recommendations + sell_recommendations + profit_taking_recommendations
            
            # Store recommendations in database
            stored_recommendations = self._store_recommendations(
                user, all_recommendations, session
            )
            
            # Execute trades if auto_execute is enabled
            if auto_execute and risk_profile.auto_execute_trades:
                executed_trades = self._execute_recommendations(
                    stored_recommendations, portfolio
                )
                session.executed_recommendations = len(executed_trades)
            
            # Update session with results
            session.total_recommendations = len(stored_recommendations)
            session.status = 'COMPLETED'
            session.completed_at = timezone.now()
            session.processing_time_seconds = (timezone.now() - session.started_at).total_seconds()
            
            # Create summary
            session.recommendations_summary = self._create_recommendations_summary(stored_recommendations)
            session.save()
            
            # Store candidate info for display
            session.candidate_info = candidate_info
            
            logger.info(f"Smart Analysis completed for user: {user.username}. "
                       f"Generated {len(stored_recommendations)} recommendations")
            
            return session
            
        except Exception as e:
            import traceback
            logger.error(f"Smart Analysis failed for user: {user.username}. Error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            session.status = 'FAILED'
            session.error_message = str(e)
            session.completed_at = timezone.now()
            session.save()
            raise
    
    def _get_existing_recommendations(self, ticker_list: List[str]) -> List[AIAdvisorRecommendation]:
        """
        Get existing recommendations from the database for the given tickers
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Get recommendations from the last 6 hours
        recent_date = timezone.now() - timedelta(hours=6)
        
        recommendations = AIAdvisorRecommendation.objects.filter(
            stock__symbol__in=ticker_list,
            created_at__gte=recent_date,
            status='ACTIVE'
        ).select_related('stock', 'advisor')
        
        return list(recommendations)
    
    def smart_analyse(self, user: User, auto_execute: bool = False, bestbuyonly: bool = False) -> SmartAnalysisSession:
        """
        Main Smart Analysis function that performs automated portfolio optimization
        
        Args:
            user: User to analyze portfolio for
            auto_execute: Whether to automatically execute recommended trades
            bestbuyonly: If True, only analyze best buy opportunities, skip existing holdings
            
        Returns:
            SmartAnalysisSession: Session tracking the analysis results
        """
        logger.info(f"Starting Smart Analysis for user: {user.username}")
        
        # Create analysis session
        session = self._create_analysis_session(user)
        
        try:
            # Get or create risk profile
            risk_profile = self._get_or_create_risk_profile(user)
            
            # Get portfolio and current holdings
            portfolio = self._get_or_create_portfolio(user)
            holdings = self._get_current_holdings(portfolio)
            
            # Build ticker list for analysis
            ticker_list, candidate_info = self._build_ticker_list(user, holdings, bestbuyonly)
            
            if not ticker_list:
                logger.warning(f"No tickers to analyze for user: {user.username}")
                session.status = 'COMPLETED'
                session.completed_at = timezone.now()
                session.save()
                return session
            
            # Get recommendations from all active advisors
            advisor_recommendations = self._get_advisor_recommendations(ticker_list)
            
            # Consolidate and rank recommendations
            smart_recommendations = self._consolidate_recommendations(
                user, advisor_recommendations, holdings, risk_profile
            )
            
            # Apply buy algorithm
            buy_recommendations = self._apply_buy_algorithm(
                smart_recommendations, portfolio, holdings, risk_profile
            )
            
            # Apply sell algorithm (NEW!)
            sell_recommendations = self._apply_sell_algorithm(
                smart_recommendations, portfolio, holdings, risk_profile
            )
            
            # Check for profit-taking opportunities (NEW!)
            profit_taking_recommendations = self._check_profit_taking_opportunities(
                holdings, risk_profile, portfolio
            )
            
            # Combine buy, sell, and profit-taking recommendations
            all_recommendations = buy_recommendations + sell_recommendations + profit_taking_recommendations
            
            # Store recommendations in database
            stored_recommendations = self._store_recommendations(
                user, all_recommendations, session
            )
            
            # Execute trades if auto_execute is enabled
            if auto_execute and risk_profile.auto_execute_trades:
                executed_trades = self._execute_recommendations(
                    stored_recommendations, portfolio
                )
                session.executed_recommendations = len(executed_trades)
            
            # Update session with results
            session.total_recommendations = len(stored_recommendations)
            session.status = 'COMPLETED'
            session.completed_at = timezone.now()
            session.processing_time_seconds = (timezone.now() - session.started_at).total_seconds()
            
            # Create summary
            session.recommendations_summary = self._create_recommendations_summary(stored_recommendations)
            session.save()
            
            # Store candidate info for display
            session.candidate_info = candidate_info
            
            logger.info(f"Smart Analysis completed for user: {user.username}. "
                       f"Generated {len(stored_recommendations)} recommendations")
            
            return session
            
        except Exception as e:
            import traceback
            logger.error(f"Smart Analysis failed for user: {user.username}. Error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            session.status = 'FAILED'
            session.error_message = str(e)
            session.completed_at = timezone.now()
            session.save()
            raise
    
    def _create_analysis_session(self, user: User) -> SmartAnalysisSession:
        """Create a new analysis session"""
        portfolio = self._get_or_create_portfolio(user)
        
        session = SmartAnalysisSession.objects.create(
            user=user,
            portfolio_value=portfolio.total_value,
            available_cash=portfolio.current_capital,
            total_cash_spend=Decimal('0.00')  # Will be calculated later
        )
        return session
    
    def _get_or_create_risk_profile(self, user: User) -> RiskProfile:
        """Get or create risk profile for user"""
        # Determine risk-based defaults for SellWeight
        # For now, use moderate defaults - can be enhanced later with user risk tolerance
        sell_weight_default = 5  # Moderate selling
        sell_hold_threshold_default = Decimal('0.30')  # 30% threshold
        
        risk_profile, created = RiskProfile.objects.get_or_create(
            user=user,
            defaults={
                'max_purchase_percentage': Decimal('5.00'),
                'min_confidence_score': Decimal('0.70'),
                'cash_spend_percentage': Decimal('20.00'),
                'cooldown_period_days': 7,
                'max_rebuy_percentage': Decimal('50.00'),
                'max_sector_allocation': Decimal('30.00'),
                'min_diversification_stocks': 5,
                'allow_penny_stocks': False,  # Default: conservative (no penny stocks)
                'min_stock_price': Decimal('5.00'),  # Default: $5 minimum
                'min_market_cap': 100_000_000,  # Default: $100M minimum
                'sell_weight': sell_weight_default,
                'sell_hold_threshold': sell_hold_threshold_default,
                'profit_taking_enabled': True,
                'profit_taking_threshold': Decimal('10.00'),
                'volatility_threshold': Decimal('20.00'),
                'auto_execute_trades': False,
                'auto_rebalance_enabled': True,
            }
        )
        return risk_profile
    
    def _get_or_create_portfolio(self, user: User) -> Portfolio:
        """Get or create portfolio for user"""
        portfolio, created = Portfolio.objects.get_or_create(
            user=user,
            defaults={
                'initial_capital': Decimal('100000.00'),
                'current_capital': Decimal('100000.00'),
            }
        )
        return portfolio
    
    def _get_current_holdings(self, portfolio: Portfolio) -> Dict[str, Holding]:
        """Get current holdings as a dictionary keyed by stock symbol"""
        holdings = {}
        for holding in portfolio.holdings.all():
            holdings[holding.stock.symbol] = holding
        return holdings
    
    def _build_ticker_list(self, user: User, holdings: Dict[str, Holding], bestbuyonly: bool = False) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Build ticker list for analysis:
        - Best buys from market screening
        - Best sells for owned stocks (unless bestbuyonly=True)
        - Current holdings for rebalancing (unless bestbuyonly=True)
        - High-confidence BUY recommendations (alternative stock discovery)
        
        Returns:
            Tuple of (ticker_list, candidate_info) where candidate_info contains
            the different types of candidates for display purposes
        """
        ticker_list = set()
        candidate_info = {
            'current_holdings': [],
            'best_buy_candidates': [],
            'sell_candidates': [],
            'high_confidence_buys': []
        }
        
        # Add current holdings (skip if bestbuyonly=True)
        if not bestbuyonly:
            current_holdings = list(holdings.keys())
            ticker_list.update(current_holdings)
            candidate_info['current_holdings'] = current_holdings
        else:
            logger.info("Best-buy-only mode: Skipping existing holdings analysis")
        
        # Add best buys from market screening (top 20 stocks)
        best_buys = self._get_best_buy_candidates()
        ticker_list.update(best_buys[:20])
        candidate_info['best_buy_candidates'] = best_buys[:20]
        
        # Add stocks for potential selling (owned stocks with sell signals)
        # Skip sell candidates if in bestbuyonly mode
        if not bestbuyonly:
            sell_candidates = self._get_sell_candidates(holdings)
            ticker_list.update(sell_candidates)
            candidate_info['sell_candidates'] = sell_candidates
        else:
            logger.info("Best-buy-only mode: Skipping sell candidates analysis")
        
        # Add high-confidence BUY recommendations for alternative stock discovery
        high_confidence_buys = self._get_high_confidence_buy_candidates()
        ticker_list.update(high_confidence_buys)
        candidate_info['high_confidence_buys'] = high_confidence_buys
        
        return list(ticker_list), candidate_info
    
    def _get_best_buy_candidates(self) -> List[str]:
        """Get best buy candidates from market screening"""
        try:
            from .market_screening_service import MarketScreeningService
            
            # Try to get real market movers from Alpha Vantage
            screening_service = MarketScreeningService()
            
            # Get top gainers and most active stocks
            top_gainers = screening_service.get_top_gainers(limit=10)
            most_active = screening_service.get_most_active(limit=10)
            
            # Extract symbols from the market data
            symbols = set()
            
            for stock in top_gainers:
                if 'ticker' in stock:
                    symbols.add(stock['ticker'])
            
            for stock in most_active:
                if 'ticker' in stock:
                    symbols.add(stock['ticker'])
            
            # Convert to list and limit to reasonable number
            candidate_symbols = list(symbols)[:15]
            
            if candidate_symbols:
                logger.info(f"Found {len(candidate_symbols)} market screening candidates: {candidate_symbols}")
                return candidate_symbols
            else:
                logger.warning("No market screening candidates found, falling back to hardcoded list")
                
        except Exception as e:
            logger.warning(f"Market screening failed: {e}, falling back to hardcoded list")
        
        # Fallback to hardcoded list if market screening fails
        return [
            'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'NFLX', 'DIS', 'BA'
        ]
    
    def _get_sell_candidates(self, holdings: Dict[str, Holding]) -> List[str]:
        """Get sell candidates from current holdings"""
        # This would check for sell signals on owned stocks
        # For now, return all holdings for potential rebalancing
        return list(holdings.keys())
    
    def _get_high_confidence_buy_candidates(self) -> List[str]:
        """
        Get stocks with high-confidence BUY recommendations for alternative stock discovery.
        This helps find quality stocks like NVO that have consistent BUY signals
        but may not be in current market screening.
        """
        from .models import AIAdvisorRecommendation, Stock
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # Look for recent BUY recommendations with high confidence (>= 0.7)
            # from the last 7 days to ensure they're still relevant
            cutoff_date = timezone.now() - timedelta(days=7)
            
            high_confidence_buys = AIAdvisorRecommendation.objects.filter(
                recommendation_type='BUY',
                confidence_score__gte=0.7,
                created_at__gte=cutoff_date
            ).values_list('stock__symbol', flat=True).distinct()
            
            # Convert to list and limit to top 15 to avoid overwhelming the system
            candidate_symbols = list(high_confidence_buys)[:15]
            
            if candidate_symbols:
                logger.info(f"Found {len(candidate_symbols)} high-confidence BUY candidates: {candidate_symbols}")
                return candidate_symbols
            else:
                logger.info("No high-confidence BUY candidates found in recent recommendations")
                return []
                
        except Exception as e:
            logger.warning(f"Failed to get high-confidence BUY candidates: {e}")
            return []
    
    def _get_advisor_recommendations(self, ticker_list: List[str]) -> List[AIAdvisorRecommendation]:
        """Get recommendations from all active advisors"""
        recommendations = []
        
        # Get recommendations for each ticker from all active advisors
        for symbol in ticker_list:
            try:
                # First, validate that Yahoo Finance recognizes this symbol
                if not self._validate_yahoo_symbol(symbol):
                    logger.warning(f"Skipping {symbol} - not recognized by Yahoo Finance")
                    continue
                
                # Try to get existing stock, create if not found
                try:
                    stock = Stock.objects.get(symbol=symbol)
                except Stock.DoesNotExist:
                    # Auto-create missing stock from market screening
                    logger.info(f"Auto-creating missing stock: {symbol}")
                    stock = self._create_stock_from_market_screening(symbol)
                    if not stock:
                        logger.warning(f"Failed to create stock {symbol}, skipping")
                        continue
                
                advisor_recs = AIAdvisorManager.get_recommendations_for_stock(stock)
                if advisor_recs:
                    recommendations.extend(advisor_recs)
            except Exception as e:
                logger.error(f"Error getting recommendations for {symbol}: {str(e)}")
                continue
        
        return recommendations
    
    def _create_stock_from_market_screening(self, symbol: str) -> Optional[Stock]:
        """Create a new stock from market screening data"""
        try:
            # First, validate that Yahoo Finance recognizes this symbol
            if not self._validate_yahoo_symbol(symbol):
                logger.warning(f"Yahoo Finance does not recognize symbol {symbol}, skipping")
                return None
            
            # Create basic stock entry
            stock = Stock.objects.create(
                symbol=symbol,
                name=f"{symbol} Corporation",
                sector="Unknown",
                market_cap_category="Unknown"
            )
            
            # Try to get additional info from Yahoo Finance
            try:
                from .yahoo_finance_service import YahooMarketDataManager
                YahooMarketDataManager.update_stock_quote(symbol)
                # Refresh the stock object to get updated data
                stock.refresh_from_db()
                logger.info(f"Successfully created and updated stock: {symbol}")
            except Exception as e:
                logger.warning(f"Could not update stock info for {symbol}: {e}")
            
            return stock
            
        except Exception as e:
            logger.error(f"Failed to create stock {symbol}: {e}")
            return None
    
    def _validate_yahoo_symbol(self, symbol: str) -> bool:
        """
        Validate that Yahoo Finance recognizes the symbol before creating recommendations.
        This prevents wasting API calls on delisted or invalid symbols.
        """
        try:
            from .yahoo_finance_service import YahooFinanceService
            
            # Try to get a quote for the symbol
            quote = YahooFinanceService.get_quote(symbol)
            
            # If we get here without an exception, the symbol is valid
            if quote and quote.get('price') and quote['price'] > 0:
                logger.info(f"Yahoo Finance validation passed for {symbol}")
                return True
            else:
                logger.warning(f"Yahoo Finance returned invalid data for {symbol}")
                return False
                
        except Exception as e:
            # If Yahoo Finance throws an exception (like 404 for delisted stocks),
            # the symbol is not valid
            logger.warning(f"Yahoo Finance validation failed for {symbol}: {e}")
            return False
    
    def _get_realtime_prices(self, stock_symbols: List[str]) -> Dict[str, Decimal]:
        """
        Fetch real-time prices from Yahoo Finance during analysis.
        Returns a dictionary mapping stock symbols to their current prices.
        """
        realtime_prices = {}
        
        logger.info(f"Fetching real-time prices for {len(stock_symbols)} stocks")
        
        for symbol in stock_symbols:
            try:
                from .yahoo_finance_service import YahooFinanceService
                quote = YahooFinanceService.get_quote(symbol)
                realtime_prices[symbol] = quote['price']
                logger.info(f"Real-time price for {symbol}: ${quote['price']}")
            except Exception as e:
                logger.warning(f"Failed to get real-time price for {symbol}: {e}")
                # Continue without this price - will use cached price later
                continue
        
        logger.info(f"Successfully fetched {len(realtime_prices)} real-time prices")
        return realtime_prices

    def _consolidate_recommendations(
        self, 
        user: User, 
        advisor_recommendations: List[AIAdvisorRecommendation],
        holdings: Dict[str, Holding],
        risk_profile: RiskProfile
    ) -> List[Dict]:
        """
        Consolidate recommendations from multiple advisors and rank them
        """
        # Get real-time prices for all stocks in recommendations
        stock_symbols = list(set(rec.stock.symbol for rec in advisor_recommendations))
        realtime_prices = self._get_realtime_prices(stock_symbols)
        
        # Group recommendations by stock
        stock_recommendations = {}
        for rec in advisor_recommendations:
            symbol = rec.stock.symbol
            if symbol not in stock_recommendations:
                stock_recommendations[symbol] = []
            stock_recommendations[symbol].append(rec)
        
        consolidated = []
        
        for symbol, recs in stock_recommendations.items():
            # Calculate consolidated scores
            priority_score = self._calculate_priority_score(recs)
            confidence_score = self._calculate_confidence_score(recs)
            
            # Filter by minimum confidence score
            if confidence_score < risk_profile.min_confidence_score:
                continue
            
            # Apply risk-based penny stock and micro-cap filters
            stock = recs[0].stock
            if not risk_profile.allow_penny_stocks:
                # Filter out penny stocks based on user's risk tolerance
                if stock.current_price and stock.current_price < risk_profile.min_stock_price:
                    logger.info(f"Filtering out penny stock: {symbol} (price: ${stock.current_price}, min: ${risk_profile.min_stock_price})")
                    continue
                
                # Filter out micro-cap stocks based on user's risk tolerance
                if stock.market_cap and stock.market_cap < risk_profile.min_market_cap:
                    logger.info(f"Filtering out micro-cap stock: {symbol} (market cap: ${stock.market_cap:,}, min: ${risk_profile.min_market_cap:,})")
                    continue
            else:
                logger.info(f"Penny stocks allowed for {user.username} - including {symbol} (price: ${stock.current_price}, market cap: ${stock.market_cap or 'N/A'})")
            
            # Get portfolio context
            existing_holding = holdings.get(symbol)
            existing_shares = existing_holding.quantity if existing_holding else 0
            
            # Determine recommendation type
            rec_type = self._determine_recommendation_type(recs, existing_shares)
            
            # Skip SELL recommendations for stocks not owned
            if rec_type == 'SELL' and existing_shares == 0:
                continue
            
            # Use real-time price if available, otherwise fall back to cached price
            current_price = realtime_prices.get(symbol, recs[0].stock.current_price)
            
            # Calculate position context using real-time price
            position_value = existing_shares * current_price if existing_shares > 0 else Decimal('0.00')
            position_percentage = (position_value / user.portfolio.total_value * Decimal('100')) if user.portfolio.total_value > 0 else Decimal('0.00')
            
            consolidated.append({
                'stock': recs[0].stock,
                'recommendation_type': rec_type,
                'priority_score': priority_score,
                'confidence_score': confidence_score,
                'existing_shares': existing_shares,
                'position_value': position_value,
                'position_percentage': position_percentage,
                'current_price': current_price,  # Use real-time price
                'target_price': self._calculate_average_target_price(recs),
                'stop_loss': self._calculate_average_stop_loss(recs),
                'reasoning': self._consolidate_reasoning(recs),
                'key_factors': self._consolidate_key_factors(recs),
                'risk_factors': self._consolidate_risk_factors(recs),
                'advisor_recommendations': recs,
            })
        
        # Sort by priority score (highest first)
        consolidated.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return consolidated
    
    def _calculate_priority_score(self, recommendations: List[AIAdvisorRecommendation]) -> Decimal:
        """Calculate consolidated priority score from multiple recommendations"""
        if not recommendations:
            return Decimal('0.00')
        
        total_score = Decimal('0.00')
        total_weight = Decimal('0.00')
        
        for rec in recommendations:
            # Convert recommendation type to score
            type_scores = {
                'STRONG_BUY': 100,
                'BUY': 75,
                'HOLD': 50,
                'SELL': 25,
                'STRONG_SELL': 0,
            }
            
            base_score = Decimal(str(type_scores.get(rec.recommendation_type, 50)))
            # Ensure all values are Decimal objects
            confidence_multiplier = Decimal(str(rec.confidence_score))
            advisor_weight = Decimal(str(rec.advisor.weight))
            
            weighted_score = base_score * confidence_multiplier * advisor_weight
            total_score += weighted_score
            total_weight += advisor_weight
        
        if total_weight > 0:
            return (total_score / total_weight).quantize(Decimal('0.01'))
        return Decimal('0.00')
    
    def _calculate_confidence_score(self, recommendations: List[AIAdvisorRecommendation]) -> Decimal:
        """Calculate average confidence score"""
        if not recommendations:
            return Decimal('0.00')
        
        total_confidence = sum(rec.confidence_score for rec in recommendations)
        return (Decimal(total_confidence) / Decimal(len(recommendations))).quantize(Decimal('0.01'))
    
    def _determine_recommendation_type(
        self, 
        recommendations: List[AIAdvisorRecommendation], 
        existing_shares: int
    ) -> str:
        """Determine consolidated recommendation type"""
        if not recommendations:
            return 'HOLD'
        
        # Count votes for each type
        votes = {'STRONG_BUY': 0, 'BUY': 0, 'HOLD': 0, 'SELL': 0, 'STRONG_SELL': 0}
        
        for rec in recommendations:
            votes[rec.recommendation_type] += rec.advisor.weight
        
        # Determine winner
        winner = max(votes, key=votes.get)
        
        # Convert to simplified types
        if winner in ['STRONG_BUY', 'BUY']:
            return 'BUY'
        elif winner in ['STRONG_SELL', 'SELL']:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _calculate_average_target_price(self, recommendations: List[AIAdvisorRecommendation]) -> Optional[Decimal]:
        """Calculate average target price from recommendations"""
        target_prices = [rec.target_price for rec in recommendations if rec.target_price]
        if target_prices:
            return sum(target_prices) / Decimal(len(target_prices))
        return None
    
    def _calculate_average_stop_loss(self, recommendations: List[AIAdvisorRecommendation]) -> Optional[Decimal]:
        """Calculate average stop loss from recommendations"""
        stop_losses = [rec.stop_loss for rec in recommendations if rec.stop_loss]
        if stop_losses:
            return sum(stop_losses) / Decimal(len(stop_losses))
        return None
    
    def _consolidate_reasoning(self, recommendations: List[AIAdvisorRecommendation]) -> str:
        """Consolidate reasoning from multiple recommendations"""
        reasoning_parts = []
        for rec in recommendations:
            reasoning_parts.append(f"{rec.advisor.name}: {rec.reasoning}")
        return "\n\n".join(reasoning_parts)
    
    def _consolidate_key_factors(self, recommendations: List[AIAdvisorRecommendation]) -> List[str]:
        """Consolidate key factors from recommendations"""
        all_factors = set()
        for rec in recommendations:
            if rec.key_factors:
                all_factors.update(rec.key_factors)
        return list(all_factors)
    
    def _consolidate_risk_factors(self, recommendations: List[AIAdvisorRecommendation]) -> List[str]:
        """Consolidate risk factors from recommendations"""
        all_risks = set()
        for rec in recommendations:
            if rec.risk_factors:
                all_risks.update(rec.risk_factors)
        return list(all_risks)
    
    def _apply_buy_algorithm(
        self,
        recommendations: List[Dict],
        portfolio: Portfolio,
        holdings: Dict[str, Holding],
        risk_profile: RiskProfile
    ) -> List[Dict]:
        """
        Apply the revised buy algorithm with anti-repetition logic
        """
        # Filter to only BUY recommendations
        buy_recommendations = [rec for rec in recommendations if rec['recommendation_type'] == 'BUY']
        
        if not buy_recommendations:
            return []
        
        # Calculate overall cash spend (SP)
        available_cash = portfolio.current_capital
        cash_spend = available_cash * (risk_profile.cash_spend_percentage / Decimal('100'))
        
        # Eliminate stocks that hit max purchase %
        filtered_recommendations = []
        for rec in buy_recommendations:
            if rec['position_percentage'] < risk_profile.max_purchase_percentage:
                filtered_recommendations.append(rec)
        
        if not filtered_recommendations:
            return []
        
        # Weigh remaining recommendations by Priority Score
        total_ps = sum(rec['priority_score'] for rec in filtered_recommendations)
        for rec in filtered_recommendations:
            rec['initial_weight'] = rec['priority_score'] / total_ps
        
        # First pass: Calculate initial shares and adjust weights
        for rec in filtered_recommendations:
            # Calculate shares to buy: ROUND((SP * weight) / sharePrice)
            shares_to_buy = int((cash_spend * rec['initial_weight']) / rec['current_price'])
            
            # Subtract existing share count (eliminates if result <= 0)
            net_shares = shares_to_buy - rec['existing_shares']
            
            if net_shares <= 0:
                rec['eliminated'] = True
                rec['shares_to_buy'] = 0
                rec['adjusted_weight'] = Decimal('0.00')
            else:
                rec['eliminated'] = False
                rec['shares_to_buy'] = net_shares
                
                # Re-evaluate weight based on existing shares
                # If oldShareCount: 100, newShareCount: 20, weight changes from .44 to .088
                if rec['existing_shares'] > 0:
                    weight_reduction = Decimal(rec['existing_shares']) / Decimal(rec['existing_shares'] + net_shares)
                    rec['adjusted_weight'] = rec['initial_weight'] * (Decimal('1') - weight_reduction)
                else:
                    rec['adjusted_weight'] = rec['initial_weight']
        
        # Remove eliminated recommendations
        active_recommendations = [rec for rec in filtered_recommendations if not rec.get('eliminated', False)]
        
        if not active_recommendations:
            return []
        
        # Recalculate total weights and adjust cash spend
        total_adjusted_weight = sum(rec['adjusted_weight'] for rec in active_recommendations)
        
        if total_adjusted_weight > 0:
            # Adjust cash spend proportionally
            adjusted_cash_spend = cash_spend / total_adjusted_weight
            
            # Second pass: Recalculate shares with new weights
            for rec in active_recommendations:
                shares_to_buy = int((adjusted_cash_spend * rec['adjusted_weight']) / rec['current_price'])
                net_shares = shares_to_buy - rec['existing_shares']
                
                if net_shares > 0:
                    rec['shares_to_buy'] = net_shares
                    rec['cash_allocated'] = net_shares * rec['current_price']
                else:
                    rec['shares_to_buy'] = 0
                    rec['cash_allocated'] = Decimal('0.00')
        
        return active_recommendations
    
    def _apply_sell_algorithm(
        self,
        recommendations: List[Dict],
        portfolio: Portfolio,
        holdings: Dict[str, Holding],
        risk_profile: RiskProfile
    ) -> List[Dict]:
        """
        Apply the SellWeight-based selling algorithm.
        This implements the new selling logic with SellWeight multiplier.
        """
        sell_recommendations = []
        
        # Filter to only SELL and HOLD recommendations for owned stocks
        sell_candidates = [
            rec for rec in recommendations 
            if rec['recommendation_type'] in ['SELL', 'HOLD'] and rec['existing_shares'] > 0
        ]
        
        if not sell_candidates:
            logger.info("No sell candidates found")
            return sell_recommendations
        
        # Use portfolio-level SellWeight if set, otherwise use risk profile setting
        effective_sell_weight = portfolio.sell_weight if hasattr(portfolio, 'sell_weight') and portfolio.sell_weight else risk_profile.sell_weight
        
        logger.info(f"Evaluating {len(sell_candidates)} sell candidates with SellWeight={effective_sell_weight} "
                   f"(portfolio={portfolio.sell_weight if hasattr(portfolio, 'sell_weight') else 'N/A'}, "
                   f"risk_profile={risk_profile.sell_weight})")
        
        for rec in sell_candidates:
            symbol = rec['stock'].symbol
            existing_shares = rec['existing_shares']
            confidence_score = rec['confidence_score']
            
            # Calculate adjusted confidence based on effective SellWeight
            if rec['recommendation_type'] == 'SELL':
                # For SELL recommendations: confidence * SellWeight
                adjusted_confidence = confidence_score * effective_sell_weight
            else:  # HOLD
                # For HOLD recommendations: (confidence * 0.5) * SellWeight
                adjusted_confidence = (confidence_score * Decimal('0.5')) * effective_sell_weight
            
            # Convert to 0-1 scale (SellWeight is 1-10, so divide by 10)
            adjusted_confidence = min(adjusted_confidence / Decimal('10'), Decimal('1.0'))
            
            logger.info(f"{symbol}: {rec['recommendation_type']} confidence={confidence_score:.2f}, "
                       f"adjusted={adjusted_confidence:.2f} (SellWeight={risk_profile.sell_weight})")
            
            # Check if adjusted confidence meets threshold
            if adjusted_confidence >= risk_profile.sell_hold_threshold:
                # Calculate sell percentage based on adjusted confidence
                # Higher confidence = sell more shares
                sell_percentage = min(adjusted_confidence, Decimal('1.0'))
                shares_to_sell = int(existing_shares * sell_percentage)
                
                # Ensure we don't sell more than we own
                shares_to_sell = min(shares_to_sell, existing_shares)
                
                if shares_to_sell > 0:
                    # Calculate cash value of sale
                    cash_from_sale = shares_to_sell * rec['current_price']
                    
                    # Create sell recommendation
                    sell_rec = rec.copy()
                    sell_rec.update({
                        'recommendation_type': 'SELL',
                        'shares_to_sell': shares_to_sell,
                        'cash_from_sale': cash_from_sale,
                        'sell_percentage': sell_percentage,
                        'adjusted_confidence': adjusted_confidence,
                        'original_confidence': confidence_score,
                        'sell_weight_applied': effective_sell_weight,
                        'reasoning': f"{rec['reasoning']}\n\n[SellWeight Analysis] Original {rec['recommendation_type']} confidence: {confidence_score:.2f}, Adjusted with SellWeight {effective_sell_weight}: {adjusted_confidence:.2f}, Selling {shares_to_sell} shares ({sell_percentage:.1%})"
                    })
                    
                    sell_recommendations.append(sell_rec)
                    
                    logger.info(f"✓ SELL recommendation for {symbol}: {shares_to_sell} shares "
                               f"({sell_percentage:.1%}) - ${cash_from_sale:.2f}")
                else:
                    logger.info(f"✗ {symbol}: Calculated 0 shares to sell")
            else:
                logger.info(f"✗ {symbol}: Adjusted confidence {adjusted_confidence:.2f} below threshold {risk_profile.sell_hold_threshold}")
        
        logger.info(f"Sell algorithm completed: {len(sell_recommendations)} sell recommendations generated")
        return sell_recommendations
    
    def _check_profit_taking_opportunities(
        self,
        holdings: Dict[str, Holding],
        risk_profile: RiskProfile,
        portfolio: Portfolio
    ) -> List[Dict]:
        """
        Check for profit-taking opportunities on volatile stocks with significant gains.
        Implements the 'quit while you're ahead' strategy.
        """
        if not risk_profile.profit_taking_enabled:
            logger.info("Profit-taking is disabled")
            return []
        
        profit_taking_candidates = []
        
        logger.info(f"Checking profit-taking opportunities (threshold: {risk_profile.profit_taking_threshold}%, "
                   f"volatility: {risk_profile.volatility_threshold}%)")
        
        for symbol, holding in holdings.items():
            try:
                # Calculate recent gain percentage
                recent_gain = self._calculate_recent_gain(holding)
                
                # Get stock volatility (simplified calculation)
                volatility = self._get_stock_volatility(holding.stock)
                
                logger.info(f"{symbol}: Recent gain: {recent_gain:.1f}%, Volatility: {volatility:.1f}%")
                
                # Check if meets profit-taking criteria
                if (recent_gain >= risk_profile.profit_taking_threshold and 
                    volatility >= risk_profile.volatility_threshold):
                    
                    # Calculate profit-taking confidence based on gain size
                    # Higher gains = higher confidence to take profits
                    gain_confidence = min(recent_gain / Decimal('20.0'), Decimal('1.0'))  # Max confidence at 20% gain
                    
                    # Apply SellWeight to profit-taking confidence
                    effective_sell_weight = portfolio.sell_weight if hasattr(portfolio, 'sell_weight') and portfolio.sell_weight else risk_profile.sell_weight
                    adjusted_confidence = gain_confidence * effective_sell_weight
                    adjusted_confidence = min(adjusted_confidence / Decimal('10'), Decimal('1.0'))
                    
                    # Calculate sell percentage based on confidence
                    sell_percentage = min(adjusted_confidence, Decimal('1.0'))
                    shares_to_sell = int(holding.quantity * sell_percentage)
                    
                    if shares_to_sell > 0:
                        cash_from_sale = shares_to_sell * holding.stock.current_price
                        
                        profit_taking_candidates.append({
                            'stock': holding.stock,
                            'recommendation_type': 'SELL',
                            'priority_score': Decimal('90.0'),  # High priority for profit-taking
                            'confidence_score': gain_confidence,
                            'existing_shares': holding.quantity,
                            'position_value': holding.current_value,
                            'position_percentage': (holding.current_value / portfolio.total_value * Decimal('100')) if portfolio.total_value > 0 else Decimal('0.00'),
                            'current_price': holding.stock.current_price,
                            'shares_to_sell': shares_to_sell,
                            'cash_from_sale': cash_from_sale,
                            'sell_percentage': sell_percentage,
                            'adjusted_confidence': adjusted_confidence,
                            'original_confidence': gain_confidence,
                            'sell_weight_applied': effective_sell_weight,
                            'recent_gain': recent_gain,
                            'volatility': volatility,
                            'reasoning': f"Profit-taking opportunity: {recent_gain:.1f}% gain on volatile stock ({volatility:.1f}% volatility). "
                                        f"Quit while you're ahead! Selling {shares_to_sell} shares ({sell_percentage:.1%}) = ${cash_from_sale:.2f}",
                            'key_factors': [f"Recent gain: {recent_gain:.1f}%", f"Volatility: {volatility:.1f}%", "Profit-taking strategy"],
                            'risk_factors': ["High volatility", "Potential for further gains"],
                            'advisor_recommendations': [],  # No advisor recommendations for profit-taking
                        })
                        
                        logger.info(f"✓ Profit-taking opportunity for {symbol}: {shares_to_sell} shares "
                                   f"({sell_percentage:.1%}) - ${cash_from_sale:.2f}")
                    else:
                        logger.info(f"✗ {symbol}: Calculated 0 shares for profit-taking")
                else:
                    logger.info(f"✗ {symbol}: Gain {recent_gain:.1f}% or volatility {volatility:.1f}% below thresholds")
                    
            except Exception as e:
                logger.warning(f"Error checking profit-taking for {symbol}: {e}")
                continue
        
        logger.info(f"Profit-taking analysis completed: {len(profit_taking_candidates)} opportunities found")
        return profit_taking_candidates
    
    def _calculate_recent_gain(self, holding: Holding) -> Decimal:
        """Calculate recent gain percentage for a holding"""
        try:
            if holding.average_price and holding.average_price > 0:
                current_price = holding.stock.current_price or holding.average_price
                gain_percentage = ((current_price - holding.average_price) / holding.average_price) * Decimal('100')
                return max(gain_percentage, Decimal('0.0'))  # Don't return negative gains
            return Decimal('0.0')
        except Exception:
            return Decimal('0.0')
    
    def _get_stock_volatility(self, stock: Stock) -> Decimal:
        """Get stock volatility (simplified calculation)"""
        try:
            # For now, use a simplified volatility calculation
            # In a real implementation, you'd calculate historical volatility
            # For demo purposes, we'll use market cap as a proxy for volatility
            
            if stock.market_cap:
                if stock.market_cap < 1_000_000_000:  # < $1B = high volatility
                    return Decimal('30.0')
                elif stock.market_cap < 10_000_000_000:  # $1B-$10B = medium volatility
                    return Decimal('25.0')
                else:  # > $10B = lower volatility
                    return Decimal('20.0')
            else:
                # Default to medium volatility if market cap unknown
                return Decimal('25.0')
                
        except Exception:
            return Decimal('25.0')  # Default volatility
    
    def _store_recommendations(
        self, 
        user: User, 
        recommendations: List[Dict], 
        session: SmartAnalysisSession
    ) -> List[SmartRecommendation]:
        """Store recommendations in the database"""
        stored_recommendations = []
        
        for rec_data in recommendations:
            # Create SmartRecommendation
            smart_rec = SmartRecommendation.objects.create(
                user=user,
                stock=rec_data['stock'],
                recommendation_type=rec_data['recommendation_type'],
                priority_score=rec_data['priority_score'],
                confidence_score=rec_data['confidence_score'],
                initial_weight=rec_data.get('initial_weight'),
                adjusted_weight=rec_data.get('adjusted_weight'),
                shares_to_buy=rec_data.get('shares_to_buy'),
                cash_allocated=rec_data.get('cash_allocated'),
                existing_shares=rec_data['existing_shares'],
                current_position_value=rec_data['position_value'],
                position_percentage=rec_data['position_percentage'],
                current_price=rec_data['current_price'],
                target_price=rec_data.get('target_price'),
                stop_loss=rec_data.get('stop_loss'),
                reasoning=rec_data['reasoning'],
                key_factors=rec_data['key_factors'],
                risk_factors=rec_data['risk_factors'],
                expires_at=timezone.now() + timedelta(days=7),  # Expire in 7 days
            )
            
            # Store sell-specific data if this is a sell recommendation
            if rec_data['recommendation_type'] == 'SELL' and 'shares_to_sell' in rec_data:
                # We'll need to add these fields to the SmartRecommendation model
                # For now, we'll store the sell data in the reasoning field
                sell_info = f"\n\n[SELL DETAILS] Shares to sell: {rec_data.get('shares_to_sell', 0)}, " \
                           f"Cash from sale: ${rec_data.get('cash_from_sale', 0):.2f}, " \
                           f"Sell percentage: {rec_data.get('sell_percentage', 0):.1%}, " \
                           f"Adjusted confidence: {rec_data.get('adjusted_confidence', 0):.2f}, " \
                           f"SellWeight applied: {rec_data.get('sell_weight_applied', 0)}"
                smart_rec.reasoning += sell_info
                smart_rec.save()
            
            # Link advisor recommendations
            smart_rec.advisor_recommendations.set(rec_data['advisor_recommendations'])
            
            stored_recommendations.append(smart_rec)
        
        return stored_recommendations
    
    def _execute_recommendations(
        self, 
        recommendations: List[SmartRecommendation], 
        portfolio: Portfolio
    ) -> List[Trade]:
        """Execute recommended trades"""
        executed_trades = []
        
        for rec in recommendations:
            if rec.recommendation_type == 'BUY' and rec.shares_to_buy > 0:
                try:
                    with transaction.atomic():
                        # Create trade
                        trade = Trade.objects.create(
                            portfolio=portfolio,
                            stock=rec.stock,
                            trade_type='BUY',
                            order_type='MARKET',
                            quantity=rec.shares_to_buy,
                            price=rec.current_price,
                            total_amount=rec.cash_allocated,
                            status='FILLED',
                            trade_source='SMART_ANALYSIS',
                            source_reference=f"SmartRecommendation-{rec.id}",
                            notes=rec.reasoning,
                            executed_at=timezone.now(),
                        )
                        
                        # Update holding
                        holding, created = Holding.objects.get_or_create(
                            portfolio=portfolio,
                            stock=rec.stock,
                            defaults={
                                'quantity': rec.shares_to_buy,
                                'average_price': rec.current_price,
                            }
                        )
                        
                        if not created:
                            # Update existing holding
                            total_shares = holding.quantity + rec.shares_to_buy
                            total_cost = (holding.quantity * holding.average_price) + rec.cash_allocated
                            new_average_price = total_cost / total_shares
                            
                            holding.quantity = total_shares
                            holding.average_price = new_average_price
                            holding.save()
                        
                        # Update portfolio cash
                        portfolio.current_capital -= rec.cash_allocated
                        portfolio.save()
                        
                        # Update recommendation
                        rec.status = 'EXECUTED'
                        rec.executed_trade = trade
                        rec.executed_at = timezone.now()
                        rec.save()
                        
                        executed_trades.append(trade)
                        
                except Exception as e:
                    logger.error(f"Failed to execute trade for {rec.stock.symbol}: {str(e)}")
                    continue
        
        return executed_trades
    
    def _create_recommendations_summary(self, recommendations: List[SmartRecommendation]) -> Dict:
        """Create summary of recommendations"""
        buy_recs = [r for r in recommendations if r.recommendation_type == 'BUY']
        sell_recs = [r for r in recommendations if r.recommendation_type == 'SELL']
        hold_recs = [r for r in recommendations if r.recommendation_type == 'HOLD']
        
        summary = {
            'total_recommendations': len(recommendations),
            'buy_recommendations': len(buy_recs),
            'sell_recommendations': len(sell_recs),
            'hold_recommendations': len(hold_recs),
            'total_cash_allocated': float(sum(r.cash_allocated or Decimal('0') for r in buy_recs)),
            'total_cash_from_sales': float(sum(self._extract_cash_from_sale(r) for r in sell_recs)),
            'average_priority_score': float(sum(r.priority_score for r in recommendations) / len(recommendations)) if recommendations else 0.0,
            'average_confidence_score': float(sum(r.confidence_score for r in recommendations) / len(recommendations)) if recommendations else 0.0,
        }
        return summary
    
    def _extract_cash_from_sale(self, recommendation: SmartRecommendation) -> Decimal:
        """Extract cash from sale amount from recommendation reasoning"""
        try:
            # Look for "Cash from sale: $X.XX" in the reasoning
            reasoning = recommendation.reasoning or ""
            if "[SELL DETAILS]" in reasoning:
                import re
                match = re.search(r'Cash from sale: \$([0-9,]+\.?[0-9]*)', reasoning)
                if match:
                    return Decimal(match.group(1).replace(',', ''))
        except Exception:
            pass
        return Decimal('0.00')

    def _execute_single_recommendation(self, recommendation, portfolio):
        """Execute a single Smart Recommendation"""
        try:
            from .trading_service import TradingService
            from .models import Trade, Holding
            
            # Validate recommendation
            if recommendation.status != 'PENDING':
                return {'success': False, 'error': 'Recommendation is not pending'}
            
            if not recommendation.shares_to_buy or recommendation.shares_to_buy <= 0:
                return {'success': False, 'error': 'Invalid shares to buy'}
            
            # Place the trade
            result = TradingService.place_order(
                portfolio=portfolio,
                stock=recommendation.stock,
                trade_type=recommendation.recommendation_type,
                quantity=recommendation.shares_to_buy,
                order_type='MARKET',
                price=None,  # Market orders don't need a price - will use current market price
                notes=f'Smart Analysis: {recommendation.reasoning[:100]}...',
                trade_source='SMART_ANALYSIS',
                source_reference=f'SmartRecommendation-{recommendation.id}'
            )
            
            if result['success']:
                trade = result['trade']
                
                # Update recommendation status
                recommendation.status = 'EXECUTED'
                recommendation.executed_trade = trade
                recommendation.executed_at = timezone.now()
                recommendation.save()
                
                return {
                    'success': True, 
                    'trade_id': trade.id,
                    'message': f'Successfully executed {recommendation.recommendation_type} for {recommendation.stock.symbol}'
                }
            else:
                return {'success': False, 'error': result['error']}
                
        except Exception as e:
            logger.error(f"Error executing single recommendation: {str(e)}")
            return {'success': False, 'error': f'Execution failed: {str(e)}'}
