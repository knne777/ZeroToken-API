import React, { useState, useEffect } from "react";
import { LayoutDashboard, Key, Sparkles, Activity, ShieldCheck, ChevronRight, Settings } from "lucide-react";
import { Header } from "./components/Header";
import { ProvidersHub } from "./components/ProvidersHub";
import { KeysManager } from "./components/KeysManager";
import { Playground } from "./components/Playground";
import { TelemetryLogs } from "./components/TelemetryLogs";
import { AuthModal } from "./components/AuthModal";
import { LoginScreen } from "./components/LoginScreen";
import { SettingsView } from "./components/SettingsView";
import { AuthStatusResponse, ApiKeyItem, AnalyticsOverview, RequestLogItem } from "./types";

export const App: React.FC = () => {
  const [adminToken, setAdminToken] = useState<string | null>(() => localStorage.getItem("ztk_admin_token"));
  const [adminUser, setAdminUser] = useState<string>(() => localStorage.getItem("ztk_admin_user") || "admin");
  const [activeTab, setActiveTab] = useState<"dashboard" | "keys" | "playground" | "logs" | "settings">("dashboard");
  const [authStatus, setAuthStatus] = useState<AuthStatusResponse | null>(null);
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [logs, setLogs] = useState<RequestLogItem[]>([]);
  const [authModalProvider, setAuthModalProvider] = useState<string | null>(null);

  const getHeaders = () => {
    return adminToken ? { Authorization: `Bearer ${adminToken}` } : {};
  };

  const handleLogout = () => {
    localStorage.removeItem("ztk_admin_token");
    localStorage.removeItem("ztk_admin_user");
    setAdminToken(null);
  };

  const fetchAuthStatus = async () => {
    try {
      const res = await fetch("/api/v1/auth/status", { headers: getHeaders() });
      if (res.ok) setAuthStatus(await res.json());
      else if (res.status === 401) handleLogout();
    } catch (err) {
      console.error("Failed to fetch auth status", err);
    }
  };

  const fetchKeys = async () => {
    try {
      const res = await fetch("/api/v1/keys", { headers: getHeaders() });
      if (res.ok) setKeys(await res.json());
      else if (res.status === 401) handleLogout();
    } catch (err) {
      console.error("Failed to fetch keys", err);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch("/api/v1/analytics/overview", { headers: getHeaders() });
      if (res.ok) setAnalytics(await res.json());
      else if (res.status === 401) handleLogout();
    } catch (err) {
      console.error("Failed to fetch analytics", err);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch("/api/v1/analytics/logs?limit=50", { headers: getHeaders() });
      if (res.ok) setLogs(await res.json());
      else if (res.status === 401) handleLogout();
    } catch (err) {
      console.error("Failed to fetch logs", err);
    }
  };

  const refreshAll = () => {
    if (!adminToken) return;
    fetchAuthStatus();
    fetchKeys();
    fetchAnalytics();
    fetchLogs();
  };

  useEffect(() => {
    if (adminToken) {
      refreshAll();
      const interval = setInterval(refreshAll, 10000);
      return () => clearInterval(interval);
    }
  }, [adminToken]);

  // If not authenticated, render LoginScreen
  if (!adminToken) {
    return (
      <LoginScreen
        onLoginSuccess={(token, user) => {
          setAdminToken(token);
          setAdminUser(user);
        }}
      />
    );
  }

  const navItems = [
    { id: "dashboard", label: "Dashboard & Conexiones", icon: LayoutDashboard },
    { id: "keys", label: "Virtual API Keys", icon: Key },
    { id: "playground", label: "Playground", icon: Sparkles },
    { id: "logs", label: "Telemetría & Auditoría", icon: Activity },
    { id: "settings", label: "Ajustes de Seguridad", icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col font-sans">
      <Header analytics={analytics} />

      <div className="flex-1 flex max-w-7xl w-full mx-auto px-6 py-6 gap-8">
        {/* Sidebar */}
        <aside className="w-56 shrink-0 hidden md:block space-y-6">
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as any)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-zinc-800/90 text-zinc-100 shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`h-4 w-4 ${isActive ? "text-emerald-400" : "text-zinc-500"}`} />
                    <span>{item.label}</span>
                  </div>
                  {isActive && <ChevronRight className="h-3.5 w-3.5 text-zinc-400" />}
                </button>
              );
            })}
          </nav>

          {/* Quick System Summary */}
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-4 space-y-3 text-xs">
            <div className="flex items-center gap-2 text-zinc-300 font-semibold text-[11px]">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>Suscripción Gateway</span>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Tus llamadas usan suscripciones locales sin tarjetas ni cobros por token de OpenAI o Google Vertex.
            </p>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 space-y-8 overflow-hidden">
          {activeTab === "dashboard" && (
            <div className="space-y-8">
              <ProvidersHub
                authStatus={authStatus}
                onOpenLoginModal={(p) => setAuthModalProvider(p)}
                onRefresh={fetchAuthStatus}
              />
              <KeysManager keys={keys} onRefresh={fetchKeys} />
              <TelemetryLogs logs={logs} onRefresh={fetchLogs} />
            </div>
          )}

          {activeTab === "keys" && (
            <KeysManager keys={keys} onRefresh={fetchKeys} />
          )}

          {activeTab === "playground" && (
            <Playground />
          )}

          {activeTab === "logs" && (
            <TelemetryLogs logs={logs} onRefresh={fetchLogs} />
          )}

          {activeTab === "settings" && (
            <SettingsView username={adminUser} onLogout={handleLogout} />
          )}
        </main>
      </div>

      {/* Auth Modal if active */}
      {authModalProvider && (
        <AuthModal
          provider={authModalProvider}
          onClose={() => setAuthModalProvider(null)}
          onSuccess={() => {
            setAuthModalProvider(null);
            fetchAuthStatus();
          }}
        />
      )}
    </div>
  );
};
