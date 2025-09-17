"""
Yahoo Finance Market Data Service for SOULTRADER
Free, unlimited market data with no API key required
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import Stock, StockPrice
import logging
import time

logger = logging.getLogger(__name__)


class YahooFinanceService:
    """Service class for Yahoo Finance API integration"""
    
    @classmethod
    def get_quote(cls, symbol):
        """Get real-time quote for a stock"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get current price data
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            
            if not current_price:
                # Fallback: get price from history
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    if len(hist) > 1:
                        previous_close = float(hist['Close'].iloc[-2])
                    else:
                        previous_close = current_price
            
            if not current_price:
                raise Exception(f"No price data available for {symbol}")
            
            # Calculate change
            if previous_close:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
            else:
                change = 0
                change_percent = 0
            
            return {
                'symbol': symbol.upper(),
                'price': Decimal(str(current_price)),
                'previous_close': Decimal(str(previous_close)) if previous_close else Decimal('0'),
                'change': Decimal(str(change)),
                'change_percent': Decimal(str(change_percent)),
                'volume': info.get('volume', 0) or info.get('regularMarketVolume', 0),
                'open': Decimal(str(info.get('open', current_price))),
                'high': Decimal(str(info.get('dayHigh', current_price))),
                'low': Decimal(str(info.get('dayLow', current_price))),
            }
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise Exception(f"Failed to fetch quote for {symbol}: {str(e)}")
    
    @classmethod
    def get_company_info(cls, symbol):
        """Get company information and fundamental data"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Map Yahoo Finance sectors to our sector choices
            sector_mapping = {
                'Technology': 'TECHNOLOGY',
                'Healthcare': 'HEALTHCARE',
                'Financial Services': 'FINANCIAL',
                'Consumer Cyclical': 'CONSUMER_DISCRETIONARY',
                'Industrials': 'INDUSTRIALS',
                'Consumer Defensive': 'CONSUMER_STAPLES',
                'Energy': 'ENERGY',
                'Utilities': 'UTILITIES',
                'Real Estate': 'REAL_ESTATE',
                'Basic Materials': 'MATERIALS',
                'Communication Services': 'COMMUNICATION',
            }
            
            yahoo_sector = info.get('sector', '')
            our_sector = sector_mapping.get(yahoo_sector, 'OTHER')
            
            return {
                'symbol': symbol.upper(),
                'name': info.get('longName', info.get('shortName', symbol)),
                'sector': our_sector,
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'description': info.get('longBusinessSummary', ''),
                'website': info.get('website', ''),
                'employees': info.get('fullTimeEmployees'),
            }
            
        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            raise Exception(f"Failed to fetch company info for {symbol}: {str(e)}")
    
    @classmethod
    def get_historical_data(cls, symbol, period="3mo"):
        """
        Get historical price data
        
        Args:
            symbol: Stock symbol
            period: Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                raise Exception(f"No historical data available for {symbol}")
            
            prices = []
            for date_index, row in hist.iterrows():
                try:
                    price_date = date_index.date()
                    prices.append({
                        'date': price_date,
                        'open': Decimal(str(row['Open'])),
                        'high': Decimal(str(row['High'])),
                        'low': Decimal(str(row['Low'])),
                        'close': Decimal(str(row['Close'])),
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing price data for {symbol} on {date_index}: {e}")
                    continue
            
            return prices
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            raise Exception(f"Failed to fetch historical data for {symbol}: {str(e)}")
    
    @classmethod
    def search_symbols(cls, query):
        """Search for stock symbols by company name or symbol"""
        try:
            # Yahoo Finance doesn't have a direct search API, but we can try common patterns
            # For now, we'll implement a basic search by trying the query as a symbol
            
            # Try the query directly as a symbol
            results = []
            
            # Clean the query
            query = query.strip().upper()
            
            # Try exact symbol match
            try:
                info = cls.get_company_info(query)
                results.append({
                    'symbol': query,
                    'name': info['name'],
                    'sector': info['sector'],
                    'industry': info['industry'],
                    'match_score': '1.0'
                })
            except:
                pass
            
            # Try common variations if it's a company name
            if len(results) == 0 and len(query) > 2:
                # Try some common patterns for well-known companies
                common_symbols = {
                    'APPLE': 'AAPL',
                    'MICROSOFT': 'MSFT',
                    'GOOGLE': 'GOOGL',
                    'ALPHABET': 'GOOGL',
                    'AMAZON': 'AMZN',
                    'TESLA': 'TSLA',
                    'NVIDIA': 'NVDA',
                    'META': 'META',
                    'FACEBOOK': 'META',
                    'NETFLIX': 'NFLX',
                    'ADOBE': 'ADBE',
                    'SALESFORCE': 'CRM',
                    'ORACLE': 'ORCL',
                    'INTEL': 'INTC',
                    'AMD': 'AMD',
                    'PAYPAL': 'PYPL',
                    'VISA': 'V',
                    'MASTERCARD': 'MA',
                    'JOHNSON': 'JNJ',
                    'PFIZER': 'PFE',
                    'COCA': 'KO',
                    'PEPSI': 'PEP',
                    'WALMART': 'WMT',
                    'DISNEY': 'DIS',
                    'BOEING': 'BA',
                    'GOLDMAN': 'GS',
                    'JPMORGAN': 'JPM',
                    'MORGAN': 'JPM',
                    'CHASE': 'JPM',
                }
                
                for name, symbol in common_symbols.items():
                    if name in query or query in name:
                        try:
                            info = cls.get_company_info(symbol)
                            results.append({
                                'symbol': symbol,
                                'name': info['name'],
                                'sector': info['sector'],
                                'industry': info['industry'],
                                'match_score': '0.8'
                            })
                            break
                        except:
                            continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search symbols for '{query}': {e}")
            return []


class YahooMarketDataManager:
    """Manager class for updating market data using Yahoo Finance"""
    
    @classmethod
    def update_stock_quote(cls, symbol):
        """Update real-time quote for a stock"""
        try:
            # Get quote from Yahoo Finance
            quote = YahooFinanceService.get_quote(symbol)
            
            # Get or create stock
            stock, created = Stock.objects.get_or_create(
                symbol=symbol.upper(),
                defaults={'name': f'{symbol} Corporation'}
            )
            
            # Update stock with quote data
            stock.current_price = quote['price']
            stock.previous_close = quote['previous_close']
            stock.day_change = quote['change']
            stock.day_change_percent = quote['change_percent']
            stock.last_updated = timezone.now()
            
            # Update company information if needed
            if not stock.name or stock.name == f'{symbol} Corporation' or created:
                try:
                    company_info = YahooFinanceService.get_company_info(symbol)
                    stock.name = company_info['name']
                    stock.sector = company_info['sector']
                    stock.industry = company_info['industry']
                    
                    # Set market cap and category
                    if company_info['market_cap']:
                        stock.market_cap = company_info['market_cap']
                        # Determine market cap category
                        if stock.market_cap >= 10000000000:  # $10B+
                            stock.market_cap_category = 'LARGE_CAP'
                        elif stock.market_cap >= 2000000000:  # $2B-$10B
                            stock.market_cap_category = 'MID_CAP'
                        elif stock.market_cap >= 300000000:  # $300M-$2B
                            stock.market_cap_category = 'SMALL_CAP'
                        else:
                            stock.market_cap_category = 'MICRO_CAP'
                    
                    # Set financial ratios
                    if company_info['pe_ratio']:
                        stock.pe_ratio = Decimal(str(company_info['pe_ratio']))
                    
                    if company_info['pb_ratio']:
                        stock.pb_ratio = Decimal(str(company_info['pb_ratio']))
                    
                    if company_info['dividend_yield']:
                        stock.dividend_yield = Decimal(str(company_info['dividend_yield'] * 100))  # Convert to percentage
                        
                except Exception as e:
                    logger.warning(f"Could not fetch company info for {symbol}: {e}")
            
            stock.save()
            
            logger.info(f"Updated quote for {symbol}: ${stock.current_price}")
            return stock
            
        except Exception as e:
            logger.error(f"Failed to update quote for {symbol}: {e}")
            raise
    
    @classmethod
    def update_historical_prices(cls, symbol, period="3mo"):
        """Update historical price data for a stock"""
        try:
            # Get historical prices
            prices = YahooFinanceService.get_historical_data(symbol, period)
            
            # Get stock
            try:
                stock = Stock.objects.get(symbol=symbol.upper())
            except Stock.DoesNotExist:
                logger.error(f"Stock {symbol} not found in database")
                return 0
            
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
    def update_multiple_stocks(cls, symbols, delay=False):
        """Update multiple stocks (no rate limiting needed for Yahoo Finance)"""
        updated_stocks = []
        
        for symbol in symbols:
            try:
                stock = cls.update_stock_quote(symbol)
                updated_stocks.append(stock)
                
                # Small delay to be respectful to Yahoo's servers
                if delay:
                    time.sleep(0.1)  # 100ms delay
                    
            except Exception as e:
                logger.error(f"Failed to update {symbol}: {e}")
                continue
        
        return updated_stocks
    
    @classmethod
    def search_and_add_stock(cls, keywords):
        """Search for stocks and add them to the database"""
        try:
            # Search for symbols
            symbols = YahooFinanceService.search_symbols(keywords)
            
            if not symbols:
                return []
            
            added_stocks = []
            
            # Add found stocks to database
            for symbol_data in symbols:
                symbol = symbol_data['symbol']
                
                # Skip if already exists
                if Stock.objects.filter(symbol=symbol).exists():
                    continue
                
                try:
                    # Update with full data
                    stock = cls.update_stock_quote(symbol)
                    added_stocks.append(stock)
                    
                    # Small delay
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to add stock {symbol}: {e}")
                    continue
            
            return added_stocks
            
        except Exception as e:
            logger.error(f"Failed to search stocks: {e}")
            raise
