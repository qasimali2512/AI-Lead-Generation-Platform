import api from "../api/client";

const notificationService = {
  async getNotifications() {
    const response = await api.get(
      "/notifications",
    );

    return response.data;
  },

  async createNotification(payload) {
    const response = await api.post(
      "/notifications",
      payload,
    );

    return response.data;
  },

  async markAsRead(notificationId) {
    const response = await api.patch(
      `/notifications/${notificationId}/read`,
    );

    return response.data;
  },

  async markAllAsRead() {
    const response = await api.post(
      "/notifications/read-all",
    );

    return response.data;
  },

  async deleteNotification(notificationId) {
    const response = await api.delete(
      `/notifications/${notificationId}`,
    );

    return response.data;
  },
};

export default notificationService;