import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/Shell";
import { TerminalProvider } from "@/components/TerminalContext";

export const metadata: Metadata = {
  title: "AstraTrade Pro — Market Intelligence Terminal",
  description: "Bloomberg-style terminal with a seven-persona AI Council, user-approved brokerage trades and paper simulation. Not financial advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TerminalProvider>
          <Shell>{children}</Shell>
        </TerminalProvider>
      </body>
    </html>
  );
}
