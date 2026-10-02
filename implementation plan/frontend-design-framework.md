# Frontend Design Framework: Institutional Financial & Telemetry Dashboard ("AuraTrade")

## 1. Visual Theme & Atmosphere
The design must convey **technical reliability**, **precision**, and **quantitative control**. It must not feel like a casual social media app or a gamified interface. The UI is designed for high-density desktop and tablet workstations (Bloomberg terminal / Power BI dashboard precision, refined for traders and portfolio managers). The atmosphere is focused, dark-mode prioritized, and optimized for prolonged visual clarity.

---

## 2. Color Palette & Tokens (Integrated with Material UI)
- **Primary Background:** `#121212` (Ultra-dark base for visual efficiency, low eye strain, and data prominence).
- **Card & Paper Surface:** `#1E1E1E` (MUI Paper / Card container surface).
- **Subtle Structural Border:** `#2C2C2E` (`1px solid #2C2C2E` for card perimeters, dividers, and table rows).
- **Primary Data Accent:** `#2563EB` (Deep Blue / Electric Sapphire) for charts, primary KPIs, active indicators, and primary action triggers.
- **Alert / Bearish Accent:** `#FF453A` (Institutional Red) for stop-losses, drawdowns, price drops, and risk alerts.
- **Live / Bullish / Success Accent:** `#32D74B` (Lime / Emerald Green) for live telemetry, winning trades, and normal system states.
- **Primary Text:** `#FFFFFF` (High contrast, crisp legibility).
- **Secondary Text:** `#98989D` (Neutral slate gray for labels, table headers, and metadata).

---

## 3. Component Stylings (MUI v6 Specifications)
- **Cards & Paper Containers (`<Card>`, `<Paper>`):**
  - Border radius: `16px` (`borderRadius: 2` or `3`).
  - Background: `#1E1E1E`.
  - Internal padding: `20px` (`p: 2.5`).
  - Border: `1px solid #2C2C2E`.
  - Box shadow: Subtle low-elevation shadow (`0 4px 20px rgba(0, 0, 0, 0.35)`).
- **Charts & Financial Visualizations:**
  - Grid lines: `#2C2C2E`.
  - Data series: `#2563EB` (Deep Blue) and `#32D74B` (Green) area gradients.
  - Zero heavy borders; minimal, clean axis markers.
- **Data Tables (`<Table>`, `<DataGrid>`):**
  - Row border bottom: `1px solid #2C2C2E`.
  - Row hover background: `#252525`.
  - Header row: Clean uppercase label styling in `#98989D` with font size `0.75rem`.
- **Alerts & Warning Banners (`<Alert>`):**
  - Danger / Error Alert: Container background `#3A1C1C`, text color `#FF453A`, with left accent border `4px solid #FF453A`.
  - Success Alert: Container background `#1C3A24`, text color `#32D74B`, with left accent border `4px solid #32D74B`.
- **Form Inputs & Textfields (`<TextField>`, `<Select>`):**
  - Background: Transparent or clean neutral surface.
  - Never invert or turn black on focus (`:focus`).
  - Active focus border: `#2563EB` or primary accent with zero black fill.

---

## 4. Typography
- **Headings & Titles:** Plus Jakarta Sans / Inter, Semi-Bold (`600` - `700`), `20px` - `24px`.
- **Financial Figures & KPIs (Prices, Volume, Precision, PnL, Tickers):**
  - JetBrains Mono or Fira Code (strictly monospaced tabular numbers).
  - Weight: Bold (`700` - `800`), `28px` - `32px` for hero metrics.
- **Body & Secondary Copy:** Plus Jakarta Sans / Inter Regular (`400`), `14px` (`0.875rem`).

---

## 5. Layout & Grid Principles
- **Grid System:** Standard 12-column responsive grid layout (`<Grid container columns={12}>`).
- **Spacing Scale:** Strict multiples of 8px (`8px`, `16px`, `24px`, `32px`).
- **Dashboard Layout:**
  - Top row: High-impact KPI metrics cards (3 or 4 columns).
  - Main section: Primary chart or data grid (occupying 8 columns).
  - Secondary section: Live event alerts / risk telemetry panel (occupying 4 columns on the right).

---

## 6. Institutional Do's and Don'ts
- ✅ **Do:** Use smooth area gradients to highlight telemetry and market volatility curves.
- ✅ **Do:** Always render financial numbers, asset symbols, lot sizes, and precision decimals in monospace fonts.
- ✅ **Do:** Co-locate primary action buttons (Save, Verify, Submit) with secondary actions (Cancel, Back) on the same row.
- ❌ **Don't:** Use washed-out pastel colors or harsh blinding white card backgrounds that cause eye fatigue during extended trading sessions.
- ❌ **Don't:** Use generic or decorative clipart icons. Prefer sharp, domain-specific Lucide/MUI icons (e.g. `Zap`, `TrendingUp`, `ShieldCheck`, `Layers`).