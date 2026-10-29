"use client";

import React, { useEffect, useState, useCallback } from "react";
import { checkBackendHealth } from "@/lib/api";
import { BackendConnectionState } from "@/types/api";
import { RefreshCw, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export function BackendStatusBadge() {
  const [state, setState] = useState<BackendConnectionState>({
    status: "loading",
    latencyMs: null,
    data: null,
    errorMessage: null,
    lastChecked: null,
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchHealth = useCallback(async () => {
    setIsRefreshing(true);
    const result = await checkBackendHealth();
    if (result.success && result.data) {
      setState({
        status: "connected",
        latencyMs: result.latencyMs,
        data: result.data,
        errorMessage: null,
        lastChecked: new Date(),
      });
    } else {
      setState({
        status: "disconnected",
        latencyMs: result.latencyMs,
        data: null,
        errorMessage: result.error || "Backend unreachable",
        lastChecked: new Date(),
      });
    }
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    fetchHealth();
    // Periodic poll every 15s
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return (
    <div className="flex items-center gap-2">
      {state.status === "loading" && (
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-xs font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <span>Checking API...</span>
        </div>
      )}

      {state.status === "connected" && (
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs font-medium shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>
            API: <strong className="font-semibold text-emerald-800 dark:text-emerald-200">Connected</strong>
          </span>
          {state.latencyMs !== null && (
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400/80 font-mono">
              ({state.latencyMs}ms)
            </span>
          )}
          {state.data?.database?.connected && (
            <span className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-800 dark:text-emerald-200 border border-emerald-500/30 uppercase font-mono">
              DB: {state.data.database.type}
            </span>
          )}
        </div>
      )}

      {state.status === "disconnected" && (
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs font-medium shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
          </span>
          <span>
            API: <strong className="font-semibold text-rose-800 dark:text-rose-200">Disconnected</strong>
          </span>
          <button
            onClick={fetchHealth}
            disabled={isRefreshing}
            title="Retry connecting to backend"
            className="ml-1 p-0.5 hover:bg-rose-500/20 rounded transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin text-rose-600 dark:text-rose-300" : "text-rose-500"}`} />
          </button>
        </div>
      )}

      {state.status === "connected" && (
        <button
          onClick={fetchHealth}
          disabled={isRefreshing}
          title="Refresh backend status"
          className="p-1.5 rounded-lg border border-slate-200 dark:border-surface-borderDark text-slate-500 dark:text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-cyan-500" : ""}`} />
        </button>
      )}
    </div>
  );
}
