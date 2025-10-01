# SOULTRADER REST API Documentation 📱

## 🎯 Overview

This REST API provides access to SOULTRADER portfolio, trading, and analysis data for mobile and external clients. Built with Django REST Framework and JWT authentication.

**Base URL**: `http://127.0.0.1:8000/api/` (development)  
**Authentication**: JWT Bearer tokens  
**Response Format**: JSON

---

## 🔐 Authentication

### Login
Get JWT access and refresh tokens.

**Endpoint**: `POST /api/auth/login/`  
**Authentication**: None required  

**Request Body**:
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "profile": {
      "risk_level": "MODERATE",
      "investment_goal": "BALANCED",
      "time_horizon": "MEDIUM",
      "max_positions": 20,
      "esg_focused": false
    }
  }
}
```

**cURL Example**:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

---

### Refresh Token
Refresh an expired access token.

**Endpoint**: `POST /api/auth/refresh/`  
**Authentication**: None required  

**Request Body**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Get Current User
Get information about the authenticated user.

**Endpoint**: `GET /api/auth/user/`  
**Authentication**: Required (Bearer token)  

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User",
  "profile": {
    "risk_level": "MODERATE",
    "investment_goal": "BALANCED",
    "time_horizon": "MEDIUM",
    "max_positions": 20,
    "esg_focused": false
  }
}
```

**cURL Example**:
```bash
curl http://127.0.0.1:8000/api/auth/user/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📊 Portfolio Endpoints (iOS Tab 1)

### Get Portfolio Holdings
Get complete portfolio data including holdings and summary.

**Endpoint**: `GET /api/portfolio/holdings/`  
**Authentication**: Required (Bearer token)  

**Response** (200 OK):
```json
{
  "portfolio_summary": {
    "total_value": 100989.30,
    "available_cash": 149.30,
    "total_invested": 100840.00,
    "total_current_value": 105963.45,
    "total_unrealized_pnl": 5123.45,
    "total_unrealized_pnl_percent": 5.08,
    "holdings_count": 11
  },
  "holdings": [
    {
      "id": 1,
      "stock": {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "logo_url": "/static/soulstrader/images/logos/MSFT.png",
        "current_price": 517.85,
        "previous_close": 514.60,
        "day_change": 3.25,
        "day_change_percent": 0.63,
        "fmp_grade": "A",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "TECHNOLOGY"
      },
      "quantity": 120,
      "average_price": 445.00,
      "current_value": 62142.00,
      "unrealized_pnl": 8742.00,
      "unrealized_pnl_percent": 16.34,
      "purchase_date": "2025-09-15T10:30:00Z",
      "last_updated": "2025-09-30T14:00:00Z"
    },
    {
      "id": 2,
      "stock": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "logo_url": "/static/soulstrader/images/logos/AAPL.png",
        "current_price": 254.43,
        "previous_close": 252.10,
        "day_change": 2.33,
        "day_change_percent": 0.92,
        "fmp_grade": "A-",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "TECHNOLOGY"
      },
      "quantity": 31,
      "average_price": 245.00,
      "current_value": 7887.33,
      "unrealized_pnl": 292.33,
      "unrealized_pnl_percent": 3.85,
      "purchase_date": "2025-09-15T11:00:00Z",
      "last_updated": "2025-09-30T14:00:00Z"
    }
  ]
}
```

**cURL Example**:
```bash
curl http://127.0.0.1:8000/api/portfolio/holdings/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**iOS Usage**:
- Display holdings in a List/TableView
- Show portfolio summary at the top
- Update with pull-to-refresh

---

### Get Portfolio Summary
Get portfolio summary without holdings data.

