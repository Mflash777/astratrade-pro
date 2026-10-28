/**
 * API client. Talks to the FastAPI backend when NEXT_PUBLIC_API_URL is set and
 * reachable; otherwise transparently falls back to demo mode (mock.ts) so the
 * static GitHub Pages build works standalone.
 */
import * as mock from "./mock";
import type {
  AuthUser, BacktestResult, Bar, CouncilResult, ForwardReport, FundamentalsBundle, HealthReport, Indicators, MacroBundle,
  NewsBundle, PortfolioBundle, Quote, Recommendation, RiskReport, SectorRow, StrategyInfo,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
let demoMode = !API_URL;
const listeners = new Set<(demo: boolean) => void>();
export const isDemo = () => demoMode;
export const onModeChange = (fn: (d: boolean) => void) => { listeners.add(fn); return () => listeners.delete(fn); };
function setDemo(d: boolean) { if (d !== demoMode) { demoMode = d; listeners.forEach((f) => f(d)); } }

const TOKEN_KEY = "atp_token";
export const getToken = () => (typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY));
export const setToken = (t: string | null) => { if (typeof window !== "undefined") { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } };

export class ApiError extends Error { constructor(public status: number, message: string) { super(message); } }

async function request<T>(path: string, init: RequestInit = {}, auth = false): Promise<T> {
  if (!API_URL) throw new ApiError(0, "demo");
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init.headers as Record<string, string>) };
  const tok = getToken();
  if (auth && tok) headers.Authorization = `Bearer ${tok}`;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    setDemo(true);
    throw new ApiError(0, "Backend unreachable — demo mode");
  }
  setDemo(false);
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j); } catch { /* ignore */ }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

/** Try the backend; on network failure use the demo generator. Auth/validation errors are surfaced. */
async function withFallback<T>(live: () => Promise<T>, demo: () => T): Promise<T> {
  try { return await live(); } catch (e) {
    if (e instanceof ApiError && e.status === 0) return demo();
    throw e;
  }
}

