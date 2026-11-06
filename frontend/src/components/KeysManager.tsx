import React, { useState } from "react";
import { Plus, Key, Copy, Check, Trash2, ShieldCheck, AlertCircle } from "lucide-react";
import { ApiKeyItem } from "../types";

interface KeysManagerProps {
  keys: ApiKeyItem[];
  onRefresh: () => void;
}

export const KeysManager: React.FC<KeysManagerProps> = ({ keys, onRefresh }) => {
  const [showModal, setShowModal] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [rateLimit, setRateLimit] = useState(60);
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/v1/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: keyName.trim(),
          rate_limit_rpm: rateLimit,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error al crear la API key");
      }

      const data = await res.json();
      setCreatedSecret(data.raw_key);
      setKeyName("");
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (id: string, name: string) => {
    if (!confirm(`¿Estás seguro de revocar la clave '${name}'? Cualquier app que la use dejará de funcionar inmediatamente.`)) {
      return;
    }
    try {
      await fetch(`/api/v1/keys/${id}`, { method: "DELETE" });
      onRefresh();
    } catch (err) {
      console.error("Revoke error", err);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <span>Virtual API Keys</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 font-mono">
              {keys.length}
            </span>
          </h2>
          <p className="text-xs text-zinc-400">
            Genera llaves seguras para tus aplicaciones externas (Conta360, bots, scripts). Compatible con OpenAI SDK.
          </p>
        </div>
        <button
          onClick={() => {
            setCreatedSecret(null);
            setShowModal(true);
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-zinc-950 rounded-lg text-xs font-semibold shadow-md shadow-emerald-950/20 transition-all"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Crear API Key</span>
        </button>
      </div>

      {/* Keys Table */}
      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 overflow-hidden">
        {keys.length === 0 ? (
          <div className="py-12 text-center text-zinc-500 text-xs">
            No tienes ninguna API Key creada. Haz clic en "Crear API Key" para comenzar.
          </div>
        ) : (
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/40">
                <th className="py-3 px-4 font-medium">Nombre</th>
                <th className="py-3 px-4 font-medium">Prefijo Secreto</th>
                <th className="py-3 px-4 font-medium">Límite</th>
                <th className="py-3 px-4 font-medium">Peticiones</th>
                <th className="py-3 px-4 font-medium">Creada</th>
                <th className="py-3 px-4 font-medium text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono text-[11px]">
              {keys.map((k) => (
                <tr key={k.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="py-3 px-4 font-sans font-medium text-zinc-200">
                    <div className="flex items-center gap-2">
                      <Key className="h-3.5 w-3.5 text-zinc-400" />
                      <span>{k.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-emerald-400 font-semibold">
                    {k.prefix}
                  </td>
                  <td className="py-3 px-4 text-zinc-400">
                    {k.rate_limit_rpm} RPM
                  </td>
                  <td className="py-3 px-4 text-zinc-300">
                    {k.requests_count}
                  </td>
                  <td className="py-3 px-4 text-zinc-500">
                    {k.created_at ? new Date(k.created_at).toLocaleDateString() : "Hoy"}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleRevoke(k.id, k.name)}
                      className="p-1.5 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                      title="Revocar clave"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Key Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>{createdSecret ? "Clave Creada Exitosamente" : "Nueva Virtual API Key"}</span>
            </h3>

            {error && (
              <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 p-2.5 rounded-lg">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {createdSecret ? (
              <div className="space-y-4">
                <p className="text-xs text-zinc-400">
                  Copia esta clave ahora. Por tu seguridad, no se volverá a mostrar completa.
                </p>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-emerald-400 break-all select-all">
                    {createdSecret}
                  </span>
                  <button
                    onClick={() => copyToClipboard(createdSecret, "new")}
                    className="shrink-0 p-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs transition-colors"
                  >
                    {copiedKey === "new" ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium rounded-lg text-xs transition-colors"
                >
                  Entendido, ya la copié
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-zinc-400 block font-medium">
                    Nombre Descriptivo
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Ej. Conta360 - Facturador Backend"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-zinc-400 block font-medium">
                    Límite de Peticiones (RPM)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={rateLimit}
                    onChange={(e) => setRateLimit(parseInt(e.target.value) || 60)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs font-medium transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={loading || !keyName.trim()}
                    className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-zinc-950 font-semibold rounded-lg text-xs transition-colors"
                  >
                    {loading ? "Generando..." : "Generar Clave"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
