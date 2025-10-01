# SOULTRADER iOS App Development Guide 📱

## 🎯 Project Information

**Project Location**: `~/Development/CursorAI/iOS/SoulTrader`  
**Backend API**: `http://127.0.0.1:8000/api/`  
**Framework**: SwiftUI  
**Authentication**: JWT Bearer tokens  
**Target**: iOS 17.0+

---

## 📁 Recommended Project Structure

```
SoulTrader/
├── SoulTrader/
│   ├── App/
│   │   ├── SoulTraderApp.swift          # Main app entry point
│   │   └── ContentView.swift            # Root view with tab bar
│   │
│   ├── Models/
│   │   ├── Stock.swift                  # Stock model
│   │   ├── Holding.swift                # Portfolio holding model
│   │   ├── Trade.swift                  # Trade model
│   │   ├── SmartRecommendation.swift    # Smart analysis recommendation
│   │   └── User.swift                   # User model
│   │
│   ├── Services/
│   │   ├── APIService.swift             # API client
│   │   ├── AuthService.swift            # Authentication manager
│   │   └── CacheService.swift           # Offline cache (demo mode)
│   │
│   ├── ViewModels/
│   │   ├── PortfolioViewModel.swift     # Portfolio view logic
│   │   ├── TradesViewModel.swift        # Trades view logic
│   │   └── AnalysisViewModel.swift      # Analysis view logic
│   │
│   ├── Views/
│   │   ├── Authentication/
│   │   │   ├── LoginView.swift          # Login screen
│   │   │   └── DemoModeView.swift       # Demo mode toggle
│   │   │
│   │   ├── Portfolio/
│   │   │   ├── PortfolioView.swift      # Tab 1: Holdings
│   │   │   ├── HoldingRow.swift         # Individual holding cell
│   │   │   └── PortfolioSummaryCard.swift
│   │   │
│   │   ├── Trades/
│   │   │   ├── TradesView.swift         # Tab 2: Trade history
│   │   │   └── TradeRow.swift           # Individual trade cell
│   │   │
│   │   └── Analysis/
│   │       ├── AnalysisView.swift       # Tab 3: Smart analysis
│   │       ├── RecommendationRow.swift  # Individual recommendation
│   │       └── SessionSummaryCard.swift
│   │
│   └── Utilities/
│       ├── Constants.swift              # API endpoints, colors
│       └── Extensions.swift             # Helper extensions
```

---

## 🏗️ Step-by-Step Implementation

### **Phase 1: Models (Data Structures)**

Create these Swift structs to match your API responses:

#### **1. Stock.swift**
```swift
import Foundation

struct Stock: Codable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let name: String
    let logoUrl: String?
    let currentPrice: Decimal
    let previousClose: Decimal?
    let dayChange: Decimal?
    let dayChangePercent: Decimal?
    let fmpGrade: String?
    let currency: String
    let exchange: String?
    let sector: String?
    
    enum CodingKeys: String, CodingKey {
        case symbol, name
        case logoUrl = "logo_url"
        case currentPrice = "current_price"
        case previousClose = "previous_close"
        case dayChange = "day_change"
        case dayChangePercent = "day_change_percent"
        case fmpGrade = "fmp_grade"
        case currency, exchange, sector
    }
}
```

#### **2. Holding.swift**
```swift
import Foundation

struct Holding: Codable, Identifiable {
    let id: Int
    let stock: Stock
    let quantity: Int
    let averagePrice: Decimal
    let currentValue: Decimal
    let unrealizedPnl: Decimal
    let unrealizedPnlPercent: Decimal
    let purchaseDate: Date?
    let lastUpdated: Date?
    
    enum CodingKeys: String, CodingKey {
        case id, stock, quantity
        case averagePrice = "average_price"
        case currentValue = "current_value"
        case unrealizedPnl = "unrealized_pnl"
        case unrealizedPnlPercent = "unrealized_pnl_percent"
        case purchaseDate = "purchase_date"
        case lastUpdated = "last_updated"
    }
}
```

