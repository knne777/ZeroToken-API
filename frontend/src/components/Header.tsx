import React from "react";
import { Zap, DollarSign, Activity, FileText } from "lucide-react";
import { AnalyticsOverview } from "../types";

interface HeaderProps {
  analytics: AnalyticsOverview | null;
}

export const Header: React.FC<HeaderProps> = ({ analytics }) => {
  const savings = analytics?.total_savings_usd || 0;
  const tokens = analytics?.total_tokens || 0;
  const formattedTokens = tokens > 1_000_000
    ? `${(tokens / 1_000_000).toFixed(1)}M`
    : tokens > 1_000
    ? `${(tokens / 1_000).toFixed(1)}k`
    : tokens.toString();

  return (
    <header className="h-14 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
          <Zap className="h-4 w-4" />
        </div>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm tracking-tight text-zinc-100">ZeroToken</span>
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-medium">
            Studio
          </span>
        </div>
      </div>

      {/* Center: The Money Counter (ROI Ticker) */}
      <div className="hidden md:flex items-center gap-6 px-4 py-1.5 rounded-full bg-zinc-900/60 border border-zinc-800/80">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-zinc-500">Ahorro Estimado:</span>
          <span className="font-mono font-semibold text-emerald-400 flex items-center">
            <DollarSign className="h-3 w-3 -mr-0.5" />
            {savings.toFixed(2)} USD
          </span>
        </div>
        <div className="h-3 w-[1px] bg-zinc-800" />
        <div className="flex items-center gap-2 text-xs">
          <span className="text-zinc-500">Tokens Procesados:</span>
          <span className="font-mono font-medium text-zinc-200">
            {formattedTokens}
          </span>
        </div>
        <div className="h-3 w-[1px] bg-zinc-800" />
        <div className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>$0 Factura Extra</span>
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-3">
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/80 rounded-md transition-colors"
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Swagger API</span>
        </a>
        <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-medium font-mono">
          <Activity className="h-3 w-3" />
          <span>Gateway Live</span>
        </div>
      </div>
    </header>
  );
};
