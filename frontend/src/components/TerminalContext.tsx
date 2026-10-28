"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, isDemo, onModeChange, setToken } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

export interface TerminalState {
  symbol: string;
  setSymbol: (s: string) => void;
  user: AuthUser | null;
  setUser: (u: AuthUser | null) => void;
  demo: boolean;
  paletteOpen: boolean;
  setPaletteOpen: (b: boolean) => void;
  toast: (msg: string, kind?: "info" | "error" | "ok") => void;
  toasts: { id: number; msg: string; kind: string }[];
  runCommand: (cmd: string) => void;
}

const Ctx = createContext<TerminalState | null>(null);
export const useTerminal = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error("useTerminal outside provider");
  return c;
};

/** Bloomberg-style mnemonics: SYMBOL <FUNCTION> e.g. "AAPL GP", "DES", "PORT", "COUNCIL" */
export const COMMANDS: { key: string; label: string; route: (sym: string) => string }[] = [
  { key: "GP", label: "Graph / price chart (terminal)", route: () => "/" },
  { key: "DES", label: "Description & fundamentals", route: () => "/?tab=fundamentals" },
  { key: "N", label: "News & sentiment", route: () => "/?tab=news" },
  { key: "ECO", label: "Macro / economic calendar", route: () => "/?tab=macro" },
  { key: "SECT", label: "Sector heatmap", route: () => "/?tab=sectors" },
  { key: "COUNCIL", label: "Run AI Council analysis", route: () => "/council" },
  { key: "PORT", label: "Portfolio & risk dashboard", route: () => "/portfolio" },
  { key: "SIM", label: "Paper-trading simulation", route: () => "/simulation" },
  { key: "TRADE", label: "Council trade recommendation (requires approval)", route: () => "/council?trade=1" },
  { key: "HELP", label: "Keyboard shortcuts", route: () => "/?tab=help" },
];

export function TerminalProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [symbol, setSymbolState] = useState("AAPL");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [demo, setDemo] = useState(isDemo());
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [toasts, setToasts] = useState<{ id: number; msg: string; kind: string }[]>([]);

  const toast = useCallback((msg: string, kind: "info" | "error" | "ok" = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, msg, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);

  const setSymbol = useCallback((s: string) => {
    const clean = s.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 6);
    if (clean) { setSymbolState(clean); if (typeof window !== "undefined") localStorage.setItem("atp_symbol", clean); }
  }, []);

  useEffect(() => {
    const saved = typeof window !== "undefined" && localStorage.getItem("atp_symbol");
    if (saved) setSymbolState(saved);
    api.me().then(setUser).catch(() => setToken(null));
    return onModeChange(setDemo);
  }, []);

  const runCommand = useCallback((raw: string) => {
    const parts = raw.trim().toUpperCase().split(/\s+/).filter(Boolean);
    if (!parts.length) return;
    let sym: string | null = null, fn: string | null = null;
    for (const p of parts) {
      if (COMMANDS.some((c) => c.key === p)) fn = p;
      else if (/^[A-Z]{1,6}$/.test(p)) sym = p;
    }
    if (sym) setSymbol(sym);
    const cmd = COMMANDS.find((c) => c.key === fn);
    if (cmd) router.push(cmd.route(sym ?? symbol));
    else if (sym && pathname !== "/") router.push("/");
    setPaletteOpen(false);
  }, [router, pathname, setSymbol, symbol]);

  // Global shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA";
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaletteOpen((o) => !o); return; }
      if (e.key === "Escape") { setPaletteOpen(false); return; }
      if (typing) return;
      if (e.key === "/") { e.preventDefault(); setPaletteOpen(true); return; }
      const fkeys: Record<string, string> = { F1: "HELP", F2: "GP", F3: "DES", F4: "N", F5: "ECO", F6: "SECT", F7: "COUNCIL", F8: "PORT", F9: "SIM" };
      if (fkeys[e.key]) { e.preventDefault(); runCommand(fkeys[e.key]); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runCommand]);

  const value = useMemo(() => ({ symbol, setSymbol, user, setUser, demo, paletteOpen, setPaletteOpen, toast, toasts, runCommand }),
    [symbol, setSymbol, user, demo, paletteOpen, toast, toasts, runCommand]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
