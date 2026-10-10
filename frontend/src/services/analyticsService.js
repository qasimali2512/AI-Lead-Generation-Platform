import api from "../api/client";

const analyticsService = {
  async getSummary(days = 30) {
    const response = await api.get("/analytics/summary", {
      params: { days },
    });

    return response.data;
  },
};

export default analyticsService;