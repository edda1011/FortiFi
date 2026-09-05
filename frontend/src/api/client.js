const API_BASE_URL = "http://127.0.0.1:8000";
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
let authToken = window.sessionStorage.getItem("fortifi_session") || "";


export function setAuthToken(token) {
  authToken = token || "";
  if (authToken) window.sessionStorage.setItem("fortifi_session", authToken);
  else window.sessionStorage.removeItem("fortifi_session");
}


/**
 * Shared fetch helper that parses FastAPI error responses
 * (which use { "detail": "..." }) into readable Error messages.
 */
export async function apiFetch(path, options = {}) {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...(options.headers || {}),
      },
    }
  );

  if (response.status === 401 && authToken) {
    setAuthToken("");
    window.sessionStorage.removeItem("fortifi_address");
    window.dispatchEvent(new Event("fortifi:session-expired"));
  }

  if (!response.ok) {
    let errorMessage = "Request failed.";

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
