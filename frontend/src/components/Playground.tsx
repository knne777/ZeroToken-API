import React, { useState } from "react";
import { Send, Loader2, Paperclip, Sparkles, Check, FileText } from "lucide-react";

export const Playground: React.FC = () => {
  const [provider, setProvider] = useState("agy");
  const [model, setModel] = useState("gemini-3.8-flash-high");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [message, setMessage] = useState("");
  const [effort, setEffort] = useState("low");
  const [attachments, setAttachments] = useState<{ name: string; content_base64: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(",")[1];
      setAttachments([{ name: file.name, content_base64: base64 }]);
    };
    reader.readAsDataURL(file);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || loading) return;

    try {
      setLoading(true);
      setResponse(null);

      const payload: any = {
        message: message.trim(),
        provider,
        model: model || undefined,
        effort,
      };

      if (systemPrompt.trim()) {
        payload.system_prompt = systemPrompt.trim();
      }

      if (attachments.length > 0) {
        payload.attachments = attachments;
      }

      const res = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      setResponse(data);
    } catch (err: any) {
      setResponse({ error: "ClientError", message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Controls & Input */}
      <div className="lg:col-span-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-emerald-400" />
            <span>Interactive Playground</span>
          </h2>
          <p className="text-xs text-zinc-400">
            Prueba prompts, adjuntos de archivos y respuestas estructuradas en tiempo real sin facturación por token.
          </p>
        </div>

        <form onSubmit={handleSend} className="space-y-3.5 bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">
                Proveedor
              </label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  if (e.target.value === "codex") setModel("gpt-6-luna");
                  else if (e.target.value === "agy") setModel("gemini-3.8-flash-high");
                  else setModel("claude-3-7-sonnet");
                }}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="agy">Google Antigravity (agy)</option>
                <option value="codex">OpenAI Codex (ChatGPT)</option>
                <option value="claude">Anthropic Claude Code</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">
                Razonamiento (Effort)
              </label>
              <select
                value={effort}
                onChange={(e) => setEffort(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="low">Low (Clasificación rápida)</option>
                <option value="medium">Medium</option>
                <option value="high">High (Razonamiento profundo)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-medium text-zinc-400 block mb-1">
              Instrucción de Sistema (System Prompt)
            </label>
            <textarea
              rows={2}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="Ej. Responde estrictamente con un JSON con las claves { category, priority }..."
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 resize-none font-mono"
            />
          </div>

          <div>
            <label className="text-[11px] font-medium text-zinc-400 block mb-1">
              Mensaje del Usuario
            </label>
            <textarea
              rows={4}
              required
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Escribe tu consulta o instrucción..."
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 resize-none font-mono"
            />
          </div>

          {/* Attachment row */}
          <div className="flex items-center justify-between pt-1">
            <label className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 cursor-pointer px-2.5 py-1 rounded bg-zinc-950 border border-zinc-800 hover:border-zinc-700 transition-colors">
              <Paperclip className="h-3.5 w-3.5" />
              <span>{attachments.length > 0 ? attachments[0].name : "Adjuntar archivo temporal"}</span>
              <input type="file" onChange={handleFileUpload} className="hidden" />
            </label>
            {attachments.length > 0 && (
              <button
                type="button"
                onClick={() => setAttachments([])}
                className="text-[11px] text-zinc-500 hover:text-red-400"
              >
                Quitar
              </button>
            )}

            <button
              type="submit"
              disabled={loading || !message.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-zinc-950 font-semibold rounded-lg text-xs transition-all shadow-md shadow-emerald-950/20"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              <span>{loading ? "Ejecutando..." : "Enviar Turno"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Output / Response Panel */}
      <div className="lg:col-span-6 space-y-4">
        <h2 className="text-base font-semibold text-zinc-100">
          Respuesta & Métricas de Turno
        </h2>

        <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-4 min-h-[340px] flex flex-col justify-between">
          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center text-zinc-400 gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
              <span className="text-xs">El motor local está procesando el turno...</span>
            </div>
          ) : response ? (
            <div className="space-y-4">
              {/* Turn Metrics Bar */}
              {response.usage && (
                <div className="flex items-center justify-between bg-zinc-950 border border-zinc-800/80 rounded-lg px-3 py-2 text-[11px] font-mono text-zinc-400">
                  <div>
                    <span className="text-zinc-500">Duración: </span>
                    <span className="text-emerald-400 font-semibold">{response.duration_seconds?.toFixed(2)}s</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Tokens: </span>
                    <span className="text-zinc-200">{response.usage.total_tokens}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Modelo: </span>
                    <span className="text-zinc-200">{response.model}</span>
                  </div>
                </div>
              )}

              {/* Text content */}
              <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg">
                <pre className="font-mono text-xs text-zinc-200 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                  {response.response || JSON.stringify(response, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="py-24 flex flex-col items-center justify-center text-zinc-500 gap-2 text-center text-xs">
              <FileText className="h-8 w-8 text-zinc-700" />
              <p>Envía una consulta desde el panel izquierdo para ver la respuesta y el desglose de tokens aquí.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
