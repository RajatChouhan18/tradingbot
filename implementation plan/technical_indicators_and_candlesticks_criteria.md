# AuraTrade / TxBot: Institutional Technical Indicators & Candlestick Pattern Criteria

> **Document Version**: 1.0.0  
> **Target Modules**: Module 3 (MarketView Engine), Module 4 (AlgoTrade & Strategy Engine), Auditing, Charts & Visualization  
> **Standard Compliance**: Institutional Quantitative Finance, CMT (Chartered Market Technician) Standards, TradingView Mathematical Conventions

---

## 1. Executive Summary & Architecture

This reference standard defines the exact mathematical formulations, algorithmic tolerances, and rendering specifications for all 18 candlestick recognition patterns and 22 technical indicators across the entire platform.

### Core Architectural Invariants:
1. **Zero Approximation / Standard Formulas**: All indicator calculations adhere strictly to Wilder's Smoothing, exponential weighting, or exact vectorized definitions.
2. **Universal Pre-computation**: All 22 indicators are synthesized simultaneously in under `1ms` per 180 bars, ensuring instantaneous on-the-fly rendering without network latency.
3. **Multi-Pane Visualization Engine (Lightweight Charts v5)**:
   - **Pane 0 (Primary Price Scale)**: Candlesticks, Volume Histogram, and on-chart overlay indicators.
   - **Pane 1..N (Dedicated Stacked Sub-Panes)**: Independent momentum oscillators, bounded scales (e.g. 0–100), and volatility meters rendered with distinct y-axes and horizontal reference thresholds.

---

## 2. Institutional Candlestick Pattern Recognition Criteria

Let:
- $O$ = Open, $H$ = High, $L$ = Low, $C$ = Close
- Total Bar Range: $R = H - L$ ($R > 0$)
- Real Body Size: $B = |C - O|$
- Upper Wick / Shadow: $U = H - \max(O, C)$
- Lower Wick / Shadow: $L_{sh} = \min(O, C) - L$
- Candle Direction: Bullish if $C \ge O$, Bearish if $C < O$
- Baseline Average Body: $B_{avg} = \text{SMA}_{14}(B)$

---

### 2.1 Single-Bar Formations

#### 1. Doji (`DOJI`)
- **Criteria**: Real body is virtually non-existent with balanced wicks.
  $$B \le 0.10 \times R \quad \text{and} \quad U \ge 0.12 \times R \quad \text{and} \quad L_{sh} \ge 0.12 \times R$$
- **Sentiment**: `NEUTRAL` (Indecision / Equilibrium)
- **Visual Marker**: Amber circle (`#fbbf24`) above bar.

#### 2. Dragonfly Doji (`DRAGONFLY_DOJI`)
- **Criteria**: Open and close are near the extreme high with a prominent lower wick.
  $$B \le 0.10 \times R \quad \text{and} \quad L_{sh} \ge 0.60 \times R \quad \text{and} \quad U \le 0.12 \times R$$
- **Sentiment**: `BULLISH` (Intraday rejection of low prices)
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 3. Gravestone Doji (`GRAVESTONE_DOJI`)
- **Criteria**: Open and close are near the extreme low with a prominent upper wick.
  $$B \le 0.10 \times R \quad \text{and} \quad U \ge 0.60 \times R \quad \text{and} \quad L_{sh} \le 0.12 \times R$$
- **Sentiment**: `BEARISH` (Intraday rejection of high prices)
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

#### 4. Hammer (`HAMMER`)
- **Criteria**: Small body near top with lower rejection shadow at least twice the body size.
  $$L_{sh} \ge 2.0 \times B \quad \text{and} \quad U \le 0.25 \times R \quad \text{and} \quad B \ge 0.08 \times R$$
  *Occurs after a pullback or in bullish candle.*
- **Sentiment**: `BULLISH`
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 5. Inverted Hammer (`INVERTED_HAMMER`)
- **Criteria**: Small body near bottom with upper shadow at least twice the body size.
  $$U \ge 2.0 \times B \quad \text{and} \quad L_{sh} \le 0.25 \times R \quad \text{and} \quad B \ge 0.08 \times R \quad \text{and} \quad C \ge O$$
- **Sentiment**: `BULLISH` (Upside test during bottoming phase)
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 6. Shooting Star (`SHOOTING_STAR`)
- **Criteria**: Small body near bottom with upper shadow at least twice the body size.
  $$U \ge 2.0 \times B \quad \text{and} \quad L_{sh} \le 0.25 \times R \quad \text{and} \quad B \ge 0.08 \times R \quad \text{and} \quad (\text{Uptrend context or } C < O)$$
- **Sentiment**: `BEARISH` (Topping rejection pin bar)
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

