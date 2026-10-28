export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  high: number;
  low: number;
  sector: string;
  timestamp: string;
}

export interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Indicators {
  price: number;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  rsi14: number | null;
  macd: number | null;
  macd_signal: number | null;
  bollinger_upper: number | null;
  bollinger_lower: number | null;
  volatility_30d_annualized: number;
  return_1m: number | null;
  return_3m: number | null;
  avg_volume_20d: number;
  volume_ratio: number;
}

export interface SectorRow {
  sector: string;
  return_1m: number;
  return_3m: number;
  relative_1m: number;
  relative_3m: number;
  rank: number;
  phase: string;
  constituents: string[];
}

export interface Fundamentals {
  name: string;
  sector: string;
  market_cap: number;
  pe_ratio: number | null;
  forward_pe: number | null;
  peg: number | null;
  eps: number | null;
  revenue_ttm: number | null;
  profit_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  dividend_yield: number | null;
  beta: number | null;
  revenue_growth_yoy: number | null;
  earnings_growth_yoy: number | null;
  source: string;
}

export interface FundamentalsBundle {
  fundamentals: Fundamentals;
  earnings: { quarter: string; eps_surprise_pct: number; revenue_surprise_pct: number; guidance: string; management_tone: string; key_themes: string[] };
  filings: { form: string; filed: string; description: string; accession: string }[];
  analysts: { buy: number; hold: number; sell: number; consensus: string; target_upside_pct: number };
}

export interface NewsItem { title: string; source: string; published: string; url: string; sentiment: number }
export interface NewsBundle {
  news: NewsItem[];
  social: { mentions_24h: number; mention_change_pct: number; bullish_pct: number; platforms: Record<string, number> };
}

export interface MacroBundle {
  snapshot: { fed_funds_rate: number; cpi_yoy: number; unemployment_rate: number; gdp_growth: number; treasury_10y: number; treasury_2y: number; source: string };
  calendar: { date: string; event: string; impact: string }[];
  political: { date: string; event: string; risk: string; sectors: string[] }[];
  prediction_markets: { question: string; yes_probability: number | null; volume_24h: number | null; source: string }[];
}

export interface Opinion {
  persona: string;
  role: string;
  score: number;
  confidence: number;
  vote: "BUY" | "HOLD" | "SELL";
  rationale: string;
  key_points: string[];
  evidence: { title: string; score: number; source: string }[];
}

export interface CouncilResult {
  symbol: string;
  question: string;
  timestamp: string;
  quote: Quote;
  opinions: Opinion[];
  debate: string[];
  votes: { BUY: number; HOLD: number; SELL: number };
  final: Opinion;
  recommendation: { action: string; score: number; confidence: number; max_position_pct: number; requires_user_approval: boolean };
  disclaimer: string;
  run_id?: number;
}

export interface Recommendation {
  id: number;
  token: string;
  symbol: string;
  side: "buy" | "sell";
  qty: number | null;
  notional: number | null;
  order_type: string;
  limit_price: number | null;
  stop_price: number | null;
  rationale: string;
  status: string;
  broker_order_id: string | null;
  created_at: string;
}

export interface Position {
  symbol: string; qty: number; avg_entry_price: number; current_price: number; market_value: number;
  unrealized_pl: number; unrealized_pl_pct: number; weight?: number; sector?: string;
}
export interface Account { broker: string; account_id: string; cash: number; buying_power: number; equity: number; paper: boolean }
export interface PortfolioBundle { account: Account; positions: Position[]; sector_weights: Record<string, number>; paper: boolean }

export interface RiskReport {
  positions: number; total_value: number; annualized_volatility: number; beta: number; var_95_1d: number; cvar_95_1d: number;
  concentration_hhi: number; effective_positions: number;
  per_position: { symbol: string; weight: number; beta: number; vol: number }[];
  correlation: { symbols: string[]; matrix: number[][] };
  scenarios: Record<string, { label: string; pnl: number; pnl_pct: number }>;
  message?: string;
}

export interface HealthReport {
  health: string; weighted_score?: number; max_concentration?: number;
  holdings: { symbol: string; weight: number; action: string; score: number; summary: string }[];
  suggestions: string[]; disclaimer: string;
}

export interface BacktestResult {
  label: string; symbol: string; strategy: string; strategy_label: string; days: number; initial_cash: number; final_equity: number;
  metrics: Record<string, number>; benchmark_metrics: Record<string, number>;
  trade_stats: { trades: number; closed: number; win_rate: number; avg_pnl: number; profit_factor: number };
  equity_curve: { date: string; equity: number; benchmark: number }[]; drawdown: number[];
  trades: { symbol: string; entry_date: string; entry_price: number; qty: number; exit_date?: string; exit_price?: number; pnl?: number }[];
}

export interface ForwardReport {
  label: string; session_id: string; symbols: string[]; strategy: string; use_council: boolean; steps: number;
  account: Account; positions: Position[]; metrics: Record<string, number>;
  equity_history: { step: number; equity: number }[];
  log: { step: number; timestamp: string; equity: number; cash: number; actions: { symbol: string; side: string; qty?: number; price?: number | null; target_exposure: number; council: { action: string; score: number } | null }[] }[];
}

export interface StrategyInfo { key: string; label: string; description: string }
export interface AuthUser { id: number; email: string; role: string; subscription_tier: string; api_key: string | null }
