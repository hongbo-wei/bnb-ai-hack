from typing import List

import httpx

from app.config import BSCSCAN_API_KEY, BSCSCAN_ENDPOINT


class BscScanClient:
    def __init__(self) -> None:
        if not BSCSCAN_API_KEY:
            raise RuntimeError("BSCSCAN_API_KEY must be set to use BscScan")

    def _normalize_value(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            amount = float(value)
        except ValueError:
            return None
        if amount > 1e9:
            return amount / 1e18
        return amount

    def fetch_wallet_activity(self, address: str, startblock: int = 0, endblock: int = 99999999) -> List[dict]:
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": startblock,
            "endblock": endblock,
            "sort": "desc",
            "apikey": BSCSCAN_API_KEY,
        }
        response = httpx.get(BSCSCAN_ENDPOINT, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "1":
            return []
        events = []
        for item in payload.get("result", []):
            value = self._normalize_value(item.get("value"))
            events.append(
                {
                    "tx_hash": item.get("hash", ""),
                    "payload": f"from {item.get('from')} to {item.get('to')} value {value} block {item.get('blockNumber')}",
                    "from_address": item.get("from"),
                    "to_address": item.get("to"),
                    "value": value,
                    "block_number": int(item.get("blockNumber")) if item.get("blockNumber") else None,
                    "tags": ["transfer"],
                }
            )
        return events
