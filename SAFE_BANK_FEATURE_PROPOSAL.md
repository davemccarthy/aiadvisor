# 🏦 SAFE/BANK Feature + Velocity-Based Profit-Taking

## 🎯 Vision

Create an intelligent cash management system that:
1. **Automatically takes profits** from volatile/spikey stocks
2. **Ring-fences profits** in a protected "SAFE" account
3. **Deploys capital strategically** during market downturns
4. **Protects against volatility** while maintaining upside exposure

---

## 💡 The Complete System

### Part 1: Velocity-Based Profit-Taking (Feeder)
**Identifies and captures gains from volatile stocks**

### Part 2: SAFE/BANK Account (Reserve)
**Stores profits safely for future opportunities**

### Part 3: Strategic Deployment (Opportunistic)
**Uses SAFE funds when markets present opportunities**

---

## 📊 Part 1: Velocity-Based Profit-Taking

### The Problem We're Solving
- **COCH example:** +2.15% one day, -41.51% the next
- Need to detect **abnormal momentum** not just total gain
- Traditional profit-taking misses these spikes

### The Solution: Gain Velocity Detection

```python
class VelocityProfitTaking:
    """
    Detects abnormal price spikes and takes profits automatically.
    Protects against sudden reversals like COCH's 41% drop.
    """
    
    def detect_spike(self, holding):
        # Calculate recent gain velocity
        recent_days = 5  # Configurable: 1, 3, 5, 7 days
        recent_gain = (current_price - price_N_days_ago) / price_N_days_ago
        recent_velocity = recent_gain / recent_days
        
        # Calculate normal velocity since purchase
        total_gain = (current_price - purchase_price) / purchase_price
        days_held = (today - purchase_date).days
        normal_velocity = total_gain / days_held if days_held > 0 else 0
        
        # Detect spike: recent velocity >> normal velocity
        velocity_ratio = recent_velocity / normal_velocity if normal_velocity > 0 else float('inf')
        
        # Trigger conditions
        if recent_gain >= spike_threshold (e.g., 5-10% in 5 days):
            if velocity_ratio > multiplier (e.g., 2x-3x normal):
                return SPIKE_DETECTED
```

### Configuration Settings
```python
# In RiskProfile model
velocity_profit_taking_enabled = True/False
spike_detection_days = 5  # Look at last N days
spike_threshold = 10.0    # Min % gain to consider
velocity_multiplier = 2.0  # Recent velocity must be 2x normal
partial_sell_percentage = 50.0  # Sell 50% of position on spike
```

### Examples

**Example 1: COCH Spike (Would Have Caught It!)**
```
Purchase: $1.59 (30 days ago)
Yesterday: $1.62 (+1.9% from purchase)
Normal velocity: 1.9% / 30 days = 0.063% per day

Recent: $1.59 → $1.62 in 1 day = +1.9%
Recent velocity: 1.9% per day

Ratio: 1.9% / 0.063% = 30x normal velocity!
Action: SELL 50% (or configurable %) → Proceeds to SAFE
```

**Example 2: Steady Growth (No Trigger)**
```
Purchase: $100 (60 days ago)
Current: $115 (+15% gain)
Normal velocity: 15% / 60 days = 0.25% per day

Recent 5 days: $113 → $115 = +1.8%
Recent velocity: 0.36% per day

Ratio: 0.36% / 0.25% = 1.4x normal (below 2x threshold)
Action: HOLD (steady growth, not a spike)
```

---

## 🏦 Part 2: SAFE/BANK Account

### Concept
A protected cash reserve within the portfolio that:
- **Receives profits** from velocity-based selling
- **Cannot be touched** by normal buy algorithms
- **Only deployed** when strategic conditions met
- **Compounds over time** as a safety net

### Database Schema

```python
class Portfolio(models.Model):
    # Existing fields
    current_capital = models.DecimalField()  # Active trading capital
    
    # NEW: SAFE Account
    safe_balance = models.DecimalField(
        default=Decimal('0.00'),
        help_text="Protected reserve from profit-taking"
    )
    safe_enabled = models.BooleanField(
        default=False,
        help_text="Enable SAFE account functionality"
    )
    safe_allocation_percentage = models.DecimalField(
        default=Decimal('100.00'),
        help_text="% of profit-taking proceeds that go to SAFE (vs regular cash)"
    )
    
    @property
    def total_cash(self):
        """Total liquid capital"""
        return self.current_capital + self.safe_balance
    
    @property
    def safe_percentage(self):
        """What % of portfolio is in SAFE"""
        return (self.safe_balance / self.total_value) * 100


class RiskProfile(models.Model):
    # NEW: SAFE Deployment Rules
    safe_deployment_enabled = models.BooleanField(default=True)
    safe_deployment_trigger = models.CharField(
        choices=[
            ('MARKET_DROP', 'Market drops X%'),
            ('PORTFOLIO_DROP', 'Portfolio drops X%'),
            ('MANUAL', 'Manual deployment only'),
            ('SMART_OPPORTUNITIES', 'AI detects opportunities'),
        ],
        default='MARKET_DROP'
    )
    safe_deployment_threshold = models.DecimalField(
        default=Decimal('10.00'),
        help_text="Market/portfolio drop % to trigger deployment"
    )
    safe_deployment_percentage = models.DecimalField(
        default=Decimal('25.00'),
        help_text="% of SAFE to deploy per trigger event"
    )
```

