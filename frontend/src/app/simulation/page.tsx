"use client";
import { useEffect, useState } from "react";
import { DrawdownChart, EquityChart } from "@/components/Charts";
import { DataTable, Loading, Panel, Stat } from "@/components/Panel";
import { useTerminal } from "@/components/TerminalContext";
import { api, ApiError, fmt } from "@/lib/api";
import type { BacktestResult, ForwardReport, StrategyInfo } from "@/lib/types";

export default function SimulationPage() {
  const { symbol, toast } = useTerminal();
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [mode, setMode] = useState<"backtest" | "forward">("backtest");
  const [sym, setSym] = useState(symbol);
  const [strategy, setStrategy] = useState("momentum");
  const [days, setDays] = useState(365);
  const [cash, setCash] = useState(100000);
  const [useCouncil, setUseCouncil] = useState(false);
  const [symbols, setSymbols] = useState("AAPL,MSFT,NVDA");
  const [bt, setBt] = useState<BacktestResult | null>(null);
  const [fw, setFw] = useState<ForwardReport | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.strategies().then(setStrategies); }, []);
  useEffect(() => setSym(symbol), [symbol]);

  const guard = (e: unknown) => toast(e instanceof ApiError && e.status === 401 ? "Login required to run simulations" : (e as Error).message, "error");
  const runBacktest = async () => { setBusy(true); try { setBt(await api.backtest(sym.toUpperCase(), strategy, days, cash, useCouncil)); } catch (e) { guard(e); } finally { setBusy(false); } };
  const runForward = async () => { setBusy(true); try { setFw(await api.forward(symbols.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean), strategy, cash, useCouncil, 3)); } catch (e) { guard(e); } finally { setBusy(false); } };
  const stepForward = async () => { if (!fw) return; setBusy(true); try { setFw(await api.forwardStep(fw.session_id, 1)); } catch (e) { guard(e); } finally { setBusy(false); } };

  const M = (m: Record<string, number>, k: string, pct = false) => (m[k] == null ? "—" : pct ? fmt.pct(m[k], 2, 100) : m[k].toFixed(2));

  return (
    <div className="flex flex-col gap-2">
      <div className="border border-term-cyan text-term-cyan text-[11px] px-3 py-1 rounded-sm uppercase tracking-widest">⚠ Simulation only — paper trading. No real orders are placed from this page.</div>
      <Panel title="Strategy lab">
        <div className="flex flex-wrap gap-2 items-end">
          <div className="flex gap-1">{(["backtest", "forward"] as const).map((m) => <button key={m} className={`btn ${mode === m ? "border-term-amber text-term-amber" : ""}`} onClick={() => setMode(m)}>{m}</button>)}</div>
          {mode === "backtest"
            ? <label className="text-term-dim text-[10px]">SYMBOL<input className="input w-24 uppercase" value={sym} onChange={(e) => setSym(e.target.value)} /></label>
            : <label className="text-term-dim text-[10px]">SYMBOLS (comma)<input className="input w-56 uppercase" value={symbols} onChange={(e) => setSymbols(e.target.value)} /></label>}
          <label className="text-term-dim text-[10px]">STRATEGY
            <select className="input" value={strategy} onChange={(e) => setStrategy(e.target.value)}>{strategies.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}</select></label>
          {mode === "backtest" && <label className="text-term-dim text-[10px]">DAYS<input className="input w-20" type="number" min={60} max={1200} value={days} onChange={(e) => setDays(+e.target.value)} /></label>}
          <label className="text-term-dim text-[10px]">CASH<input className="input w-28" type="number" min={1000} value={cash} onChange={(e) => setCash(+e.target.value)} /></label>
          <label className="text-[11px] flex items-center gap-1"><input type="checkbox" checked={useCouncil} onChange={(e) => setUseCouncil(e.target.checked)} /> Council-driven</label>
          {mode === "backtest" ? <button className="btn btn-primary" disabled={busy} onClick={runBacktest}>{busy ? "Running…" : "Run backtest"}</button>
            : <><button className="btn btn-primary" disabled={busy} onClick={runForward}>{busy ? "Running…" : "Start forward sim"}</button><button className="btn" disabled={busy || !fw} onClick={stepForward}>Step +1</button></>}
        </div>
        <p className="text-[10px] text-term-dim mt-1">{strategies.find((s) => s.key === strategy)?.description}</p>
      </Panel>

      {mode === "backtest" && bt && (
        <>
          <div className="grid grid-cols-3 md:grid-cols-6 xl:grid-cols-9 gap-2">
            <Panel title="Final equity"><span className="text-sm">{fmt.money(bt.final_equity)}</span></Panel>
            <Panel title="Total return"><span className={`text-sm ${bt.metrics.total_return >= 0 ? "up" : "down"}`}>{M(bt.metrics, "total_return", true)}</span></Panel>
            <Panel title="CAGR"><span className="text-sm">{M(bt.metrics, "cagr", true)}</span></Panel>
            <Panel title="Sharpe"><span className="text-sm">{M(bt.metrics, "sharpe")}</span></Panel>
            <Panel title="Sortino"><span className="text-sm">{M(bt.metrics, "sortino")}</span></Panel>
            <Panel title="Max drawdown"><span className="text-sm down">{M(bt.metrics, "max_drawdown", true)}</span></Panel>
            <Panel title="Volatility"><span className="text-sm">{M(bt.metrics, "volatility", true)}</span></Panel>
            <Panel title="Trades"><span className="text-sm">{bt.trade_stats.trades} · win {(bt.trade_stats.win_rate * 100).toFixed(0)}%</span></Panel>
            <Panel title="B&H Sharpe"><span className="text-sm text-term-dim">{M(bt.benchmark_metrics, "sharpe")} / {M(bt.benchmark_metrics, "total_return", true)}</span></Panel>
          </div>
          <Panel title={`${bt.symbol} · ${bt.strategy_label} vs buy & hold`} className="min-h-[300px]"><div className="h-[280px]"><EquityChart data={bt.equity_curve} /></div></Panel>
          <Panel title="Drawdown" className="min-h-[160px]"><div className="h-[140px]"><DrawdownChart data={bt.equity_curve.map((e, i) => ({ date: e.date, dd: bt.drawdown[i] }))} /></div></Panel>
          <Panel title="Trade log">
            <DataTable rows={bt.trades as unknown as Record<string, unknown>[]} empty="No trades triggered" columns={[
              { key: "entry_date", label: "Entry" }, { key: "entry_price", label: "Entry px", render: (r) => fmt.money(r.entry_price as number) }, { key: "qty", label: "Qty" },
              { key: "exit_date", label: "Exit", render: (r) => String(r.exit_date ?? "open") }, { key: "exit_price", label: "Exit px", render: (r) => r.exit_price ? fmt.money(r.exit_price as number) : "—" },
              { key: "pnl", label: "P/L", render: (r) => r.pnl == null ? "—" : <span className={(r.pnl as number) >= 0 ? "up" : "down"}>{fmt.money(r.pnl as number)}</span> },
            ]} />
          </Panel>
        </>
      )}

      {mode === "forward" && fw && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            <Panel title="Session"><span className="text-[11px]">{fw.session_id.slice(0, 8)} · step {fw.steps}</span></Panel>
            <Panel title="Equity"><span className="text-sm">{fmt.money(fw.account.equity)}</span></Panel>
            <Panel title="Cash"><span className="text-sm">{fmt.money(fw.account.cash)}</span></Panel>
            <Panel title="Return"><span className={`text-sm ${(fw.metrics.total_return ?? 0) >= 0 ? "up" : "down"}`}>{M(fw.metrics, "total_return", true)}</span></Panel>
            <Panel title="Council"><span className="text-sm">{fw.use_council ? "ON" : "OFF"}</span></Panel>
          </div>
          <Panel title="Equity by step" className="min-h-[220px]"><div className="h-[200px]">{fw.equity_history.length > 1 ? <EquityChart data={fw.equity_history} /> : <Loading label="Need more steps" />}</div></Panel>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-2">
            <Panel title="Positions">
              <DataTable rows={fw.positions as unknown as Record<string, unknown>[]} empty="Flat" columns={[{ key: "symbol", label: "Sym" }, { key: "qty", label: "Qty" }, { key: "avg_entry_price", label: "Avg", render: (r) => fmt.money(r.avg_entry_price as number) }, { key: "market_value", label: "Value", render: (r) => fmt.money(r.market_value as number) }, { key: "unrealized_pl", label: "P/L", render: (r) => <span className={(r.unrealized_pl as number) >= 0 ? "up" : "down"}>{fmt.money(r.unrealized_pl as number)}</span> }]} />
            </Panel>
            <Panel title="Decision log">
              <div className="space-y-2 text-[11px]">{[...fw.log].reverse().map((l) => (
                <div key={l.step} className="border-l-2 border-term-border pl-2">
                  <div className="text-term-dim">Step {l.step} · {new Date(l.timestamp).toLocaleTimeString()} · equity {fmt.money(l.equity)}</div>
                  {l.actions.map((a, i) => <div key={i}><b className={a.side === "buy" ? "up" : a.side === "sell" ? "down" : "text-term-dim"}>{a.side.toUpperCase()}</b> {a.symbol} {a.qty ? `×${a.qty}` : ""} → exposure {(a.target_exposure * 100).toFixed(0)}%{a.council ? ` · council ${a.council.action} (${a.council.score >= 0 ? "+" : ""}${a.council.score.toFixed(2)})` : ""}</div>)}
                </div>))}</div>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
