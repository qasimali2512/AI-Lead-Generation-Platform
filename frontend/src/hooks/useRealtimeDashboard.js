/**
 * useRealtimeDashboard
 *
 * Dashboard ke liye real-time analytics hook.
 *
 * Strategy:
 *  1. SSE (Server-Sent Events) se connect karo — backend push karta hai
 *     har `interval` seconds mein.
 *  2. Agar SSE support nahi hai ya connection fail ho jaye, automatic
 *     polling fallback (every `pollInterval` ms).
 *  3. Page tab hidden hone par SSE pause, visible hone par reconnect.
 *
 * Returns:
 *   { data, loading, error, lastUpdated, isLive, refresh }
 */

import { useCallback, useEffect, useRef, useState } from "react";

import storage from "../utils/storage";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

// SSE push interval (seconds) — backend ko bata do kitni baar bheje
const SSE_INTERVAL_SEC = 15;

// Polling fallback interval (ms)
const POLL_INTERVAL_MS = 30_000;

// SSE reconnect delay after error (ms) — exponential backoff ke saath
const RECONNECT_BASE_MS = 3_000;
const RECONNECT_MAX_MS = 60_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildStreamUrl(token, days) {
  const params = new URLSearchParams({
    token,
    days: String(days),
    interval: String(SSE_INTERVAL_SEC),
  });
  // Raw base URL se /api/v1 prefix hata ke sirf origin rakho, kyunki
  // API_BASE already /api/v1 include karta hai
  return `${API_BASE}/analytics/stream?${params.toString()}`;
}

async function fetchSummaryOnce(days) {
  // Polling fallback: normal axios client se nahi (circular dep avoid),
  // seedha fetch use karo
  const token = storage.getAccessToken();
  const url = `${API_BASE}/analytics/summary?days=${days}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useRealtimeDashboard(days = 30) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isLive, setIsLive] = useState(false);

  const esRef = useRef(null);
  const pollRef = useRef(null);
  const reconnectRef = useRef(null);
  const reconnectDelay = useRef(RECONNECT_BASE_MS);
  const mountedRef = useRef(true);
  // Track whether we've received first data (to stop initial spinner fast)
  const hasDataRef = useRef(false);

  // -------------------------------------------------------------------------
  // Data setter
  // -------------------------------------------------------------------------

  const applyData = useCallback((summary) => {
    if (!mountedRef.current) return;
    setData(summary);
    setLastUpdated(new Date());
    setLoading(false);
    setError(null);
    hasDataRef.current = true;
  }, []);

  // -------------------------------------------------------------------------
  // Fast initial load — fetch summary immediately on mount
  // -------------------------------------------------------------------------

  const fetchImmediate = useCallback(() => {
    fetchSummaryOnce(days)
      .then(applyData)
      .catch(() => {
        // Ignore — SSE or polling will cover it
        if (mountedRef.current && !hasDataRef.current) {
          setLoading(false);
        }
      });
  }, [days, applyData]);

  // -------------------------------------------------------------------------
  // Polling fallback
  // -------------------------------------------------------------------------

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    setIsLive(false);

    // Don't fetch immediately here — fetchImmediate already did it on mount
    pollRef.current = setInterval(() => {
      fetchSummaryOnce(days).then(applyData).catch((err) => {
        if (mountedRef.current) setError(err.message);
      });
    }, POLL_INTERVAL_MS);
  }, [days, applyData]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // -------------------------------------------------------------------------
  // SSE connection
  // -------------------------------------------------------------------------

  const connectSSE = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }

    const token = storage.getAccessToken();
    if (!token) {
      startPolling();
      return;
    }

    if (typeof EventSource === "undefined") {
      startPolling();
      return;
    }

    const url = buildStreamUrl(token, days);
    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener("connected", () => {
      if (!mountedRef.current) return;
      setIsLive(true);
      setError(null);
      stopPolling();
      reconnectDelay.current = RECONNECT_BASE_MS;
    });

    es.addEventListener("analytics", (event) => {
      if (!mountedRef.current) return;
      try {
        const summary = JSON.parse(event.data);
        applyData(summary);
      } catch (e) {
        console.error("[SSE] JSON parse error:", e);
      }
    });

    es.addEventListener("heartbeat", () => {});

    es.addEventListener("error", (event) => {
      if (!mountedRef.current) return;

      const isAuthError =
        event?.data && JSON.parse(event.data || "{}").detail?.includes("auth");

      if (isAuthError) {
        es.close();
        setError("Session expired. Please refresh.");
        startPolling();
        return;
      }

      es.close();
      esRef.current = null;
      setIsLive(false);

      if (!pollRef.current) startPolling();

      reconnectRef.current = setTimeout(() => {
        if (!mountedRef.current) return;
        reconnectDelay.current = Math.min(
          reconnectDelay.current * 2,
          RECONNECT_MAX_MS,
        );
        connectSSE();
      }, reconnectDelay.current);
    });
  }, [days, applyData, startPolling, stopPolling]);

  // -------------------------------------------------------------------------
  // Visibility change
  // -------------------------------------------------------------------------

  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        if (esRef.current) {
          esRef.current.close();
          esRef.current = null;
          setIsLive(false);
        }
        stopPolling();
      } else {
        // Immediate fetch on tab focus so data is fresh instantly
        fetchSummaryOnce(days).then(applyData).catch(() => {});
        connectSSE();
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibility);
  }, [connectSSE, stopPolling, days, applyData]);

  // -------------------------------------------------------------------------
  // Mount — fetch immediately + connect SSE in parallel
  // -------------------------------------------------------------------------

  useEffect(() => {
    mountedRef.current = true;
    hasDataRef.current = false;

    // 1. Fast path: fetch summary immediately (no SSE overhead)
    fetchImmediate();

    // 2. Also start SSE for live updates (runs in parallel)
    connectSSE();

    return () => {
      mountedRef.current = false;
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      stopPolling();
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  // -------------------------------------------------------------------------
  // Manual refresh
  // -------------------------------------------------------------------------

  const refresh = useCallback(() => {
    setLoading(true);
    fetchSummaryOnce(days)
      .then(applyData)
      .catch((err) => {
        if (mountedRef.current) {
          setError(err.message);
          setLoading(false);
        }
      });
  }, [days, applyData]);

  return { data, loading, error, lastUpdated, isLive, refresh };
}
