const API_BASE_URL = "http://127.0.0.1:8000";


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
    let errorMessage =
      "Failed to check the wallet.";

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        errorMessage = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(errorMessage);
  }

  return response.json();
}
