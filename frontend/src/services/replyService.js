import api from "../api/client";

const replyService = {
  async getThreads(params = {}) {
    const response = await api.get("/replies/threads", {
      params,
    });

    return response.data;
  },

  async getThread(threadId) {
    const response = await api.get(`/replies/threads/${threadId}`);

    return response.data;
  },

  async getThreadMessages(threadId) {
    const response = await api.get(
      `/replies/threads/${threadId}/messages`,
    );

    return response.data;
  },

  async ingestReply(payload) {
    const response = await api.post(
      "/replies/ingest",
      payload,
    );

    return response.data;
  },
};

export default replyService;