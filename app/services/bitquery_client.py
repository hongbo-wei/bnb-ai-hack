from typing import List

import httpx

from app.config import BITQUERY_API_KEY, BITQUERY_ENDPOINT


class BitqueryClient:
    def __init__(self) -> None:
        if not BITQUERY_API_KEY:
            raise RuntimeError("BITQUERY_API_KEY must be set to use Bitquery")

    def _normalize_value(self, value: float | None) -> float | None:
        if value is None:
            return None
        amount = float(value)
        if amount > 1e9:
            return amount / 1e18
        return amount

    def fetch_wallet_activity(self, address: str) -> List[dict]:
        query = """
        query ($address: String!) {
          ethereum(network: bsc) {
            transactions(txSender: {is: $address}, options: {limit: 20, desc: "block.height"}) {
              hash
              block {
                height
              }
              to {
                address
              }
              value
            }
          }
        }
        """
        payload = {"query": query, "variables": {"address": address}}
        headers = {"X-API-KEY": BITQUERY_API_KEY}
        response = httpx.post(BITQUERY_ENDPOINT, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json().get("data", {})
        txs = data.get("ethereum", {}).get("transactions", [])
        events = []
        for item in txs:
            value = self._normalize_value(item.get("value"))
            block_height = item.get("block", {}).get("height")
            events.append(
                {
                    "tx_hash": item.get("hash", ""),
                    "payload": f"from {address} to {item.get('to', {}).get('address')} value {value} block {block_height}",
                    "from_address": address,
                    "to_address": item.get("to", {}).get("address"),
                    "value": value,
                    "block_number": int(block_height) if block_height is not None else None,
                    "tags": ["transfer"],
                }
            )
        return events
