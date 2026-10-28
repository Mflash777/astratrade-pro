"use client";
import { useMemo, useState } from "react";

export function Panel({ title, right, children, className = "" }: { title: string; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-head"><span>{title}</span>{right && <span className="normal-case tracking-normal text-term-dim">{right}</span>}</div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Stat({ label, value, delta, className = "" }: { label: string; value: React.ReactNode; delta?: number | null; className?: string }) {
  return (
    <div className={`flex flex-col ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-term-dim">{label}</span>
      <span className="text-sm">{value}</span>
      {delta != null && <span className={`text-[10px] ${delta >= 0 ? "up" : "down"}`}>{delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(2)}%</span>}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="text-term-dim text-[11px] animate-pulse">{label}…</div>;
}

export interface Column<T> { key: string; label: string; render?: (row: T) => React.ReactNode; sort?: (row: T) => number | string; className?: string }

/** Sortable, filterable data table used across the terminal. */
export function DataTable<T extends Record<string, unknown>>({ rows, columns, filter, onRowClick, empty = "No data" }:
  { rows: T[]; columns: Column<T>[]; filter?: string; onRowClick?: (row: T) => void; empty?: string }) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [dir, setDir] = useState<1 | -1>(1);
  const sorted = useMemo(() => {
    let r = rows;
    if (filter) { const f = filter.toLowerCase(); r = r.filter((row) => Object.values(row).some((v) => String(v).toLowerCase().includes(f))); }
    if (sortKey) {
      const col = columns.find((c) => c.key === sortKey);
      const get = col?.sort ?? ((row: T) => row[sortKey] as number | string);
      r = [...r].sort((a, b) => { const x = get(a), y = get(b); return (x < y ? -1 : x > y ? 1 : 0) * dir; });
    }
    return r;
  }, [rows, columns, filter, sortKey, dir]);
  if (!rows.length) return <div className="text-term-dim">{empty}</div>;
  return (
    <table className="table-term">
      <thead><tr>{columns.map((c) => (
        <th key={c.key} className={c.className} onClick={() => { if (sortKey === c.key) setDir((d) => (d === 1 ? -1 : 1)); else { setSortKey(c.key); setDir(1); } }}>
          {c.label}{sortKey === c.key ? (dir === 1 ? " ▲" : " ▼") : ""}
        </th>))}</tr></thead>
      <tbody>{sorted.map((row, i) => (
        <tr key={i} onClick={() => onRowClick?.(row)} className={onRowClick ? "cursor-pointer" : ""}>
          {columns.map((c) => <td key={c.key} className={c.className}>{c.render ? c.render(row) : String(row[c.key] ?? "")}</td>)}
        </tr>))}</tbody>
    </table>
  );
}

export function Vote({ vote }: { vote: string }) {
  const cls = vote === "BUY" ? "border-term-green text-term-green" : vote === "SELL" ? "border-term-red text-term-red" : "border-term-amber text-term-amber";
  return <span className={`tag ${cls}`}>{vote}</span>;
}

export function ScoreBar({ score }: { score: number }) {
  const pct = Math.abs(score) * 50;
  return (
    <div className="relative h-1.5 w-full bg-term-bg border border-term-border rounded">
      <div className={`absolute top-0 h-full ${score >= 0 ? "bg-term-green" : "bg-term-red"}`} style={{ left: score >= 0 ? "50%" : `${50 - pct}%`, width: `${pct}%` }} />
      <div className="absolute top-0 left-1/2 h-full w-px bg-term-dim" />
    </div>
  );
}