#### **3. Trade.swift**
```swift
import Foundation

struct Trade: Codable, Identifiable {
    let id: String
    let stock: Stock
    let tradeType: String
    let orderType: String
    let quantity: Int
    let price: Decimal?
    let averageFillPrice: Decimal?
    let totalAmount: Decimal
    let commission: Decimal
    let status: String
    let tradeSource: String
    let executedAt: Date?
    let createdAt: Date
    let notes: String?
    
    enum CodingKeys: String, CodingKey {
        case id, stock, quantity, price, commission, status, notes
        case tradeType = "trade_type"
        case orderType = "order_type"
        case averageFillPrice = "average_fill_price"
        case totalAmount = "total_amount"
        case tradeSource = "trade_source"
        case executedAt = "executed_at"
        case createdAt = "created_at"
    }
}
```

#### **4. SmartRecommendation.swift**
```swift
import Foundation

struct SmartRecommendation: Codable, Identifiable {
    let id: Int
    let stock: Stock
    let recommendationType: String
    let priorityScore: Decimal
    let confidenceScore: Decimal
    let sharesToBuy: Int?
    let cashAllocated: Decimal?
    let currentPrice: Decimal
    let targetPrice: Decimal?
    let stopLoss: Decimal?
    let reasoning: String
    let keyFactors: [String]
    let riskFactors: [String]
    let status: String
    let createdAt: Date
    let expiresAt: Date?
    
    enum CodingKeys: String, CodingKey {
        case id, stock, status, reasoning
        case recommendationType = "recommendation_type"
        case priorityScore = "priority_score"
        case confidenceScore = "confidence_score"
        case sharesToBuy = "shares_to_buy"
        case cashAllocated = "cash_allocated"
        case currentPrice = "current_price"
        case targetPrice = "target_price"
        case stopLoss = "stop_loss"
        case keyFactors = "key_factors"
        case riskFactors = "risk_factors"
        case createdAt = "created_at"
        case expiresAt = "expires_at"
    }
}
```

---

### **Phase 2: API Service**

