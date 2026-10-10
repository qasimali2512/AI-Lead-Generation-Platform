import api from "../api/client";

const discoveryService = {
  async discoverBusinesses(payload) {
    const response = await api.post(
      "/discovery/businesses",
      payload,
      // Large-city Overpass searches can take longer than the app-wide
      // 30-second timeout, especially when many leads are requested.
      // Qualified-email searches deliberately inspect more candidates before
      // applying the requested result limit, so allow a longer browser wait.
      { timeout: 300000 },
    );

    return response.data;
  },
};

export default discoveryService;
