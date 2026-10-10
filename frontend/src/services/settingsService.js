import api from "../api/client";
export async function getBrandSettings() {
  const response = await api.get("/settings/brand");
  return response.data;
}

export async function createBrandSettings(payload) {
  const response = await api.post(
    "/settings/brand",
    payload,
  );

  return response.data;
}

export async function updateBrandSettings(payload) {
  const response = await api.put(
    "/settings/brand",
    payload,
  );

  return response.data;
}