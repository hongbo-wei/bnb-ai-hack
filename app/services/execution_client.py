from dataclasses import dataclass

from web3 import Web3

from app.config import EXECUTE_LIVE, PRIVATE_KEY, RPC_URL

ZERO_ADDRESS = "0x" + "0" * 40


@dataclass
class ExecutionResult:
    tx_hash: str
    status: str


class ExecutionClient:
    def __init__(self) -> None:
        self.web3 = Web3(Web3.HTTPProvider(RPC_URL)) if RPC_URL else None

    def _normalize_address(self, to_address: str) -> str | None:
        if not to_address:
            return None
        if to_address.lower() == ZERO_ADDRESS:
            return None
        if not Web3.is_address(to_address):
            return None
        return Web3.to_checksum_address(to_address)

    def submit(self, to_address: str, data: bytes, value_wei: int = 0) -> ExecutionResult:
        if not EXECUTE_LIVE:
            return ExecutionResult(tx_hash="", status="dry-run")
        if not self.web3 or not PRIVATE_KEY:
            return ExecutionResult(tx_hash="", status="missing-credentials")
        normalized = self._normalize_address(to_address)
        if not normalized:
            return ExecutionResult(tx_hash="", status="invalid-target")
        if not data and value_wei == 0:
            return ExecutionResult(tx_hash="", status="missing-call-data")

        account = self.web3.eth.account.from_key(PRIVATE_KEY)
        nonce = self.web3.eth.get_transaction_count(account.address)
        txn = {
            "to": normalized,
            "value": value_wei,
            "data": data,
            "nonce": nonce,
            "gas": 200000,
            "gasPrice": self.web3.eth.gas_price,
            "chainId": self.web3.eth.chain_id,
        }
        signed = account.sign_transaction(txn)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return ExecutionResult(tx_hash=tx_hash.hex(), status="submitted")
