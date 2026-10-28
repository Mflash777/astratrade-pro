/**
 * Demo-mode data. Used automatically when NEXT_PUBLIC_API_URL is empty or the
 * backend is unreachable (e.g. on GitHub Pages), so the terminal is fully
 * explorable without a server. Mirrors the backend's deterministic generators.
 */
import type {
  Account, BacktestResult, Bar, CouncilResult, ForwardReport, FundamentalsBundle, HealthReport, Indicators,
  MacroBundle, NewsBundle, Opinion, PortfolioBundle, Position, Quote, Recommendation, RiskReport, SectorRow,
} from "./types";

export const SECTORS: Record<string, string> = {
  AAPL: "Technology", MSFT: "Technology", NVDA: "Technology", GOOGL: "Communication", META: "Communication",
  AMZN: "Consumer Discretionary", TSLA: "Consumer Discretionary", JPM: "Financials", BAC: "Financials", GS: "Financials",
  XOM: "Energy", CVX: "Energy", JNJ: "Health Care", PFE: "Health Care", UNH: "Health Care", PG: "Consumer Staples",
  KO: "Consumer Staples", WMT: "Consumer Staples", CAT: "Industrials", BA: "Industrials", NEE: "Utilities",
  LIN: "Materials", PLD: "Real Estate", SPY: "Index", QQQ: "Index",
};
const BASE: Record<string, number> = {
  AAPL: 228, MSFT: 425, NVDA: 132, GOOGL: 168, META: 560, AMZN: 190, TSLA: 240, JPM: 215, BAC: 41, GS: 510, XOM: 118,
  CVX: 150, JNJ: 160, PFE: 29, UNH: 580, PG: 170, KO: 69, WMT: 80, CAT: 370, BA: 160, NEE: 80, LIN: 470, PLD: 125, SPY: 575, QQQ: 490,
};

function seeded(key: string): () => number {
  let h = 2166136261;
  for (const c of key) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
  return () => { h += 0x6d2b79f5; let t = Math.imul(h ^ (h >>> 15), 1 | h); t ^= t + Math.imul(t ^ (t >>> 7), 61 | t); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function gauss(r: () => number): number { const u = 1 - r(), v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }

export function history(symbol: string, days = 365): Bar[] {
  const r = seeded(symbol.toUpperCase());
  const base = BASE[symbol.toUpperCase()] ?? 100;
  const sigma = 0.25 / Math.sqrt(252), mu = 0.08 / 252;
  let p = base * (0.6 + r() * 0.3);
  const closes: number[] = [];
  for (let i = 0; i < days; i++) { p *= Math.exp(mu + sigma * gauss(r)); closes.push(p); }
  const scale = base / closes[closes.length - 1];
  const out: Bar[] = [];
  const d = new Date(); d.setDate(d.getDate() - days);
  for (let i = 0; i < days; i++) {
    d.setDate(d.getDate() + 1);
    if (d.getDay() === 0 || d.getDay() === 6) { d.setDate(d.getDate() + (d.getDay() === 0 ? 1 : 2)); }
    const c = closes[i] * scale, o = c * (1 + gauss(r) * 0.004);
    out.push({ date: d.toISOString().slice(0, 10), open: +o.toFixed(2), high: +(Math.max(o, c) * (1 + Math.abs(gauss(r)) * 0.006)).toFixed(2),
      low: +(Math.min(o, c) * (1 - Math.abs(gauss(r)) * 0.006)).toFixed(2), close: +c.toFixed(2), volume: Math.round(30e6 * Math.exp(gauss(r) * 0.4)) });
  }
  return out;
}

export function quote(symbol: string): Quote {
  const h = history(symbol, 60), last = h[h.length - 1], prev = h[h.length - 2];
  return { symbol: symbol.toUpperCase(), price: last.close, change: +(last.close - prev.close).toFixed(2),
    change_pct: +((last.close / prev.close - 1) * 100).toFixed(2), volume: last.volume, high: last.high, low: last.low,
    sector: SECTORS[symbol.toUpperCase()] ?? "Unknown", timestamp: new Date().toISOString() };
}

const sma = (a: number[], n: number) => (a.length < n ? null : +(a.slice(-n).reduce((x, y) => x + y, 0) / n).toFixed(4));
function ema(a: number[], n: number): number[] { const k = 2 / (n + 1); const out: number[] = []; a.forEach((v, i) => out.push(i === 0 ? v : v * k + out[i - 1] * (1 - k))); return out; }

export function indicators(symbol: string): Indicators {
  const bars = history(symbol, 365), c = bars.map((b) => b.close);
  const gains: number[] = [], losses: number[] = [];
  for (let i = c.length - 14; i < c.length; i++) { const d = c[i] - c[i - 1]; gains.push(Math.max(d, 0)); losses.push(Math.max(-d, 0)); }
  const ag = gains.reduce((a, b) => a + b, 0) / 14, al = losses.reduce((a, b) => a + b, 0) / 14;
  const rsi = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  const macdSeries = ema(c, 12).map((v, i) => v - ema(c, 26)[i]);
  const sig = ema(macdSeries, 9);
  const rets = c.slice(-31).map((v, i, a) => (i ? v / a[i - 1] - 1 : 0)).slice(1);
  const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
  const vol = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length - 1)) * Math.sqrt(252);
  const s20 = sma(c, 20)!, sd20 = Math.sqrt(c.slice(-20).reduce((a, b) => a + (b - s20) ** 2, 0) / 19);
  const vols = bars.slice(-20).map((b) => b.volume), avgV = vols.reduce((a, b) => a + b, 0) / 20;
  return { price: c[c.length - 1], sma20: s20, sma50: sma(c, 50), sma200: sma(c, 200), rsi14: +rsi.toFixed(2),
    macd: +macdSeries[macdSeries.length - 1].toFixed(4), macd_signal: +sig[sig.length - 1].toFixed(4),
    bollinger_upper: +(s20 + 2 * sd20).toFixed(2), bollinger_lower: +(s20 - 2 * sd20).toFixed(2),
    volatility_30d_annualized: +vol.toFixed(4), return_1m: +(c[c.length - 1] / c[c.length - 22] - 1).toFixed(4),
    return_3m: +(c[c.length - 1] / c[c.length - 64] - 1).toFixed(4), avg_volume_20d: Math.round(avgV),
    volume_ratio: +(bars[bars.length - 1].volume / avgV).toFixed(3) };
}

