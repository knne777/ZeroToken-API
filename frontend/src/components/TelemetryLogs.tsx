import React from "react";
import { Activity, Clock, DollarSign, RefreshCw } from "lucide-react";
import { RequestLogItem } from "../types";

interface TelemetryLogsProps {
  logs: RequestLogItem[];
  onRefresh: () => void;
}

export const TelemetryLogs: React.FC<TelemetryLogsProps> = ({ logs, onRefresh }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-400" />
            <span>Telemetría & Auditoría de Llamadas</span>
          </h2>
          <p className="text-xs text-zinc-400">
            Registro en tiempo real de todas las solicitudes enviadas a través de ZeroToken (REST o OpenAI SDK).
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-lg text-xs font-medium border border-zinc-800 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refrescar Logs</span>
        </button>
      </div>

      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 overflow-hidden">
        {logs.length === 0 ? (
          <div className="py-12 text-center text-zinc-500 text-xs">
            No hay registros de llamadas aún. Realiza consultas desde el Playground o mediante cURL.
          </div>
        ) : (
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/40">
                <th className="py-3 px-4 font-medium">Hora</th>
                <th className="py-3 px-4 font-medium">Origen / Key</th>
                <th className="py-3 px-4 font-medium">Motor</th>
                <th className="py-3 px-4 font-medium">Modelo</th>
                <th className="py-3 px-4 font-medium">Tokens</th>
                <th className="py-3 px-4 font-medium">Latencia</th>
                <th className="py-3 px-4 font-medium text-right">Ahorro ($)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono text-[11px]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="py-3 px-4 text-zinc-400">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </td>
                  <td className="py-3 px-4 font-sans font-medium text-zinc-200">
                    {log.api_key_name || "Direct REST"}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 text-[10px]">
                      {log.provider}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-zinc-400">
                    {log.model}
                  </td>
                  <td className="py-3 px-4 text-zinc-300">
                    {log.total_tokens}
                  </td>
                  <td className="py-3 px-4 text-zinc-400">
                    {(log.duration_ms / 1000).toFixed(2)}s
                  </td>
                  <td className="py-3 px-4 text-right text-emerald-400 font-semibold">
                    +${log.savings_usd.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