#### **APIService.swift**
```swift
import Foundation

class APIService: ObservableObject {
    static let shared = APIService()
    
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    
    private let baseURL = "http://127.0.0.1:8000/api"
    private var accessToken: String? {
        didSet {
            isAuthenticated = accessToken != nil
        }
    }
    
    // MARK: - Authentication
    
    func login(username: String, password: String) async throws -> LoginResponse {
        let url = URL(string: "\(baseURL)/auth/login/")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["username": username, "password": password]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
        
        // Store token securely
        await MainActor.run {
            self.accessToken = loginResponse.access
            self.currentUser = loginResponse.user
        }
        
        return loginResponse
    }
    
    func logout() {
        accessToken = nil
        currentUser = nil
    }
    
    // MARK: - Portfolio API
    
    func getPortfolioHoldings() async throws -> PortfolioHoldingsResponse {
        return try await authenticatedRequest(
            endpoint: "/portfolio/holdings/",
            type: PortfolioHoldingsResponse.self
        )
    }
    
    // MARK: - Trades API
    
    func getRecentTrades(limit: Int = 20) async throws -> TradesResponse {
        return try await authenticatedRequest(
            endpoint: "/trades/recent/?limit=\(limit)",
            type: TradesResponse.self
        )
    }
    
    // MARK: - Analysis API
    
    func getSmartAnalysis() async throws -> SmartAnalysisResponse {
        return try await authenticatedRequest(
            endpoint: "/analysis/smart/",
            type: SmartAnalysisResponse.self
        )
    }
    
    // MARK: - Helper Methods
    
    private func authenticatedRequest<T: Decodable>(
        endpoint: String,
        type: T.Type
    ) async throws -> T {
        guard let token = accessToken else {
            throw APIError.notAuthenticated
        }
        
        let url = URL(string: "\(baseURL)\(endpoint)")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw APIError.serverError("HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0)")
        }
        
        return try JSONDecoder().decode(T.self, from: data)
    }
}

// MARK: - Error Types

enum APIError: LocalizedError {
    case notAuthenticated
    case invalidResponse
    case serverError(String)
    
    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "Not authenticated. Please login."
        case .invalidResponse:
            return "Invalid server response"
        case .serverError(let message):
            return "Server error: \(message)"
        }
    }
}

// MARK: - Response Models

struct LoginResponse: Codable {
    let access: String
    let refresh: String
    let user: User
}

struct PortfolioHoldingsResponse: Codable {
    let portfolioSummary: PortfolioSummary
    let holdings: [Holding]
    
    enum CodingKeys: String, CodingKey {
        case portfolioSummary = "portfolio_summary"
        case holdings
    }
}

struct PortfolioSummary: Codable {
    let totalValue: Decimal
    let availableCash: Decimal
    let totalInvested: Decimal
    let totalCurrentValue: Decimal
    let totalUnrealizedPnl: Decimal
    let totalUnrealizedPnlPercent: Decimal
    let holdingsCount: Int
    
    enum CodingKeys: String, CodingKey {
        case totalValue = "total_value"
        case availableCash = "available_cash"
        case totalInvested = "total_invested"
        case totalCurrentValue = "total_current_value"
        case totalUnrealizedPnl = "total_unrealized_pnl"
        case totalUnrealizedPnlPercent = "total_unrealized_pnl_percent"
        case holdingsCount = "holdings_count"
    }
}

struct TradesResponse: Codable {
    let count: Int
    let results: [Trade]
}

struct SmartAnalysisResponse: Codable {
    let latestSession: AnalysisSession?
    let recommendations: [SmartRecommendation]
    
    enum CodingKeys: String, CodingKey {
        case latestSession = "latest_session"
        case recommendations
    }
}

struct AnalysisSession: Codable, Identifiable {
    let id: Int
    let status: String
    let startedAt: Date
    let completedAt: Date?
    let processingTimeSeconds: Double?
    let totalRecommendations: Int
    let executedRecommendations: Int
    
    enum CodingKeys: String, CodingKey {
        case id, status
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case processingTimeSeconds = "processing_time_seconds"
        case totalRecommendations = "total_recommendations"
        case executedRecommendations = "executed_recommendations"
    }
}
```

---

### **Phase 3: Tab Bar Setup**

#### **ContentView.swift** (Main Tab Bar)
```swift
import SwiftUI

struct ContentView: View {
    @StateObject private var apiService = APIService.shared
    @State private var selectedTab = 0
    
    var body: some View {
        if apiService.isAuthenticated {
            TabView(selection: $selectedTab) {
                // Tab 1: Portfolio
                PortfolioView()
                    .tabItem {
                        Label("Portfolio", systemImage: "chart.pie.fill")
                    }
                    .tag(0)
                
                // Tab 2: Trades
                TradesView()
                    .tabItem {
                        Label("Trades", systemImage: "arrow.left.arrow.right")
                    }
                    .tag(1)
                
                // Tab 3: Analysis
                AnalysisView()
                    .tabItem {
                        Label("Analysis", systemImage: "brain.head.profile")
                    }
                    .tag(2)
            }
            .accentColor(.purple)
        } else {
            LoginView()
        }
    }
}
```

---

### **Phase 4: View Implementation**