### Transaction Flow

```python
class SAFETransaction(models.Model):
    """Track all SAFE account movements"""
    portfolio = models.ForeignKey(Portfolio)
    transaction_type = models.CharField(
        choices=[
            ('DEPOSIT', 'Profit-taking deposit'),
            ('WITHDRAWAL', 'Strategic deployment'),
            ('TRANSFER', 'Manual transfer'),
        ]
    )
    amount = models.DecimalField()
    source_holding = models.ForeignKey(Holding, null=True)  # If from profit-taking
    reason = models.TextField()  # Why was this triggered?
    created_at = models.DateTimeField(auto_now_add=True)
```

### Visual Display

```
Portfolio Overview:
├── Active Trading Capital: $20,000
├── 🏦 SAFE Balance: $5,000 (20% of portfolio)
└── Total Cash: $25,000

Holdings: $75,000
Total Portfolio Value: $100,000

SAFE History:
- Oct 9: +$863 from COCH velocity profit-taking
- Oct 8: +$450 from RGTI spike detection
- Oct 5: -$2,000 deployed during market dip
```

---

## 🎯 Part 3: Strategic Deployment

### Deployment Triggers

**1. Market Drop Detection**
```python
# S&P 500 drops 10% from recent high
if sp500_current < (sp500_high_30d * 0.90):
    deploy_safe_funds(percentage=25)
```

**2. Portfolio Drop Detection**
```python
# User's portfolio drops 8% from recent high
if portfolio_value < (portfolio_high_7d * 0.92):
    deploy_safe_funds(percentage=25)
```

**3. Smart Opportunities (Advanced)**
```python
# AI detects oversold conditions + high-quality BUY signals
if consensus_strong_buys >= 3 and market_sentiment == 'oversold':
    deploy_safe_funds(percentage=50)
```

**4. Manual Override**
```python
# User manually deploys SAFE funds
# Useful when user sees opportunity
```

### Deployment Algorithm

```python
def deploy_safe_funds(portfolio, percentage, reason):
    """
    Move funds from SAFE to active trading capital.
    These funds are then available for the buy algorithm.
    """
    amount_to_deploy = portfolio.safe_balance * (percentage / 100)
    
    # Transfer from SAFE to active capital
    portfolio.safe_balance -= amount_to_deploy
    portfolio.current_capital += amount_to_deploy
    portfolio.save()
    
    # Log transaction
    SAFETransaction.objects.create(
        portfolio=portfolio,
        transaction_type='WITHDRAWAL',
        amount=amount_to_deploy,
        reason=reason
    )
    
    # Run smart analysis with boosted capital
    SmartAnalysisService.analyze_portfolio(portfolio.user)
```

---

## 🔄 Complete Workflow Example

### Scenario: Bull Market → Correction → Recovery

**Phase 1: Bull Market (Building SAFE)**
```
Day 1:  Portfolio = $100k (Cash: $10k, Holdings: $90k, SAFE: $0)
Day 5:  NVDA spikes +12% in 3 days → Velocity detected
        Sell 50% of NVDA → +$3k to SAFE
        Portfolio = $103k (Cash: $10k, Holdings: $90k, SAFE: $3k)

Day 10: RGTI spikes +15% in 2 days → Velocity detected
        Sell 40% of RGTI → +$2k to SAFE
        Portfolio = $105k (Cash: $10k, Holdings: $90k, SAFE: $5k)

Day 15: SAFE has grown to $5k (5% of portfolio)
        Protected and ready for opportunities
```

**Phase 2: Market Correction (Deploy SAFE)**
```
Day 20: Market drops 12% from recent high
        Trigger: Deploy 25% of SAFE
        Move $1,250 from SAFE to active capital
        Portfolio = $95k (Cash: $11.25k, Holdings: $79k, SAFE: $3.75k)
        
        Smart Analysis runs with boosted cash
        Buys quality stocks at discount prices
```

**Phase 3: Recovery (Rebuild SAFE)**
```
Day 30: Market recovers
        New positions from correction are up
        Velocity detection catches spikes again
        SAFE begins rebuilding for next opportunity
```

---

## 📊 Benefits

### 1. **Risk Management**
- Automatically captures profits before reversals
- Ring-fences gains from volatile trading
- Always has dry powder for opportunities

