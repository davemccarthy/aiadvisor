# Financial Modeling Prep (FMP) API Integration Guide

This guide explains how to use the Financial Modeling Prep API integration with your AI Advisor Django application.

## 🚀 Features Implemented

### ✅ Stock Search API
- **Endpoint**: `https://financialmodelingprep.com/api/v3/search?query=AA&apikey=YOUR_KEY`
- Search for stocks by symbol or company name
- Integrated into the FMP service class

### ✅ Stock Grades & Consensus API  
- **Endpoint**: `https://financialmodelingprep.com/stable/grades-consensus?symbol=AAPL&apikey=YOUR_KEY`
- Get stock grades (A+, A, B+, etc.) and analyst consensus
- Automatically converted to AI recommendations

### ✅ Company Logo Images
- **Endpoint**: `https://financialmodelingprep.com/image-stock/{SYMBOL}.png`
- Company logos displayed in portfolio table
- Fallback to symbol initials if logo fails to load

### ✅ Enhanced Portfolio Display
- Company logos in holdings table
- FMP grades with color-coded badges
- Analyst target prices and ratings

## 📋 Setup Instructions

### 1. Get Your FMP API Key
1. Visit [Financial Modeling Prep](https://financialmodelingprep.com)
2. Sign up for a free account
3. Get your API key from the dashboard

### 2. Configure Your API Key

#### Option A: Add to Django Settings (Recommended)
```python
# In aiadvisor/settings.py
FMP_API_KEY = 'your_fmp_api_key_here'
```

#### Option B: Add via Admin Panel
1. Go to Django Admin → AI Advisors
2. Create new AIAdvisor with:
   - **Advisor Type**: FMP
   - **Name**: Financial Modeling Prep
   - **API Key**: Your FMP API key
   - **API Endpoint**: https://financialmodelingprep.com/api/v3

### 3. Run Database Migration
```bash
# Activate your virtual environment
source ~/Development/scratch/python/tutorial-env/bin/activate

# Navigate to project directory
cd /Users/davidmccarthy/Development/CursorAI/Django/aiadvisor

# Apply migrations
python manage.py migrate
```

## 🛠️ Usage Commands

### Test FMP Integration
```bash
# Test the FMP API connection and functionality
python test_fmp_integration.py
```

### Update Stock Data with FMP
```bash
# Create FMP advisor and update all stocks
python manage.py update_fmp_data --create-advisor --all

# Update specific stocks only
python manage.py update_fmp_data --symbols AAPL MSFT GOOGL

# Dry run to see what would be updated
python manage.py update_fmp_data --all --dry-run
```

### Create FMP-Based Recommendations
```bash
# Create recommendations for all stocks with FMP grades
python manage.py create_fmp_recommendations --all

# Create recommendations for specific stocks
python manage.py create_fmp_recommendations --symbols AAPL MSFT

# Force create new recommendations (ignore recent ones)
python manage.py create_fmp_recommendations --all --force
```

## 📊 What Gets Updated

### Stock Model Fields Added:
- **logo_url**: Company logo image URL
- **fmp_grade**: FMP consensus grade (A+, A, B+, etc.)
- **fmp_score**: Numerical score from FMP
- **analyst_target_price**: Average analyst target price
- **analyst_rating_strong_buy**: Number of strong buy ratings
- **analyst_rating_buy**: Number of buy ratings  
- **analyst_rating_hold**: Number of hold ratings
- **analyst_rating_sell**: Number of sell ratings
- **analyst_rating_strong_sell**: Number of strong sell ratings

### Portfolio Display Enhancements:
- 🖼️ Company logos (32x32px) with fallback to symbol initials
- 🏆 Color-coded grade badges (A=Green, B=Yellow, C/D=Red)
- 📈 Enhanced stock information display

## 🔧 API Service Usage

### Using the FMP Service in Code
```python
from soulstrader.fmp_service import FMPAPIService

# Initialize service
fmp_service = FMPAPIService()

# Search stocks
results = fmp_service.search_stocks("AAPL", limit=5)

# Get stock grade
grade_data = fmp_service.get_stock_grade("AAPL")

# Get company logo URL
logo_url = fmp_service.get_company_logo_url("AAPL")

# Update stock with FMP data
stock = Stock.objects.get(symbol="AAPL")
success = fmp_service.update_stock_with_fmp_data(stock)
```

## 📈 Grade to Recommendation Mapping

| FMP Grade | AI Recommendation | Confidence |
|-----------|------------------|------------|
| A+, A     | STRONG_BUY       | VERY_HIGH  |
| A-, B+    | BUY              | HIGH       |
| B, B-     | HOLD             | MEDIUM     |
| C+, C     | SELL             | HIGH       |
| C-, D, F  | STRONG_SELL      | VERY_HIGH  |

## 🎨 Portfolio Visual Enhancements

### Before Integration:
- Plain text stock symbols
- No visual indicators
- Basic table layout

### After Integration:
- 🖼️ Company logos for visual appeal
- 🏆 Color-coded grade badges
- 📊 Enhanced stock information
- 🎯 Professional appearance

## 🔍 Troubleshooting

### API Key Issues
```bash
# Test your API key
python test_fmp_integration.py
```

### No Logos Showing
- Check if `logo_url` field is populated in database
- Verify FMP API key is working
- Check browser console for image loading errors

### No Grades Available
- Run: `python manage.py update_fmp_data --all`
- Some stocks may not have FMP grade data
- Check FMP API rate limits (250/day for free tier)

### Permission Errors
```bash
# Make sure virtual environment is activated
source ~/Development/scratch/python/tutorial-env/bin/activate
```

## 📚 Available Endpoints

The FMP service integrates these key endpoints:

1. **Stock Search**: Find stocks by symbol/name
2. **Grades Consensus**: Get analyst grades and consensus
3. **Company Logos**: Retrieve company logo images
4. **Analyst Estimates**: Get analyst price targets
5. **Price Target Consensus**: Get consensus price targets

## 🚦 Rate Limits

- **Free Tier**: 250 calls/day, 10 calls/minute
- **Paid Tiers**: Higher limits available
- Rate limiting is automatically handled in the service

## 💡 Next Steps

1. **Add Your API Key** to settings.py or admin panel
2. **Run the Test Script** to verify everything works
3. **Update Stock Data** with FMP information
4. **Create Recommendations** based on FMP grades
5. **Check Your Portfolio** to see the enhanced display!

## 📞 Support

If you encounter issues:
1. Check the test script output
2. Verify your API key is valid
3. Check Django logs in `logs/soulstrader.log`
4. Ensure virtual environment is activated

---

**Happy Trading with Enhanced AI Advisor! 📈🤖**