export const api = {
  // ---- auth ----
  async login(email: string, password: string): Promise<AuthUser> {
    if (!API_URL) { setDemo(true); return { id: 0, email: "demo@astratrade.local", role: "user", subscription_tier: "pro", api_key: null }; }
    const body = new URLSearchParams({ username: email, password });
    const r = await fetch(`${API_URL}/api/auth/login`, { method: "POST", body });
    if (!r.ok) throw new ApiError(r.status, "Incorrect email or password");
    const j = await r.json(); setToken(j.access_token); setDemo(false); return j.user;
  },
  register: (email: string, password: string) => request<AuthUser>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => withFallback(() => request<AuthUser>("/api/auth/me", {}, true), () => ({ id: 0, email: "demo@astratrade.local", role: "user", subscription_tier: "pro", api_key: null })),
  logout: () => setToken(null),

  // ---- market ----
  quotes: (symbols: string[]) => withFallback(() => request<Quote[]>(`/api/market/quotes?symbols=${symbols.join(",")}`), () => symbols.map(mock.quote)),
  quote: (s: string) => withFallback(() => request<Quote>(`/api/market/quote/${s}`), () => mock.quote(s)),
  history: (s: string, days = 180) => withFallback(() => request<{ bars: Bar[] }>(`/api/market/history/${s}?days=${days}`).then((r) => r.bars), () => mock.history(s, days)),
  indicators: (s: string) => withFallback(() => request<Indicators>(`/api/market/indicators/${s}`), () => mock.indicators(s)),
  fundamentals: (s: string) => withFallback(() => request<FundamentalsBundle>(`/api/market/fundamentals/${s}`), () => mock.fundamentals(s)),
  news: (s: string) => withFallback(() => request<NewsBundle>(`/api/market/news/${s}`), () => mock.news(s)),
  macro: () => withFallback(() => request<MacroBundle>("/api/market/macro"), () => mock.macro()),
  sectors: () => withFallback(() => request<SectorRow[]>("/api/market/sectors"), () => mock.sectors()),

  // ---- council ----
  council: (symbol: string, question?: string) => withFallback(() => request<CouncilResult>("/api/council/analyze", { method: "POST", body: JSON.stringify({ symbol, question }) }, true), () => mock.council(symbol)),

  // ---- brokers / trades (user-approved only) ----
  recommend: (symbol: string, budget: number) => withFallback(() => request<{ recommendation: Recommendation | null; council: CouncilResult; message: string }>("/api/brokers/recommend", { method: "POST", body: JSON.stringify({ symbol, budget }) }, true), () => mock.recommend(symbol, budget)),
  recommendations: () => withFallback(() => request<Recommendation[]>("/api/brokers/recommendations", {}, true), () => mock.recommendations()),
  decide: (token: string, approve: boolean, overrides: { qty?: number; order_type?: string; limit_price?: number; stop_price?: number; broker?: string; confirm_phrase?: string } = {}) =>
    withFallback(() => request<{ status: string; recommendation: Recommendation; order?: Record<string, unknown> }>("/api/brokers/orders", { method: "POST", body: JSON.stringify({ approval_token: token, approve, ...overrides }) }, true), () => mock.decide(token, approve, overrides.qty)),

  // ---- portfolio ----
  portfolio: () => withFallback(() => request<PortfolioBundle>("/api/portfolio/", {}, true), () => mock.portfolio()),
  risk: () => withFallback(() => request<RiskReport>("/api/portfolio/risk", {}, true), () => mock.risk()),
  health: () => withFallback(() => request<HealthReport>("/api/portfolio/health", {}, true), () => mock.health()),

  // ---- simulation ----
  strategies: () => withFallback(() => request<StrategyInfo[]>("/api/simulation/strategies"), () => [
    { key: "momentum", label: "Momentum", description: "Long when fast SMA is above slow SMA and 3-month return is positive." },
    { key: "mean_reversion", label: "Mean Reversion", description: "Buy when price is >2σ below its 20-day mean; exit at the mean." },
    { key: "fundamental", label: "Fundamental", description: "Hold when fundamentals score is positive; scale into drawdowns." },
    { key: "ai_hybrid", label: "AI Hybrid", description: "Blends the three strategies, tilted by the Council's score." },
  ]),
  backtest: (symbol: string, strategy: string, days: number, initial_cash: number, use_council: boolean) =>
    withFallback(() => request<BacktestResult>("/api/simulation/backtest", { method: "POST", body: JSON.stringify({ symbol, strategy, days, initial_cash, use_council }) }, true), () => mock.backtest(symbol, strategy, days, initial_cash)),
  forward: (symbols: string[], strategy: string, initial_cash: number, use_council: boolean, steps: number) =>
    withFallback(() => request<ForwardReport>("/api/simulation/forward", { method: "POST", body: JSON.stringify({ symbols, strategy, initial_cash, use_council, steps }) }, true), () => mock.forward(symbols, strategy, initial_cash, use_council, steps)),
  forwardStep: (id: string, steps = 1) => withFallback(() => request<ForwardReport>(`/api/simulation/forward/${id}/step?steps=${steps}`, { method: "POST" }, true), () => mock.forwardStep(id, steps)),
};

export const fmt = {
  money: (n: number | null | undefined, d = 2) => (n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: d, maximumFractionDigits: d })),
  num: (n: number | null | undefined, d = 2) => (n == null ? "—" : n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })),
  pct: (n: number | null | undefined, d = 2, mult = 1) => (n == null ? "—" : `${n * mult >= 0 ? "+" : ""}${(n * mult).toFixed(d)}%`),
  big: (n: number | null | undefined) => (n == null ? "—" : n >= 1e12 ? `${(n / 1e12).toFixed(2)}T` : n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n.toLocaleString()),
};
