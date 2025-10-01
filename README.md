# SOULTRADER - AI Stock Advisor Platform 🚀

A comprehensive fintech platform combining Django backend with iOS mobile app for intelligent stock portfolio management and AI-driven investment recommendations.

## 🏗️ Architecture

### Backend (Django)
- **API Server**: RESTful API with JWT authentication
- **Database**: SQLite with comprehensive trading models
- **AI Integration**: Multiple advisor services (FMP, Yahoo Finance, IEX Cloud)
- **Smart Analysis**: Automated portfolio analysis and recommendations
- **Market Data**: Real-time stock prices and company information

### Frontend (iOS App)
- **Native SwiftUI**: Professional mobile interface
- **Three Main Tabs**: Portfolio, Trades, Analysis
- **Demo Mode**: Complete offline functionality
- **Real-time Data**: Live integration with Django API
- **Professional UI**: Stock logos, charts, and responsive design

## 📱 iOS App Features

### Portfolio Management
- ✅ Real-time portfolio value and P&L
- ✅ Holdings with stock logos and performance metrics
- ✅ Pull-to-refresh functionality
- ✅ Professional summary cards

### Trade History
- ✅ Complete transaction records
- ✅ Buy/sell indicators with status
- ✅ Date stamps and commission tracking
- ✅ Searchable trade history

### AI Analysis
- ✅ Smart investment recommendations
- ✅ Confidence scores and reasoning
- ✅ Priority rankings and target prices
- ✅ Risk factor analysis

### Demo Mode
- ✅ Offline functionality with sample data
- ✅ Realistic portfolio simulation
- ✅ Complete feature demonstration
- ✅ No backend dependency required

## 🔧 Technical Stack

### Backend
- **Django 5.2.5** - Web framework
- **Django REST Framework** - API development
- **JWT Authentication** - Secure token-based auth
- **Financial Modeling Prep API** - Market data
- **SQLite** - Database

### iOS App
- **SwiftUI** - Modern iOS interface
- **Combine** - Reactive programming
- **URLSession** - Network requests
- **AsyncImage** - Image loading
- **iOS 17.0+** - Target deployment

## 🚀 Quick Start

### Backend Setup
```bash
cd /Users/davidmccarthy/Development/CursorAI/Django/aiadvisor
~/Development/scratch/python/tutorial-env/bin/python manage.py runserver 192.168.1.6:8000
```

### iOS App Setup
1. Open `~/Development/CursorAI/iOS/SoulTrader/SoulTrader.xcodeproj`
2. Build and run on iOS Simulator or device
3. Login with `user1`/`password123` for live data
4. Or use `demo`/`demo` for demo mode

## 📊 API Endpoints

### Authentication
- `POST /api/auth/login/` - User login with JWT tokens
- `GET /api/auth/user/` - Current user information

### Portfolio
- `GET /api/portfolio/holdings/` - Portfolio holdings and summary
- `GET /api/portfolio/summary/` - Portfolio summary only

### Trades
- `GET /api/trades/recent/` - Recent trade history
- `GET /api/trades/` - All trades with pagination

### Analysis
- `GET /api/analysis/smart/` - Smart analysis recommendations
- `GET /api/analysis/sessions/` - Analysis session history

## 🎯 Project Status

### ✅ Completed Features
- [x] Django API backend with JWT authentication
- [x] Complete iOS app with SwiftUI interface
- [x] Portfolio management and trade history
- [x] AI analysis and recommendations
- [x] Demo mode for offline testing
- [x] Professional UI with stock logos
- [x] Real-time data integration
- [x] Error handling and loading states

### 📱 iOS App Screenshots
- Portfolio view with holdings and P&L
- Trade history with transaction details
- AI analysis with recommendations
- Demo mode with sample data
- Professional login interface

## 🔗 Project Structure

```
aiadvisor/
├── api/                    # REST API endpoints
├── soulstrader/           # Django app with models and services
├── static/                # Static files (logos, images)
└── logs/                  # Application logs

iOS/SoulTrader/
├── Models/                # Swift data models
├── Services/              # API client and demo service
├── ViewModels/            # Business logic
├── Views/                 # SwiftUI interface
└── Utilities/             # Constants and helpers
```

## 📚 Documentation

- [API Documentation](./API_DOCUMENTATION.md) - Complete API reference
- [iOS Development Guide](./IOS_APP_GUIDE.md) - iOS app implementation
- [Demo Mode Guide](./DEMO_MODE_GUIDE.md) - Demo functionality

## 🎉 Success Metrics

- ✅ **Professional Quality**: App rivals commercial trading platforms
- ✅ **Complete Functionality**: All core features implemented
- ✅ **Mobile Optimized**: Responsive design for all screen sizes
- ✅ **Offline Capable**: Demo mode for presentations
- ✅ **Production Ready**: Error handling and performance optimized

---

**Built with ❤️ using Django, SwiftUI, and modern fintech APIs**