### 2. **Psychological Benefits**
- Removes emotion from profit-taking
- "Banking" profits feels good
- Reduces FOMO (kept some exposure)

### 3. **Strategic Advantage**
- Buy quality stocks when others are scared
- Dollar-cost average on the way up (via profit-taking)
- Deploy capital when sentiment is worst

### 4. **Compound Growth**
- SAFE grows from multiple small wins
- Protected from daily trading losses
- Becomes larger reserve over time

---

## 🛠️ Implementation Phases

### Phase 1: Velocity-Based Profit-Taking ✓
- [ ] Add historical price tracking
- [ ] Implement velocity detection algorithm
- [ ] Add RiskProfile settings
- [ ] Integrate with Smart Analysis
- [ ] Test with historical data

### Phase 2: SAFE Account ✓
- [ ] Add SAFE fields to Portfolio model
- [ ] Create SAFETransaction model
- [ ] Build transaction tracking
- [ ] Update UI to show SAFE balance
- [ ] Create SAFE history view

### Phase 3: Deployment Logic ✓
- [ ] Implement market drop detection
- [ ] Implement portfolio drop detection
- [ ] Create deployment algorithm
- [ ] Add manual deployment controls
- [ ] Build deployment notifications

### Phase 4: Advanced Features ✓
- [ ] AI-based opportunity detection
- [ ] Smart deployment optimization
- [ ] SAFE performance analytics
- [ ] Historical simulation/backtesting

---

## 🎨 UI Mockups

### Portfolio Page - SAFE Section
```
┌─────────────────────────────────────────────────┐
│ 💰 Cash Management                              │
├─────────────────────────────────────────────────┤
│ Active Trading Capital:      $20,000.00         │
│ 🏦 SAFE Reserve:             $5,000.00 (20%)    │
│ ├─ Available for deployment                     │
│ └─ [Deploy 25%] [Deploy 50%] [Deploy All]       │
│                                                  │
│ Total Liquid:                $25,000.00         │
│                                                  │
│ Recent SAFE Activity:                            │
│ ✓ +$863.00 from COCH (velocity detected)        │
│ ✓ +$450.00 from RGTI (spike detected)           │
│ ✓ -$2,000.00 deployed (market drop 10%)         │
└─────────────────────────────────────────────────┘
```

### Settings Page - SAFE Configuration
```
┌─────────────────────────────────────────────────┐
│ 🏦 SAFE Account Settings                        │
├─────────────────────────────────────────────────┤
│ ☑ Enable SAFE Account                           │
│                                                  │
│ Profit-Taking → SAFE:         [100%] ▼          │
│ (What % of profits go to SAFE vs active cash)   │
│                                                  │
│ Deployment Trigger:   [Market Drop 10%] ▼       │
│ Deployment Amount:    [25% per trigger] ▼       │
│                                                  │
│ Velocity Detection:                              │
│ ☑ Spike Detection Days:       [5 days] ▼        │
│ ☑ Spike Threshold:            [10%] ▼           │
│ ☑ Velocity Multiplier:        [2.0x] ▼          │
│ ☑ Partial Sell %:             [50%] ▼           │
└─────────────────────────────────────────────────┘
```

---

## 🔮 Future Enhancements

1. **SAFE Goals**: Set target SAFE percentage (e.g., 15% of portfolio)
2. **Tiered Deployment**: Different triggers for 25%, 50%, 75% deployment
3. **SAFE Interest**: Integrate with money market funds for yield
4. **Tax Optimization**: Track short-term vs long-term gains in SAFE
5. **Multi-Account**: Separate SAFE accounts for different strategies
6. **Alert System**: Notify when SAFE reaches milestones or deployment triggers

---

## 📈 Expected Outcomes

### Conservative Scenario (1 year)
- 10-15 velocity profit-taking events
- SAFE grows to 8-12% of portfolio
- 2-3 strategic deployments during corrections
- **Result:** Smoother returns, reduced drawdowns

### Aggressive Scenario (1 year)
- 20-30 velocity profit-taking events
- SAFE grows to 15-20% of portfolio
- 4-6 strategic deployments
- **Result:** Significant outperformance during volatile markets

---

## ✅ Next Steps

1. **Review and approve** this proposal
2. **Prioritize implementation** phases
3. **Design database schema** changes
4. **Create migration plan** for existing users
5. **Build and test** velocity detection first
6. **Iterate on SAFE deployment** logic

---

**Status:** 📋 Proposal - Awaiting Implementation Decision  
**Priority:** 🔥 High - Addresses real pain point (COCH -41% drop)  
**Complexity:** 🟡 Medium - Requires careful design but straightforward implementation  
**Impact:** 🚀 High - Game-changing risk management feature

---

*This feature transforms SOULTRADER from a recommendation system into a complete risk-managed trading platform.*