const PROXIES: Record<string, string[]> = {
  Technology: ["AAPL", "MSFT", "NVDA"], Communication: ["GOOGL", "META"], "Consumer Discretionary": ["AMZN", "TSLA"],
  Financials: ["JPM", "BAC", "GS"], Energy: ["XOM", "CVX"], "Health Care": ["JNJ", "PFE", "UNH"],
  "Consumer Staples": ["PG", "KO", "WMT"], Industrials: ["CAT", "BA"], Utilities: ["NEE"], Materials: ["LIN"], "Real Estate": ["PLD"],
};
const ret = (s: string, n: number) => { const h = history(s, n + 5).map((b) => b.close); return h[h.length - 1] / h[h.length - n] - 1; };

export function sectors(): SectorRow[] {
  const b1 = ret("SPY", 21), b3 = ret("SPY", 63);
  const rows = Object.entries(PROXIES).map(([sector, syms]) => {
    const r1 = syms.reduce((a, s) => a + ret(s, 21), 0) / syms.length, r3 = syms.reduce((a, s) => a + ret(s, 63), 0) / syms.length;
    return { sector, return_1m: +(r1 * 100).toFixed(2), return_3m: +(r3 * 100).toFixed(2), relative_1m: +((r1 - b1) * 100).toFixed(2),
      relative_3m: +((r3 - b3) * 100).toFixed(2), constituents: syms, rank: 0, phase: "" };
  }).sort((a, b) => b.relative_3m - a.relative_3m);
  rows.forEach((r, i) => { r.rank = i + 1; r.phase = r.relative_3m > 0 && r.relative_1m > 0 ? "leading" : r.relative_3m > 0 ? "weakening" : r.relative_1m > 0 ? "improving" : "lagging"; });
  return rows;
}

export function fundamentals(symbol: string): FundamentalsBundle {
  const r = seeded("fund:" + symbol.toUpperCase()), sector = SECTORS[symbol.toUpperCase()] ?? "Technology";
  const growth = ["Technology", "Communication", "Consumer Discretionary"].includes(sector);
  const u = (a: number, b: number) => a + r() * (b - a);
  const beat = r() > 0.35, guidance = ["raised", "maintained", "lowered"][Math.floor(r() * 3)];
  const buy = 8 + Math.floor(r() * 22), hold = 2 + Math.floor(r() * 10), sell = Math.floor(r() * 5);
  return {
    fundamentals: { name: `${symbol.toUpperCase()} Corp.`, sector, market_cap: Math.round(u(20e9, 3e12)), pe_ratio: +u(growth ? 22 : 9, growth ? 45 : 22).toFixed(2),
      forward_pe: +u(growth ? 18 : 8, growth ? 38 : 20).toFixed(2), peg: +u(0.8, 2.8).toFixed(2), eps: +u(1.5, 14).toFixed(2), revenue_ttm: Math.round(u(10e9, 400e9)),
      profit_margin: +u(0.05, 0.35).toFixed(3), roe: +u(0.08, 0.45).toFixed(3), debt_to_equity: +u(0.1, 1.8).toFixed(2), dividend_yield: +u(0, 0.04).toFixed(4),
      beta: +u(0.6, 1.8).toFixed(2), revenue_growth_yoy: +u(growth ? -0.05 : -0.08, growth ? 0.3 : 0.12).toFixed(3), earnings_growth_yoy: +u(-0.1, 0.4).toFixed(3), source: "mock" },
    earnings: { quarter: "Q3 2026", eps_surprise_pct: +(beat ? u(2, 12) : u(-9, -1)).toFixed(2), revenue_surprise_pct: +(beat ? u(0.5, 5) : u(-4, 0.5)).toFixed(2), guidance,
      management_tone: beat && guidance !== "lowered" ? "confident" : "cautious", key_themes: ["AI capex", "margin expansion", "pricing power", "cost discipline"] },
    filings: ["10-Q", "8-K", "4", "10-K", "8-K"].map((f, i) => ({ form: f, filed: `2026-${String(9 - i).padStart(2, "0")}-${String(3 + i * 5).padStart(2, "0")}`, description: `${f} filing`, accession: `0000000000-26-${100000 + i}` })),
    analysts: { buy, hold, sell, consensus: buy > hold + sell ? "Buy" : "Hold", target_upside_pct: +u(-10, 28).toFixed(1) },
  };
}

