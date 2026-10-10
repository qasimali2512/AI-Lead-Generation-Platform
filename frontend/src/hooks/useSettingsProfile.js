/**
 * useSettingsProfile
 *
 * Settings page ke liye real-time profile hook.
 *
 * - Page pe aate hi (mount) backend se profile fetch karta hai.
 * - Tab wapas active hone par silently re-fetch karta hai (fresh data).
 * - `profile`, `loading`, `error`, `lastSynced`, `refresh` expose karta hai.
 * - `updateProfile` aur `changePassword` wrappers bhi deta hai jo state
 *   automatically update karte hain.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import settingsService from "../services/settingsService";

export function useSettingsProfile() {
  const [profile, setProfile]       = useState(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [lastSynced, setLastSynced] = useState(null);

  const mountedRef = useRef(true);

  // -------------------------------------------------------------------------
  // Core fetch
  // -------------------------------------------------------------------------

  const fetchProfile = useCallback(async (silent = false) => {
    if (!mountedRef.current) return;
    if (!silent) setLoading(true);
    setError(null);

    try {
      const res  = await settingsService.getProfile();
      const data = res?.profile || res;

      if (!mountedRef.current) return;

      setProfile(data);
      setLastSynced(new Date());
    } catch (err) {
      if (!mountedRef.current) return;
      const detail =
        err?.response?.data?.detail || "Unable to load your profile.";
      setError(detail);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  // -------------------------------------------------------------------------
  // Visibility: tab wapas active hone par silent re-fetch
  // -------------------------------------------------------------------------

  useEffect(() => {
    const handleVisibility = () => {
      if (!document.hidden && profile) {
        fetchProfile(true); // silent — loading spinner mat dikhao
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibility);
  }, [fetchProfile, profile]);

  // -------------------------------------------------------------------------
  // Mount / unmount
  // -------------------------------------------------------------------------

  useEffect(() => {
    mountedRef.current = true;
    fetchProfile(false);

    return () => {
      mountedRef.current = false;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // -------------------------------------------------------------------------
  // updateProfile — PATCH /settings/profile
  // -------------------------------------------------------------------------

  const updateProfile = useCallback(async (fullName) => {
    const res = await settingsService.updateProfile({
      full_name: fullName.trim(),
    });

    const updated = res?.profile || res;

    if (mountedRef.current) {
      setProfile((prev) => ({
        ...prev,
        ...updated,
        full_name: updated?.full_name || fullName.trim(),
      }));
      setLastSynced(new Date());
    }

    return res;
  }, []);

  // -------------------------------------------------------------------------
  // changePassword — POST /settings/password
  // -------------------------------------------------------------------------

  const changePassword = useCallback(async (payload) => {
    const res = await settingsService.changePassword(payload);
    return res;
  }, []);

  // -------------------------------------------------------------------------
  // Manual refresh
  // -------------------------------------------------------------------------

  const refresh = useCallback(() => fetchProfile(false), [fetchProfile]);

  return {
    profile,
    loading,
    error,
    lastSynced,
    refresh,
    updateProfile,
    changePassword,
  };
}
