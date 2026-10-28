"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { SECTORS } from "@/lib/mock";
import { COMMANDS, useTerminal } from "./TerminalContext";

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen, runCommand, symbol } = useTerminal();
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => { if (paletteOpen) { setQ(""); setIdx(0); setTimeout(() => ref.current?.focus(), 10); } }, [paletteOpen]);

  const items = useMemo(() => {
    const up = q.trim().toUpperCase();
    const cmds = COMMANDS.filter((c) => !up || c.key.includes(up) || c.label.toUpperCase().includes(up)).map((c) => ({ text: c.key, label: c.label }));
    const syms = Object.keys(SECTORS).filter((s) => up && s.startsWith(up.split(" ")[0])).slice(0, 6).map((s) => ({ text: `${s} GP`, label: `${s} · ${SECTORS[s]}` }));
    const parts = up.split(/\s+/);
    const direct = parts.length === 2 && /^[A-Z]{1,6}$/.test(parts[0]) && COMMANDS.some((c) => c.key === parts[1]) ? [{ text: up, label: `${parts[0]} → ${COMMANDS.find((c) => c.key === parts[1])!.label}` }] : [];
    return [...direct, ...syms, ...cmds].slice(0, 12);
  }, [q]);

  if (!paletteOpen) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-start justify-center pt-24" onClick={() => setPaletteOpen(false)}>
      <div className="w-[640px] max-w-[92vw] panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">Command · current {symbol} <span className="kbd">ESC</span></div>
        <input ref={ref} className="input border-0 border-b border-term-border rounded-none py-2 text-base uppercase" placeholder="e.g.  NVDA GP   ·   DES   ·   COUNCIL   ·   PORT" value={q}
          onChange={(e) => { setQ(e.target.value); setIdx(0); }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, items.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
            if (e.key === "Enter") { e.preventDefault(); runCommand(items[idx]?.text ?? q); }
          }} />
        <ul className="max-h-80 overflow-auto">
          {items.map((it, i) => (
            <li key={it.text + i} className={`px-3 py-1.5 flex gap-3 cursor-pointer ${i === idx ? "bg-term-bg text-term-amber" : ""}`} onMouseEnter={() => setIdx(i)} onClick={() => runCommand(it.text)}>
              <span className="w-28 shrink-0 font-bold">{it.text}</span><span className="text-term-dim">{it.label}</span>
            </li>
          ))}
        </ul>
        <div className="px-3 py-1 text-[10px] text-term-dim border-t border-term-border">Type a ticker then a function, Bloomberg-style. F-keys: F2 GP · F3 DES · F4 N · F5 ECO · F6 SECT · F7 COUNCIL · F8 PORT · F9 SIM</div>
      </div>
    </div>
  );
}
