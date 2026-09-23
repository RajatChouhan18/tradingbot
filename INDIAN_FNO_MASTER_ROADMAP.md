# The Complete Indian F&O (Futures & Options) Master Roadmap
### *A Quantitative & Practical Guide for Equity Traders Transitioning to Derivatives with < ₹50,000 Capital*

---

## Table of Contents
1. [Executive Summary & The Retail Reality Check](#1-executive-summary--the-retail-reality-check)
2. [Macro Architecture & SEBI Regulations (2024–2026 Framework)](#2-macro-architecture--sebi-regulations-20242026-framework)
3. [The 4-Phase Step-by-Step Learning Roadmap](#3-the-4-phase-step-by-step-learning-roadmap)
4. [Unheard but Crucial Institutional Concepts ("The Hidden Mechanics")](#4-unheard-but-crucial-institutional-concepts-the-hidden-mechanics)
5. [The Sub-₹50K Playbook: High-Probability Trading Systems](#5-the-sub-50k-playbook-high-probability-trading-systems)
6. [Mathematics of Account Survival: Fees, Slippage & Position Sizing](#6-mathematics-of-account-survival-fees-slippage--position-sizing)
7. [Comprehensive Free Online Resources & Tool Stack](#7-comprehensive-free-online-resources--tool-stack)
8. [Sensibull & TradingView Live Practice Blueprint](#8-sensibull--tradingview-live-practice-blueprint)

---

## 1. Executive Summary & The Retail Reality Check

Transitioning from Indian Cash/Equity (Delivery or Intraday stocks) to F&O is like shifting from driving a family sedan to piloting a fighter jet. 

### Key Structural Differences
| Dimension | Equity / Cash Market | F&O (Derivatives) |
| :--- | :--- | :--- |
| **Asset Type** | Ownership of real shares | Perishable legal contract |
| **Time Decay (Theta)** | Zero. You can hold for 10 years | Severe. Every second costs money |
| **Leverage** | 1x (Delivery) to 5x (MIS Intraday) | 10x to 50x notional leverage |
| **Market Nature** | Wealth creation (Non-zero sum) | Wealth transfer (Strictly zero-sum after fees) |
| **Primary Risk** | Stock drops in value | Contract value expires to ₹0.00 |

### SEBI Study Ground Truth (January 2023 & September 2024 Reports)
- **93% of individual retail F&O traders incurred net losses** over FY22–FY24.
- Average loss per trader: **₹1.25 Lakhs** (excluding transaction costs).
- Top 3 reasons for failure:
  1. **Overtrading OTM (Out-of-the-Money) Options:** Chasing ₹10–₹30 lottery tickets that expire worthless.
  2. **Transaction Drag (STT + Brokerage):** Making 10–20 trades a day on a small account, eroding 30%–50% of the capital purely in fees.
  3. **Lack of Defined-Risk Hedging:** Holding single-leg options overnight through gap-downs or IV crush.

*This roadmap is engineered to place you systematically in the top 7% by focusing on high-probability execution, defined-risk spreads, and mathematical risk management tailored for accounts below ₹50,000.*

---

## 2. Macro Architecture & SEBI Regulations (2024–2026 Framework)

To trade Indian derivatives today, you must master the regulatory landscape shaped by SEBI's recent measures to curb retail over-speculation:

### 1. The Single Weekly Expiry Rule
- **Previous System:** Every day of the week had an expiry (Nifty on Thursday, BankNifty on Wednesday, FinNifty on Tuesday, Midcap on Monday, Sensex on Friday).
- **Current System:** Exchanges are restricted to **one benchmark weekly expiry per exchange**.
  - **NSE:** Nifty 50 (Weekly Thursday).
  - **BSE:** Sensex (Weekly Friday).
  - *Impact:* Concentrates liquidity into primary indices, reducing scattered daily expiry gambling.

### 2. Upward Revision of Contract Lot Sizes
- Contract values were raised to ₹15 Lakhs – ₹20 Lakhs per lot to discourage under-capitalized retail betting.
  - **Nifty 50:** Lot size revised (e.g., 25 / 75 shares per lot depending on index recalibration cycles).
  - **Bank Nifty:** Revised lot sizes (e.g., 15 / 30).
  - *Capital Impact:* For Option Buyers, 1 lot of Nifty ATM (priced at ₹100) requires ₹2,500 – ₹7,500. For Option Sellers, naked shorting requires ₹1.1L – ₹1.4L per lot, but a **Hedged Debit Spread requires only ₹20,000 – ₹30,000**.

### 3. Revised Securities Transaction Tax (STT) Rates (Effective Oct 2024)
- **Futures:** STT increased from 0.0125% to **0.02%**.
- **Options Premium:** STT increased from 0.0625% to **0.1%** on option sales.
- *Trading Implication:* Quick scalping of tiny 1–2 point gains is mathematically dead due to breakeven slippage. You must target asymmetric R:R (minimum 1:2).

### 4. Physical Delivery vs. Cash Settlement
- **Index Options (Nifty, BankNifty, Sensex):** **100% Cash-settled.** If your option expires ITM, you receive cash credit. No risk of receiving actual shares.
- **Stock Options (Reliance, Tata Motors, etc.):** **Physical Delivery on Expiry.** If you hold an ITM stock option into Thursday expiry, you are legally obligated to take or give physical delivery of lakhs worth of shares! 
  > **Golden Rule for < ₹50K Capital:** **Never trade or hold stock options till expiry.** Stick 100% to **Index Options (Nifty/BankNifty)**.

---

## 3. The 4-Phase Step-by-Step Learning Roadmap

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Derivatives Architecture & The Core Physics (Greeks)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Derivatives Order Flow & Volatility Dynamics        │
│          (OI Chains, PCR, Max Pain, India VIX)              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: The Sub-₹50K Strategy Playbooks                     │
│          (Directional Momentum Buying & Low-Margin Spreads) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: Execution Engine, Sensibull Paper-Trading & Risk   │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 1: Derivatives Architecture & Core Physics

#### Topic 1.1: Futures vs. Options Mechanics
- **Futures Contract:** Linear payout. Symmetrical risk/reward. Mark-to-Market (MTM) settlement daily.
- **Option Contract:** Non-linear payout. Asymmetrical risk. Rights without obligations (Buyer) vs. Obligations with unlimited risk (Seller).
- **Moneyness:**
  - **ITM (In-The-Money):** Has Intrinsic Value + Extrinsic (Time) Value.
  - **ATM (At-The-Money):** Pure Extrinsic Value. Highest absolute time decay.
  - **OTM (Out-of-The-Money):** Zero Intrinsic Value. Pure lottery ticket value.

#### Topic 1.2: The Core Option Greeks
1. **Delta ($\Delta$):**
   - Spot change multiplier.
   - ATM $\Delta \approx 0.50$, ITM $\Delta \approx 0.65–0.85$, OTM $\Delta < 0.30$.
2. **Theta ($\Theta$):**
   - The non-linear daily decay rate.
   - Formula intuition: Decay follows the $\sqrt{\text{Time}}$ rule. Decay in the final 3 days before expiry is 400% faster than 20 days prior.
3. **Vega ($\mathcal{V}$):**
   - Sensitivity per 1% change in Implied Volatility (IV).
4. **Gamma ($\Gamma$):**
   - Rate of change of Delta. Explains explosive expiry day 0DTE surges and violent reversals.

---

### Phase 2: Order Flow, Volatility & Data Reading

#### Topic 2.1: Futures Open Interest (OI) Quadrants
Open Interest is the total number of outstanding active derivative contracts held by market participants.
```
Price UP   + OI UP   = LONG BUILDUP (Aggressive Institutional Buying)
Price DOWN + OI UP   = SHORT BUILDUP (Aggressive Institutional Shorting)
Price UP   + OI DOWN = SHORT COVERING (Temporary Bounce / Bears Exiting)
Price DOWN + OI DOWN = LONG UNWINDING (Weak Longs Exiting / Panic Selling)
```

#### Topic 2.2: Live Option Chain Deconstruction
- **Call OI Concentrations:** Act as Institutional **Resistance** (where Call Writers defend their strikes).
- **Put OI Concentrations:** Act as Institutional **Support** (where Put Writers defend their strikes).
- **Change in OI (Chg in OI):** Tracks intraday institutional positioning shifts. When Call OI suddenly unwinds intraday, a massive short-covering rally follows.
- **Put-Call Ratio (PCR):**
  $$\text{PCR} = \frac{\text{Total Put Open Interest}}{\text{Total Call Open Interest}}$$
  - $\text{PCR} > 1.3$: Overbought market / Strong Bullish sentiment (caution on extreme values $> 1.6$).
  - $\text{PCR} < 0.7$: Oversold market / Bearish sentiment (ripe for short-covering bounce).

#### Topic 2.3: India VIX & Implied Volatility (IV)
- **India VIX:** The 30-day annualized expected volatility of Nifty 50 computed by NSE based on Black & Scholes option bid-ask quotes.
- **Low VIX Environment (VIX 10–13):** Cheap premiums, sluggish ranges, frequent whipsaws for buyers.
- **Normal VIX Environment (VIX 13–17):** Best environment for directional momentum option buying.
- **High VIX Environment (VIX > 20):** Sky-high option premiums; prone to massive "IV Crush" after anticipated events pass.

---

### Phase 3: The Sub-₹50K Strategy Playbooks

#### Playbook A: Directional Intraday Option Buying (Momentum Breakout)
- **Core Principle:** Option buyers should only trade when there is **speed and expansion**, never in consolidation.
- **Selection:** Always buy **ATM (Delta 0.50)** or **1-Strike ITM (Delta 0.60)**. Never buy OTM.
- **Setup Trigger:** 15-Minute Opening Range Breakout (ORB) or Consolidation Squeeze confirmed by Volume + Futures Long/Short Buildup.
- **Execution Rules:**
  - **Stop Loss:** Max 15%–20% of the option premium (or technical SL on Nifty spot chart).
  - **Target:** Minimum 1:2 Risk-to-Reward (30%–40% premium gain).
  - **Time Stop:** If the market goes sideways for **20 minutes**, exit immediately regardless of P&L. (Do not let Theta bleed your trade).

#### Playbook B: Low-Margin Hedged Debit Spreads (Bull Call / Bear Put)
- **Why this beats Single-Leg Buying:**
  - In a Bull Call Spread, you buy an ATM Call and sell an OTM Call.
  - The sold OTM Call **funds** your bought Call, protects you from Theta decay, and cushions you against IV crush.
- **SEBI Margin Benefit Mechanics:**
  - Naked Short Call: Requires ~₹1,20,000 margin.
  - **Hedged Bull Call Spread:** Requires only **₹20,000 – ₹28,000** total margin because your maximum loss is strictly capped!
- **Payoff Profile:**
  - Risk is 100% defined.
  - Ideal for multi-day swing trades where overnight gap-downs would otherwise destroy a single-leg option buyer.

---

### Phase 4: Execution Engine & Account Scaling

#### Topic 4.1: The SEBI Margin Basket Order Sequence
- **The Critical Mistake:** If you enter the sell leg first in your terminal, the broker will reject your order with `"Insufficient Margin: Required ₹1,20,000"`.
- **The Rule:** In your broker's Basket Order (Zerodha / Dhan / Angel One):
  1. **Leg 1 (Buy Leg):** Place Buy order first.
  2. **Leg 2 (Sell Leg):** Place Sell order second.
  *The broker detects the hedge instantly and unlocks the reduced ₹25,000 margin requirement.*

#### Topic 4.2: Psychological Circuit Breakers
- The "Two-Loss Daily Rule": If you hit 2 stop-losses in a single day, shut down your terminal. Do not revenge trade.
- Trade journaling in Excel or Notion tracking: Setup name, Entry/Exit Delta, India VIX level, and emotional state.

---

## 4. Unheard but Crucial Institutional Concepts ("The Hidden Mechanics")

These are advanced derivatives dynamics that retail traders rarely encounter in free YouTube videos, but which dictate 80% of institutional profits:

### 1. Max Pain Theory (Strike Pinning)
- **The Concept:** Option Writers (institutions with hundreds of crores in capital) stand to lose the most money if the index closes far away from their sold strikes.
- **Mechanism:** As weekly Thursday expiry approaches (between 1:30 PM and 3:30 PM), the spot price gravitates toward the strike price where the cumulative payout to option buyers is at its absolute minimum ("Maximum Pain" point).
- **Application:** If Nifty is at 25,120 at 1:00 PM on Thursday, but the Max Pain is at 25,050 with massive 25,100 Call OI additions, the probability of an afternoon downward drift to pin at 25,050–25,100 is > 70%.

### 2. IV Skew & "Crashophobia"
- In Indian equities, **Out-of-the-Money Puts consistently trade at a higher Implied Volatility (IV) than equidistant Out-of-the-Money Calls.**
- **Why:** Markets drop much faster than they rise. Institutional portfolio managers continuously bid up OTM Puts to insure multi-thousand-crore stock portfolios against catastrophic crashes.
- **Practical Takeaway:** Buying OTM Puts is fundamentally more expensive than buying OTM Calls. When trading Bearish setups, buying Bear Put Spreads is far superior to buying naked Puts because you sell that overpriced high-IV Put leg!

### 3. IV Percentile (IVP) vs. IV Rank (IVR)
- **The Trap:** An equity trader looks at Nifty ATM IV of 14% and thinks *"14% is low."*
- **IV Rank (IVR):** Measures where the current IV sits relative to the 52-week High and Low:
  $$\text{IVR} = \frac{\text{Current IV} - \text{52-Week Low IV}}{\text{52-Week High IV} - \text{52-Week Low IV}} \times 100$$
- **Rule of Thumb:**
  - $\text{IVR} < 25$: Great for **Option Buyers** & **Debit Spreads** (volatility is cheap; expansion likely).
  - $\text{IVR} > 70$: Great for **Credit Spreads** (volatility is bloated; impending IV crush).

### 4. Second-Order Greeks: Vanna & Charm
- **Vanna ($\frac{\partial \Delta}{\partial \sigma}$):** How your Delta changes when Volatility (IV) changes.
  - When India VIX suddenly plunges, your option's Delta drops even if the market hasn't moved.
- **Charm ($\frac{\partial \Delta}{\partial t}$ - Delta Bleed):** How your Delta changes as time passes.
  - An OTM option's Delta naturally bleeds toward 0 every single night you hold it, demanding increasingly violent spot moves just to keep the option alive.

### 5. Pin Risk on Expiry Day
- When an index spot price closes right on your strike (e.g., you bought 25,000 Call and Nifty closes at 25,001 at 3:30 PM).
- In Stock Options, this triggers massive physical delivery margin penalties. In Index Options, it creates erratic automated reconciliation fees.
- **The Golden Habit:** Always close out all intraday positions before **3:15 PM**. Never let an option settle through the exchange's closing auction.

---

## 5. The Sub-₹50K Playbook: High-Probability Trading Systems

### System 1: The "9:30 AM Momentum Scalp" (Single-Leg ATM Buying)
- **Target Asset:** Nifty 50 Index.
- **Capital Required:** ₹5,000 – ₹8,000 per lot.
- **Market Conditions:** India VIX between 13 and 17.
- **Step 1:** Mark the High and Low of the first 15-minute candle (9:15 AM to 9:30 AM).
- **Step 2:** Check 5-minute VWAP (Volume Weighted Average Price) and Supertrend (10, 2).
- **Step 3:** 
  - If 5-minute candle closes above 15-min High + Spot is above VWAP + Nifty Futures shows *Long Buildup* $\rightarrow$ **Buy 1 Lot ATM Call (Delta 0.50)**.
  - If 5-minute candle closes below 15-min Low + Spot is below VWAP + Nifty Futures shows *Short Buildup* $\rightarrow$ **Buy 1 Lot ATM Put (Delta -0.50)**.
- **Trade Management:**
  - **Stop Loss:** 15% of premium (e.g., if bought at ₹100, hard SL at ₹85).
  - **Target 1:** 20% gain (move SL to Cost).
  - **Target 2:** 35%–40% gain (Full exit).
  - **Hard Time Exit:** 20 minutes maximum holding time.

---

### System 2: The "Hedged Trend Rider" (2-Leg Debit Spread)
- **Target Asset:** Nifty 50 Index (Tuesday or Wednesday entry for Thursday expiry).
- **Capital Required:** ₹22,000 – ₹28,000 total margin.
- **Setup:** Daily Trend Breakout with Rising Open Interest.
- **Execution (Bullish Example):**
  - Suppose Nifty Spot = 25,000.
  - **Leg 1:** Buy 1 Lot 25,000 Call @ ₹120 (Debit paid: ₹120).
  - **Leg 2:** Sell 1 Lot 25,200 Call @ ₹40 (Credit received: ₹40).
  - **Net Debit Paid:** $₹120 - ₹40 = ₹80$ points (Max Risk = $80 \times \text{Lot Size}$).
  - **Spread Width:** $25,200 - 25,000 = 200$ points.
  - **Max Reward:** $\text{Width} - \text{Net Debit} = 200 - 80 = 120$ points ($120 \times \text{Lot Size}$).
- **Why this protects small accounts:**
  - Max loss is capped at ₹80 even if Nifty crashes 1,000 points overnight.
  - Theta decay on your bought 25,000 CE is partially offset by the sold 25,200 CE.
  - You can sleep peacefully without overnight panic.

---

## 6. Mathematics of Account Survival: Fees, Slippage & Position Sizing

In an account under ₹50,000, **brokerage and taxes are your deadliest competitors.**

### The Friction Cost Breakdown (1 Lot Round-Trip Nifty Trade)
- **Brokerage (Zerodha / Groww / Angel):** ₹20 Buy + ₹20 Sell = **₹40**.
- **STT (Securities Transaction Tax):** 0.1% on sell premium.
- **Exchange Turnover Charges (NSE):** ~₹5–₹10.
- **GST (18% on Brokerage + Exchange charges):** ~₹9.
- **SEBI Turnover Charges & Stamp Duty:** ~₹2.
- **Slippage (Bid-Ask Spread):** ~0.5 to 1 point per execution = **₹25 – ₹50**.
- **Total Cost per Round-Trip:** $\approx \mathbf{₹90 - ₹120}$.

### The Small Account Danger Math
- If you execute **4 trades a day**:
  - $4 \times ₹100 = \text{₹400 per day in fees}$.
  - In 20 trading days: $20 \times ₹400 = \mathbf{₹8,000 \text{ per month}}$.
  - **That is 16% of your ₹50,000 capital destroyed every month purely by transaction friction!**

### The Survival Rules
1. **Trade Cap:** Maximum **2 trades per day**. Zero trades on choppy days.
2. **Per-Trade Risk Budget:** Max risk per trade = **2% of capital** ($₹1,000$ max risk on a ₹50,000 account).
3. **Lot Discipline:** **Strictly 1 Lot** until your account reaches ₹1,00,000 organically from trading profits. Never average down a losing option.

---

## 7. Comprehensive Free Online Resources & Tool Stack

You do **not** need to pay thousands of rupees for commercial courses or paid screener subscriptions. The entire Indian professional derivatives stack is available for free:

### 1. Conceptual Mastery & Documentation
- **Zerodha Varsity (Web & Mobile App - 100% Free):**
  - *Module 4:* Futures Trading.
  - *Module 5:* Options Theory for Professional Trading.
  - *Module 6:* Option Strategies.
  - *Link:* [zerodha.com/varsity](https://zerodha.com/varsity/)
- **NSE India Knowledge Hub:**
  - Official NSE derivatives manuals, historical contract specifications, and settlement formulas.
  - *Link:* [nseindia.com/learn/find-a-course](https://www.nseindia.com/)

### 2. Live Derivative Analytics & Strategy Builders
- **Sensibull (Free for Zerodha, Angel One, Upstox, and 5Paisa account holders):**
  - Free live Option Chain with real-time Greeks ($\Delta, \Theta, \mathcal{V}, \Gamma$).
  - Multi-Strike Open Interest (OI) charts to see where smart money is accumulating.
  - Free Strategy Builder with visual payoff diagrams and Max Profit / Max Loss calculations.
  - *Link:* [web.sensibull.com](https://web.sensibull.com/)
- **Opstra Options Strategy Builder (Definege - Free Tier):**
  - Excellent for plotting custom spreads, IV skew charts, and simulated Greeks profiles.
  - *Link:* [opstra.definedge.com](https://opstra.definedge.com/)
- **NSE Official Option Chain:**
  - The authoritative live feed for Nifty & BankNifty strike data, OI additions, and volume.
  - *Link:* [nseindia.com/option-chain](https://www.nseindia.com/option-chain)

### 3. Charting, Volume Profile & Order Flow
- **TradingView (Free Tier):**
  - Nifty 50, Bank Nifty Spot and Futures charts.
  - Indicators to apply: **VWAP (Volume Weighted Average Price)**, **Supertrend (10, 2)**, **RSI (14)**.
  - *Link:* [in.tradingview.com](https://in.tradingview.com/)
- **GoCharting (Free Indian NSE Data):**
  - Multi-pane charting, Market Profile, and Volume Footprint simulations.
  - *Link:* [gocharting.com](https://gocharting.com/)

### 4. Free Open Interest (OI) & Sector Flow Trackers
- **Trendlyne F&O Dashboard (Free Tier):**
  - Instant visualization of Long Buildup, Short Buildup, Long Unwinding, and Short Covering lists.
  - *Link:* [trendlyne.com/futures-options](https://trendlyne.com/)
- **Chartink (Free Custom Derivatives Screeners):**
  - User-built screeners for high-volume breakouts and PCR extremes.
  - *Link:* [chartink.com](https://chartink.com/)

### 5. Curated & Trustworthy YouTube Playlists (Zero-Hype Free Courses)
The Indian trading ecosystem is full of fake screenshots and course sellers. These channels provide verified, conflict-free, institutional-grade education:

1. **[Varsity by Zerodha](https://www.youtube.com/@VarsitybyZerodha) (Karthik Rangappa)**
   - *Key Playlists:* **Options Theory & Strategies (Modules 5 & 6)**, **Futures Trading Basics (Module 4)**.
   - *Why it's essential:* The cleanest, most authoritative foundation for Option Greeks, Moneyness (ITM/ATM/OTM), and Payoff Diagrams without commercial upselling.
2. **[Sensibull](https://www.youtube.com/@sensibull) (Abid Hassan - Co-Founder & Ex-IIM Pro Trader)**
   - *Key Playlists:* **Options Trading Masterclass for Beginners**, **Open Interest (OI) Demystified**, **Greeks & India VIX Dynamics**.
   - *Why it's essential:* Exposes the brutal reality of single-leg option buying, teaches hedged debit spreads with SEBI margin benefits, and explains how institutional market makers think.
3. **[Quantsapp](https://www.youtube.com/@Quantsapp) (Shubham Agarwal, CMT, CFA)**
   - *Key Playlists:* **Open Interest (OI) Decoded Masterclass**, **Max Pain & Strike Pinning Series**.
   - *Why it's essential:* Teaches you how to read institutional footprint data: Long Buildup vs. Short Covering, PCR extremes, and IV Percentile (IVP/IVR).
4. **[Power Of Stocks](https://www.youtube.com/@PowerOfStocks) (Subasish Pani)**
   - *Key Playlists:* **Option Buying Strategies & Price Action Breakouts**, **Risk Management Masterclass**.
   - *Why it's essential:* Tailored for < ₹50k traders wanting to trade intraday directional momentum with strict 1:2 R:R and 15-minute time exits.
5. **[Elearnmarkets - Face2Face Series](https://www.youtube.com/@Elearnmarkets) (Vivek Bajaj)**
   - *Key Episodes:* Sivakumar Jayachandran (Order flow & scalping), Premal Parekh (Adjustments & spread mechanics).
   - *Why it's essential:* Transparent interviews breaking down the real trading desks of verified, profitable derivatives traders.
6. **[Theta Gainers](https://www.youtube.com/@ThetaGainers) (Janak Patel)**
   - *Key Playlists:* **Non-Directional Option Selling Masterclass**, **Adjustment Blueprints for Challenged Spreads**.
   - *Why it's essential:* Detailed guides on rolling strikes and delta hedging when a spread or sold leg is under pressure.

---

## 8. Sensibull & TradingView Live Practice Blueprint

Before risking real money from your ₹50,000 capital, execute this **30-Day Simulation Protocol**:

### Week 1: Greeks & Market Observation (No Trades)
- Open Sensibull's Live Option Chain at **9:30 AM**, **12:00 PM**, and **2:30 PM**.
- Track Nifty ATM Call and Put premiums:
  - Note how much premium melts between 9:30 AM and 2:30 PM even if Nifty is flat (Observe **Theta**).
  - Note what happens to premiums when Nifty moves 50 points in 5 minutes vs. 50 points in 2 hours (Observe **Delta vs. Theta**).

### Week 2: Virtual Paper-Trading (Sensibull Virtual Trading)
- Execute **10 Single-Leg ATM Momentum Trades** using Sensibull's Virtual Paper Trading tool.
- Track win rate, average win size, average loss size, and rule discipline (Did you honor the 15% Stop Loss?).

### Week 3: Hedged Debit Spreads Simulation
- Execute **5 Bull Call / Bear Put Spreads** on Nifty with 2-day holding horizons.
- Compare emotional calm and drawdown percentage relative to single-leg trades.

### Week 4: Audit & Real Capital Launch
- Calculate Net P&L after deducting ₹100 per trade for simulated brokerage and STT.
- If simulated net profit is positive across 20+ disciplined trades, deploy **1 Real Lot** with a strict ₹1,000 maximum daily loss limit.

---
*Roadmap Version: 1.0.0 | Built for Indian Equity Traders transitioning to F&O | Offline Reference File*