#### **Tab 1: PortfolioView.swift**
```swift
import SwiftUI

struct PortfolioView: View {
    @StateObject private var viewModel = PortfolioViewModel()
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // Portfolio Summary Card
                    if let summary = viewModel.portfolioSummary {
                        PortfolioSummaryCard(summary: summary)
                    }
                    
                    // Holdings List
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Holdings")
                            .font(.headline)
                            .padding(.horizontal)
                        
                        ForEach(viewModel.holdings) { holding in
                            HoldingRow(holding: holding)
                        }
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Portfolio")
            .refreshable {
                await viewModel.loadData()
            }
            .task {
                await viewModel.loadData()
            }
        }
    }
}

// MARK: - Portfolio Summary Card

struct PortfolioSummaryCard: View {
    let summary: PortfolioSummary
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Total Value")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("$\(summary.totalValue, specifier: "%.2f")")
                        .font(.title)
                        .fontWeight(.bold)
                }
                Spacer()
                VStack(alignment: .trailing) {
                    Text("P&L")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("$\(summary.totalUnrealizedPnl, specifier: "%.2f")")
                        .font(.title3)
                        .fontWeight(.semibold)
                        .foregroundColor(summary.totalUnrealizedPnl >= 0 ? .green : .red)
                }
            }
            
            HStack {
                InfoItem(label: "Cash", value: "$\(summary.availableCash, specifier: "%.2f")")
                Spacer()
                InfoItem(label: "Invested", value: "$\(summary.totalInvested, specifier: "%.2f")")
                Spacer()
                InfoItem(label: "Holdings", value: "\(summary.holdingsCount)")
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(radius: 2)
        .padding(.horizontal)
    }
}

struct InfoItem: View {
    let label: String
    let value: String
    
    var body: some View {
        VStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
        }
    }
}

// MARK: - Holding Row

struct HoldingRow: View {
    let holding: Holding
    
    var body: some View {
        HStack(spacing: 12) {
            // Stock logo (placeholder for now)
            Circle()
                .fill(Color.purple.opacity(0.2))
                .frame(width: 40, height: 40)
                .overlay(
                    Text(holding.stock.symbol.prefix(2))
                        .font(.caption)
                        .fontWeight(.bold)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text(holding.stock.symbol)
                    .font(.headline)
                Text("\(holding.quantity) shares")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 4) {
                Text("$\(holding.currentValue, specifier: "%.2f")")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text("\(holding.unrealizedPnlPercent >= 0 ? "+" : "")\(holding.unrealizedPnlPercent, specifier: "%.2f")%")
                    .font(.caption)
                    .foregroundColor(holding.unrealizedPnlPercent >= 0 ? .green : .red)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(8)
        .shadow(radius: 1)
        .padding(.horizontal)
    }
}
```

#### **Tab 2: TradesView.swift**
```swift
import SwiftUI

struct TradesView: View {
    @StateObject private var viewModel = TradesViewModel()
    
    var body: some View {
        NavigationView {
            List(viewModel.trades) { trade in
                TradeRow(trade: trade)
            }
            .navigationTitle("Trades")
            .refreshable {
                await viewModel.loadData()
            }
            .task {
                await viewModel.loadData()
            }
        }
    }
}

// MARK: - Trade Row

struct TradeRow: View {
    let trade: Trade
    
    var body: some View {
        HStack {
            // Trade type indicator
            Circle()
                .fill(trade.tradeType == "BUY" ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(trade.stock.symbol)
                    .font(.headline)
                HStack {
                    Text(trade.tradeType)
                        .font(.caption)
                        .foregroundColor(trade.tradeType == "BUY" ? .green : .red)
                    Text("•")
                        .foregroundColor(.secondary)
                    Text("\(trade.quantity) shares")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 4) {
                Text("$\(trade.totalAmount, specifier: "%.2f")")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                if let date = trade.executedAt {
                    Text(date, style: .date)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }
}
```

