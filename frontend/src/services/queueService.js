import api from "../api/client";

const queueService = {
  async getQueue(status = "", days = 3) {
    const params = {};

    if (status) {
      params.queue_status = status;
    }

    // days=0 means no filter (all time); otherwise filter last N days
    if (days > 0) {
      params.days = days;
    }

    const response = await api.get("/email-queue", { params });
    return response.data;
  },

  async getQueueItem(queueId) {
    const response = await api.get(`/email-queue/${queueId}`);
    return response.data;
  },

  async updateStatus(queueId, status) {
    const response = await api.patch(
      `/email-queue/${queueId}/status`,
      { status },
    );

    return response.data;
  },

  async cancel(queueId) {
    const response = await api.post(
      `/email-queue/${queueId}/cancel`,
    );

    return response.data;
  },

  async retry(queueId) {
    const response = await api.post(
      `/email-queue/${queueId}/retry`,
    );

    return response.data;
  },

  async processQueue(batchSize = 20) {
    const response = await api.post(
      `/email-queue/process`,
      null,
      { params: { batch_size: batchSize } },
    );

    return response.data;
  },
};

export default queueService;