**Endpoint**: `GET /api/portfolio/summary/`  
**Authentication**: Required (Bearer token)  

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "testuser's Portfolio",
  "initial_capital": "100000.00",
  "current_capital": "149.30",
  "total_value": "100989.30",
  "total_invested": "100840.00",
  "total_return": "5123.45",
  "total_return_percent": "5.08",
  "holdings_count": 11,
  "created_at": "2025-09-01T10:00:00Z"
}
```

---

## 📈 Trades Endpoints (iOS Tab 2)

### Get Recent Trades
Get recent trade history (default 20).

**Endpoint**: `GET /api/trades/recent/`  
**Authentication**: Required (Bearer token)  
**Query Parameters**:
- `limit` (optional): Number of trades to return (default: 20)

**Response** (200 OK):
```json
{
  "count": 15,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "stock": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "logo_url": "/static/soulstrader/images/logos/AAPL.png",
        "current_price": 254.43,
        "fmp_grade": "A-",
        "currency": "USD"
      },
      "trade_type": "BUY",
      "order_type": "MARKET",
      "quantity": 31,
      "price": 245.00,
      "average_fill_price": 245.00,
      "total_amount": "7595.00",
      "commission": "0.00",
      "status": "FILLED",
      "trade_source": "MANUAL",
      "executed_at": "2025-09-15T10:30:00Z",
      "created_at": "2025-09-15T10:30:00Z",
      "notes": "Initial purchase"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "stock": {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "logo_url": "/static/soulstrader/images/logos/MSFT.png",
        "current_price": 517.85,
        "fmp_grade": "A",
        "currency": "USD"
      },
      "trade_type": "BUY",
      "order_type": "MARKET",
      "quantity": 120,
      "price": 445.00,
      "average_fill_price": 445.00,
      "total_amount": "53400.00",
      "commission": "0.00",
      "status": "FILLED",
      "trade_source": "SMART_ANALYSIS",
      "executed_at": "2025-09-20T14:15:00Z",
      "created_at": "2025-09-20T14:15:00Z",
      "notes": "Smart Analysis recommendation"
    }
  ]
}
```

**cURL Example**:
```bash
# Get last 20 trades
curl http://127.0.0.1:8000/api/trades/recent/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Get last 50 trades
curl http://127.0.0.1:8000/api/trades/recent/?limit=50 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**iOS Usage**:
- Display trades in chronological order (newest first)
- Show BUY/SELL with color coding (green/red)
- Display status badges (FILLED, PENDING, etc.)

---

### Get All Trades (Paginated)
Get all trades with pagination support.

**Endpoint**: `GET /api/trades/`  
**Authentication**: Required (Bearer token)  
**Query Parameters**:
- `page` (optional): Page number (default: 1)

**Response** (200 OK):
```json
{
  "count": 125,
  "next": "http://127.0.0.1:8000/api/trades/?page=2",
  "previous": null,
  "results": [
    {
      "id": "...",
      "stock": {...},
      "trade_type": "BUY",
      ...
    }
  ]
}
```

---

## 🧠 Smart Analysis Endpoints (iOS Tab 3)

### Get Smart Analysis
Get latest smart analysis session and recommendations.

**Endpoint**: `GET /api/analysis/smart/`  
**Authentication**: Required (Bearer token)  

**Response** (200 OK):
```json
{
  "latest_session": {
    "id": 5,
    "status": "COMPLETED",
    "started_at": "2025-09-30T13:00:00Z",
    "completed_at": "2025-09-30T13:00:24Z",
    "processing_time_seconds": 24.39,
    "total_recommendations": 8,
    "executed_recommendations": 0,
    "portfolio_value": "100000.00",
    "available_cash": "100000.00",
    "total_cash_spend": "39916.40",
    "recommendations_summary": {
      "buy_recommendations": 8,
      "total_cash_allocated": 39916.40,
      "average_priority_score": 54.12,
      "average_confidence_score": 0.74
    }
  },
  "recommendations": [
    {
      "id": 1,
      "stock": {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "logo_url": "/static/soulstrader/images/logos/NVDA.png",
        "current_price": 181.85,
        "fmp_grade": "A+",
        "currency": "USD",
        "sector": "TECHNOLOGY"
      },
      "recommendation_type": "BUY",
      "priority_score": "71.59",
      "confidence_score": "0.82",
      "shares_to_buy": 36,
      "cash_allocated": "6546.60",
      "current_price": "181.85",
      "target_price": "200.00",
      "stop_loss": "170.00",
      "reasoning": "Strong momentum in AI sector with robust technical indicators...",
      "key_factors": [
        "AI sector leadership",
        "Strong Q3 earnings",
        "Technical breakout pattern"
      ],
      "risk_factors": [
        "High volatility",
        "Market correction risk"
      ],
      "status": "PENDING",
      "created_at": "2025-09-30T13:00:24Z",
      "expires_at": "2025-10-07T13:00:24Z"
    },
    {
      "id": 2,
      "stock": {
        "symbol": "DFLI",
        "name": "DFLI Corporation",
        "logo_url": "/static/soulstrader/images/logos/DFLI.png",
        "current_price": 0.66,
        "fmp_grade": null,
        "currency": "USD",
        "sector": "Unknown"
      },
      "recommendation_type": "BUY",
      "priority_score": "56.25",
      "confidence_score": "0.75",
      "shares_to_buy": 7873,
      "cash_allocated": "5196.18",
      "current_price": "0.66",
      "target_price": "0.85",
      "stop_loss": "0.50",
      "reasoning": "High growth potential in emerging market...",
      "key_factors": [
        "Top gainer",
        "High volume"
      ],
      "risk_factors": [
        "Penny stock volatility",
        "Limited fundamentals"
      ],
      "status": "PENDING",
      "created_at": "2025-09-30T13:00:24Z",
      "expires_at": "2025-10-07T13:00:24Z"
    }
  ]
}
```

