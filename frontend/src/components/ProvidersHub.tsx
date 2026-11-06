import React from "react";
import { CheckCircle2, AlertTriangle, KeyRound, RefreshCw, LogOut, Terminal, Cpu } from "lucide-react";
import { AuthStatusResponse, ProviderAuthInfo } from "../types";

interface ProvidersHubProps {
  authStatus: AuthStatusResponse | null;
  onOpenLoginModal: (provider: string) => void;
  onRefresh: () => void;
}

export const ProvidersHub: React.FC<ProvidersHubProps> = ({
  authStatus,
  onOpenLoginModal,
  onRefresh,
}) => {
  const providersConfig = [
    {
      id: "agy",
      name: "Google Antigravity",
      icon: "🪐",
      models: "gemini-3.8-flash-high, gemini-3.8-pro",
      description: "Modelos multimodales de Google con razonamiento rápido y memoria nativa.",
    },
    {
      id: "codex",
      name: "OpenAI Codex CLI",
      icon: "⚡",
      models: "gpt-6-luna, gpt-5.6-luna, gpt-5.6-terra",
      description: "Suscripción activa de ChatGPT Plus/Pro para tareas de código y chat conversacional.",
    },
    {
      id: "claude",
      name: "Anthropic Claude Code",
      icon: "🧠",
      models: "claude-3-7-sonnet, claude-3-5-sonnet",
      description: "Suscripción Claude Max/Pro para razonamiento complejo y análisis profundo.",
    },
  ];

  const handleLogout = async (provider: string) => {
    if (!confirm(`¿Deseas desconectar las credenciales locales de ${provider}?`)) return;
    try {
      await fetch(`/api/v1/auth/${provider}/logout`, { method: "POST" });
      onRefresh();
    } catch (err) {
      console.error("Logout error", err);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <span>Proveedores & Suscripciones Conectadas</span>
          </h2>
          <p className="text-xs text-zinc-400">
            Conecta tus planes Pro/Team existentes para activar llamadas con facturación cero por token.
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-lg text-xs font-medium border border-zinc-800 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Actualizar Estado</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {providersConfig.map((p) => {
          const statusInfo: ProviderAuthInfo | undefined = authStatus?.[p.id as keyof AuthStatusResponse];
          const isConnected = statusInfo?.authenticated;
          const isInstalled = statusInfo?.installed;

          return (
            <div
              key={p.id}
              className={`rounded-xl border p-5 flex flex-col justify-between transition-all ${
                isConnected
                  ? "bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700/80"
                  : "bg-zinc-900/20 border-zinc-800/40 hover:border-zinc-800"
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="text-2xl">{p.icon}</span>
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-100">{p.name}</h3>
                      <span className="text-[11px] font-mono text-zinc-400 block truncate max-w-[180px]">
                        {p.models}
                      </span>
                    </div>
                  </div>

                  {isConnected ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      Activo
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
                      <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
                      Inactivo
                    </span>
                  )}
                </div>

                <p className="text-xs text-zinc-400 leading-relaxed mb-4">
                  {p.description}
                </p>

                {/* Status info details */}
                <div className="bg-zinc-950/60 rounded-lg p-2.5 border border-zinc-800/60 space-y-1.5 text-[11px] font-mono text-zinc-400 mb-4">
                  <div className="flex items-center justify-between">
                    <span>CLI Instalado:</span>
                    <span className={isInstalled ? "text-emerald-400" : "text-amber-400"}>
                      {isInstalled ? "Sí" : "No detectado"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Plan detectado:</span>
                    <span className="text-zinc-200 truncate max-w-[140px]">
                      {statusInfo?.plan || "Ninguno"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2">
                {isConnected ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onOpenLoginModal(p.id)}
                      className="flex-1 py-2 px-3 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition-colors border border-zinc-700/80 flex items-center justify-center gap-1.5"
                    >
                      <RefreshCw className="h-3 w-3 text-zinc-400" />
                      <span>Reconectar</span>
                    </button>
                    <button
                      onClick={() => handleLogout(p.id)}
                      title="Cerrar sesión"
                      className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors border border-zinc-800 hover:border-red-500/20"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => onOpenLoginModal(p.id)}
                    className="w-full py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-zinc-950 text-xs font-semibold rounded-lg transition-all shadow-md shadow-emerald-950/20 flex items-center justify-center gap-1.5"
                  >
                    <KeyRound className="h-3.5 w-3.5" />
                    <span>Conectar con 1 Clic</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
