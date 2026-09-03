from decimal import Decimal
from typing import Any

import httpx


class BaseRpcError(Exception):
    """Raised when the Base JSON-RPC endpoint fails or returns an error."""


class BaseClient:
    """
    Minimal read-only JSON-RPC client for the Base chain.

    Only ever calls "read" RPC methods (eth_getBalance, eth_call).
    Never touches a private key, never sends a signed transaction -
    this client can only look at public on-chain state.
    """

    def __init__(
        self,
        rpc_url: str,
        timeout: float = 10.0,
    ) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout

    async def get_eth_balance(
        self,
        address: str,
    ) -> Decimal:
        """
        Native ETH balance for an address, in whole ETH.
        """

        result = await self._call(
            "eth_getBalance",
            [address, "latest"],
        )

        return self._hex_to_decimal(
            result,
            decimals=18,
        )

    async def get_erc20_balance(
        self,
        token_address: str,
        holder_address: str,
        decimals: int,
    ) -> Decimal:
        """
        ERC-20 balanceOf(holder_address) for token_address,
        in whole tokens (already divided by 10**decimals).
        """

        call_data = self._encode_balance_of(holder_address)

        result = await self._call(
            "eth_call",
            [
                {
                    "to": token_address,
                    "data": call_data,
                },
                "latest",
            ],
        )

        return self._hex_to_decimal(
            result,
            decimals=decimals,
        )

    async def _call(
        self,
        method: str,
        params: list[Any],
    ) -> str:

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.rpc_url,
                    json=payload,
                )
                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise BaseRpcError(
                f"Base RPC request failed ({method}): {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise BaseRpcError(
                f"Base RPC returned a non-JSON response ({method})."
            ) from exc

        if "error" in data:
            raise BaseRpcError(
                f"Base RPC error ({method}): {data['error']}"
            )

        result = data.get("result")

        if result is None:
            raise BaseRpcError(
                f"Base RPC returned no result for {method}."
            )

        return result

    @staticmethod
    def _encode_balance_of(holder_address: str) -> str:
        """
        ABI-encode balanceOf(address) without pulling in a full
        ABI library: 4-byte selector + the address left-padded
        to 32 bytes.
        """

        selector = "70a08231"
        padded_address = holder_address[2:].lower().rjust(64, "0")

        return f"0x{selector}{padded_address}"

    @staticmethod
    def _hex_to_decimal(
        hex_value: str,
        decimals: int,
    ) -> Decimal:

        if not hex_value or hex_value == "0x":
            return Decimal(0)

        raw = int(hex_value, 16)

        return Decimal(raw) / Decimal(10 ** decimals)
