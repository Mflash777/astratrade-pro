"use client";
import { useState } from "react";
import { api, ApiError, API_URL } from "@/lib/api";
import { useTerminal } from "./TerminalContext";

export function LoginDialog({ onClose }: { onClose: () => void }) {
  const { setUser, toast } = useTerminal();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin12345");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "register") { await api.register(email, password); toast("Registered — now logging in", "ok"); }
      setUser(await api.login(email, password));
      toast(API_URL ? "Signed in" : "Demo session started", "ok");
      onClose();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Login failed", "error");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center" onClick={onClose}>
      <form className="panel w-96 max-w-[92vw]" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="panel-head">{mode === "login" ? "Sign in" : "Create account"}</div>
        <div className="panel-body flex flex-col gap-2">
          {!API_URL && <p className="text-term-cyan text-[11px]">No backend configured — a demo session with mock data will start.</p>}
          <label className="text-term-dim">Email<input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label className="text-term-dim">Password<input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} /></label>
          <div className="flex gap-2 mt-2">
            <button className="btn btn-primary" type="submit" disabled={busy}>{mode === "login" ? "Sign in" : "Register"}</button>
            <button className="btn" type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Need an account?" : "Have an account?"}</button>
            <button className="btn ml-auto" type="button" onClick={onClose}>Cancel</button>
          </div>
        </div>
      </form>
    </div>
  );
}
