# UI / UX mockups

Dark amber-on-black terminal aesthetic (JetBrains Mono, 12px). Every screen shares the shell: header with symbol box, nav (F-keys), ⌘K command button, DEMO/LIVE badge, login; a scrolling ticker; a footer disclaimer.

## 1. Terminal dashboard (`/`, mnemonic GP)

```
┌ ASTRATRADE PRO  [AAPL ][GO]  TERMINAL F2  AI COUNCIL F7  PORTFOLIO F8  SIMULATION F9   ⌘K COMMAND  [DEMO DATA] [LOGIN] 2026-10-14 ┐
│ SPY 575.12 ▲0.41%  QQQ 490.03 ▼0.12%  AAPL 228.00 ▲0.85%  MSFT 425.00 ▲0.20%  NVDA 132.00 ▲2.10% …                                  │
├──────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ AAPL · TECHNOLOGY        │ [chart][fundamentals][news][macro][sectors][help]                 [60d][120d][180d][365d][730d]  │
│ Last  $228.00  ▲ 0.85%   │ ┌ AAPL PRICE · SMA20 (CYAN) · SMA50 (VIOLET) ───────────────────────────────────────────────┐ │
│ High 229.10  Low 226.40  │ │          ╱╲      ╱╲╱╲                                                                    │ │
│ Volume 31.2M  Vol 1.04x  │ │   ╱╲╱╲╱╲╱  ╲╱╲╱╲╱    ╲╱╲        ╱╲╱╲                                                      │ │
├──────────────────────────┤ │ ╱╲╱                        ╲╱╲╱╲╱    ╲╱╲╱──────                                           │ │
│ TECHNICALS               │ └──────────────────────────────────────────────────────────────────────────────────────────┘ │
│ SMA20 225.1  RSI 58.2    │ ┌ VOLUME ─────────────────────────────┐ ┌ REALIZED VOLATILITY (20D, ANN.) ─────────────────┐ │
│ SMA50 219.4  MACD 1.21   │ │ ▇▅▆▇▃▅▆▇▇▅▃▆▇▅▆▇▃▅▆▇▇▅▃▆▇▅         │ │   ╱╲   ╱╲╱╲                                      │ │
│ SMA200 205.8 Vol30 24%   │ └──────────────────────────────────────┘ └──────────────────────────────────────────────────┘ │
├──────────────────────────┤                                                                                                 │
│ WATCHLIST     [filter  ] │                                                                                                 │
│ SYM   LAST    CHG%       │                                                                                                 │
│ NVDA  132.00  +2.10      │                                                                                                 │
│ MSFT  425.00  +0.20      │                                                                                                 │
│ XOM   118.00  -0.60      │                                                                                                 │
└──────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┘
│ Not financial advice. Trades require user approval.   Press / or ⌘K for commands · F1 help           AstraTrade Pro v1.0 │
```

Tabs swap the main area: **fundamentals** (financials grid, earnings card, SEC filings table), **news** (sentiment-tagged headlines + social bullish bar), **macro** (snapshot stats, economic calendar, political events, prediction markets), **sectors** (heatmap, metric toggle), **help** (mnemonic table).

### Command palette (⌘K or /)

```
┌ COMMAND · CURRENT AAPL                                                        ESC ┐
│ NVDA DES_                                                                          │
├────────────────────────────────────────────────────────────────────────────────────┤
│ ▶ NVDA DES      NVDA → Description & fundamentals                                  │
│   NVDA GP       NVDA · Technology                                                  │
│   DES           Description & fundamentals                                         │
│   COUNCIL       Run AI Council analysis                                            │
├────────────────────────────────────────────────────────────────────────────────────┤
│ Type a ticker then a function, Bloomberg-style. F2 GP · F3 DES · F4 N · F5 ECO …   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Council debate panel (`/council`)

Personas fade in one by one (350 ms apart), then the debate, the vote bar, and the Optimizer's final insight.

```
┌ AI COUNCIL · 7-PERSONA DELIBERATION                                          last run 09:41:12 ┐
│ SYMBOL [NVDA ]  QUESTION [Is this a good entry ahead of earnings?        ] [CONVENE COUNCIL]   │
│ BUDGET $[1000 ] [PROPOSE TRADE →]   A proposed trade is held as pending until you approve it.   │
├───────────────────────────────────────────┬─────────────────────────────────────────────────────┤
│ 🏦 Macro Economist     conf 60%   [HOLD]  │ ┌ DEBATE ─────────────────────────────────────────┐ │
│ Rates, inflation, GDP…                    │ │ ▏Quant Analyst to Risk Manager: I see your HOLD  │ │
│ ──────────┼──▓▓──────                      │ │ ▏ case, but technical factors (SMA50 > SMA200)   │ │
│ The macro backdrop is neutral for NVDA…   │ │ ▏ dominate on my horizon. Staying BUY.           │ │
│ • Fed funds 4.00% vs CPI 2.7% → real +1.3%│ │ ▏Risk Manager: no material disagreement…         │ │
│ • 10y-2y spread +0.35%                    │ └──────────────────────────────────────────────────┘ │
├───────────────────────────────────────────┤ ┌ VOTE ───────────────────────────────────────────┐ │
│ 📐 Quant Analyst       conf 62%   [BUY]   │ │ ████ BUY 3 ████│███ HOLD 2 ███│█ SELL 1 █         │ │
│ ──────────┼──────▓▓▓▓▓                     │ └──────────────────────────────────────────────────┘ │
│ Price action for NVDA: uptrend; RSI 58…   │ ┌ ⚖️ OPTIMIZER · FINAL INSIGHT ════════════════════┐ │
├───────────────────────────────────────────┤ │ [BUY]  score +0.24 · conf 52% · max size 6%       │ │
│ 📊 Fundamental Investor conf 65%  [BUY]   │ │ ──────────┼──────▓▓▓▓                              │ │
│ 🏛️ Political Analyst    conf 50%  [HOLD]  │ │ Synthesis for NVDA: the council leans BUY with a  │ │
│ 📰 News & Sentiment     conf 45%  [BUY]   │ │ weighted score of +0.24. Fundamental Investor     │ │
│ 🛡️ Risk Manager         conf 60%  [SELL]  │ │ carries the most conviction; the panel is split…  │ │
│   • 1-day 95% VaR ≈ $3.41/share (2.6%)    │ │ ──────────────────────────────────────────────── │ │
│   • Max position size: 6% of portfolio    │ │ Not financial advice. Trades require user approval│ │
└───────────────────────────────────────────┴──┴──────────────────────────────────────────────────┴─┘
┌ TRADE RECOMMENDATIONS · APPROVAL QUEUE ───────────────────────────────────────────────────────────┐
│ TIME            SYM   SIDE  QTY      TYPE    STATUS                                                 │
│ 09:41:30        NVDA  BUY   7.5758   market  [PENDING]   [REVIEW]                                   │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Trade-approval modal

