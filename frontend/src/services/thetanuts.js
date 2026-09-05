import { buildProtectionChoices } from "./hedgeRecommendation";

const BASE_CHAIN_ID = 8453;
const BASE_RPC_URL = "https://mainnet.base.org";
const FORTIFI_API_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
let client;

async function getClient() {
  if (!client) {
    const [{ ethers }, { ThetanutsClient }] = await Promise.all([import("ethers"), import("@thetanuts-finance/thetanuts-client")]);
    client = new ThetanutsClient({ chainId: BASE_CHAIN_ID, provider: new ethers.JsonRpcProvider(BASE_RPC_URL), apiBaseUrl: `${FORTIFI_API_URL}/api/thetanuts/orderbook` });
  }
  return client;
}

function sameAddress(left, right) { return left?.toLowerCase() === right?.toLowerCase(); }
function orderKey(order) { return order.signature; }
function productName(config, address) {
  return Object.entries(config.implementations).find(([, value]) => sameAddress(value, address))?.[0] || "PUT";
}
function tokenSymbol(config, address) {
  return Object.values(config.tokens).find((token) => sameAddress(token.address, address))?.symbol || "Unknown token";
}

function transactionError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  const code = error?.code ?? error?.info?.error?.code;
  if (code === "ACTION_REJECTED" || code === 4001 || /user (?:denied|rejected)/i.test(message)) return new Error("Transaction cancelled. No funds were moved.");
  if (code === "INSUFFICIENT_FUNDS" || /insufficient funds|not enough funds/i.test(message)) return new Error("Not enough Base ETH to pay the network fee.");
  if (/transfer amount exceeds balance|exceeds.*balance/i.test(message)) return new Error("Your Base USDC balance is not enough for this protection.");
  return new Error("The hedge transaction could not be completed. Check your Base balances and try again.");
}

function eligibleOrders(sdk, orders, now) {
  const ethFeed = sdk.chainConfig.priceFeeds.ETH;
  return orders.filter((item) => {
    const raw = item.rawApiData;
    return raw && sameAddress(raw.priceFeed, ethFeed) && raw.isCall === false && raw.isLong === true
      && raw.strikes?.length === 1 && raw.orderExpiryTimestamp > now
      && Number(item.order.expiry) > now && item.availableAmount > 0n;
  });
}

function normalizeOrder(order, sdk, spotPrice, maxBudget) {
  const raw = order.rawApiData;
  return {
    orderKey: orderKey(order), strike: Number(raw.strikes[0]) / 1e8,
    expiry: new Date(Number(order.order.expiry) * 1000).toISOString(),
    pricePerContract: Number(order.order.price) / 1e8,
    availableAmount: Number(order.availableAmount) / 1e6, maxSpend: maxBudget,
    product: productName(sdk.chainConfig, raw.implementation),
    optionBook: raw.optionBookAddress || sdk.chainConfig.contracts.optionBook, spotPrice,
  };
}

function previewChoice(sdk, order, choice) {
  const preview = sdk.optionBook.previewFillOrder(order, BigInt(Math.round(choice.spend * 1e6)));
  return {
    ...choice, budget: Number(preview.totalCollateral) / 1e6,
    contracts: Number(preview.numContracts) / 1e6,
    pricePerContract: Number(preview.pricePerContract) / 1e8,
    collateral: tokenSymbol(sdk.chainConfig, preview.collateralToken),
    collateralAddress: preview.collateralToken, maker: preview.maker,
    settlement: choice.product.startsWith("PHYSICAL_") ? "Physical" : "Cash",
  };
}

export async function loadHedgeRecommendations({ maxBudget, preference = "balanced" }) {
  const sdk = await getClient();
  const [orders, market] = await Promise.all([sdk.api.fetchOrders(), sdk.api.getMarketData()]);
  const now = Math.floor(Date.now() / 1000);
  const spotPrice = Number(market.prices.ETH);
  const eligible = eligibleOrders(sdk, orders, now);
  if (!eligible.length) throw new Error("No active ETH put orders are available on Thetanuts right now.");
  const choices = buildProtectionChoices(
    eligible.map((order) => normalizeOrder(order, sdk, spotPrice, maxBudget)),
    { maxBudget, preference, spotPrice, now },
  );
  const byKey = new Map(eligible.map((order) => [orderKey(order), order]));
  return {
    network: "Base Mainnet", spotPrice, scannedOrders: orders.length,
    eligibleOrders: eligible.length, updatedAt: new Date().toISOString(),
    recommendations: choices.map((choice) => ({ ...previewChoice(sdk, byKey.get(choice.orderKey), choice), updatedAt: new Date().toISOString() })),
  };
}

export async function purchaseRecommendedHedge(recommendation, expectedAccount) {
  try {
    if (!recommendation) throw new Error("Update recommendations before purchasing.");
    if (!window.ethereum) throw new Error("A Base-compatible wallet is required.");
    const readSdk = await getClient();
    const freshOrders = eligibleOrders(readSdk, await readSdk.api.fetchOrders(), Math.floor(Date.now() / 1000));
    const freshOrder = freshOrders.find((order) => orderKey(order) === recommendation.orderKey);
    if (!freshOrder) throw new Error("MARKET_CHANGED");
    const latest = previewChoice(readSdk, freshOrder, recommendation);
    const priceChange = Math.abs(latest.pricePerContract - recommendation.pricePerContract) / Math.max(recommendation.pricePerContract, 0.000001);
    const quantityChange = Math.abs(latest.contracts - recommendation.contracts) / Math.max(recommendation.contracts, 0.000001);
    if (priceChange > 0.02 || quantityChange > 0.02) throw new Error("MARKET_CHANGED");

    const [{ ethers }, { ThetanutsClient }] = await Promise.all([import("ethers"), import("@thetanuts-finance/thetanuts-client")]);
    await window.ethereum.request({ method: "wallet_switchEthereumChain", params: [{ chainId: "0x2105" }] });
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    if ((await signer.getAddress()).toLowerCase() !== expectedAccount.toLowerCase()) throw new Error("ACCOUNT_MISMATCH");
    const sdk = new ThetanutsClient({ chainId: BASE_CHAIN_ID, provider, signer, apiBaseUrl: `${FORTIFI_API_URL}/api/thetanuts/orderbook` });
    const amount = BigInt(Math.round(latest.spend * 1e6));
    const optionBook = freshOrder.rawApiData.optionBookAddress || sdk.chainConfig.contracts.optionBook;
    const approval = await sdk.erc20.ensureAllowance(BASE_USDC, optionBook, amount);
    try {
      const receipt = await sdk.optionBook.fillOrder(freshOrder, amount);
      return { approvalHash: approval?.hash || null, transactionHash: receipt.hash, execution: latest };
    } catch (error) {
      if (approval?.hash) throw new Error("APPROVED_NOT_PURCHASED", { cause: error });
      throw error;
    }
  } catch (error) {
    if (error.message === "MARKET_CHANGED") throw new Error("Market conditions changed. Update recommendations and review the new terms.");
    if (error.message === "ACCOUNT_MISMATCH") throw new Error("Switch MetaMask back to the wallet signed in to FortiFi.");
    if (error.message === "APPROVED_NOT_PURCHASED") throw new Error("The hedge was not purchased. Your USDC spending permission may remain active.");
    if (["Update recommendations before purchasing.", "A Base-compatible wallet is required."].includes(error.message)) throw error;
    throw transactionError(error);
  }
}
