import api from "../api/client";

const campaignService = {
  async getCampaigns() {
    const response = await api.get("/campaigns");
    return response.data;
  },

  async getCampaign(campaignId) {
    // Campaign detail loads enriched data (leads + queue + drafts).
    // Supabase can take a little longer to restore an idle pooled database
    // connection.  The old 15s override was shorter than Axios' normal 30s
    // timeout and caused the detail page to fail even while the API query was
    // still completing.
    const response = await api.get(`/campaigns/${campaignId}`, {
      timeout: 60000,
    });
    return response.data;
  },

  async createCampaign(payload) {
    const response = await api.post("/campaigns", payload);
    return response.data;
  },

  async startCampaign(campaignId) {
    const response = await api.post(`/campaigns/${campaignId}/start`);
    return response.data;
  },

  async processCampaign(campaignId) {
    // Generates one AI email per lead in a single request, so it needs
    // far more than the default 30s API timeout (10 minutes here).
    const response = await api.post(
      `/campaigns/${campaignId}/process`,
      null,
      { timeout: 600000 },
    );
    return response.data;
  },

  async pauseCampaign(campaignId) {
    const response = await api.post(`/campaigns/${campaignId}/pause`);
    return response.data;
  },

  async resumeCampaign(campaignId) {
    const response = await api.post(`/campaigns/${campaignId}/resume`);
    return response.data;
  },

  async cancelCampaign(campaignId) {
    const response = await api.post(`/campaigns/${campaignId}/cancel`);
    return response.data;
  },
  async deleteCampaign(campaignId) {
    await api.delete(`/campaigns/${campaignId}`);
  },
};
export default campaignService;
