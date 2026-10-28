"use client";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Bar as PriceBar } from "@/lib/types";

const AX = { stroke: "#6B7A8C", fontSize: 10 };
const TIP = { contentStyle: { background: "#0D121A", border: "1px solid #1C2633", fontSize: 11 }, labelStyle: { color: "#FFB000" } };

function sma(vals: number[], n: number): (number | null)[] {
  return vals.map((_, i) => (i + 1 < n ? null : +(vals.slice(i + 1 - n, i + 1).reduce((a, b) => a + b, 0) / n).toFixed(2)));
}

export function PriceChart({ bars, overlays = true }: { bars: PriceBar[]; overlays?: boolean }) {
  const closes = bars.map((b) => b.close);
  const s20 = sma(closes, 20), s50 = sma(closes, 50);
  const data = bars.map((b, i) => ({ ...b, sma20: s20[i], sma50: s50[i] }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
        <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#FFB000" stopOpacity={0.35} /><stop offset="100%" stopColor="#FFB000" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid stroke="#1C2633" strokeDasharray="2 4" />
        <XAxis dataKey="date" tick={AX} minTickGap={40} />
        <YAxis domain={["auto", "auto"]} tick={AX} width={48} />
        <Tooltip {...TIP} />
        <Area type="monotone" dataKey="close" stroke="#FFB000" fill="url(#g)" strokeWidth={1.4} dot={false} isAnimationActive={false} />
        {overlays && <Line type="monotone" dataKey="sma20" stroke="#22D3EE" dot={false} strokeWidth={1} isAnimationActive={false} />}
        {overlays && <Line type="monotone" dataKey="sma50" stroke="#A78BFA" dot={false} strokeWidth={1} isAnimationActive={false} />}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function VolumeChart({ bars }: { bars: PriceBar[] }) {
  const data = bars.map((b) => ({ date: b.date, volume: b.volume, up: b.close >= b.open }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 2, right: 5, left: 0, bottom: 0 }}>
        <XAxis dataKey="date" tick={AX} minTickGap={40} hide />
        <YAxis tick={AX} width={48} tickFormatter={(v) => `${(v / 1e6).toFixed(0)}M`} />
        <Tooltip {...TIP} formatter={(v: unknown) => Number(v).toLocaleString()} />
        <Bar dataKey="volume" fill="#1C2633" stroke="#6B7A8C" isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VolatilityChart({ bars }: { bars: PriceBar[] }) {
  const rets = bars.map((b, i) => (i ? b.close / bars[i - 1].close - 1 : 0));
  const data = bars.map((b, i) => {
    if (i < 20) return { date: b.date, vol: null };
    const w = rets.slice(i - 19, i + 1), m = w.reduce((a, x) => a + x, 0) / 20;
    return { date: b.date, vol: +(Math.sqrt(w.reduce((a, x) => a + (x - m) ** 2, 0) / 19) * Math.sqrt(252) * 100).toFixed(1) };
  });
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 2, right: 5, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1C2633" strokeDasharray="2 4" />
        <XAxis dataKey="date" tick={AX} minTickGap={40} />
        <YAxis tick={AX} width={48} unit="%" />
        <Tooltip {...TIP} />
        <Line type="monotone" dataKey="vol" stroke="#EF4444" dot={false} strokeWidth={1.2} isAnimationActive={false} name="20d realized vol (ann.)" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function EquityChart({ data }: { data: { date?: string; step?: number; equity: number; benchmark?: number }[] }) {
  const key = data[0]?.date !== undefined ? "date" : "step";
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1C2633" strokeDasharray="2 4" />
        <XAxis dataKey={key} tick={AX} minTickGap={40} />
        <YAxis domain={["auto", "auto"]} tick={AX} width={64} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
        <Tooltip {...TIP} formatter={(v: unknown) => `$${Number(v).toLocaleString()}`} />
        <Line type="monotone" dataKey="equity" stroke="#22C55E" dot={false} strokeWidth={1.5} isAnimationActive={false} name="Strategy" />
        {data[0]?.benchmark !== undefined && <Line type="monotone" dataKey="benchmark" stroke="#6B7A8C" dot={false} strokeWidth={1} isAnimationActive={false} name="Buy & hold" />}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DrawdownChart({ data }: { data: { date: string; dd: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 2, right: 5, left: 0, bottom: 0 }}>
        <XAxis dataKey="date" tick={AX} minTickGap={40} hide />
        <YAxis tick={AX} width={48} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
        <Tooltip {...TIP} formatter={(v: unknown) => `${(Number(v) * 100).toFixed(2)}%`} />
        <ReferenceLine y={0} stroke="#6B7A8C" />
        <Area type="monotone" dataKey="dd" stroke="#EF4444" fill="#EF4444" fillOpacity={0.25} isAnimationActive={false} name="Drawdown" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