export function news(symbol: string): NewsBundle {
  const r = seeded("news:" + symbol.toUpperCase()), s = symbol.toUpperCase();
  const t = [[`${s} beats quarterly estimates as demand stays strong`, 1], [`Analysts upgrade ${s} on margin expansion`, 1], [`${s} faces regulatory probe over data practices`, -1],
    [`${s} shares fall after guidance cut`, -1], [`${s} announces record buyback program`, 1], [`Supply-chain warning weighs on ${s}`, -1], [`${s} expands AI partnership, shares rally`, 1],
    [`Lawsuit filed against ${s} by former employees`, -1]] as [string, number][];
  const srcs = ["Reuters", "Bloomberg", "WSJ", "CNBC", "FT"];
  return { news: t.filter(() => r() > 0.3).map(([title, sent], i) => ({ title, source: srcs[Math.floor(r() * 5)], published: new Date(Date.now() - r() * 72 * 3.6e6).toISOString(), url: `https://example.com/${s}/${i}`, sentiment: sent })),
    social: { mentions_24h: Math.round(800 + r() * 60000), mention_change_pct: +(-40 + r() * 160).toFixed(1), bullish_pct: +(35 + r() * 40).toFixed(1), platforms: { x: +(r() - 0.4).toFixed(2), reddit: +(r() - 0.5).toFixed(2), stocktwits: +(r() - 0.3).toFixed(2) } } };
}

export function macro(): MacroBundle {
  const d = (n: number) => { const x = new Date(); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };
  return { snapshot: { fed_funds_rate: 4.0, cpi_yoy: 2.7, unemployment_rate: 4.3, gdp_growth: 2.1, treasury_10y: 4.05, treasury_2y: 3.7, source: "mock" },
    calendar: [[2, "CPI (MoM/YoY)", "high"], [3, "Initial Jobless Claims", "medium"], [6, "FOMC Rate Decision", "high"], [7, "Retail Sales", "medium"], [9, "PPI", "medium"], [13, "Nonfarm Payrolls", "high"]].map(([n, e, i]) => ({ date: d(n as number), event: e as string, impact: i as string })),
    political: [{ date: d(21), event: "US midterm elections", risk: "high", sectors: ["Health Care", "Energy", "Financials"] }, { date: d(5), event: "Senate vote on digital-services tax bill", risk: "medium", sectors: ["Technology", "Communication"] }, { date: d(12), event: "EU AI Act enforcement deadline", risk: "medium", sectors: ["Technology"] }, { date: d(30), event: "Debt-ceiling negotiation window", risk: "high", sectors: ["Index", "Financials"] }],
    prediction_markets: [{ question: "Fed cuts rates at next FOMC meeting?", yes_probability: 0.62, volume_24h: 1.8e6, source: "mock" }, { question: "US recession declared in 2026?", yes_probability: 0.21, volume_24h: 9.4e5, source: "mock" }, { question: "10y Treasury above 4.5% by year end?", yes_probability: 0.33, volume_24h: 4.1e5, source: "mock" }, { question: "New semiconductor tariffs this quarter?", yes_probability: 0.41, volume_24h: 6.7e5, source: "mock" }] };
}

const vote = (s: number, t = 0.2) => (s > t ? "BUY" : s < -t ? "SELL" : "HOLD") as Opinion["vote"];

