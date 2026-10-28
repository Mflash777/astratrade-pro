"use client";
import { useEffect, useState } from "react";
import type { CouncilResult, Opinion } from "@/lib/types";
import { Panel, ScoreBar, Vote } from "./Panel";

const ICONS: Record<string, string> = {
  "Macro Economist": "🏦", "Quant Analyst": "📐", "Fundamental Investor": "📊", "Political Analyst": "🏛️",
  "News & Sentiment Analyst": "📰", "Risk Manager": "🛡️", Optimizer: "⚖️",
};

function OpinionCard({ o, revealed }: { o: Opinion; revealed: boolean }) {
  return (
    <div className={`border border-term-border rounded-sm p-2 flex flex-col gap-1 transition-opacity duration-500 ${revealed ? "opacity-100" : "opacity-20"}`}>
      <div className="flex items-center gap-2">
        <span>{ICONS[o.persona] ?? "•"}</span>
        <span className="font-bold text-term-text">{o.persona}</span>
        <span className="ml-auto text-term-dim text-[10px]">conf {(o.confidence * 100).toFixed(0)}%</span>
        <Vote vote={o.vote} />
      </div>
      <div className="text-[10px] text-term-dim">{o.role}</div>
      <ScoreBar score={o.score} />
      <p className="text-[11px] leading-relaxed">{o.rationale}</p>
      <ul className="text-[10px] text-term-dim list-disc pl-4">{o.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul>
    </div>
  );
}

/** Council debate panel: personas appear one by one, then the debate, vote tally and final synthesis. */
export function CouncilPanel({ result, animate = true }: { result: CouncilResult; animate?: boolean }) {
  const [stage, setStage] = useState(animate ? 0 : 99);
  useEffect(() => {
    if (!animate) return;
    setStage(0);
    const timers = Array.from({ length: result.opinions.length + 3 }, (_, i) => setTimeout(() => setStage(i + 1), 350 * (i + 1)));
    return () => timers.forEach(clearTimeout);
  }, [result, animate]);
  const n = result.opinions.length;
  const total = result.votes.BUY + result.votes.HOLD + result.votes.SELL || 1;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-2">
      <div className="xl:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-2">
        {result.opinions.map((o, i) => <OpinionCard key={o.persona} o={o} revealed={stage > i} />)}
      </div>
      <div className="flex flex-col gap-2">
        <Panel title="Debate" className={`transition-opacity ${stage > n ? "opacity-100" : "opacity-20"}`}>
          <ol className="text-[11px] space-y-1.5">
            {result.debate.map((d, i) => <li key={i} className="border-l-2 border-term-border pl-2">{d}</li>)}
          </ol>
        </Panel>
        <Panel title="Vote" className={`transition-opacity ${stage > n + 1 ? "opacity-100" : "opacity-20"}`}>
          <div className="flex h-4 rounded-sm overflow-hidden text-[10px] text-black font-bold">
            {(["BUY", "HOLD", "SELL"] as const).map((k) => result.votes[k] > 0 && (
              <div key={k} style={{ width: `${(result.votes[k] / total) * 100}%` }} className={`flex items-center justify-center ${k === "BUY" ? "bg-term-green" : k === "SELL" ? "bg-term-red" : "bg-term-amber"}`}>{k} {result.votes[k]}</div>
            ))}
          </div>
        </Panel>
        <Panel title="⚖️ Optimizer · Final insight" className={`transition-opacity border-term-amber ${stage > n + 2 ? "opacity-100" : "opacity-20"}`}>
          <div className="flex items-center gap-2 mb-1">
            <Vote vote={result.final.vote} />
            <span className="text-term-dim text-[10px]">score {result.final.score >= 0 ? "+" : ""}{result.final.score.toFixed(2)} · conf {(result.final.confidence * 100).toFixed(0)}% · max size {result.recommendation.max_position_pct}%</span>
          </div>
          <ScoreBar score={result.final.score} />
          <p className="text-[11px] leading-relaxed mt-2">{result.final.rationale}</p>
          <ul className="text-[10px] text-term-dim list-disc pl-4 mt-1">{result.final.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul>
          <p className="mt-2 text-[10px] text-term-amber border-t border-term-border pt-1">{result.disclaimer}</p>
        </Panel>
      </div>
    </div>
  );
}
