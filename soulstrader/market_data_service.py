"""
Alpha Vantage Market Data Service for SOULTRADER
Handles real-time and historical market data integration
"""

import requests
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import Stock, StockPrice
import time
import logging

logger = logging.getLogger(__name__)


class AlphaVantageService:
    """Service class for Alpha Vantage API integration"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    @classmethod
    def get_api_key(cls):
        """Get API key from Django settings"""
        from django.conf import settings
        return getattr(settings, 'ALPHA_VANTAGE_API_KEY', 'G0C346PZOQVFHNIF')
    
    @classmethod
    def get_rate_limit_delay(cls):
        """Get rate limit delay from Django settings"""
        from django.conf import settings
        return getattr(settings, 'ALPHA_VANTAGE_RATE_LIMIT_DELAY', 12)
    
    @classmethod
    def _make_request(cls, params):
        """Make API request with rate limiting and error handling"""
        try:
            # Add API key to params
            params['apikey'] = cls.get_api_key()
            
            # Make request
            response = requests.get(cls.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                raise Exception(f"Alpha Vantage API Error: {data['Error Message']}")
            
            if 'Note' in data:
                raise Exception(f"Alpha Vantage API Note: {data['Note']}")
            
            if 'Information' in data:
                raise Exception(f"Alpha Vantage API Information: {data['Information']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Failed to fetch data from Alpha Vantage: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception("Invalid response from Alpha Vantage API")
    
    @classmethod
    def get_quote(cls, symbol):
        """Get real-time quote for a stock"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        }
        
        data = cls._make_request(params)
        
        if 'Global Quote' not in data:
            raise Exception(f"No quote data available for {symbol}")
        
        quote = data['Global Quote']
        
        return {
            'symbol': quote.get('01. symbol', symbol),
            'open': Decimal(quote.get('02. open', '0')),
            'high': Decimal(quote.get('03. high', '0')),
            'low': Decimal(quote.get('04. low', '0')),
            'price': Decimal(quote.get('05. price', '0')),
            'volume': int(quote.get('06. volume', '0')),
            'latest_trading_day': quote.get('07. latest trading day', ''),
            'previous_close': Decimal(quote.get('08. previous close', '0')),
            'change': Decimal(quote.get('09. change', '0')),
            'change_percent': quote.get('10. change percent', '0%').replace('%', '')
        }
    
    @classmethod
    def get_company_overview(cls, symbol):
        """Get company overview and fundamental data"""
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        data = cls._make_request(params)
        
        if not data or 'Symbol' not in data:
            raise Exception(f"No company data available for {symbol}")
        
        return {
            'symbol': data.get('Symbol', symbol),
            'name': data.get('Name', ''),
            'sector': data.get('Sector', ''),
            'industry': data.get('Industry', ''),
            'market_cap': data.get('MarketCapitalization', ''),
            'pe_ratio': data.get('PERatio', ''),
            'pb_ratio': data.get('PriceToBookRatio', ''),
            'dividend_yield': data.get('DividendYield', ''),
            'eps': data.get('EPS', ''),
            'beta': data.get('Beta', ''),
            '52_week_high': data.get('52WeekHigh', ''),
            '52_week_low': data.get('52WeekLow', ''),
            'description': data.get('Description', '')
        }
    
    @classmethod
    def get_daily_prices(cls, symbol, outputsize='compact'):
        """Get daily historical prices (last 100 days for compact)"""
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize  # 'compact' for last 100 days, 'full' for 20+ years
        }
        
        data = cls._make_request(params)
        
        if 'Time Series (Daily)' not in data:
            raise Exception(f"No daily price data available for {symbol}")
        
        time_series = data['Time Series (Daily)']
        prices = []
        
        for date_str, price_data in time_series.items():
            try:
                price_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                prices.append({
                    'date': price_date,
                    'open': Decimal(price_data['1. open']),
                    'high': Decimal(price_data['2. high']),
                    'low': Decimal(price_data['3. low']),
                    'close': Decimal(price_data['4. close']),
                    'volume': int(price_data['5. volume'])
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing price data for {symbol} on {date_str}: {e}")
                continue
        
        # Sort by date (oldest first)
        prices.sort(key=lambda x: x['date'])
        return prices
    
    @classmethod
    def get_intraday_prices(cls, symbol, interval='5min'):
        """Get intraday prices (1min, 5min, 15min, 30min, 60min)"""
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval,
            'outputsize': 'compact'
        }
        
        data = cls._make_request(params)
        
        if f'Time Series ({interval})' not in data:
            raise Exception(f"No intraday price data available for {symbol}")
        
        time_series = data[f'Time Series ({interval})']
        prices = []
        
        for datetime_str, price_data in time_series.items():
            try:
                price_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                prices.append({
                    'datetime': price_datetime,
                    'open': Decimal(price_data['1. open']),
                    'high': Decimal(price_data['2. high']),
                    'low': Decimal(price_data['3. low']),
                    'close': Decimal(price_data['4. close']),
                    'volume': int(price_data['5. volume'])
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing intraday data for {symbol} on {datetime_str}: {e}")
                continue
        
        # Sort by datetime (oldest first)
        prices.sort(key=lambda x: x['datetime'])
        return prices
    
    @classmethod
    def search_symbols(cls, keywords):
        """Search for stock symbols by keywords"""
        params = {
            'function': 'SYMBOL_SEARCH',
            'keywords': keywords
        }
        
        data = cls._make_request(params)
        
        if 'bestMatches' not in data:
            return []
        
        symbols = []
        for match in data['bestMatches']:
            symbols.append({
                'symbol': match.get('1. symbol', ''),
                'name': match.get('2. name', ''),
                'type': match.get('3. type', ''),
                'region': match.get('4. region', ''),
                'market_open': match.get('5. marketOpen', ''),
                'market_close': match.get('6. marketClose', ''),
                'timezone': match.get('7. timezone', ''),
                'currency': match.get('8. currency', ''),
                'match_score': match.get('9. matchScore', '')
            })
        
        return symbols


class MarketDataManager:
    """Manager class for updating market data in the database"""
    
    @classmethod
    def update_stock_quote(cls, symbol):
        """Update real-time quote for a stock"""
        try:
            # Get quote from Alpha Vantage
            quote = AlphaVantageService.get_quote(symbol)
            
            # Get or create stock
            stock, created = Stock.objects.get_or_create(
                symbol=symbol.upper(),
                defaults={'name': f'{symbol} Corporation'}
            )
            
            # Update stock with quote data
            stock.current_price = quote['price']
            stock.previous_close = quote['previous_close']
            stock.day_change = quote['change']
            stock.day_change_percent = Decimal(quote['change_percent'])
            stock.last_updated = timezone.now()
            
            # Update name if we have it
            if not stock.name or stock.name == f'{symbol} Corporation':
                try:
                    overview = AlphaVantageService.get_company_overview(symbol)
                    stock.name = overview['name']
                    stock.sector = overview['sector']
                    stock.industry = overview['industry']
                    
                    # Parse market cap
                    if overview['market_cap']:
                        try:
                            stock.market_cap = int(overview['market_cap'])
                            # Determine market cap category
                            if stock.market_cap >= 10000000000:  # $10B+
                                stock.market_cap_category = 'LARGE_CAP'
                            elif stock.market_cap >= 2000000000:  # $2B-$10B
                                stock.market_cap_category = 'MID_CAP'
                            elif stock.market_cap >= 300000000:  # $300M-$2B
                                stock.market_cap_category = 'SMALL_CAP'
                            else:
                                stock.market_cap_category = 'MICRO_CAP'
                        except (ValueError, TypeError):
                            pass
                    
                    # Parse ratios
                    if overview['pe_ratio']:
                        try:
                            stock.pe_ratio = Decimal(overview['pe_ratio'])
                        except (ValueError, TypeError):
                            pass
                    
                    if overview['pb_ratio']:
                        try:
                            stock.pb_ratio = Decimal(overview['pb_ratio'])
                        except (ValueError, TypeError):
                            pass
                    
                    if overview['dividend_yield']:
                        try:
                            stock.dividend_yield = Decimal(overview['dividend_yield'])
                        except (ValueError, TypeError):
                            pass
                            
                except Exception as e:
                    logger.warning(f"Could not fetch company overview for {symbol}: {e}")
            
            stock.save()
            
            logger.info(f"Updated quote for {symbol}: ${stock.current_price}")
            return stock
            
        except Exception as e:
            logger.error(f"Failed to update quote for {symbol}: {e}")
            raise
    
    @classmethod
    def update_historical_prices(cls, symbol, days=100):
        """Update historical price data for a stock"""
        try:
            # Get historical prices
            prices = AlphaVantageService.get_daily_prices(symbol)
            
            # Get stock
            try:
                stock = Stock.objects.get(symbol=symbol.upper())
            except Stock.DoesNotExist:
                logger.error(f"Stock {symbol} not found in database")
                return
            
            # Update price data
            updated_count = 0
            for price_data in prices:
                price_obj, created = StockPrice.objects.get_or_create(
                    stock=stock,
                    date=price_data['date'],
                    defaults={
                        'open_price': price_data['open'],
                        'high_price': price_data['high'],
                        'low_price': price_data['low'],
                        'close_price': price_data['close'],
                        'volume': price_data['volume'],
                        'adjusted_close': price_data['close']
                    }
                )
                
                if created:
                    updated_count += 1
            
            logger.info(f"Updated {updated_count} price records for {symbol}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update historical prices for {symbol}: {e}")
            raise
    
    @classmethod
    def update_multiple_stocks(cls, symbols, delay=True):
        """Update multiple stocks with rate limiting"""
        updated_stocks = []
        
        for i, symbol in enumerate(symbols):
            try:
                stock = cls.update_stock_quote(symbol)
                updated_stocks.append(stock)
                
                # Rate limiting delay (except for last stock)
                if delay and i < len(symbols) - 1:
                    time.sleep(AlphaVantageService.get_rate_limit_delay())
                    
            except Exception as e:
                logger.error(f"Failed to update {symbol}: {e}")
                continue
        
        return updated_stocks
    
    @classmethod
    def search_and_add_stock(cls, keywords):
        """Search for stocks and add them to the database"""
        try:
            # Search for symbols
            symbols = AlphaVantageService.search_symbols(keywords)
            
            if not symbols:
                return []
            
            added_stocks = []
            
            # Add top matches to database
            for symbol_data in symbols[:5]:  # Limit to top 5 matches
                symbol = symbol_data['symbol']
                
                # Skip if already exists
                if Stock.objects.filter(symbol=symbol).exists():
                    continue
                
                try:
                    # Create stock with basic info
                    stock = Stock.objects.create(
                        symbol=symbol,
                        name=symbol_data['name'],
                        is_active=True
                    )
                    
                    # Update with full data
                    cls.update_stock_quote(symbol)
                    added_stocks.append(stock)
                    
                    # Rate limiting
                    time.sleep(AlphaVantageService.get_rate_limit_delay())
                    
                except Exception as e:
                    logger.error(f"Failed to add stock {symbol}: {e}")
                    continue
            
            return added_stocks
            
        except Exception as e:
            logger.error(f"Failed to search stocks: {e}")
            raise
