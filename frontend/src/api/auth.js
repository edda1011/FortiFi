import { apiFetch, setAuthToken } from "./client";


export function savedWalletAddress() {
  return window.sessionStorage.getItem("fortifi_address") || "";
}


export async function connectBaseWallet() {
  if (!window.ethereum) {
    throw new Error("Install a Base-compatible wallet such as MetaMask first.");
  }

  const { ethers } = await import("ethers");
  const provider = new ethers.BrowserProvider(window.ethereum);
  await provider.send("wallet_switchEthereumChain", [{ chainId: "0x2105" }]);
  const signer = await provider.getSigner();
  const address = await signer.getAddress();
  const challenge = await apiFetch("/api/auth/nonce", {
    method: "POST",
    body: JSON.stringify({ address }),
  });
  const signature = await signer.signMessage(challenge.message);
  const session = await apiFetch("/api/auth/verify", {
    method: "POST",
    body: JSON.stringify({ address, signature }),
  });
  setAuthToken(session.token);
  window.sessionStorage.setItem("fortifi_address", session.address);
  return session.address;
}


export function disconnectBaseWallet() {
  setAuthToken("");
  window.sessionStorage.removeItem("fortifi_address");
}