#### 7. Hanging Man (`HANGING_MAN`)
- **Criteria**: Bearish warning candle with long lower shadow at local swing highs.
  $$L_{sh} \ge 2.0 \times B \quad \text{and} \quad U \le 0.25 \times R \quad \text{and} \quad B \ge 0.08 \times R \quad \text{and } C \le O$$
- **Sentiment**: `BEARISH`
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

#### 8. Bullish Marubozu (`MARUBOZU_BULLISH`)
- **Criteria**: Unidirectional strong green expansion candle with minimal to zero wicks.
  $$C > O \quad \text{and} \quad B \ge 0.75 \times R \quad \text{and} \quad U \le 0.12 \times R \quad \text{and} \quad L_{sh} \le 0.12 \times R \quad \text{and} \quad B \ge 0.70 \times B_{avg}$$
- **Sentiment**: `BULLISH`
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 9. Bearish Marubozu (`MARUBOZU_BEARISH`)
- **Criteria**: Unidirectional strong red expansion candle with minimal to zero wicks.
  $$C < O \quad \text{and} \quad B \ge 0.75 \times R \quad \text{and} \quad U \le 0.12 \times R \quad \text{and} \quad L_{sh} \le 0.12 \times R \quad \text{and} \quad B \ge 0.70 \times B_{avg}$$
- **Sentiment**: `BEARISH`
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

---

### 2.2 Two-Bar Formations

Let subscript $i-1$ denote the previous candle and $i$ denote the current candle.

#### 10. Bullish Engulfing (`ENGULFING_BULLISH`)
- **Criteria**: Prior bearish candle completely enveloped by current bullish candle.
  $$C_{i-1} < O_{i-1} \quad \text{and} \quad C_i > O_i \quad \text{and} \quad O_i \le C_{i-1} \times 1.002 \quad \text{and} \quad C_i \ge O_{i-1} \quad \text{and} \quad B_i \ge B_{i-1}$$
- **Sentiment**: `BULLISH`
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 11. Bearish Engulfing (`ENGULFING_BEARISH`)
- **Criteria**: Prior bullish candle completely enveloped by current bearish candle.
  $$C_{i-1} > O_{i-1} \quad \text{and} \quad C_i < O_i \quad \text{and} \quad O_i \ge C_{i-1} \times 0.998 \quad \text{and} \quad C_i \le O_{i-1} \quad \text{and} \quad B_i \ge B_{i-1}$$
- **Sentiment**: `BEARISH`
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

#### 12. Bullish Harami (`HARAMI_BULLISH`)
- **Criteria**: Small green inside bar contained entirely inside prior large red candle body.
  $$C_{i-1} < O_{i-1} \quad \text{and} \quad C_i > O_i \quad \text{and} \quad B_{i-1} \ge 0.40 \times R_{i-1} \quad \text{and} \quad O_i \ge C_{i-1} \quad \text{and} \quad C_i \le O_{i-1} \quad \text{and} \quad B_i \le 0.65 \times B_{i-1}$$
- **Sentiment**: `BULLISH`
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 13. Bearish Harami (`HARAMI_BEARISH`)
- **Criteria**: Small red inside bar contained entirely inside prior large green candle body.
  $$C_{i-1} > O_{i-1} \quad \text{and} \quad C_i < O_i \quad \text{and} \quad B_{i-1} \ge 0.40 \times R_{i-1} \quad \text{and} \quad O_i \le C_{i-1} \quad \text{and} \quad C_i \ge O_{i-1} \quad \text{and} \quad B_i \le 0.65 \times B_{i-1}$$
- **Sentiment**: `BEARISH`
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

#### 14. Piercing Line (`PIERCING_LINE`)
- **Criteria**: Current candle opens below prior low and closes above the 50% midpoint of the prior red candle body.
  $$C_{i-1} < O_{i-1} \quad \text{and} \quad C_i > O_i \quad \text{and} \quad O_i \le C_{i-1} \quad \text{and} \quad C_i > \frac{O_{i-1} + C_{i-1}}{2} \quad \text{and} \quad C_i < O_{i-1}$$
- **Sentiment**: `BULLISH`
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 15. Dark Cloud Cover (`DARK_CLOUD_COVER`)
- **Criteria**: Current candle opens above prior high and closes below the 50% midpoint of the prior green candle body.
  $$C_{i-1} > O_{i-1} \quad \text{and} \quad C_i < O_i \quad \text{and} \quad O_i \ge C_{i-1} \quad \text{and} \quad C_i < \frac{O_{i-1} + C_{i-1}}{2} \quad \text{and} \quad C_i > O_{i-1}$$
- **Sentiment**: `BEARISH`
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

---

### 2.3 Three-Bar Formations

