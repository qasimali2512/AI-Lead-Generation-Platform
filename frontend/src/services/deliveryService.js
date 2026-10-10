import api from "../api/client";

const deliveryService = {
  async getDeliveries(params = {}) {
    const response = await api.get("/email-deliveries", {
      params,
    });

    return response.data;
  },

  async getDelivery(deliveryId) {
    const response = await api.get(
      `/email-deliveries/${deliveryId}`,
    );

    return response.data;
  },

  async getQueueDelivery(queueId) {
    const response = await api.get(
      `/email-deliveries/queue/${queueId}`,
    );

    return response.data;
  },

  async createFromQueue(queueId) {
    const response = await api.post(
      `/email-deliveries/from-queue/${queueId}`,
    );

    return response.data;
  },

  async updateEvent(deliveryId, payload) {
    const response = await api.patch(
      `/email-deliveries/${deliveryId}/event`,
      payload,
    );

    return response.data;
  },

  async recordBounce(deliveryId, bounceType, reason) {
    const response = await api.post(
      `/email-deliveries/${deliveryId}/bounce`,
      null,
      {
        params: {
          bounce_type: bounceType,
          reason,
        },
      },
    );

    return response.data;
  },

  async recordComplaint(deliveryId, complaintType = "") {
    const response = await api.post(
      `/email-deliveries/${deliveryId}/complaint`,
      null,
      {
        params: complaintType
          ? { complaint_type: complaintType }
          : {},
      },
    );

    return response.data;
  },

  async recordUnsubscribe(deliveryId) {
    const response = await api.post(
      `/email-deliveries/${deliveryId}/unsubscribe`,
    );

    return response.data;
  },
};

export default deliveryService;