import {
  createContext,
  useEffect,
  useState,
} from "react";

import authService from "../services/authService";
import storage from "../utils/storage";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = Boolean(
    storage.getAccessToken() && user,
  );

  useEffect(() => {
    initializeAuth();
  }, []);

  async function initializeAuth() {
    const accessToken =
      storage.getAccessToken();

    if (!accessToken) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const currentUser =
        await authService.getCurrentUser();

      setUser(currentUser);
    } catch (error) {
      storage.clearAuth();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function login(payload) {
    const data =
      await authService.login(payload);

    const accessToken =
      data?.access_token ||
      data?.accessToken ||
      "";

    const refreshToken =
      data?.refresh_token ||
      data?.refreshToken ||
      null;

    if (!accessToken) {
      throw new Error(
        "Login did not return an access token.",
      );
    }

    storage.setAccessToken(
      accessToken,
    );

    if (refreshToken) {
      storage.setRefreshToken(
        refreshToken,
      );
    }

    const authenticatedUser =
      data?.user ||
      null;

    if (authenticatedUser) {
      setUser(authenticatedUser);
    } else {
      const currentUser =
        await authService.getCurrentUser();

      setUser(currentUser);
    }

    return data;
  }

  async function register(payload) {
    const data =
      await authService.register(payload);

    const accessToken =
      data?.access_token ||
      data?.accessToken ||
      "";

    const refreshToken =
      data?.refresh_token ||
      data?.refreshToken ||
      null;

    /*
     * IMPORTANT
     *
     * When Supabase email confirmation
     * is enabled, signup can successfully
     * create the account without returning
     * an access token.
     *
     * In that situation:
     *
     * - Do NOT log the user in.
     * - Do NOT set user.
     * - Do NOT go to dashboard.
     * - Keep the user on the verification flow.
     */

    if (!accessToken) {
      storage.clearAuth();
      setUser(null);

      return data;
    }

    /*
     * This branch is only used when the
     * backend actually returns a session.
     */

    storage.setAccessToken(
      accessToken,
    );

    if (refreshToken) {
      storage.setRefreshToken(
        refreshToken,
      );
    }

    const authenticatedUser =
      data?.user ||
      null;

    if (authenticatedUser) {
      setUser(authenticatedUser);
    } else {
      const currentUser =
        await authService.getCurrentUser();

      setUser(currentUser);
    }

    return data;
  }

  async function refreshSession() {
    const refreshToken =
      storage.getRefreshToken();

    if (!refreshToken) {
      throw new Error(
        "No refresh token available.",
      );
    }

    const data =
      await authService.refresh(
        refreshToken,
      );

    const accessToken =
      data?.access_token ||
      data?.accessToken ||
      "";

    const newRefreshToken =
      data?.refresh_token ||
      data?.refreshToken ||
      refreshToken;

    if (!accessToken) {
      throw new Error(
        "Session refresh failed.",
      );
    }

    storage.setAccessToken(
      accessToken,
    );

    storage.setRefreshToken(
      newRefreshToken,
    );

    const currentUser =
      await authService.getCurrentUser();

    setUser(currentUser);

    return data;
  }

  async function logout() {
    try {
      await authService.logout();
    } catch (error) {
      // Local auth state must still be cleared.
    } finally {
      storage.clearAuth();
      setUser(null);
    }
  }

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    refreshSession,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}