#### 16. Morning Star (`MORNING_STAR`)
- **Criteria**: 3-bar bottom reversal.
  1. Bar $i-2$: Large bearish candle ($C_{i-2} < O_{i-2}$, $B_{i-2} \ge 0.45 \times R_{i-2}$).
  2. Bar $i-1$: Small star/doji body ($B_{i-1} \le 0.45 \times B_{i-2}$).
  3. Bar $i$: Strong bullish candle ($C_i > O_i$) closing above 50% midpoint of Bar $i-2$ ($C_i \ge \frac{O_{i-2} + C_{i-2}}{2}$).
- **Sentiment**: `BULLISH`
- **Visual Marker**: Green arrow (`#32D74B`) below bar.

#### 17. Evening Star (`EVENING_STAR`)
- **Criteria**: 3-bar top reversal.
  1. Bar $i-2$: Large bullish candle ($C_{i-2} > O_{i-2}$, $B_{i-2} \ge 0.45 \times R_{i-2}$).
  2. Bar $i-1$: Small star/doji body ($B_{i-1} \le 0.45 \times B_{i-2}$).
  3. Bar $i$: Strong bearish candle ($C_i < O_i$) closing below 50% midpoint of Bar $i-2$ ($C_i \le \frac{O_{i-2} + C_{i-2}}{2}$).
- **Sentiment**: `BEARISH`
- **Visual Marker**: Red arrow (`#FF453A`) above bar.

---

## 3. Institutional Technical Indicators Mathematical Formulas

---

### 3.1 Moving Averages & Baselines (On-Chart: Pane 0)

1. **Exponential Moving Average (EMA 9, 21, 50, 200)**:
   $$\alpha = \frac{2}{N + 1}, \quad \text{EMA}_t = (P_t \times \alpha) + (\text{EMA}_{t-1} \times (1 - \alpha))$$
2. **Simple Moving Average (SMA 20, 50, 200)**:
   $$\text{SMA}_t = \frac{1}{N} \sum_{k=0}^{N-1} P_{t-k}$$

---

### 3.2 Volume & Volatility Envelopes (On-Chart: Pane 0)

3. **Volume-Weighted Average Price (VWAP)**:
   $$\text{Typical Price}_k = \frac{H_k + L_k + C_k}{3}, \quad \text{VWAP}_t = \frac{\sum_{k=1}^t (\text{Typical Price}_k \times V_k)}{\sum_{k=1}^t V_k}$$

4. **Bollinger Bands (20, 2.0)**:
   $$\text{Middle} = \text{SMA}_{20}(C), \quad \sigma = \text{StdDev}_{20}(C)$$
   $$\text{Upper Band} = \text{Middle} + (2.0 \times \sigma), \quad \text{Lower Band} = \text{Middle} - (2.0 \times \sigma)$$

5. **Supertrend (10, 3.0)**:
   $$\text{Basic Upper} = \frac{H_t + L_t}{2} + (3.0 \times \text{ATR}_{10}), \quad \text{Basic Lower} = \frac{H_t + L_t}{2} - (3.0 \times \text{ATR}_{10})$$
   Band locks dynamically until a confirmed close across the band triggers direction reversal.

6. **Keltner Channels (20 EMA, 10 ATR, 2.0x)**:
   $$\text{Middle} = \text{EMA}_{20}(C), \quad \text{Upper} = \text{Middle} + (2.0 \times \text{ATR}_{10}), \quad \text{Lower} = \text{Middle} - (2.0 \times \text{ATR}_{10})$$

7. **Donchian Channels (20)**:
   $$\text{Upper Band} = \max_{k=0..19}(H_{t-k}), \quad \text{Lower Band} = \min_{k=0..19}(L_{t-k}), \quad \text{Middle Band} = \frac{\text{Upper} + \text{Lower}}{2}$$

8. **Parabolic SAR (0.02 Step, 0.20 Max)**:
   $$\text{SAR}_{t} = \text{SAR}_{t-1} + \text{AF} \times (\text{EP} - \text{SAR}_{t-1})$$
   Accelerates dynamically with each new high (in uptrend) or low (in downtrend) up to maximum 0.20.

9. **Classic Pivot Points (Daily / Standard Floor)**:
   $$P = \frac{H + L + C}{3}, \quad R_1 = 2P - L, \quad S_1 = 2P - H, \quad R_2 = P + (H - L), \quad S_2 = P - (H - L)$$

10. **ZigZag (5% Swing Pivots)**:
    Filters out noise by connecting alternating local peak ($H$) and trough ($L$) pivot points exceeding the minimum percentage threshold.