export function council(symbol: string): CouncilResult {
  const s = symbol.toUpperCase(), ind = indicators(s), f = fundamentals(s), n = news(s), m = macro().snapshot, sec = sectors();
  const sectorRow = sec.find((x) => x.sector === SECTORS[s]);
  const beta = f.fundamentals.beta ?? 1;
  const curve = m.treasury_10y - m.treasury_2y, real = m.fed_funds_rate - m.cpi_yoy;
  const macroScore = Math.max(-1, Math.min(1, (curve * 1.5 - real / 3 + (m.gdp_growth - 1.5) / 2) / 3 * Math.min(1.5, Math.max(0.6, beta))));
  const trend = ind.sma50! > ind.sma200! ? 0.6 : -0.6, rsiS = ind.rsi14! > 70 ? -0.8 : ind.rsi14! < 30 ? 0.8 : (50 - ind.rsi14!) / 50;
  const quantScore = (trend + rsiS + Math.max(-1, Math.min(1, (ind.return_3m ?? 0) * 4)) - Math.min(1, ind.volatility_30d_annualized / 0.6) * 0.5) / 3.5;
  const fair = ["Technology", "Communication"].includes(f.fundamentals.sector) ? 30 : 18;
  const fundScore = ((fair - f.fundamentals.pe_ratio!) / fair + (f.fundamentals.revenue_growth_yoy ?? 0) * 4 + ((f.fundamentals.profit_margin ?? 0) - 0.12) * 4 + (f.earnings.guidance === "raised" ? 0.7 : f.earnings.guidance === "lowered" ? -0.7 : 0.1)) / 4;
  const relevantPol = macro().political.filter((e) => e.sectors.includes(SECTORS[s]) || e.sectors.includes("Index"));
  const polScore = -Math.min(1, relevantPol.reduce((a, e) => a + (e.risk === "high" ? 0.3 : 0.15), 0));
  const avgNews = n.news.reduce((a, x) => a + x.sentiment, 0) / Math.max(n.news.length, 1);
  const sentScore = (avgNews + (n.social.bullish_pct - 50) / 50) / 2 - (n.social.bullish_pct > 72 ? 0.2 : 0);
  const riskPenalty = Math.min(1, ind.volatility_30d_annualized / 0.5) * 0.5 + Math.max(0, beta - 1) * 0.3;
  const riskScore = Math.min(0.15, -riskPenalty + (sectorRow ? 1 - 2 * (sectorRow.rank - 1) / (sec.length - 1) : 0) * 0.3);
  const maxPos = Math.max(1, Math.floor(10 / Math.max(ind.volatility_30d_annualized / 0.2, 1)));
  const varPS = ind.price * ind.volatility_30d_annualized / Math.sqrt(252) * 1.65;
  const mk = (persona: string, role: string, score: number, confidence: number, key_points: string[], rationale: string): Opinion => ({ persona, role, score: +score.toFixed(3), confidence, vote: vote(score), rationale, key_points, evidence: [] });
  const opinions: Opinion[] = [
    mk("Macro Economist", "Rates, inflation, GDP, unemployment, Fed policy", macroScore, 0.6, [`Fed funds ${m.fed_funds_rate.toFixed(2)}% vs CPI ${m.cpi_yoy}% → real rate ${real >= 0 ? "+" : ""}${real.toFixed(1)}%`, `10y-2y spread ${curve >= 0 ? "+" : ""}${curve.toFixed(2)}%`, `GDP ${m.gdp_growth}%, unemployment ${m.unemployment_rate}%`, `Beta ${beta.toFixed(2)} scales macro sensitivity`],
      `The macro backdrop is ${macroScore > 0.15 ? "supportive" : macroScore < -0.15 ? "restrictive" : "neutral"} for ${s}. Real policy rate ${real.toFixed(1)}% with a ${curve >= 0 ? "positive" : "inverted"} curve; growth data suggests the cycle is ${m.gdp_growth > 1.5 ? "late but intact" : "decelerating"}.`),
    mk("Quant Analyst", "Technical indicators, volatility, risk models, backtests", quantScore, 0.62, [`SMA50 ${trend > 0 ? ">" : "<"} SMA200 (${trend > 0 ? "uptrend" : "downtrend"})`, `RSI(14) ${ind.rsi14!.toFixed(0)}`, `MACD ${ind.macd! > ind.macd_signal! ? "above" : "below"} signal`, `30d realized vol ${(ind.volatility_30d_annualized * 100).toFixed(0)}%`],
      `Price action for ${s}: ${trend > 0 ? "uptrend" : "downtrend"} with RSI ${ind.rsi14!.toFixed(0)}. Volatility at ${(ind.volatility_30d_annualized * 100).toFixed(0)}% is ${ind.volatility_30d_annualized > 0.35 ? "elevated" : "moderate"}; position sizing should scale inversely with it.`),
    mk("Fundamental Investor", "Earnings, balance sheets, valuation, competitive landscape", fundScore, 0.65, [`P/E ${f.fundamentals.pe_ratio} (fwd ${f.fundamentals.forward_pe}), PEG ${f.fundamentals.peg}`, `Revenue growth ${((f.fundamentals.revenue_growth_yoy ?? 0) * 100).toFixed(1)}%, margin ${((f.fundamentals.profit_margin ?? 0) * 100).toFixed(1)}%`, `EPS surprise ${f.earnings.eps_surprise_pct}%, guidance ${f.earnings.guidance}`],
      `${s} screens as a ${(f.fundamentals.roe ?? 0) > 0.2 && (f.fundamentals.profit_margin ?? 0) > 0.15 ? "high-quality compounder" : "average-quality business"}. ${f.fundamentals.peg! > 2 ? "Valuation leaves limited margin of safety." : "Valuation is reasonable relative to growth."}`),
    mk("Political Analyst", "Elections, legislation, geopolitical risk, regulatory changes", polScore, 0.5, relevantPol.slice(0, 3).map((e) => `${e.event} (${e.date}, ${e.risk} risk)`),
      `${s}'s sector faces ${relevantPol.length} upcoming political/regulatory catalysts. ${relevantPol.some((e) => e.risk === "high") ? "Headline risk argues for tighter stops into these dates." : "Policy risk looks manageable near term."}`),
    mk("News & Sentiment Analyst", "Headlines, social media sentiment, prediction markets", sentScore, 0.45, [`Headline sentiment ${avgNews >= 0 ? "+" : ""}${avgNews.toFixed(2)} across ${n.news.length} stories`, `${n.social.mentions_24h.toLocaleString()} social mentions, ${n.social.bullish_pct}% bullish`],
      `Narrative flow on ${s} is ${sentScore > 0.1 ? "constructive" : sentScore < -0.1 ? "negative" : "mixed"}.${n.social.bullish_pct > 72 ? " Extreme bullish positioning raises reversal risk." : ""}`),
    mk("Risk Manager", "Drawdown, exposure, hedging, scenario analysis", riskScore, 0.6, [`1-day 95% VaR ≈ $${varPS.toFixed(2)}/share (${((varPS / ind.price) * 100).toFixed(1)}%)`, `Scenario P/L: rate hike ${(-8 * beta).toFixed(1)}%, recession ${(-25 * beta).toFixed(1)}%, soft landing +${(12 * beta).toFixed(1)}%`, `Max position size: ${maxPos}% of portfolio`],
      `Risk profile for ${s}: beta ${beta.toFixed(2)} amplifies macro shocks. Max position ${maxPos}%; hedge via index puts if exposure exceeds that.`),
  ];
  const W: Record<string, number> = { "Macro Economist": 1, "Quant Analyst": 1.1, "Fundamental Investor": 1.2, "Political Analyst": 0.8, "News & Sentiment Analyst": 0.8, "Risk Manager": 1.3 };
  const tw = opinions.reduce((a, o) => a + W[o.persona] * o.confidence, 0);
  const score = opinions.reduce((a, o) => a + W[o.persona] * o.confidence * o.score, 0) / tw;
  const votes = { BUY: 0, HOLD: 0, SELL: 0 }; opinions.forEach((o) => votes[o.vote]++);
  const disp = Math.max(...opinions.map((o) => o.score)) - Math.min(...opinions.map((o) => o.score));
  const strongest = opinions.reduce((a, o) => (Math.abs(o.score) * o.confidence > Math.abs(a.score) * a.confidence ? o : a));
  const finalVote = vote(score, 0.15);
  const final: Opinion = { persona: "Optimizer", role: "Synthesizes all viewpoints into a final recommendation", score: +score.toFixed(3), confidence: +Math.max(0.1, 0.57 * (1 - disp / 4)).toFixed(3), vote: finalVote,
    key_points: [`Weighted score ${score >= 0 ? "+" : ""}${score.toFixed(2)}; votes BUY ${votes.BUY} / HOLD ${votes.HOLD} / SELL ${votes.SELL}`, `Dispersion ${disp.toFixed(2)} (${disp < 0.6 ? "consensus" : "contested"})`, `Strongest conviction: ${strongest.persona} (${strongest.vote})`],
    rationale: `Synthesis for ${s}: the council leans ${finalVote} with a weighted score of ${score >= 0 ? "+" : ""}${score.toFixed(2)}. ${strongest.persona} carries the most conviction; ${disp < 0.6 ? "views are broadly aligned" : "the panel is split, so conviction is tempered"}. Risk-manager sizing limits apply.`,
    evidence: opinions.map((o) => ({ title: o.persona, score: o.score, source: o.vote })) };
  const debate = opinions.map((o) => {
    const peers = opinions.filter((p) => p.persona !== o.persona && (p.score - o.score) * (o.score || 1e-9) < 0);
    if (!peers.length) return `${o.persona}: no material disagreement with the panel; holding my ${o.vote} view.`;
    const peer = peers.reduce((a, p) => (Math.abs(p.score - o.score) > Math.abs(a.score - o.score) ? p : a));
    return `${o.persona} to ${peer.persona}: I see your ${peer.vote} case, but ${o.role.toLowerCase()} factors (${o.key_points[0] ?? "my evidence"}) dominate on my horizon. Staying ${o.vote}.`;
  });
  return { symbol: s, question: `Should the portfolio be long ${s}?`, timestamp: new Date().toISOString(), quote: quote(s), opinions, debate, votes, final,
    recommendation: { action: finalVote, score: final.score, confidence: final.confidence, max_position_pct: maxPos, requires_user_approval: true },
    disclaimer: "Not financial advice. Trades require user approval." };
}

