"use client";
import type { SectorRow } from "@/lib/types";
import { useTerminal } from "./TerminalContext";

export function SectorHeatmap({ rows, metric = "relative_3m" }: { rows: SectorRow[]; metric?: "return_1m" | "return_3m" | "relative_1m" | "relative_3m" }) {
  const { setSymbol } = useTerminal();
  const max = Math.max(1, ...rows.map((r) => Math.abs(r[metric])));
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-1 h-full">
      {rows.map((r) => {
        const v = r[metric], a = Math.min(1, Math.abs(v) / max) * 0.85 + 0.15;
        const bg = v >= 0 ? `rgba(34,197,94,${a})` : `rgba(239,68,68,${a})`;
        return (
          <div key={r.sector} className="p-2 rounded-sm flex flex-col justify-between min-h-[70px] text-black/90" style={{ background: bg }} title={`Rank #${r.rank} · ${r.phase}`}>
            <div className="flex justify-between text-[11px] font-bold"><span>{r.sector}</span><span>#{r.rank}</span></div>
            <div className="text-lg font-bold">{v >= 0 ? "+" : ""}{v.toFixed(2)}%</div>
            <div className="flex justify-between text-[10px]">
              <span className="uppercase">{r.phase}</span>
              <span>{r.constituents.map((s) => <button key={s} className="underline mr-1" onClick={() => setSymbol(s)}>{s}</button>)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
