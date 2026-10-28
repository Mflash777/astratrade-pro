"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Quote } from "@/lib/types";
import { CommandPalette } from "./CommandPalette";
import { LoginDialog } from "./LoginDialog";
import { useTerminal } from "./TerminalContext";

const NAV = [
  { href: "/", label: "TERMINAL", key: "F2" },
  { href: "/council", label: "AI COUNCIL", key: "F7" },
  { href: "/portfolio", label: "PORTFOLIO", key: "F8" },
  { href: "/simulation", label: "SIMULATION", key: "F9" },
];
const TICKER = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "XOM", "UNH"];

export function Shell({ children }: { children: React.ReactNode }) {
  const { symbol, setSymbol, user, setUser, demo, setPaletteOpen, toasts } = useTerminal();
  const pathname = usePathname();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [login, setLogin] = useState(false);
  const [clock, setClock] = useState("");
  const [input, setInput] = useState(symbol);

  useEffect(() => setInput(symbol), [symbol]);
  useEffect(() => {
    const load = () => api.quotes(TICKER).then(setQuotes).catch(() => undefined);
    load();
    const t = setInterval(load, 15000);
    const c = setInterval(() => setClock(new Date().toISOString().replace("T", " ").slice(0, 19) + "Z"), 1000);
    return () => { clearInterval(t); clearInterval(c); };
  }, []);

  return (
    <div className="h-screen flex flex-col bg-term-bg">
      <header className="flex items-center gap-3 px-3 h-9 border-b border-term-border bg-term-panel">
        <span className="text-term-amber font-bold tracking-[0.3em]">ASTRATRADE<span className="text-term-dim">PRO</span></span>
        <form className="flex items-center gap-1" onSubmit={(e) => { e.preventDefault(); setSymbol(input); }}>
          <input className="input w-24 uppercase" value={input} onChange={(e) => setInput(e.target.value)} aria-label="Symbol" />
          <button className="btn" type="submit">GO</button>
        </form>
        <nav className="flex gap-1">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className={`px-2 py-1 text-[11px] tracking-wider border-b-2 ${pathname === n.href ? "border-term-amber text-term-amber" : "border-transparent text-term-dim hover:text-term-text"}`}>
              {n.label} <span className="kbd">{n.key}</span>
            </Link>
          ))}
        </nav>
        <button className="btn ml-auto" onClick={() => setPaletteOpen(true)}>⌘K COMMAND</button>
        <span className={`tag ${demo ? "border-term-cyan text-term-cyan" : "border-term-green text-term-green"}`}>{demo ? "DEMO DATA" : "LIVE API"}</span>
        {user ? (
          <button className="btn" onClick={() => { api.logout(); setUser(null); }} title={user.email}>{user.subscription_tier.toUpperCase()} · LOGOUT</button>
        ) : (
          <button className="btn" onClick={() => setLogin(true)}>LOGIN</button>
        )}
        <span className="text-term-dim text-[10px] hidden lg:inline">{clock}</span>
      </header>

      <div className="h-6 flex items-center overflow-hidden border-b border-term-border bg-black/40 text-[11px]">
        <div className="flex gap-6 px-3 whitespace-nowrap animate-[ticker_60s_linear_infinite]">
          {[...quotes, ...quotes].map((q, i) => (
            <button key={q.symbol + i} onClick={() => setSymbol(q.symbol)} className="hover:text-term-amber">
              <span className="text-term-text">{q.symbol}</span> <span>{q.price.toFixed(2)}</span> <span className={q.change >= 0 ? "up" : "down"}>{q.change >= 0 ? "▲" : "▼"} {Math.abs(q.change_pct).toFixed(2)}%</span>
            </button>
          ))}
        </div>
      </div>

      <main className="flex-1 min-h-0 p-2 overflow-auto">{children}</main>

      <footer className="h-6 flex items-center px-3 gap-4 border-t border-term-border text-[10px] text-term-dim">
        <span>Not financial advice. Trades require user approval.</span>
        <span className="hidden md:inline">Press <span className="kbd">/</span> or <span className="kbd">⌘K</span> for commands · <span className="kbd">F1</span> help</span>
        <span className="ml-auto">AstraTrade Pro v1.0</span>
      </footer>

      <CommandPalette />
      {login && <LoginDialog onClose={() => setLogin(false)} />}
      <div className="fixed bottom-8 right-3 flex flex-col gap-1 z-50">
        {toasts.map((t) => (
          <div key={t.id} className={`px-3 py-2 text-[11px] border rounded-sm bg-term-panel ${t.kind === "error" ? "border-term-red text-term-red" : t.kind === "ok" ? "border-term-green text-term-green" : "border-term-amber text-term-amber"}`}>{t.msg}</div>
        ))}
      </div>
      <style jsx global>{`@keyframes ticker { from { transform: translateX(0); } to { transform: translateX(-50%); } }`}</style>
    </div>
  );
}