#### **Tab 3: AnalysisView.swift**
```swift
import SwiftUI

struct AnalysisView: View {
    @StateObject private var viewModel = AnalysisViewModel()
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // Session Summary
                    if let session = viewModel.session {
                        SessionSummaryCard(session: session)
                    }
                    
                    // Recommendations
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Recommendations")
                            .font(.headline)
                            .padding(.horizontal)
                        
                        ForEach(viewModel.recommendations) { rec in
                            RecommendationRow(recommendation: rec)
                        }
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Smart Analysis")
            .refreshable {
                await viewModel.loadData()
            }
            .task {
                await viewModel.loadData()
            }
        }
    }
}

// MARK: - Recommendation Row

struct RecommendationRow: View {
    let recommendation: SmartRecommendation
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(recommendation.stock.symbol)
                    .font(.headline)
                Spacer()
                Text(recommendation.recommendationType)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.green)
                    .cornerRadius(4)
            }
            
            HStack {
                VStack(alignment: .leading) {
                    Text("Shares: \(recommendation.sharesToBuy ?? 0)")
                        .font(.caption)
                    Text("Priority: \(recommendation.priorityScore, specifier: "%.2f")")
                        .font(.caption)
                }
                Spacer()
                VStack(alignment: .trailing) {
                    Text("$\(recommendation.cashAllocated ?? 0, specifier: "%.2f")")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Text("Confidence: \(recommendation.confidenceScore, specifier: "%.2f")")
                        .font(.caption)
                }
            }
            .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(8)
        .shadow(radius: 1)
        .padding(.horizontal)
    }
}
```

---

### **Phase 5: ViewModels**

#### **PortfolioViewModel.swift**
```swift
import Foundation

@MainActor
class PortfolioViewModel: ObservableObject {
    @Published var holdings: [Holding] = []
    @Published var portfolioSummary: PortfolioSummary?
    @Published var isLoading = false
    @Published var error: String?
    
    func loadData() async {
        isLoading = true
        error = nil
        
        do {
            let response = try await APIService.shared.getPortfolioHoldings()
            self.portfolioSummary = response.portfolioSummary
            self.holdings = response.holdings
        } catch {
            self.error = error.localizedDescription
        }
        
        isLoading = false
    }
}
```

---

## 🎨 Demo Mode Implementation

### **DemoService.swift**
```swift
import Foundation

class DemoService {
    static let shared = DemoService()
    
    func getSamplePortfolio() -> PortfolioHoldingsResponse {
        // Return cached/sample data for demo mode
        let sampleSummary = PortfolioSummary(
            totalValue: 100989.30,
            availableCash: 149.30,
            totalInvested: 100840.00,
            totalCurrentValue: 105963.45,
            totalUnrealizedPnl: 5123.45,
            totalUnrealizedPnlPercent: 5.08,
            holdingsCount: 11
        )
        
        let sampleHoldings: [Holding] = [] // Add sample data
        
        return PortfolioHoldingsResponse(
            portfolioSummary: sampleSummary,
            holdings: sampleHoldings
        )
    }
}
```

---

## 🧪 Testing Checklist

### ✅ API Endpoints (All Working)
- [x] POST /api/auth/login/ - Tested with user1
- [x] GET /api/portfolio/holdings/
- [x] GET /api/trades/recent/
- [x] GET /api/analysis/smart/

### ⬜ iOS App (To Build)
- [ ] Models created
- [ ] API Service implemented
- [ ] Portfolio View (Tab 1)
- [ ] Trades View (Tab 2)
- [ ] Analysis View (Tab 3)
- [ ] Tab bar navigation
- [ ] Pull-to-refresh
- [ ] Demo mode

---

## 🚀 Next Steps

1. **Create Models** - Copy Stock, Holding, Trade, SmartRecommendation models to iOS
2. **Build APIService** - Implement the API client with JWT authentication
3. **Create ViewModels** - PortfolioViewModel, TradesViewModel, AnalysisViewModel
4. **Build Views** - Three tab views with UI matching Django web app
5. **Test with Live Data** - Connect to your running Django server
6. **Add Demo Mode** - Implement offline caching for demos

---

**API Status**: ✅ Fully Functional  
**Tested With**: user1  
**iOS Project**: ~/Development/CursorAI/iOS/SoulTrader  
**Ready For**: SwiftUI development

