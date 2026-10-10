import api from "../api/client";

const websiteService = {
  async scanWebsite(leadId, forceRescan = false) {
    const response = await api.post(
      `/leads/${leadId}/scan`,
      {
        force_rescan: forceRescan,
      },
    );

    return response.data;
  },

  async getLatestScan(leadId) {
    const response = await api.get(
      `/leads/${leadId}/scan`,
    );

    return response.data;
  },

  async getScanHistory(leadId, limit = 10) {
    const response = await api.get(
      `/leads/${leadId}/scans`,
      {
        params: {
          limit,
        },
      },
    );

    return response.data;
  },

  async analyzeIssues(leadId, scanId = null) {
    const url = scanId
      ? `/leads/${leadId}/scans/${scanId}/issues/analyze`
      : `/leads/${leadId}/issues/analyze`;

    const response = await api.post(url);

    return response.data;
  },

  async getIssues(leadId, params = {}) {
    const response = await api.get(
      `/leads/${leadId}/issues`,
      {
        params,
      },
    );

    return response.data;
  },
};

export default websiteService;