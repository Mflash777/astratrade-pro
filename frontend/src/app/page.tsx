"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PriceChart, VolatilityChart, VolumeChart } from "@/components/Charts";
import { DataTable, Loading, Panel, Stat } from "@/components/Panel";
import { SectorHeatmap } from "@/components/SectorHeatmap";
import { COMMANDS, useTerminal } from "@/components/TerminalContext";
import { api, fmt } from "@/lib/api";
import type { Bar, FundamentalsBundle, Indicators, MacroBundle, NewsBundle, Quote, SectorRow } from "@/lib/types";

const TABS = ["chart", "fundamentals", "news", "macro", "sectors", "help"] as const;
type Tab = (typeof TABS)[number];
const RANGES = [60, 120, 180, 365, 730];

function Terminal() {
  const { symbol, setSymbol } = useTerminal();
  const params = useSearchParams();
  const router = useRouter();
  const tab = (TABS.includes(params.get("tab") as Tab) ? params.get("tab") : "chart") as Tab;
  const setTab = (t: Tab) => router.push(t === "chart" ? "/" : `/?tab=${t}`);

  const [quote, setQuote] = useState<Quote | null>(null);
  const [bars, setBars] = useState<Bar[]>([]);
  const [days, setDays] = useState(180);
  const [ind, setInd] = useState<Indicators | null>(null);
  const [fund, setFund] = useState<FundamentalsBundle | null>(null);
  const [news, setNews] = useState<NewsBundle | null>(null);
  const [macro, setMacro] = useState<MacroBundle | null>(null);
  const [sectors, setSectors] = useState<SectorRow[]>([]);
  const [watch, setWatch] = useState<Quote[]>([]);
  const [filter, setFilter] = useState("");
  const [metric, setMetric] = useState<"relative_3m" | "relative_1m" | "return_1m" | "return_3m">("relative_3m");

  useEffect(() => {
    setFund(null); setNews(null);
    api.quote(symbol).then(setQuote);
    api.indicators(symbol).then(setInd);
    api.fundamentals(symbol).then(setFund);
    api.news(symbol).then(setNews);
    const t = setInterval(() => api.quote(symbol).then(setQuote), 10000);
    return () => clearInterval(t);
  }, [symbol]);
  useEffect(() => { api.history(symbol, days).then(setBars); }, [symbol, days]);
  useEffect(() => {
    api.macro().then(setMacro);
    api.sectors().then(setSectors);
    api.quotes(["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "XOM", "UNH", "KO", "CAT", "BA", "PFE", "NEE"]).then(setWatch);
  }, []);

  return (
    <div className="grid grid-cols-12 gap-2 h-full min-h-[calc(100vh-110px)]">
      {/* Left rail: quote + indicators + watchlist */}
      <div className="col-span-12 lg:col-span-3 flex flex-col gap-2 min-h-0">
        <Panel title={`${symbol} · ${quote?.sector ?? ""}`} right={quote ? new Date(quote.timestamp).toLocaleTimeString() : ""}>
          {quote ? (
            <div className="grid grid-cols-2 gap-2">
              <Stat label="Last" value={<span className="text-2xl">{fmt.money(quote.price)}</span>} delta={quote.change_pct} className="col-span-2" />
              <Stat label="High" value={fmt.money(quote.high)} /><Stat label="Low" value={fmt.money(quote.low)} />
              <Stat label="Volume" value={fmt.big(quote.volume)} /><Stat label="Vol ratio" value={ind ? `${ind.volume_ratio.toFixed(2)}x` : "—"} />
            </div>
          ) : <Loading />}
        </Panel>
        <Panel title="Technicals">
          {ind ? (
            <div className="grid grid-cols-2 gap-y-1 text-[11px]">
              {[["SMA20", ind.sma20], ["SMA50", ind.sma50], ["SMA200", ind.sma200], ["RSI(14)", ind.rsi14], ["MACD", ind.macd], ["Signal", ind.macd_signal],
                ["BB upper", ind.bollinger_upper], ["BB lower", ind.bollinger_lower]].map(([k, v]) => (
                <div key={k as string} className="flex justify-between pr-3"><span className="text-term-dim">{k}</span><span>{fmt.num(v as number | null)}</span></div>))}
              <div className="flex justify-between pr-3"><span className="text-term-dim">Vol 30d</span><span>{fmt.pct(ind.volatility_30d_annualized, 1, 100).replace("+", "")}</span></div>
              <div className="flex justify-between pr-3"><span className="text-term-dim">Ret 1m</span><span className={(ind.return_1m ?? 0) >= 0 ? "up" : "down"}>{fmt.pct(ind.return_1m, 1, 100)}</span></div>
              <div className="flex justify-between pr-3"><span className="text-term-dim">Ret 3m</span><span className={(ind.return_3m ?? 0) >= 0 ? "up" : "down"}>{fmt.pct(ind.return_3m, 1, 100)}</span></div>
            </div>
          ) : <Loading />}
        </Panel>
        <Panel title="Watchlist" className="flex-1" right={<input className="input w-24 py-0" placeholder="filter" value={filter} onChange={(e) => setFilter(e.target.value)} />}>
          <DataTable rows={watch as unknown as Record<string, unknown>[]} filter={filter} onRowClick={(r) => setSymbol(String(r.symbol))} columns={[
            { key: "symbol", label: "Sym" },
            { key: "price", label: "Last", render: (r) => fmt.num(r.price as number) },
            { key: "change_pct", label: "Chg%", render: (r) => <span className={(r.change_pct as number) >= 0 ? "up" : "down"}>{fmt.pct(r.change_pct as number)}</span> },
            { key: "sector", label: "Sector", className: "hidden xl:table-cell" },
          ]} />
        </Panel>
      </div>

      {/* Main area */}
      <div className="col-span-12 lg:col-span-9 flex flex-col gap-2 min-h-0">
        <div className="flex gap-1 flex-wrap">
          {TABS.map((t) => <button key={t} className={`btn ${tab === t ? "border-term-amber text-term-amber" : ""}`} onClick={() => setTab(t)}>{t}</button>)}
          {tab === "chart" && <span className="ml-auto flex gap-1">{RANGES.map((d) => <button key={d} className={`btn ${days === d ? "border-term-amber text-term-amber" : ""}`} onClick={() => setDays(d)}>{d}d</button>)}</span>}
          {tab === "sectors" && <span className="ml-auto flex gap-1">{(["relative_3m", "relative_1m", "return_3m", "return_1m"] as const).map((m) => <button key={m} className={`btn ${metric === m ? "border-term-amber text-term-amber" : ""}`} onClick={() => setMetric(m)}>{m.replace("_", " ")}</button>)}</span>}
        </div>

        {tab === "chart" && (
          <>
            <Panel title={`${symbol} price · SMA20 (cyan) · SMA50 (violet)`} className="flex-[3] min-h-[280px]"><div className="h-full min-h-[260px]">{bars.length ? <PriceChart bars={bars} /> : <Loading />}</div></Panel>
            <div className="grid grid-cols-2 gap-2 flex-[1.2] min-h-[160px]">
              <Panel title="Volume"><div className="h-full min-h-[130px]">{bars.length ? <VolumeChart bars={bars} /> : <Loading />}</div></Panel>
              <Panel title="Realized volatility (20d, annualized)"><div className="h-full min-h-[130px]">{bars.length ? <VolatilityChart bars={bars} /> : <Loading />}</div></Panel>
            </div>
          </>
        )}

        {tab === "fundamentals" && (fund ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 flex-1">
            <Panel title={`${fund.fundamentals.name} · financials`} right={`source: ${fund.fundamentals.source}`}>
              <div className="grid grid-cols-2 gap-y-1 text-[11px]">
                {[["Market cap", fmt.big(fund.fundamentals.market_cap)], ["Revenue TTM", fmt.big(fund.fundamentals.revenue_ttm)], ["P/E", fmt.num(fund.fundamentals.pe_ratio)], ["Forward P/E", fmt.num(fund.fundamentals.forward_pe)],
                  ["PEG", fmt.num(fund.fundamentals.peg)], ["EPS", fmt.num(fund.fundamentals.eps)], ["Profit margin", fmt.pct(fund.fundamentals.profit_margin, 1, 100).replace("+", "")], ["ROE", fmt.pct(fund.fundamentals.roe, 1, 100).replace("+", "")],
                  ["Rev growth YoY", fmt.pct(fund.fundamentals.revenue_growth_yoy, 1, 100)], ["EPS growth YoY", fmt.pct(fund.fundamentals.earnings_growth_yoy, 1, 100)], ["Debt/Equity", fmt.num(fund.fundamentals.debt_to_equity)], ["Div yield", fmt.pct(fund.fundamentals.dividend_yield, 2, 100).replace("+", "")], ["Beta", fmt.num(fund.fundamentals.beta)]]
                  .map(([k, v]) => <div key={k} className="flex justify-between pr-4"><span className="text-term-dim">{k}</span><span>{v}</span></div>)}
              </div>
            </Panel>
            <Panel title={`Earnings · ${fund.earnings.quarter}`}>
              <div className="text-[11px] space-y-1">
                <div>EPS surprise <span className={fund.earnings.eps_surprise_pct >= 0 ? "up" : "down"}>{fmt.pct(fund.earnings.eps_surprise_pct)}</span> · Revenue surprise <span className={fund.earnings.revenue_surprise_pct >= 0 ? "up" : "down"}>{fmt.pct(fund.earnings.revenue_surprise_pct)}</span></div>
                <div>Guidance <b className="text-term-amber uppercase">{fund.earnings.guidance}</b> · tone {fund.earnings.management_tone}</div>
                <div className="text-term-dim">Themes: {fund.earnings.key_themes.join(" · ")}</div>
                <div className="pt-2 border-t border-term-border">Analyst consensus <b className="text-term-amber">{fund.analysts.consensus}</b> — {fund.analysts.buy} Buy / {fund.analysts.hold} Hold / {fund.analysts.sell} Sell · target upside {fmt.pct(fund.analysts.target_upside_pct, 1)}</div>
              </div>
            </Panel>
            <Panel title="SEC filings" className="md:col-span-2">
              <DataTable rows={fund.filings as unknown as Record<string, unknown>[]} columns={[{ key: "form", label: "Form" }, { key: "filed", label: "Filed" }, { key: "description", label: "Description" }, { key: "accession", label: "Accession" }]} />
            </Panel>
          </div>
        ) : <Loading />)}

        {tab === "news" && (news ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 flex-1">
            <Panel title="Headlines" className="md:col-span-2">
              <ul className="space-y-1.5 text-[11px]">{news.news.map((n, i) => (
                <li key={i} className="flex gap-2 items-start">
                  <span className={`tag shrink-0 ${n.sentiment > 0 ? "border-term-green text-term-green" : n.sentiment < 0 ? "border-term-red text-term-red" : "border-term-dim text-term-dim"}`}>{n.sentiment > 0 ? "POS" : n.sentiment < 0 ? "NEG" : "NEU"}</span>
                  <span><a href={n.url} target="_blank" rel="noreferrer" className="hover:text-term-amber">{n.title}</a><span className="text-term-dim"> — {n.source}, {new Date(n.published).toLocaleString()}</span></span>
                </li>))}</ul>
            </Panel>
            <Panel title="Social sentiment">
              <Stat label="Mentions 24h" value={news.social.mentions_24h.toLocaleString()} delta={news.social.mention_change_pct} />
              <div className="mt-2 text-[10px] text-term-dim uppercase">Bullish share</div>
              <div className="h-3 bg-term-red/60 rounded-sm overflow-hidden"><div className="h-full bg-term-green" style={{ width: `${news.social.bullish_pct}%` }} /></div>
              <div className="text-[11px] mt-1">{news.social.bullish_pct}% bullish</div>
              <div className="mt-2 text-[11px] space-y-1">{Object.entries(news.social.platforms).map(([p, v]) => <div key={p} className="flex justify-between"><span className="text-term-dim">{p}</span><span className={v >= 0 ? "up" : "down"}>{v >= 0 ? "+" : ""}{v.toFixed(2)}</span></div>)}</div>
            </Panel>
          </div>
        ) : <Loading />)}

        {tab === "macro" && (macro ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 flex-1">
            <Panel title="Macro snapshot" right={`source: ${macro.snapshot.source}`}>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Fed funds" value={`${macro.snapshot.fed_funds_rate.toFixed(2)}%`} /><Stat label="CPI YoY" value={`${macro.snapshot.cpi_yoy.toFixed(1)}%`} /><Stat label="Unemployment" value={`${macro.snapshot.unemployment_rate.toFixed(1)}%`} />
                <Stat label="GDP growth" value={`${macro.snapshot.gdp_growth.toFixed(1)}%`} /><Stat label="10y" value={`${macro.snapshot.treasury_10y.toFixed(2)}%`} /><Stat label="10y–2y" value={`${(macro.snapshot.treasury_10y - macro.snapshot.treasury_2y).toFixed(2)}%`} />
              </div>
            </Panel>
            <Panel title="Economic calendar">
              <DataTable rows={macro.calendar as unknown as Record<string, unknown>[]} columns={[{ key: "date", label: "Date" }, { key: "event", label: "Event" }, { key: "impact", label: "Impact", render: (r) => <span className={r.impact === "high" ? "text-term-red" : r.impact === "medium" ? "text-term-amber" : "text-term-dim"}>{String(r.impact)}</span> }]} />
            </Panel>
            <Panel title="Political & regulatory events">
              <DataTable rows={macro.political as unknown as Record<string, unknown>[]} columns={[{ key: "date", label: "Date" }, { key: "event", label: "Event" }, { key: "risk", label: "Risk" }, { key: "sectors", label: "Sectors", render: (r) => (r.sectors as string[]).join(", ") }]} />
            </Panel>
            <Panel title="Prediction markets">
              <DataTable rows={macro.prediction_markets as unknown as Record<string, unknown>[]} columns={[{ key: "question", label: "Market" }, { key: "yes_probability", label: "P(yes)", render: (r) => r.yes_probability == null ? "—" : `${((r.yes_probability as number) * 100).toFixed(0)}%` }, { key: "volume_24h", label: "Vol 24h", render: (r) => fmt.big(r.volume_24h as number) }, { key: "source", label: "Src" }]} />
            </Panel>
          </div>
        ) : <Loading />)}

        {tab === "sectors" && <Panel title="Sector rotation heatmap" className="flex-1" right="click a ticker to load it">{sectors.length ? <SectorHeatmap rows={sectors} metric={metric} /> : <Loading />}</Panel>}

        {tab === "help" && (
          <Panel title="Keyboard commands" className="flex-1">
            <table className="table-term"><thead><tr><th>Mnemonic</th><th>Function</th></tr></thead>
              <tbody>{COMMANDS.map((c) => <tr key={c.key}><td className="text-term-amber">{c.key}</td><td>{c.label}</td></tr>)}</tbody></table>
            <p className="mt-3 text-[11px] text-term-dim">Open the palette with <span className="kbd">/</span> or <span className="kbd">⌘K</span>, type <b>TICKER FUNCTION</b> (e.g. <b>NVDA DES</b>) and press Enter. F-keys jump directly: F2 chart · F3 fundamentals · F4 news · F5 macro · F6 sectors · F7 council · F8 portfolio · F9 simulation.</p>
          </Panel>
        )}
      </div>
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<Loading />}><Terminal /></Suspense>;
}