**cURL Example**:
```bash
curl http://127.0.0.1:8000/api/analysis/smart/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**iOS Usage**:
- Display session status at top
- Show recommendations in order of priority_score
- Color code by recommendation_type (BUY=green)
- Show confidence as progress bar or stars

---

### Get Analysis Sessions
Get history of smart analysis sessions.

**Endpoint**: `GET /api/analysis/sessions/`  
**Authentication**: Required (Bearer token)  

**Response** (200 OK):
```json
{
  "count": 5,
  "results": [
    {
      "id": 5,
      "status": "COMPLETED",
      "started_at": "2025-09-30T13:00:00Z",
      "completed_at": "2025-09-30T13:00:24Z",
      "processing_time_seconds": 24.39,
      "total_recommendations": 8,
      "executed_recommendations": 0,
      "portfolio_value": "100000.00",
      "available_cash": "100000.00",
      "total_cash_spend": "39916.40",
      "recommendations_summary": {
        "buy_recommendations": 8,
        "average_priority_score": 54.12
      }
    }
  ]
}
```

---

## 🔧 Utility Endpoints

### Health Check
Check if API is responding.

**Endpoint**: `GET /api/health/`  
**Authentication**: Required (Bearer token)  

**Response** (200 OK):
```json
{
  "status": "healthy",
  "user": "testuser",
  "timestamp": "2025-09-30T14:30:00Z"
}
```

---

## 🍎 iOS Implementation Guide

### Swift API Service Setup

```swift
import Foundation

class SOULTRADERAPIService {
    static let shared = SOULTRADERAPIService()
    private let baseURL = "http://127.0.0.1:8000/api"
    
    private var accessToken: String?
    
    // MARK: - Authentication
    
    func login(username: String, password: String) async throws -> LoginResponse {
        let url = URL(string: "\(baseURL)/auth/login/")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["username": username, "password": password]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(LoginResponse.self, from: data)
        
        // Store token
        self.accessToken = response.access
        
        return response
    }
    
    // MARK: - Portfolio
    
    func getPortfolioHoldings() async throws -> PortfolioHoldingsResponse {
        guard let token = accessToken else {
            throw APIError.notAuthenticated
        }
        
        let url = URL(string: "\(baseURL)/portfolio/holdings/")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(PortfolioHoldingsResponse.self, from: data)
    }
    
    // MARK: - Trades
    
    func getRecentTrades(limit: Int = 20) async throws -> TradesResponse {
        guard let token = accessToken else {
            throw APIError.notAuthenticated
        }
        
        let url = URL(string: "\(baseURL)/trades/recent/?limit=\(limit)")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(TradesResponse.self, from: data)
    }
    
    // MARK: - Smart Analysis
    
    func getSmartAnalysis() async throws -> SmartAnalysisResponse {
        guard let token = accessToken else {
            throw APIError.notAuthenticated
        }
        
        let url = URL(string: "\(baseURL)/analysis/smart/")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(SmartAnalysisResponse.self, from: data)
    }
}

