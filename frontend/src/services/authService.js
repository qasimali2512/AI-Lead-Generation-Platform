import api from "../api/client";

const authService = {
  async login(credentials) {
    const response = await api.post(
      "/auth/login",
      credentials,
    );

    return response.data;
  },

  async register(payload) {
    const response = await api.post(
      "/auth/register",
      payload,
    );

    return response.data;
  },

  async getCurrentUser() {
    const response = await api.get(
      "/auth/me",
    );

    return response.data;
  },

  async refreshToken(refreshToken) {
    const response = await api.post(
      "/auth/refresh",
      {
        refresh_token: refreshToken,
      },
    );

    return response.data;
  },

  async logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      // Local authentication state is cleared regardless.
    }
  },
};

export default authService;