11. **Ichimoku Kinko Hyo (9, 26, 52)**:
    - Tenkan-sen (Conversion Line): $\frac{\max_9(H) + \min_9(L)}{2}$
    - Kijun-sen (Base Line): $\frac{\max_{26}(H) + \min_{26}(L)}{2}$
    - Senkou Span A (Leading Span A): $\frac{\text{Tenkan} + \text{Kijun}}{2}$ (Projected forward 26 periods)
    - Senkou Span B (Leading Span B): $\frac{\max_{52}(H) + \min_{52}(L)}{2}$ (Projected forward 26 periods)

---

### 3.3 Sub-Pane Momentum & Oscillators (Dedicated Sub-Panes: Pane 1..N)

12. **Relative Strength Index (RSI 14 - Wilder's Smoothed)**:
    $$\Delta_t = C_t - C_{t-1}, \quad U_t = \max(\Delta_t, 0), \quad D_t = \max(-\Delta_t, 0)$$
    $$\text{AvgGain} = \text{EWM}_{\alpha=1/14}(U), \quad \text{AvgLoss} = \text{EWM}_{\alpha=1/14}(D)$$
    $$\text{RS} = \frac{\text{AvgGain}}{\text{AvgLoss}}, \quad \text{RSI} = 100 - \frac{100}{1 + \text{RS}}$$
    *Reference Lines*: Overbought at `70`, Oversold at `30`.

13. **Moving Average Convergence Divergence (MACD 12, 26, 9)**:
    $$\text{MACD Line} = \text{EMA}_{12}(C) - \text{EMA}_{26}(C)$$
    $$\text{Signal Line} = \text{EMA}_9(\text{MACD Line})$$
    $$\text{MACD Histogram} = \text{MACD Line} - \text{Signal Line}$$
    *Histogram Colors*: Lime Green (`#32D74B`) if $\ge 0$, Institutional Red (`#FF453A`) if $< 0$.

14. **Stochastic RSI (14, 14, 3, 3)**:
    $$\text{StochRSI} = \frac{\text{RSI}_{14} - \min_{14}(\text{RSI}_{14})}{\max_{14}(\text{RSI}_{14}) - \min_{14}(\text{RSI}_{14})} \times 100$$
    $$\%K = \text{SMA}_3(\text{StochRSI}), \quad \%D = \text{SMA}_3(\%K)$$
    *Reference Lines*: `80` (Overbought), `20` (Oversold).

15. **Average Directional Index (ADX 14 & Directional Movement)**:
    $$+\text{DM} = \text{if } (H_t - H_{t-1} > L_{t-1} - L_t \text{ and } >0) \text{ then } H_t - H_{t-1} \text{ else } 0$$
    $$-\text{DM} = \text{if } (L_{t-1} - L_t > H_t - H_{t-1} \text{ and } >0) \text{ then } L_{t-1} - L_t \text{ else } 0$$
    $$+\text{DI}_{14} = \frac{\text{EWM}_{1/14}(+\text{DM})}{\text{ATR}_{14}} \times 100, \quad -\text{DI}_{14} = \frac{\text{EWM}_{1/14}(-\text{DM})}{\text{ATR}_{14}} \times 100$$
    $$\text{DX} = \frac{|+\text{DI} - -\text{DI}|}{+\text{DI} + -\text{DI}} \times 100, \quad \text{ADX} = \text{EWM}_{1/14}(\text{DX})$$
    *Reference Line*: Trend Strength Threshold at `25`.

16. **Average True Range (ATR 14)**:
    $$\text{TR}_t = \max(H_t - L_t, \, |H_t - C_{t-1}|, \, |L_t - C_{t-1}|), \quad \text{ATR}_t = \text{EWM}_{\alpha=1/14}(\text{TR})$$

17. **On-Balance Volume (OBV)**:
    $$\text{OBV}_t = \text{OBV}_{t-1} + \begin{cases} +V_t & \text{if } C_t > C_{t-1} \\ -V_t & \text{if } C_t < C_{t-1} \\ 0 & \text{if } C_t = C_{t-1} \end{cases}$$

---

## 4. Multi-Pane Layout & Sizing Invariants

In TradingView Lightweight Charts (v5.2.1), multi-pane rendering is governed by:
1. **Pane 0 Allocation**: Primary Candlestick series, Volume Histogram (bottom margin `0.82`), and price overlays.
2. **Sub-Pane Allocation**: Each active oscillator is placed in an incremental `paneIndex` ($1, 2, \dots, N$).
3. **Container Dimension Equation**:
   $$\text{Height}_{\text{total}} = 480\text{px} + (N_{\text{subpanes}} \times 130\text{px})$$
4. **Synchronized Time Horizon**: All stacked panes automatically track the master `timeScale`, pan, zoom, and crosshair hover in perfect lockstep.
