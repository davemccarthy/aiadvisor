#!/usr/bin/env python
"""
Test script for FMP API integration
Run this script to test the FMP API integration with your Django project.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/davidmccarthy/Development/CursorAI/Django/aiadvisor')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiadvisor.settings')
django.setup()

from soulstrader.models import Stock, AIAdvisor
from soulstrader.fmp_service import FMPAPIService


def test_fmp_integration():
    """Test FMP API integration"""
    
    print("🚀 Testing FMP API Integration")
    print("=" * 50)
    
    # Check if we have an FMP API key
    try:
        from django.conf import settings
        api_key = getattr(settings, 'FMP_API_KEY', '')
        if not api_key:
            print("❌ No FMP API key found in settings.")
            print("   Please add your FMP API key to settings.py:")
            print("   FMP_API_KEY = 'your_api_key_here'")
            return False
        
        print(f"✅ FMP API key found: {api_key[:10]}...")
        
    except Exception as e:
        print(f"❌ Error checking API key: {e}")
        return False
    
    # Test FMP service initialization
    try:
        fmp_service = FMPAPIService()
        print("✅ FMP service initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing FMP service: {e}")
        return False
    
    # Test API connection
    try:
        if fmp_service.test_connection():
            print("✅ FMP API connection successful")
        else:
            print("❌ FMP API connection failed")
            return False
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False
    
    # Test stock search
    try:
        print("\n🔍 Testing stock search...")
        search_results = fmp_service.search_stocks("AAPL", limit=3)
        if search_results:
            print(f"✅ Found {len(search_results)} results for AAPL")
            for result in search_results:
                print(f"   - {result.get('symbol', 'N/A')}: {result.get('name', 'N/A')}")
        else:
            print("⚠️  No search results found")
    except Exception as e:
        print(f"❌ Error testing search: {e}")
    
    # Test stock grade retrieval
    try:
        print("\n📊 Testing stock grade retrieval...")
        grade_data = fmp_service.get_stock_grade("AAPL")
        if grade_data:
            print("✅ Grade data retrieved successfully")
            if isinstance(grade_data, list) and grade_data:
                grade_info = grade_data[0]
            elif isinstance(grade_data, dict):
                grade_info = grade_data
            else:
                grade_info = {}
            
            if grade_info:
                print(f"   Grade: {grade_info.get('grade', 'N/A')}")
                print(f"   Score: {grade_info.get('score', 'N/A')}")
        else:
            print("⚠️  No grade data found")
    except Exception as e:
        print(f"❌ Error testing grade retrieval: {e}")
    
    # Test logo URL generation
    try:
        print("\n🖼️  Testing logo URL generation...")
        logo_url = fmp_service.get_company_logo_url("AAPL")
        print(f"✅ Logo URL: {logo_url}")
    except Exception as e:
        print(f"❌ Error generating logo URL: {e}")
    
    # Test with existing stock in database
    try:
        print("\n💾 Testing database integration...")
        # Try to find an existing stock
        stock = Stock.objects.filter(symbol__in=['AAPL', 'MSFT', 'GOOGL', 'TSLA']).first()
        
        if stock:
            print(f"✅ Found stock in database: {stock.symbol}")
            
            # Test updating stock with FMP data
            success = fmp_service.update_stock_with_fmp_data(stock)
            if success:
                print(f"✅ Successfully updated {stock.symbol} with FMP data")
                print(f"   Logo URL: {stock.logo_url}")
                print(f"   FMP Grade: {stock.fmp_grade or 'N/A'}")
                print(f"   FMP Score: {stock.fmp_score or 'N/A'}")
            else:
                print(f"⚠️  Failed to update {stock.symbol} with FMP data")
        else:
            print("⚠️  No stocks found in database to test with")
            print("   You may need to load some stock data first")
    except Exception as e:
        print(f"❌ Error testing database integration: {e}")
    
    print("\n" + "=" * 50)
    print("✅ FMP API integration test completed!")
    print("\nNext steps:")
    print("1. Add your FMP API key to settings.py if you haven't already")
    print("2. Create an FMP AIAdvisor in the admin panel")
    print("3. Run: python manage.py update_fmp_data --create-advisor --all")
    print("4. Check your portfolio page to see logos and grades!")
    
    return True


if __name__ == "__main__":
    test_fmp_integration()
