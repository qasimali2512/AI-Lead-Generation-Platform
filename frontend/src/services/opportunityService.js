import api from "../api/client";

const opportunityService = {
  async getOpportunities(params = {}) {
    const response = await api.get("/website-opportunities", { params });
    return response.data;
  },

  async getOpportunityByLead(leadId) {
    const response = await api.get(`/leads/${leadId}/website-opportunity`);
    return response.data;
  },

  async createOpportunity(leadId) {
    const response = await api.post(`/leads/${leadId}/website-opportunity`);
    return response.data;
  },

  async updateOpportunityStatus(opportunityId, payload) {
    const response = await api.patch(
      `/website-opportunities/${opportunityId}`,
      payload,
    );
    return response.data;
  },

  async deleteOpportunity(opportunityId) {
    await api.delete(`/website-opportunities/${opportunityId}`);
  },

  // Generate opportunities for all no-website leads (up to `limit` per call)
  async bulkGenerate(limit = 20) {
    const response = await api.post(
      `/website-opportunities/bulk-generate?limit=${limit}`,
      null,
      { timeout: 300_000 }, // 5 min — AI calls take time
    );
    return response.data;
  },
};

export default opportunityService;
