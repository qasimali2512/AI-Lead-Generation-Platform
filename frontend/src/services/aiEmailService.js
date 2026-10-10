import api from "../api/client";

const aiEmailService = {
  async generateEmail(leadId, payload) {
    // AI generation can take longer than the default 30s API timeout,
    // so this request gets its own, longer timeout.
    const response = await api.post(
      `/ai-email/leads/${leadId}/generate`,
      payload,
      { timeout: 120000 },
    );

    return response.data;
  },

  async getDrafts(params = {}) {
    const response = await api.get(
      "/ai-email/drafts",
      { params },
    );

    return response.data;
  },

  async getDraft(draftId) {
    const response = await api.get(
      `/ai-email/drafts/${draftId}`,
    );

    return response.data;
  },

  async updateDraft(draftId, payload) {
    const response = await api.patch(
      `/ai-email/drafts/${draftId}`,
      payload,
    );

    return response.data;
  },

  async deleteDraft(draftId) {
    await api.delete(`/ai-email/drafts/${draftId}`);
  },

  async queueEmail(payload) {
    // payload: { draft_id, email_account_id }
    const response = await api.post("/email-queue", payload);

    return response.data;
  },
};

export default aiEmailService;