```
┌ TRADE APPROVAL REQUIRED                                               [PAPER ACCOUNT] ┐
│        SIDE                 SYMBOL                 LAST                                │
│        BUY                  NVDA                   $132.00                             │
│ ▏Synthesis for NVDA: the council leans BUY with a weighted score of +0.24 …           │
│ QTY [7.5758   ]   TYPE [limit ▾]   LIMIT PRICE [131.50 ]                               │
│ Estimated value                                                     $996.18            │
│ (LIVE only) Type I APPROVE to authorize a real-money order  [I APPROVE   ]             │
│ Not financial advice. This order is sent to your brokerage only after you approve it.  │
│ AstraTrade Pro never holds funds.                                                       │
│ [✔ APPROVE & SEND]  [✖ REJECT]                                               [LATER]   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Approve is disabled until qty > 0 and, for live accounts, until the exact phrase is typed.

## 4. Portfolio page (`/portfolio`)

```
┌ ACCOUNT · PAPER ──────────────────────────────────────────────────────────────────────────────────┐
│ EQUITY $112,480.20   CASH $71,870   BUYING POWER $71,870   UNREALIZED P/L +$2,614   POSITIONS 4   │
│ [PAPER]                                            [↻ SYNC]  [AI COUNCIL HEALTH REPORT]           │
├────────────────────────────────────────────────────────────┬──────────────────────────────────────┤
│ POSITIONS                                                  │ SECTOR EXPOSURE                       │
│ SYM  SECTOR       QTY  AVG     LAST    VALUE     WT   P/L  │ Technology        ███████████  52.1%  │
│ AAPL Technology   40   205.00  228.00  9,120   22.5% +920  │ Energy            ████         14.6%  │
│ NVDA Technology   60   118.00  132.00  7,920   19.5% +840  │ Financials        ███          13.3%  │
│ XOM  Energy       50   110.00  118.00  5,900   14.6% +400  │                                       │
├─────────────────────────┬──────────────────────────┬───────┴──────────────────────────────────────┤
│ RISK DASHBOARD          │ SCENARIO ANALYSIS        │ CORRELATION MATRIX                            │
│ Ann. vol 21.3%          │ Fed hikes 100bp  -$3,2k  │        AAPL  NVDA  XOM   JPM                  │
│ Beta 1.12               │ Fed cuts 100bp   +$2,4k  │ AAPL   1.00  0.62  0.18  0.35                 │
│ 1-day VaR 95% -$1,140   │ Recession        -$10k   │ NVDA   0.62  1.00  0.11  0.30                 │
│ 1-day CVaR    -$1,620   │ Contested election -$2,8k│ XOM    0.18  0.11  1.00  0.41                 │
│ HHI 0.27  Eff. pos 3.7  │ Soft landing     +$4,9k  │ JPM    0.35  0.30  0.41  1.00                 │
├─────────────────────────┴──────────────────────────┴──────────────────────────────────────────────┤
│ AI COUNCIL · PORTFOLIO HEALTH REPORT                                                      [WATCH] │
│ AAPL 22.5%  score +0.18 [BUY]  Synthesis for AAPL …        │ REBALANCING SUGGESTIONS              │
│ NVDA 19.5%  score +0.24 [BUY]  …                           │ • Review XOM: council leans SELL     │
│ XOM  14.6%  score -0.21 [SELL] …                           │ Not financial advice…                │
└────────────────────────────────────────────────────────────┴──────────────────────────────────────┘
```

## 5. Simulation page (`/simulation`)

A cyan "SIMULATION ONLY" banner sits above a strategy lab (backtest/forward toggle, symbol(s), strategy, days, cash, Council-driven checkbox). Backtests render nine stat tiles (final equity, return, CAGR, Sharpe, Sortino, max DD, vol, trades, buy-and-hold comparison), the equity-vs-benchmark chart, a drawdown chart and a trade log. Forward sessions show equity-by-step, positions and a decision log with the Council's action/score per symbol.

## Responsive behaviour

* ≥1280px: three-column grids (XL).
* 1024–1279px (laptop): left rail + main area; council/portfolio panels stack to two columns.
* <1024px: single column; the ticker and footer stay fixed. Phones are not a target.
