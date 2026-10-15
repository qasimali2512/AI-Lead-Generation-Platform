import api from "../api/client";

const autoDiscoveryService = {
  async getSettings() {
    const response = await api.get("/auto-discovery");
    return response.data;
  },

  async updateSettings(payload) {
    const response = await api.put("/auto-discovery", payload);
    return response.data;
  },

  async runNow() {
    const response = await api.post("/auto-discovery/run-now");
    return response.data;
  },

  async resetLocation() {
    const response = await api.post("/auto-discovery/reset-location");
    return response.data;
  },

  async getCountries() {
    const response = await api.get("/auto-discovery/countries");
    return response.data.countries || [];
  },
};

export default autoDiscoveryService;