// ---- Demo paper book (in-memory, per browser session) ----
const demoBook: { cash: number; holdings: Record<string, { qty: number; avg: number }>; recs: Recommendation[] } = {
  cash: 100000, holdings: { AAPL: { qty: 40, avg: 205 }, NVDA: { qty: 60, avg: 118 }, XOM: { qty: 50, avg: 110 }, JPM: { qty: 25, avg: 198 } }, recs: [],
};
demoBook.cash = 100000 - Object.entries(demoBook.holdings).reduce((a, [, h]) => a + h.qty * h.avg, 0);

export function portfolio(): PortfolioBundle {
  const positions: Position[] = Object.entries(demoBook.holdings).filter(([, h]) => h.qty > 0).map(([symbol, h]) => {
    const px = quote(symbol).price, mv = h.qty * px, pl = (px - h.avg) * h.qty;
    return { symbol, qty: h.qty, avg_entry_price: h.avg, current_price: px, market_value: +mv.toFixed(2), unrealized_pl: +pl.toFixed(2), unrealized_pl_pct: +((pl / (h.avg * h.qty)) * 100).toFixed(2), sector: SECTORS[symbol] };
  });
  const total = positions.reduce((a, p) => a + p.market_value, 0) || 1;
  positions.forEach((p) => (p.weight = +(p.market_value / total).toFixed(4)));
  const sector_weights: Record<string, number> = {};
  positions.forEach((p) => (sector_weights[p.sector!] = +((sector_weights[p.sector!] ?? 0) + p.weight!).toFixed(4)));
  const account: Account = { broker: "paper", account_id: "DEMO-0001", cash: +demoBook.cash.toFixed(2), buying_power: +demoBook.cash.toFixed(2), equity: +(demoBook.cash + total).toFixed(2), paper: true };
  return { account, positions, sector_weights, paper: true };
}

