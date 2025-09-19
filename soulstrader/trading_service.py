"""
Trading Service for SOULTRADER
Handles order execution, portfolio updates, and trade validation
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import random
from .models import Trade, Portfolio, Holding, OrderBook, Stock


class TradingService:
    """Service class for handling trading operations"""
    
    COMMISSION_RATE = Decimal('0.001')  # 0.1% commission
    MIN_COMMISSION = Decimal('1.00')    # Minimum $1 commission
    
    @classmethod
    def place_order(cls, portfolio, stock, trade_type, quantity, order_type='MARKET', 
                   price=None, stop_price=None, notes=''):
        """
        Place a new trading order
        
        Args:
            portfolio: Portfolio instance
            stock: Stock instance
            trade_type: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
            price: Limit price for limit orders
            stop_price: Stop price for stop orders
            notes: Optional notes
            
        Returns:
            dict with 'success': bool, 'trade': Trade instance or None, 'error': str or None
        """
        
        # Validate the order
        validation_result = cls.validate_order(portfolio, stock, trade_type, quantity, order_type, price)
        if not validation_result['valid']:
            return {
                'success': False,
                'trade': None,
                'error': validation_result['reason']
            }
        
        # Create the trade
        trade = Trade.objects.create(
            portfolio=portfolio,
            stock=stock,
            trade_type=trade_type,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            notes=notes,
            status='PENDING'
        )
        
        # Add to order book if not a market order
        if order_type != 'MARKET':
            OrderBook.objects.create(trade=trade)
        
        # Execute market orders immediately
        if order_type == 'MARKET':
            execution_success = cls.execute_market_order(trade)
            if not execution_success:
                return {
                    'success': False,
                    'trade': trade,
                    'error': trade.rejection_reason if hasattr(trade, 'rejection_reason') else 'Order execution failed'
                }
        
        return {
            'success': True,
            'trade': trade,
            'error': None
        }
    
    @classmethod
    def validate_order(cls, portfolio, stock, trade_type, quantity, order_type, price=None):
        """
        Validate if an order can be placed
        
        Returns:
            dict with 'valid' boolean and 'reason' string
        """
        
        # Check if stock is active
        if not stock.is_active:
            return {'valid': False, 'reason': 'Stock is not active for trading'}
        
        # Check if stock has current price
        if not stock.current_price and order_type == 'MARKET':
            return {'valid': False, 'reason': 'No current price available for market order'}
        
        # Validate quantity
        if quantity <= 0:
            return {'valid': False, 'reason': 'Quantity must be positive'}
        
        # For buy orders, check available cash
        if trade_type == 'BUY':
            if order_type == 'MARKET':
                required_cash = quantity * stock.current_price
            elif order_type == 'LIMIT' and price:
                required_cash = quantity * price
            else:
                return {'valid': False, 'reason': 'Price required for limit orders'}
            
            # Add commission
            commission = max(required_cash * cls.COMMISSION_RATE, cls.MIN_COMMISSION)
            total_required = required_cash + commission
            
            if portfolio.current_capital < total_required:
                return {
                    'valid': False, 
                    'reason': f'Insufficient funds. Required: ${total_required:.2f}, Available: ${portfolio.current_capital:.2f}'
                }
        
        # For sell orders, check available shares
        elif trade_type == 'SELL':
            try:
                holding = portfolio.holdings.get(stock=stock)
                if holding.quantity < quantity:
                    return {
                        'valid': False,
                        'reason': f'Insufficient shares. Available: {holding.quantity}, Requested: {quantity}'
                    }
            except Holding.DoesNotExist:
                return {'valid': False, 'reason': 'No shares to sell'}
        
        return {'valid': True, 'reason': 'Order is valid'}
    
    @classmethod
    def execute_market_order(cls, trade):
        """Execute a market order immediately"""
        
        with transaction.atomic():
            # Get current stock price
            current_price = trade.stock.current_price
            
            if not current_price:
                trade.status = 'REJECTED'
                trade.rejection_reason = 'No current price available'
                trade.save()
                return False
            
            # Calculate commission
            total_amount = trade.quantity * current_price
            commission = max(total_amount * cls.COMMISSION_RATE, cls.MIN_COMMISSION)
            
            # Update trade with execution details
            trade.filled_quantity = trade.quantity
            trade.average_fill_price = current_price
            trade.total_amount = total_amount
            trade.commission = commission
            trade.status = 'FILLED'
            trade.executed_at = timezone.now()
            trade.save()
            
            # Update portfolio
            cls.update_portfolio_after_trade(trade)
            
            return True
    
    @classmethod
    def execute_limit_order(cls, trade):
        """Execute a limit order if conditions are met"""
        
        current_price = trade.stock.current_price
        if not current_price:
            return False
        
        # Check if limit order can be executed
        can_execute = False
        
        if trade.trade_type == 'BUY' and current_price <= trade.price:
            can_execute = True
        elif trade.trade_type == 'SELL' and current_price >= trade.price:
            can_execute = True
        
        if can_execute:
            # Execute at limit price
            total_amount = trade.quantity * trade.price
            commission = max(total_amount * cls.COMMISSION_RATE, cls.MIN_COMMISSION)
            
            trade.filled_quantity = trade.quantity
            trade.average_fill_price = trade.price
            trade.total_amount = total_amount
            trade.commission = commission
            trade.status = 'FILLED'
            trade.executed_at = timezone.now()
            trade.save()
            
            # Remove from order book
            if hasattr(trade, 'order_book_entry'):
                trade.order_book_entry.delete()
            
            # Update portfolio
            cls.update_portfolio_after_trade(trade)
            
            return True
        
        return False
    
    @classmethod
    def update_portfolio_after_trade(cls, trade):
        """Update portfolio holdings and cash after trade execution"""
        
        portfolio = trade.portfolio
        
        if trade.trade_type == 'BUY':
            # Deduct cash
            total_cost = trade.total_amount + trade.commission
            portfolio.current_capital -= total_cost
            portfolio.total_invested += trade.total_amount
            
            # Update or create holding
            holding, created = Holding.objects.get_or_create(
                portfolio=portfolio,
                stock=trade.stock,
                defaults={
                    'quantity': trade.filled_quantity,
                    'average_price': trade.average_fill_price
                }
            )
            
            if not created:
                # Update existing holding with weighted average price
                total_shares = holding.quantity + trade.filled_quantity
                total_cost_basis = (holding.quantity * holding.average_price) + trade.total_amount
                holding.average_price = total_cost_basis / total_shares
                holding.quantity = total_shares
                holding.save()
        
        elif trade.trade_type == 'SELL':
            # Add cash
            total_proceeds = trade.total_amount - trade.commission
            portfolio.current_capital += total_proceeds
            portfolio.total_invested -= trade.total_amount
            
            # Update holding
            holding = portfolio.holdings.get(stock=trade.stock)
            holding.quantity -= trade.filled_quantity
            
            if holding.quantity <= 0:
                holding.delete()
            else:
                holding.save()
        
        portfolio.save()
    
    @classmethod
    def cancel_order(cls, trade):
        """Cancel a pending order"""
        
        if trade.status not in ['PENDING', 'PARTIALLY_FILLED']:
            return False
        
        trade.status = 'CANCELLED'
        trade.save()
        
        # Remove from order book
        if hasattr(trade, 'order_book_entry'):
            trade.order_book_entry.delete()
        
        return True
    
    @classmethod
    def process_pending_orders(cls):
        """Process all pending orders (called periodically)"""
        
        # Process limit orders
        pending_trades = Trade.objects.filter(
            status__in=['PENDING', 'PARTIALLY_FILLED'],
            order_type__in=['LIMIT', 'STOP']
        ).select_related('stock', 'portfolio')
        
        for trade in pending_trades:
            if trade.order_type == 'LIMIT':
                cls.execute_limit_order(trade)
            # Add stop order logic here if needed
    
    @classmethod
    def simulate_price_movement(cls, stock, volatility=0.02):
        """Simulate realistic price movement for testing"""
        
        if not stock.current_price:
            return
        
        # Generate random price change (-volatility to +volatility)
        change_percent = random.uniform(-volatility, volatility)
        new_price = stock.current_price * (1 + Decimal(str(change_percent)))
        
        # Update stock price
        stock.previous_close = stock.current_price
        stock.current_price = new_price
        stock.day_change = new_price - stock.previous_close
        stock.day_change_percent = (stock.day_change / stock.previous_close) * 100
        stock.save()
    
    @classmethod
    def get_trade_summary(cls, portfolio):
        """Get trading summary for a portfolio"""
        
        trades = portfolio.trades.all()
        
        total_trades = trades.count()
        filled_trades = trades.filter(status='FILLED').count()
        pending_trades = trades.filter(status__in=['PENDING', 'PARTIALLY_FILLED']).count()
        
        total_volume = sum(trade.total_amount for trade in trades.filter(status='FILLED'))
        total_commission = sum(trade.commission for trade in trades.filter(status='FILLED'))
        
        return {
            'total_trades': total_trades,
            'filled_trades': filled_trades,
            'pending_trades': pending_trades,
            'total_volume': total_volume,
            'total_commission': total_commission,
            'success_rate': (filled_trades / total_trades * 100) if total_trades > 0 else 0
        }
