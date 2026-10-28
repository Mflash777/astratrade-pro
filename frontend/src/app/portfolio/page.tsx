"use client";
import { useCallback, useEffect, useState } from "react";
import { DataTable, Loading, Panel, Stat, Vote } from "@/components/Panel";
import { useTerminal } from "@/components/TerminalContext";
import { api, ApiError, fmt } from "@/lib/api";
import type { HealthReport, PortfolioBundle, RiskReport } from "@/lib/types";

export default function PortfolioPage() {
  const { setSymbol, user, toast } = useTerminal();
  const [pf, setPf] = useState<PortfolioBundle | null>(null);
  const [risk, setRisk] = useState<RiskReport | null>(null);
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try { setPf(await api.portfolio()); setRisk(await api.risk()); }
    catch (e) { setErr(e instanceof ApiError && e.status === 401 ? "Login to sync your brokerage portfolio." : (e as Error).message); }
  }, []);
  useEffect(() => { load(); }, [load, user]);

  const runHealth = async () => {
    setBusy(true);
    try { setHealth(await api.health()); } catch (e) { toast((e as Error).message, "error"); } finally { setBusy(false); }
  };

  if (err) return <Panel title="Portfolio"><p className="text-term-amber">{err}</p></Panel>;
  if (!pf) return <Loading label="Syncing portfolio" />;
  const { account, positions, sector_weights } = pf;
  const totalPL = positions.reduce((a, p) => a + p.unrealized_pl, 0);

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        <Panel title={`Account · ${account.broker}`} className="md:col-span-5">
          <div className="flex flex-wrap gap-6 items-center">
            <Stat label="Equity" value={<span className="text-xl">{fmt.money(account.equity)}</span>} />
            <Stat label="Cash" value={fmt.money(account.cash)} />
            <Stat label="Buying power" value={fmt.money(account.buying_power)} />
            <Stat label="Unrealized P/L" value={<span className={totalPL >= 0 ? "up" : "down"}>{fmt.money(totalPL)}</span>} />
            <Stat label="Positions" value={positions.length} />
            <span className={`tag ${account.paper ? "border-term-cyan text-term-cyan" : "border-term-red text-term-red"}`}>{account.paper ? "PAPER" : "LIVE"}</span>
            <button className="btn ml-auto" onClick={load}>↻ Sync</button>
            <button className="btn btn-primary" onClick={runHealth} disabled={busy}>{busy ? "Council reviewing…" : "AI Council health report"}</button>
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-2">
        <Panel title="Positions" className="xl:col-span-2">
          <DataTable rows={positions as unknown as Record<string, unknown>[]} onRowClick={(r) => setSymbol(String(r.symbol))} empty="No open positions" columns={[
            { key: "symbol", label: "Sym" }, { key: "sector", label: "Sector" },
            { key: "qty", label: "Qty", render: (r) => fmt.num(r.qty as number, 4) },
            { key: "avg_entry_price", label: "Avg", render: (r) => fmt.money(r.avg_entry_price as number) },
            { key: "current_price", label: "Last", render: (r) => fmt.money(r.current_price as number) },
            { key: "market_value", label: "Value", render: (r) => fmt.money(r.market_value as number) },
            { key: "weight", label: "Wt", render: (r) => `${((r.weight as number) * 100).toFixed(1)}%` },
            { key: "unrealized_pl", label: "P/L", render: (r) => <span className={(r.unrealized_pl as number) >= 0 ? "up" : "down"}>{fmt.money(r.unrealized_pl as number)} ({fmt.pct(r.unrealized_pl_pct as number, 1)})</span> },
          ]} />
        </Panel>
        <Panel title="Sector exposure">
          {Object.entries(sector_weights).sort((a, b) => b[1] - a[1]).map(([s, w]) => (
            <div key={s} className="mb-1.5 text-[11px]">
              <div className="flex justify-between"><span>{s}</span><span className={w > 0.4 ? "text-term-red" : ""}>{(w * 100).toFixed(1)}%</span></div>
              <div className="h-1.5 bg-term-bg border border-term-border"><div className={`h-full ${w > 0.4 ? "bg-term-red" : "bg-term-amber"}`} style={{ width: `${w * 100}%` }} /></div>
            </div>
          ))}
        </Panel>
      </div>

      {risk && risk.positions > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-2">
          <Panel title="Risk dashboard">
            <div className="grid grid-cols-2 gap-2">
              <Stat label="Ann. volatility" value={`${(risk.annualized_volatility * 100).toFixed(1)}%`} />
              <Stat label="Portfolio beta" value={risk.beta.toFixed(2)} />
              <Stat label="1-day VaR 95%" value={<span className="down">{fmt.money(risk.var_95_1d)}</span>} />
              <Stat label="1-day CVaR 95%" value={<span className="down">{fmt.money(risk.cvar_95_1d)}</span>} />
              <Stat label="HHI concentration" value={risk.concentration_hhi.toFixed(3)} />
              <Stat label="Effective positions" value={risk.effective_positions.toFixed(1)} />
            </div>
            <table className="table-term mt-2"><thead><tr><th>Sym</th><th>Wt</th><th>Beta</th><th>Vol</th></tr></thead>
              <tbody>{risk.per_position.map((p) => <tr key={p.symbol}><td>{p.symbol}</td><td>{(p.weight * 100).toFixed(1)}%</td><td>{p.beta.toFixed(2)}</td><td>{(p.vol * 100).toFixed(0)}%</td></tr>)}</tbody></table>
          </Panel>
          <Panel title="Scenario analysis">
            {Object.entries(risk.scenarios).map(([k, s]) => (
              <div key={k} className="flex justify-between items-center text-[11px] py-1 border-b border-term-border/50">
                <span>{s.label}</span>
                <span className={s.pnl >= 0 ? "up" : "down"}>{fmt.money(s.pnl)} <span className="text-term-dim">({fmt.pct(s.pnl_pct, 1)})</span></span>
              </div>
            ))}
            <p className="text-[10px] text-term-dim mt-2">Shock × portfolio beta. Illustrative, not predictive.</p>
          </Panel>
          <Panel title="Correlation matrix">
            <table className="table-term text-[10px]"><thead><tr><th></th>{risk.correlation.symbols.map((s) => <th key={s}>{s}</th>)}</tr></thead>
              <tbody>{risk.correlation.matrix.map((row, i) => (
                <tr key={i}><td className="text-term-dim">{risk.correlation.symbols[i]}</td>
                  {row.map((v, j) => <td key={j} style={{ background: `rgba(${v >= 0 ? "34,197,94" : "239,68,68"},${Math.abs(v) * 0.5})` }}>{v.toFixed(2)}</td>)}</tr>))}</tbody></table>
          </Panel>
        </div>
      )}

      {health && (
        <Panel title="AI Council · portfolio health report" right={<span className={`tag ${health.health === "healthy" ? "border-term-green text-term-green" : health.health === "watch" ? "border-term-amber text-term-amber" : "border-term-red text-term-red"}`}>{health.health.toUpperCase()}</span>}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
            <div className="lg:col-span-2 space-y-2">
              {health.holdings.map((h) => (
                <div key={h.symbol} className="border border-term-border rounded-sm p-2 text-[11px]">
                  <div className="flex items-center gap-2"><b>{h.symbol}</b><span className="text-term-dim">{(h.weight * 100).toFixed(1)}%</span><span className="ml-auto text-term-dim">score {h.score >= 0 ? "+" : ""}{h.score.toFixed(2)}</span><Vote vote={h.action} /></div>
                  <p className="mt-1 text-term-dim">{h.summary}</p>
                </div>
              ))}
            </div>
            <div>
              <div className="text-[10px] uppercase text-term-dim mb-1">Rebalancing suggestions</div>
              <ul className="text-[11px] list-disc pl-4 space-y-1">{health.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <p className="text-[10px] text-term-amber mt-3">{health.disclaimer}</p>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
