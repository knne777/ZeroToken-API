import React, { useState, useEffect } from "react";
import { Copy, Check, ExternalLink, AlertCircle, Loader2, KeyRound } from "lucide-react";
import { AuthSessionResponse } from "../types";

interface AuthModalProps {
  provider: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ provider, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<AuthSessionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [pollingStatus, setPollingStatus] = useState<string>("INITIALIZING");
  const [tokenInput, setTokenInput] = useState("");
  const [importing, setImporting] = useState(false);
  const [tab, setTab] = useState<"device" | "import">("device");

  const providerNames: Record<string, string> = {
    codex: "OpenAI ChatGPT (Codex)",
    agy: "Google Antigravity",
    claude: "Anthropic Claude Code",
  };

  useEffect(() => {
    let timer: NodeJS.Timeout;

    const startSession = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/v1/auth/${provider}/start`, { method: "POST" });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Error al iniciar sesión de login");
        }
        const data: AuthSessionResponse = await res.json();
        setSession(data);
        setPollingStatus(data.status);

        // Start polling if device auth session is active
        if (data.session_id && provider === "codex") {
          timer = setInterval(async () => {
            try {
              const checkRes = await fetch(`/api/v1/auth/session/${data.session_id}`);
              if (checkRes.ok) {
                const sData = await checkRes.json();
                setPollingStatus(sData.status);
                if (sData.status === "SUCCESS") {
                  clearInterval(timer);
                  setTimeout(() => onSuccess(), 1200);
                } else if (sData.status === "FAILED") {
                  clearInterval(timer);
                  setError(sData.error_message || "La autorización fue rechazada o expiró.");
                }
              }
            } catch (err) {
              console.error("Polling error", err);
            }
          }, 2000);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    startSession();

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [provider]);

  const handleCopyCode = () => {
    if (session?.user_code) {
      navigator.clipboard.writeText(session.user_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleImportToken = async () => {
    if (!tokenInput.trim()) return;
    try {
      setImporting(true);
      setError(null);
      const res = await fetch(`/api/v1/auth/${provider}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: tokenInput }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error al guardar el token");
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <h3 className="text-base font-medium text-zinc-100">
              Conectar con {providerNames[provider] || provider}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 text-sm p-1 rounded-md hover:bg-zinc-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800/80 bg-zinc-950/40 px-6">
          <button
            onClick={() => setTab("device")}
            className={`py-2.5 text-xs font-medium border-b-2 transition-colors mr-6 ${
              tab === "device"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Autorización Asistida (1-Clic)
          </button>
          <button
            onClick={() => setTab("import")}
            className={`py-2.5 text-xs font-medium border-b-2 transition-colors ${
              tab === "import"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Pegar Token / Credencial
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 flex items-start gap-3 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {tab === "device" ? (
            loading ? (
              <div className="py-12 flex flex-col items-center justify-center text-zinc-400 gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
                <p className="text-sm">Iniciando protocolo de autorización con {provider}...</p>
              </div>
            ) : pollingStatus === "SUCCESS" ? (
              <div className="py-10 flex flex-col items-center justify-center text-center gap-3">
                <div className="h-12 w-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                  <Check className="h-6 w-6" />
                </div>
                <h4 className="text-base font-semibold text-zinc-100">¡Conexión Exitosa!</h4>
                <p className="text-xs text-zinc-400">
                  Tu suscripción ha quedado vinculada y lista para responder peticiones sin costo por token.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {session?.instructions || "Sigue los pasos para vincular tu suscripción:"}
                </p>

                {session?.user_code ? (
                  <div className="space-y-3">
                    <label className="text-xs font-medium text-zinc-400 block">
                      Paso 1: Copia este código de verificación
                    </label>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-zinc-950 border border-zinc-700 rounded-lg px-4 py-3 text-center font-mono text-xl font-bold tracking-widest text-emerald-400 select-all">
                        {session.user_code}
                      </div>
                      <button
                        onClick={handleCopyCode}
                        className="px-4 py-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors border border-zinc-700"
                      >
                        {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                        {copied ? "Copiado" : "Copiar"}
                      </button>
                    </div>

                    <label className="text-xs font-medium text-zinc-400 block pt-2">
                      Paso 2: Abre el portal oficial de autorización
                    </label>
                    <a
                      href={session.verification_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-zinc-950 font-semibold rounded-lg text-sm transition-all shadow-lg shadow-emerald-950/40"
                    >
                      <span>Abrir OpenAI y Autorizar</span>
                      <ExternalLink className="h-4 w-4" />
                    </a>

                    <div className="pt-3 flex items-center justify-center gap-2 text-xs text-zinc-500">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-zinc-400" />
                      <span>Esperando que completes la confirmación en el navegador...</span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-zinc-300">
                      Este motor utiliza un token de sesión local. Puedes abrir el enlace de autorización o pegar tus credenciales en la pestaña superior.
                    </p>
                    <a
                      href={session?.verification_url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-medium rounded-lg text-xs transition-colors border border-zinc-700"
                    >
                      <span>Abrir portal de autorización</span>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                )}
              </div>
            )
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-zinc-400">
                Pega directamente el contenido JSON de tu archivo de credenciales:
              </p>
              <textarea
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                rows={6}
                placeholder='{\n  "tokens": { ... }\n}'
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 font-mono text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 resize-none"
              />
              <button
                onClick={handleImportToken}
                disabled={importing || !tokenInput.trim()}
                className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-zinc-950 font-semibold rounded-lg text-xs transition-all flex items-center justify-center gap-2"
              >
                {importing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <KeyRound className="h-3.5 w-3.5" />}
                Guardar Credenciales
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
