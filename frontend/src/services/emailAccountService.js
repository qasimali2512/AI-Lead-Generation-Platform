import api from "../api/client";

const emailAccountService = {
  async getAccounts(params = {}) {
    const response = await api.get("/email-accounts", {
      params,
    });

    return response.data;
  },

  async getAccount(accountId) {
    const response = await api.get(
      `/email-accounts/${accountId}`,
    );

    return response.data;
  },

  async createAccount(payload) {
    const response = await api.post(
      "/email-accounts",
      payload,
    );

    return response.data;
  },

  async updateAccount(accountId, payload) {
    const response = await api.patch(
      `/email-accounts/${accountId}`,
      payload,
    );

    return response.data;
  },

  async updateStatus(accountId, status) {
    const response = await api.patch(
      `/email-accounts/${accountId}/status`,
      { status },
    );

    return response.data;
  },

  async deleteAccount(accountId) {
    const response = await api.delete(
      `/email-accounts/${accountId}`,
    );

    return response.data;
  },
};

export default emailAccountService;