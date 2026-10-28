"use client";
import { useState } from "react";
import { api, ApiError, fmt } from "@/lib/api";
import type { Recommendation } from "@/lib/types";
import { useTerminal } from "./TerminalContext";

/**
 * Explicit user-approval gate. Nothing reaches a brokerage until the user
 * reviews the order, optionally edits it, and clicks APPROVE. Live (non-paper)
 * brokers additionally require typing "I APPROVE".
 */
export function TradeApprovalModal({ rec, price, paper, onClose, onDone }:
  { rec: Recommendation; price: number; paper: boolean; onClose: () => void; onDone: (status: string) => void }) {
  const { toast } = useTerminal();
  const [qty, setQty] = useState(rec.qty ?? 0);
  const [orderType, setOrderType] = useState(rec.order_type);
  const [limit, setLimit] = useState<number | "">(rec.limit_price ?? price);
  const [stop, setStop] = useState<number | "">(rec.stop_price ?? "");
  const [phrase, setPhrase] = useState("");
  const [busy, setBusy] = useState(false);
  const est = qty * (orderType === "limit" && limit !== "" ? limit : price);

  const submit = async (approve: boolean) => {
    setBusy(true);
    try {
      const r = await api.decide(rec.token, approve, approve ? {
        qty, order_type: orderType, limit_price: orderType.includes("limit") && limit !== "" ? limit : undefined,
        stop_price: orderType.includes("stop") && stop !== "" ? stop : undefined, confirm_phrase: phrase,
      } : {});
      toast(approve ? `Order ${r.status}: ${rec.side.toUpperCase()} ${qty} ${rec.symbol}` : "Recommendation rejected", approve ? "ok" : "info");
      onDone(r.status);
    } catch (e) {
      toast(e instanceof ApiError || e instanceof Error ? e.message : "Order failed", "error");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center" onClick={onClose}>
      <div className="panel w-[560px] max-w-[94vw] border-term-amber" onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">Trade approval required <span className={`tag ${paper ? "border-term-cyan text-term-cyan" : "border-term-red text-term-red"}`}>{paper ? "PAPER ACCOUNT" : "LIVE MONEY"}</span></div>
        <div className="panel-body flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div><div className="text-term-dim text-[10px]">SIDE</div><div className={`text-lg font-bold ${rec.side === "buy" ? "up" : "down"}`}>{rec.side.toUpperCase()}</div></div>
            <div><div className="text-term-dim text-[10px]">SYMBOL</div><div className="text-lg font-bold">{rec.symbol}</div></div>
            <div><div className="text-term-dim text-[10px]">LAST</div><div className="text-lg">{fmt.money(price)}</div></div>
          </div>
          <p className="text-[11px] text-term-dim border-l-2 border-term-amber pl-2">{rec.rationale}</p>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-term-dim text-[10px]">QTY<input className="input" type="number" step="0.0001" min="0" value={qty} onChange={(e) => setQty(+e.target.value)} /></label>
            <label className="text-term-dim text-[10px]">TYPE
              <select className="input" value={orderType} onChange={(e) => setOrderType(e.target.value)}>
                <option value="market">market</option><option value="limit">limit</option><option value="stop">stop</option><option value="stop_limit">stop_limit</option>
              </select></label>
            {orderType.includes("limit") && <label className="text-term-dim text-[10px]">LIMIT PRICE<input className="input" type="number" step="0.01" value={limit} onChange={(e) => setLimit(e.target.value === "" ? "" : +e.target.value)} /></label>}
            {orderType.includes("stop") && <label className="text-term-dim text-[10px]">STOP PRICE<input className="input" type="number" step="0.01" value={stop} onChange={(e) => setStop(e.target.value === "" ? "" : +e.target.value)} /></label>}
          </div>
          <div className="flex justify-between text-[11px]"><span className="text-term-dim">Estimated value</span><span>{fmt.money(est)}</span></div>
          {!paper && (
            <label className="text-term-red text-[10px]">Type <b>I APPROVE</b> to authorize a real-money order
              <input className="input border-term-red" value={phrase} onChange={(e) => setPhrase(e.target.value)} placeholder="I APPROVE" /></label>
          )}
          <p className="text-[10px] text-term-amber">Not financial advice. This order is sent to your brokerage only after you approve it. AstraTrade Pro never holds funds.</p>
          <div className="flex gap-2">
            <button className="btn btn-success" disabled={busy || qty <= 0 || (!paper && phrase !== "I APPROVE")} onClick={() => submit(true)}>✔ Approve & send</button>
            <button className="btn btn-danger" disabled={busy} onClick={() => submit(false)}>✖ Reject</button>
            <button className="btn ml-auto" onClick={onClose}>Later</button>
          </div>
        </div>
      </div>
    </div>
  );
}