enum APIError: Error {
    case notAuthenticated
    case invalidResponse
    case serverError(String)
}
```

---

## 📱 iOS App Structure

### Tab 1: Portfolio View
```swift
struct PortfolioView: View {
    @StateObject private var viewModel = PortfolioViewModel()
    
    var body: some View {
        VStack {
            // Portfolio Summary Card
            PortfolioSummaryCard(summary: viewModel.summary)
            
            // Holdings List
            List(viewModel.holdings) { holding in
                HoldingRow(holding: holding)
            }
            .refreshable {
                await viewModel.refresh()
            }
        }
    }
}
```

### Tab 2: Trades View
```swift
struct TradesView: View {
    @StateObject private var viewModel = TradesViewModel()
    
    var body: some View {
        List(viewModel.trades) { trade in
            TradeRow(trade: trade)
        }
        .refreshable {
            await viewModel.refresh()
        }
    }
}
```

### Tab 3: Analysis View
```swift
struct AnalysisView: View {
    @StateObject private var viewModel = AnalysisViewModel()
    
    var body: some View {
        VStack {
            // Session Summary
            if let session = viewModel.session {
                SessionSummaryCard(session: session)
            }
            
            // Recommendations List
            List(viewModel.recommendations) { rec in
                RecommendationRow(recommendation: rec)
            }
            .refreshable {
                await viewModel.refresh()
            }
        }
    }
}
```

---

## 🎨 Demo Mode Implementation

### Strategy 1: Cached Data
```swift
class CacheService {
    static let shared = CacheService()
    
    func cachePortfolioData(_ data: PortfolioHoldingsResponse) {
        // Save to UserDefaults or CoreData
        if let encoded = try? JSONEncoder().encode(data) {
            UserDefaults.standard.set(encoded, forKey: "cached_portfolio")
        }
    }
    
    func getCachedPortfolioData() -> PortfolioHoldingsResponse? {
        guard let data = UserDefaults.standard.data(forKey: "cached_portfolio"),
              let decoded = try? JSONDecoder().decode(PortfolioHoldingsResponse.self, from: data) else {
            return nil
        }
        return decoded
    }
}
```

### App Launch Flow
```swift
struct ContentView: View {
    @State private var isDemo = false
    
    var body: some View {
        if isDemo {
            // Show cached/demo data
            MainTabView(mode: .demo)
        } else {
            // Show login screen
            LoginView()
        }
    }
}
```

---

## 🧪 Testing the API

### Test with cURL

**1. Login:**
```bash
TOKEN=$(curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}' \
  | jq -r '.access')

echo "Token: $TOKEN"
```

**2. Get Holdings:**
```bash
curl http://127.0.0.1:8000/api/portfolio/holdings/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

**3. Get Trades:**
```bash
curl http://127.0.0.1:8000/api/trades/recent/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

**4. Get Smart Analysis:**
```bash
curl http://127.0.0.1:8000/api/analysis/smart/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 📋 API Checklist

### ✅ Backend (Complete)
- [x] Django REST Framework installed
- [x] JWT authentication configured
- [x] Serializers created
- [x] API views created
- [x] URL routing configured
- [x] Tested with user1

### ⬜ iOS App (Next Steps)
- [ ] Create Xcode SwiftUI project
- [ ] Create data models matching API
- [ ] Build API service layer
- [ ] Implement authentication
- [ ] Build Portfolio view (Tab 1)
- [ ] Build Trades view (Tab 2)
- [ ] Build Analysis view (Tab 3)
- [ ] Add demo mode toggle
- [ ] Implement caching

---

## 🔑 Quick Reference

### Test Users
- **testuser** / password123 (active portfolio)
- **user1** / password (tested with API)
- **user2** / pass123 (clean slate)
- **user3** / testpass123 (aggressive risk)

### Key Endpoints for iOS
```
POST   /api/auth/login/           → Get token
GET    /api/portfolio/holdings/   → Tab 1 data
GET    /api/trades/recent/        → Tab 2 data
GET    /api/analysis/smart/       → Tab 3 data
```

### Authorization Header
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
```

---

**API Status**: ✅ Fully Functional  
**Last Tested**: September 30, 2025 with user1  
**Ready For**: iOS SwiftUI development  
**Next Step**: Create Xcode project

