import api from "../api/client";

const leadsService = {
  async getLeads(params = {}) {
    const response = await api.get("/leads", {
      params,
    });

    return response.data;
  },

  async getLead(leadId) {
    const response = await api.get(`/leads/${leadId}`);

    return response.data;
  },
};

export default leadsService;