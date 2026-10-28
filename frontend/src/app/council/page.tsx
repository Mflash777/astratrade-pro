"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CouncilPanel } from "@/components/CouncilPanel";
import { DataTable, Loading, Panel } from "@/components/Panel";
import { useTerminal } from "@/components/TerminalContext";
import { TradeApprovalModal } from "@/components/TradeApprovalModal";
import { api, ApiError, fmt } from "@/lib/api";
import type { CouncilResult, Recommendation } from "@/lib/types";

function Council() {
  const { symbol, setSymbol, user, toast } = useTerminal();
  const params = useSearchParams();
  const [input, setInput] = useState(symbol);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<CouncilResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [budget, setBudget] = useState(1000);
  const [pending, setPending] = useState<Recommendation | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);

  useEffect(() => setInput(symbol), [symbol]);
  const [paper, setPaper] = useState(true);
  useEffect(() => {
    api.recommendations().then(setRecs).catch(() => undefined);
    api.portfolio().then((p) => setPaper(p.paper)).catch(() => undefined);
  }, [user]);

  const run = async (sym = input) => {
    setSymbol(sym); setBusy(true);
    try { setResult(await api.council(sym.toUpperCase(), question || undefined)); }
    catch (e) { toast(e instanceof ApiError && e.status === 401 ? "Login required to run the Council" : (e as Error).message, "error"); }
    finally { setBusy(false); }
  };

  const propose = async () => {
    setBusy(true);
    try {
      const r = await api.recommend(symbol, budget);
      setResult(r.council);
      if (r.recommendation) { setPending(r.recommendation); setRecs((x) => [r.recommendation!, ...x]); }
      else toast(r.message, "info");
    } catch (e) { toast(e instanceof ApiError && e.status === 401 ? "Login required" : (e as Error).message, "error"); }
    finally { setBusy(false); }
  };

  useEffect(() => {
    if (params.get("trade")) { propose(); } else { run(symbol); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col gap-2">
      <Panel title="AI Council · 7-persona deliberation" right={result ? `last run ${new Date(result.timestamp).toLocaleTimeString()}` : ""}>
        <form className="flex flex-wrap gap-2 items-end" onSubmit={(e) => { e.preventDefault(); run(); }}>
          <label className="text-term-dim text-[10px]">SYMBOL<input className="input w-24 uppercase" value={input} onChange={(e) => setInput(e.target.value)} /></label>
          <label className="text-term-dim text-[10px] flex-1 min-w-[200px]">QUESTION (optional)<input className="input" placeholder="e.g. Is this a good entry ahead of earnings?" value={question} onChange={(e) => setQuestion(e.target.value)} /></label>
          <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Deliberating…" : "Convene council"}</button>
          <label className="text-term-dim text-[10px]">BUDGET $<input className="input w-24" type="number" min="1" value={budget} onChange={(e) => setBudget(+e.target.value)} /></label>
          <button className="btn" type="button" disabled={busy} onClick={propose}>Propose trade →</button>
        </form>
        <p className="text-[10px] text-term-dim mt-1">A proposed trade is only a recommendation. It is held as <b>pending</b> until you explicitly approve it in the review modal.</p>
      </Panel>

      {busy && !result && <Loading label="Council members are reviewing the signals" />}
      {result && <CouncilPanel result={result} />}

      <Panel title="Trade recommendations · approval queue">
        <DataTable rows={recs as unknown as Record<string, unknown>[]} empty="No recommendations yet" columns={[
          { key: "created_at", label: "Time", render: (r) => new Date(String(r.created_at)).toLocaleString() },
          { key: "symbol", label: "Sym" },
          { key: "side", label: "Side", render: (r) => <span className={r.side === "buy" ? "up" : "down"}>{String(r.side).toUpperCase()}</span> },
          { key: "qty", label: "Qty", render: (r) => fmt.num(r.qty as number, 4) },
          { key: "order_type", label: "Type" },
          { key: "status", label: "Status", render: (r) => <span className={`tag ${r.status === "pending" ? "border-term-amber text-term-amber" : r.status === "submitted" ? "border-term-green text-term-green" : "border-term-dim text-term-dim"}`}>{String(r.status)}</span> },
          { key: "token", label: "", render: (r) => r.status === "pending" ? <button className="btn btn-success py-0" onClick={() => setPending(r as unknown as Recommendation)}>Review</button> : null },
        ]} />
      </Panel>

      {pending && result && (
        <TradeApprovalModal rec={pending} price={result.quote.price} paper={paper} onClose={() => setPending(null)}
          onDone={() => { setPending(null); api.recommendations().then(setRecs); }} />
      )}
    </div>
  );
}

export default function Page() { return <Suspense fallback={<Loading />}><Council /></Suspense>; }
