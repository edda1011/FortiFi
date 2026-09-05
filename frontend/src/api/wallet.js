import { apiFetch } from "./client";

const API_BASE_URL = "http://127.0.0.1:8000";
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";


async function parseError(response, fallback) {
  let errorMessage = fallback;

  try {
    const errorData = await response.json();

    if (typeof errorData.detail === "string") {
      errorMessage = errorData.detail;
    }
  } catch {
    // Keep the default error message.
  }

  return errorMessage;
}


export async function checkWallet(address) {
  const response = await fetch(
    `${API_BASE_URL}/api/wallet/check`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        address,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to check the wallet.")
    );
  }

  return response.json();
}


export function checkConnectedWallet() {
  return apiFetch("/api/wallet/connected");
}


export async function getWalletHistory(address, limit = 20) {
  const response = await fetch(
    `${API_BASE_URL}/api/wallet/${encodeURIComponent(address)}/history?limit=${limit}`
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to load wallet history.")
    );
  }

  return response.json();
}


export async function getWalletExposure(address) {
  const response = await fetch(
    `${API_BASE_URL}/api/wallet/${encodeURIComponent(address)}/exposure`
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to load wallet exposure.")
    );
  }

  return response.json();
}
