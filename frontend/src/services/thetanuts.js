const BASE_CHAIN_ID = 8453;
const BASE_RPC_URL = "https://mainnet.base.org";
const FORTIFI_API_URL = "http://127.0.0.1:8000";
const PREVIEW_USDC = 5_000000n;
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

let client;
let selectedOrder;


async function getClient() {
  if (!client) {
    const [{ ethers }, { ThetanutsClient }] = await Promise.all([
      import("ethers"),
      import("@thetanuts-finance/thetanuts-client"),
    ]);
    client = new ThetanutsClient({
      chainId: BASE_CHAIN_ID,
      provider: new ethers.JsonRpcProvider(BASE_RPC_URL),
      apiBaseUrl: `${FORTIFI_API_URL}/api/thetanuts/orderbook`,
    });
  }
  return client;
}


function sameAddress(left, right) {
  return left?.toLowerCase() === right?.toLowerCase();
}


function tokenSymbol(chainConfig, address) {
  const match = Object.values(chainConfig.tokens).find((token) =>
    sameAddress(token.address, address)
  );
  return match?.symbol || "Unknown token";
}


function productName(chainConfig, address) {
  const match = Object.entries(chainConfig.implementations).find(([, implementation]) =>
    sameAddress(implementation, address)
  );
  return match?.[0] || "PUT";
}


function transactionError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  const code = error?.code ?? error?.info?.error?.code;
  if (code === "ACTION_REJECTED" || code === 4001 || /user (?:denied|rejected)/i.test(message)) {
    return new Error("Transaction cancelled. No funds were moved.");
  }
  if (code === "INSUFFICIENT_FUNDS" || /insufficient funds|not enough funds/i.test(message)) {
    return new Error("Not enough Base ETH to pay the network fee.");
  }
  if (/transfer amount exceeds balance|exceeds.*balance/i.test(message)) {
    return new Error("You need at least 5 USDC on Base to purchase this hedge.");
  }
  return new Error("The hedge transaction could not be completed. Check your Base balances and try again.");
}


export async function loadLiveHedgePreview() {
  const sdk = await getClient();
  const [orders, market] = await Promise.all([
    sdk.api.fetchOrders(),
    sdk.api.getMarketData(),
  ]);
  const now = Math.floor(Date.now() / 1000);
  const ethFeed = sdk.chainConfig.priceFeeds.ETH;
  const ethPrice = Number(market.prices.ETH);

  const candidates = orders.filter((item) => {
    const raw = item.rawApiData;
    return raw
      && sameAddress(raw.priceFeed, ethFeed)
      && raw.isCall === false
      && raw.isLong === true
      && raw.strikes?.length === 1
      && raw.orderExpiryTimestamp > now
      && Number(item.order.expiry) > now
      && item.availableAmount > 0n;
  });

  if (!candidates.length) {
    throw new Error("No active ETH put orders are available on Thetanuts right now.");
  }

  const targetStrike = ethPrice * 0.9;
  candidates.sort((left, right) => {
    const leftStrike = Number(left.rawApiData.strikes[0]) / 1e8;
    const rightStrike = Number(right.rawApiData.strikes[0]) / 1e8;
    const leftDays = (Number(left.order.expiry) - now) / 86400;
    const rightDays = (Number(right.order.expiry) - now) / 86400;
    const leftScore = Math.abs(leftStrike - targetStrike) / Math.max(ethPrice, 1)
      + Math.abs(leftDays - 14) / 365;
    const rightScore = Math.abs(rightStrike - targetStrike) / Math.max(ethPrice, 1)
      + Math.abs(rightDays - 14) / 365;
    return leftScore - rightScore;
  });

  const order = candidates[0];
  selectedOrder = order;
  const preview = sdk.optionBook.previewFillOrder(order, PREVIEW_USDC);
  const product = productName(sdk.chainConfig, order.rawApiData.implementation);

  return {
    network: "Base Mainnet",
    optionBook: order.rawApiData.optionBookAddress || sdk.chainConfig.contracts.optionBook,
    product,
    settlement: product.startsWith("PHYSICAL_") ? "Physical settlement" : "Cash settlement",
    strike: Number(order.rawApiData.strikes[0]) / 1e8,
    expiry: new Date(Number(preview.expiry) * 1000).toISOString(),
    budget: Number(preview.totalCollateral) / 1e6,
    contracts: Number(preview.numContracts) / 1e6,
    pricePerContract: Number(preview.pricePerContract) / 1e8,
    collateral: tokenSymbol(sdk.chainConfig, preview.collateralToken),
    collateralAddress: preview.collateralToken,
    maker: preview.maker,
    availableOrders: candidates.length,
    spotPrice: ethPrice,
  };
}


export async function purchaseLiveHedge(expectedAccount) {
  try {
    if (!selectedOrder) throw new Error("Refresh the live hedge preview first.");
    if (!window.ethereum) throw new Error("A Base-compatible wallet is required.");

    const [{ ethers }, { ThetanutsClient }] = await Promise.all([
    import("ethers"),
    import("@thetanuts-finance/thetanuts-client"),
  ]);
    await window.ethereum.request({
    method: "wallet_switchEthereumChain",
    params: [{ chainId: "0x2105" }],
  });
    const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const address = await signer.getAddress();
    if (address.toLowerCase() !== expectedAccount.toLowerCase()) {
      throw new Error("ACCOUNT_MISMATCH");
    }

    const sdk = new ThetanutsClient({
    chainId: BASE_CHAIN_ID,
    provider,
    signer,
    apiBaseUrl: `${FORTIFI_API_URL}/api/thetanuts/orderbook`,
  });
    const optionBook = selectedOrder.rawApiData.optionBookAddress
      || sdk.chainConfig.contracts.optionBook;
    const approval = await sdk.erc20.ensureAllowance(
    BASE_USDC,
    optionBook,
    PREVIEW_USDC,
  );
    const receipt = await sdk.optionBook.fillOrder(selectedOrder, PREVIEW_USDC);
    return { approvalHash: approval?.hash || null, transactionHash: receipt.hash };
  } catch (error) {
    if (error instanceof Error && error.message === "ACCOUNT_MISMATCH") {
      throw new Error("Switch MetaMask back to the wallet signed in to FortiFi.");
    }
    if (error instanceof Error && [
      "Refresh the live hedge preview first.",
      "A Base-compatible wallet is required.",
    ].includes(error.message)) throw error;
    throw transactionError(error);
  }
}
