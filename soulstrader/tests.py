from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Portfolio, Stock, Holding
from .trading_service import TradingService


class TradingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Test",
            initial_capital=Decimal('100000.00'),
            current_capital=Decimal('100000.00')
        )
        self.stock = Stock.objects.create(symbol='TEST', name='Test Inc', current_price=Decimal('100.00'))
        Holding.objects.create(portfolio=self.portfolio, stock=self.stock, quantity=10, average_price=Decimal('50.00'))

    def test_bank_allocation_basic(self):
        # Enable bank and set settings
        self.portfolio.safety_bank_enabled = True
        self.portfolio.safety_bank_balance = Decimal('10000.00')  # 10% filled vs initial 100k
        self.portfolio.bank_divisor = 10  # vacancy 90% -> 9%
        self.portfolio.bank_rate_ceiling_percent = Decimal('20.00')
        self.portfolio.save()

        # Place SELL of 5 shares @ $100 => total_amount 500, commission min $1 => proceeds 499
        result = TradingService.place_order(self.portfolio, self.stock, 'SELL', 5, order_type='MARKET')
        self.assertTrue(result['success'])

        # After fees allocation: ~9% of proceeds to bank, rounded to $1
        self.portfolio.refresh_from_db()
        self.assertGreaterEqual(self.portfolio.safety_bank_balance, Decimal('10000.00'))
        self.assertGreater(self.portfolio.current_capital, Decimal('100000.00'))

    def test_bank_floor_rate_when_full(self):
        self.portfolio.safety_bank_enabled = True
        self.portfolio.safety_bank_balance = Decimal('200000.00')  # > initial, vacancy 0
        self.portfolio.bank_divisor = 10
        self.portfolio.bank_rate_ceiling_percent = Decimal('20.00')
        self.portfolio.save()

        result = TradingService.place_order(self.portfolio, self.stock, 'SELL', 2, order_type='MARKET')
        self.assertTrue(result['success'])
        self.portfolio.refresh_from_db()
        # Should still allocate at least 1% of proceeds
        self.assertGreater(self.portfolio.safety_bank_balance, Decimal('200000.00'))

    def test_not_green_no_allocation(self):
        self.portfolio.safety_bank_enabled = True
        self.portfolio.safety_bank_balance = Decimal('0.00')
        self.portfolio.bank_divisor = 10
        self.portfolio.bank_rate_ceiling_percent = Decimal('20.00')
        # Force not green by lowering cash and price
        self.portfolio.current_capital = Decimal('1000.00')
        self.portfolio.initial_capital = Decimal('100000.00')
        self.portfolio.save()
        self.stock.current_price = Decimal('1.00')
        self.stock.save()

        result = TradingService.place_order(self.portfolio, self.stock, 'SELL', 1, order_type='MARKET')
        self.assertTrue(result['success'])
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.safety_bank_balance, Decimal('0.00'))