export function risk(): RiskReport {
  const p = portfolio().positions, syms = p.map((x) => x.symbol), total = p.reduce((a, x) => a + x.market_value, 0);
  const w = p.map((x) => x.market_value / total);
  const R = syms.map((s) => history(s, 252).map((b) => b.close).map((v, i, a) => (i ? v / a[i - 1] - 1 : 0)).slice(1));
  const spy = history("SPY", 252).map((b) => b.close).map((v, i, a) => (i ? v / a[i - 1] - 1 : 0)).slice(1);
  const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
  const cov = (a: number[], b: number[]) => { const ma = mean(a), mb = mean(b); return a.reduce((s, v, i) => s + (v - ma) * (b[i] - mb), 0) / (a.length - 1); };
  const betas = R.map((r) => cov(r, spy) / cov(spy, spy));
  const pr = spy.map((_, i) => R.reduce((s, r, j) => s + r[i] * w[j], 0)).sort((a, b) => a - b);
  const p5 = pr[Math.floor(pr.length * 0.05)];
  const beta = betas.reduce((s, b, i) => s + b * w[i], 0), hhi = w.reduce((s, x) => s + x * x, 0);
  const portVol = Math.sqrt(w.reduce((s, wi, i) => s + w.reduce((t, wj, j) => t + wi * wj * cov(R[i], R[j]), 0), 0) * 252);
  const SC: Record<string, [string, number]> = { rate_hike_100bp: ["Fed hikes 100bp", -0.08], rate_cut_100bp: ["Fed cuts 100bp", 0.06], recession: ["Recession", -0.25], election_shock: ["Contested election", -0.07], soft_landing: ["Soft landing", 0.12], oil_spike: ["Oil +40%", -0.05] };
  const scenarios: RiskReport["scenarios"] = {};
  Object.entries(SC).forEach(([k, [label, sh]]) => (scenarios[k] = { label, pnl: +(sh * beta * total).toFixed(2), pnl_pct: +(sh * beta * 100).toFixed(2) }));
  return { positions: p.length, total_value: +total.toFixed(2), annualized_volatility: +portVol.toFixed(4), beta: +beta.toFixed(3), var_95_1d: +(-p5 * total).toFixed(2),
    cvar_95_1d: +(-mean(pr.filter((x) => x <= p5)) * total).toFixed(2), concentration_hhi: +hhi.toFixed(4), effective_positions: +(1 / hhi).toFixed(2),
    per_position: syms.map((s, i) => ({ symbol: s, weight: +w[i].toFixed(4), beta: +betas[i].toFixed(3), vol: +(Math.sqrt(cov(R[i], R[i]) * 252)).toFixed(4) })),
    correlation: { symbols: syms, matrix: R.map((a) => R.map((b) => +(cov(a, b) / Math.sqrt(cov(a, a) * cov(b, b))).toFixed(3))) }, scenarios };
}

export function health(): HealthReport {
  const p = portfolio().positions, total = p.reduce((a, x) => a + x.market_value, 0);
  const holdings = p.map((x) => { const c = council(x.symbol); return { symbol: x.symbol, weight: +(x.market_value / total).toFixed(4), action: c.recommendation.action, score: c.final.score, summary: c.final.rationale }; });
  const ws = holdings.reduce((a, h) => a + h.score * h.weight, 0), conc = Math.max(...holdings.map((h) => h.weight));
  const suggestions = holdings.flatMap((h) => [...(h.weight > 0.3 ? [`Trim ${h.symbol}: ${(h.weight * 100).toFixed(0)}% exceeds 30% concentration limit.`] : []), ...(h.action === "SELL" && h.weight > 0.05 ? [`Review ${h.symbol}: council leans SELL (score ${h.score.toFixed(2)}).`] : [])]);
  return { health: ws > 0.1 && conc < 0.3 ? "healthy" : ws > -0.1 ? "watch" : "at risk", weighted_score: +ws.toFixed(3), max_concentration: +conc.toFixed(3), holdings, suggestions: suggestions.length ? suggestions : ["No rebalancing actions suggested by the council."], disclaimer: "Not financial advice. Trades require user approval." };
}

export function recommend(symbol: string, budget: number): { recommendation: Recommendation | null; council: CouncilResult; message: string } {
  const c = council(symbol);
  if (c.recommendation.action === "HOLD") return { recommendation: null, council: c, message: "Council recommends HOLD — no trade proposed." };
  const rec: Recommendation = { id: demoBook.recs.length + 1, token: `demo-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, symbol: c.symbol, side: c.recommendation.action === "BUY" ? "buy" : "sell",
    qty: +(budget / c.quote.price).toFixed(4), notional: null, order_type: "market", limit_price: null, stop_price: null, rationale: c.final.rationale, status: "pending", broker_order_id: null, created_at: new Date().toISOString() };
  demoBook.recs.unshift(rec);
  return { recommendation: rec, council: c, message: "Review and approve explicitly. Nothing is sent to the broker until you approve." };
}

export function decide(token: string, approve: boolean, qty?: number): { status: string; recommendation: Recommendation; order?: Record<string, unknown> } {
  const rec = demoBook.recs.find((r) => r.token === token);
  if (!rec) throw new Error("Recommendation not found");
  if (rec.status !== "pending") throw new Error(`Recommendation already ${rec.status}`);
  if (!approve) { rec.status = "rejected"; return { status: "rejected", recommendation: rec }; }
  const q = qty ?? rec.qty ?? 0, px = quote(rec.symbol).price, h = (demoBook.holdings[rec.symbol] ??= { qty: 0, avg: 0 });
  if (rec.side === "buy") { if (q * px > demoBook.cash) throw new Error("Insufficient paper cash"); h.avg = (h.avg * h.qty + q * px) / (h.qty + q); h.qty += q; demoBook.cash -= q * px; }
  else { if (q > h.qty + 1e-4) throw new Error("Insufficient paper position"); h.qty = Math.max(0, h.qty - q); demoBook.cash += q * px; }
  rec.status = "submitted"; rec.broker_order_id = `demo-${rec.id}`;
  return { status: "submitted", recommendation: rec, order: { broker: "paper", order_id: rec.broker_order_id, status: "filled", filled_avg_price: px, paper: true } };
}
export const recommendations = () => demoBook.recs;

export function backtest(symbol: string, strategy: string, days: number, cash: number): BacktestResult {
  const bars = history(symbol, days + 260), c = bars.map((b) => b.close);
  const smaAt = (i: number, n: number) => (i + 1 < n ? NaN : c.slice(i + 1 - n, i + 1).reduce((a, b) => a + b, 0) / n);
  const target: number[] = []; let holding = 0;
  for (let i = 0; i < c.length; i++) {
    const s20 = smaAt(i, 20), s50 = smaAt(i, 50), r63 = i >= 63 ? c[i] / c[i - 63] - 1 : NaN;
    const sd = i >= 19 ? Math.sqrt(c.slice(i - 19, i + 1).reduce((a, b) => a + (b - s20) ** 2, 0) / 19) : NaN, z = (c[i] - s20) / sd;
    const mom = isNaN(s50) || isNaN(r63) ? 0 : s20 > s50 && r63 > 0 ? 1 : 0;
    if (!isNaN(z)) { if (holding === 0 && z < -2) holding = 1; else if (holding === 1 && z >= 0) holding = 0; }
    const mr = holding, fund = 0.7;
    target.push(strategy === "momentum" ? mom : strategy === "mean_reversion" ? mr : strategy === "fundamental" ? fund : Math.min(1, 0.4 * mom + 0.2 * mr + 0.4 * fund));
  }
  const start = c.length - days; let cashL = cash, qty = 0; const curve: BacktestResult["equity_curve"] = [], trades: BacktestResult["trades"] = []; let open: BacktestResult["trades"][number] | null = null;
  for (let i = start; i < c.length; i++) {
    const port = cashL + qty * c[i], want = (port * target[i]) / c[i], delta = want - qty;
    if (Math.abs(delta * c[i]) > port * 0.01) { cashL -= delta * c[i] * 1.0003; qty = want;
      if (delta > 0 && !open) { open = { symbol, entry_date: bars[i].date, entry_price: c[i], qty: +qty.toFixed(4) }; trades.push(open); }
      else if (delta < 0 && open && qty < 1e-9) { open.exit_date = bars[i].date; open.exit_price = c[i]; open.pnl = +((c[i] - open.entry_price) * open.qty).toFixed(2); open = null; } }
    curve.push({ date: bars[i].date, equity: +(cashL + qty * c[i]).toFixed(2), benchmark: +((c[i] / c[start]) * cash).toFixed(2) });
  }
  const metrics = (eq: number[]) => { const r = eq.map((v, i, a) => (i ? v / a[i - 1] - 1 : 0)).slice(1), m = mean(r), sd = Math.sqrt(r.reduce((a, b) => a + (b - m) ** 2, 0) / (r.length - 1)); let peak = eq[0], mdd = 0; eq.forEach((v) => { peak = Math.max(peak, v); mdd = Math.min(mdd, v / peak - 1); });
    const total = eq[eq.length - 1] / eq[0] - 1, cagr = Math.pow(1 + total, 252 / eq.length) - 1;
    return { total_return: +total.toFixed(4), cagr: +cagr.toFixed(4), sharpe: +(((m - 0.04 / 252) / sd) * Math.sqrt(252)).toFixed(3), max_drawdown: +mdd.toFixed(4), volatility: +(sd * Math.sqrt(252)).toFixed(4), calmar: mdd < 0 ? +(cagr / -mdd).toFixed(3) : 0, days: eq.length }; };
  const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
  const eq = curve.map((x) => x.equity); let peak = eq[0];
  const closed = trades.filter((t) => t.pnl !== undefined), wins = closed.filter((t) => t.pnl! > 0);
  const labels: Record<string, string> = { momentum: "Momentum", mean_reversion: "Mean Reversion", fundamental: "Fundamental", ai_hybrid: "AI Hybrid" };
  return { label: "SIMULATION ONLY — paper trading, no real orders are placed.", symbol: symbol.toUpperCase(), strategy, strategy_label: labels[strategy] ?? strategy, days, initial_cash: cash, final_equity: eq[eq.length - 1],
    metrics: metrics(eq), benchmark_metrics: metrics(curve.map((x) => x.benchmark)), trade_stats: { trades: trades.length, closed: closed.length, win_rate: closed.length ? +(wins.length / closed.length).toFixed(4) : 0, avg_pnl: closed.length ? +mean(closed.map((t) => t.pnl!)).toFixed(2) : 0, profit_factor: 0 },
    equity_curve: curve, drawdown: eq.map((v) => { peak = Math.max(peak, v); return +(v / peak - 1).toFixed(4); }), trades };
}

const forwardSessions: Record<string, ForwardReport> = {};
export function forward(symbols: string[], strategy: string, cash: number, useCouncil: boolean, steps: number): ForwardReport {
  const id = `demo-${Date.now()}`;
  const rep: ForwardReport = { label: "SIMULATION ONLY — paper trading, no real orders are placed.", session_id: id, symbols, strategy, use_council: useCouncil, steps: 0,
    account: { broker: "paper", account_id: "SIM", cash, buying_power: cash, equity: cash, paper: true }, positions: [], metrics: {}, equity_history: [], log: [] };
  forwardSessions[id] = rep;
  return forwardStep(id, steps);
}
export function forwardStep(id: string, steps = 1): ForwardReport {
  const rep = forwardSessions[id]; if (!rep) throw new Error("Session not found");
  const hold: Record<string, { qty: number; avg: number }> = Object.fromEntries(rep.positions.map((p) => [p.symbol, { qty: p.qty, avg: p.avg_entry_price }]));
  for (let k = 0; k < steps; k++) {
    rep.steps++; const per = rep.account.equity / rep.symbols.length; const actions: ForwardReport["log"][number]["actions"] = [];
    for (const s of rep.symbols) {
      const c = useScore(s, rep.use_council), px = quote(s).price * (1 + (rep.steps * 0.0013 * (c.score + 0.2))), ind = indicators(s);
      const base = strategyExposure(rep.strategy, ind), tgt = Math.max(0, Math.min(1, base * (1 + 0.5 * c.score)));
      const h = (hold[s] ??= { qty: 0, avg: 0 }), want = (per * tgt) / px, delta = want - h.qty;
      if (Math.abs(delta * px) > Math.max(50, rep.account.equity * 0.005)) { if (delta > 0) { h.avg = (h.avg * h.qty + delta * px) / want; } h.qty = want; rep.account.cash -= delta * px; actions.push({ symbol: s, side: delta > 0 ? "buy" : "sell", qty: +Math.abs(delta).toFixed(4), price: px, target_exposure: +tgt.toFixed(3), council: rep.use_council ? { action: c.action, score: c.score } : null }); }
      else actions.push({ symbol: s, side: "hold", target_exposure: +tgt.toFixed(3), council: rep.use_council ? { action: c.action, score: c.score } : null });
    }
    rep.positions = Object.entries(hold).filter(([, h]) => h.qty > 0).map(([symbol, h]) => { const px = quote(symbol).price, mv = h.qty * px, pl = (px - h.avg) * h.qty; return { symbol, qty: +h.qty.toFixed(4), avg_entry_price: +h.avg.toFixed(2), current_price: px, market_value: +mv.toFixed(2), unrealized_pl: +pl.toFixed(2), unrealized_pl_pct: +((pl / (h.avg * h.qty || 1)) * 100).toFixed(2) }; });
    rep.account.equity = +(rep.account.cash + rep.positions.reduce((a, p) => a + p.market_value, 0)).toFixed(2); rep.account.cash = +rep.account.cash.toFixed(2); rep.account.buying_power = rep.account.cash;
    rep.log.push({ step: rep.steps, timestamp: new Date().toISOString(), equity: rep.account.equity, cash: rep.account.cash, actions }); rep.equity_history.push({ step: rep.steps, equity: rep.account.equity });
  }
  const eq = rep.equity_history.map((e) => e.equity); rep.metrics = { total_return: +(eq[eq.length - 1] / eq[0] - 1).toFixed(4), days: eq.length };
  return rep;
}
function useScore(s: string, useCouncil: boolean) { if (!useCouncil) return { action: "HOLD", score: 0 }; const c = council(s); return { action: c.recommendation.action, score: c.final.score }; }
function strategyExposure(strategy: string, ind: Indicators): number {
  const mom = ind.sma20! > ind.sma50! && (ind.return_3m ?? 0) > 0 ? 1 : 0, mr = ind.rsi14! < 30 ? 1 : 0, fund = 0.7;
  return strategy === "momentum" ? mom : strategy === "mean_reversion" ? mr : strategy === "fundamental" ? fund : 0.4 * mom + 0.2 * mr + 0.4 * fund;
}
