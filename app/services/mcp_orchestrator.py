import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.config import DATA_PROVIDER, EXECUTE_LIVE, MAX_GAS, MAX_SLIPPAGE_BPS, POLICY_MODE
from app.models import MCPDecision
from app.schemas import RiskProfile, TradeIntent
from app.services.advisor_agent import AdvisorAgent
from app.services.bitquery_client import BitqueryClient
from app.services.bscscan_client import BscScanClient
from app.services.data_agent import DataAgent
from app.services.execution_agent import ExecutionAgent
from app.services.execution_client import ExecutionClient
from app.services.llm_advisor import LLMAdvisor
from app.services.policy import validate_profile, validate_trade

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
ZERO_ADDRESS = "0x" + "0" * 40


class MCPOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.data_agent = DataAgent(db)
        self.advisor_agent = AdvisorAgent(db)
        self.llm_advisor = LLMAdvisor()
        self.exec_agent = ExecutionAgent()
        self.exec_client = ExecutionClient()

    def _log_decision(self, route: str, status: str, reason: str, payload: dict) -> None:
        entry = MCPDecision(route=route, status=status, reason=reason, payload=json.dumps(payload))
        self.db.add(entry)
        self.db.commit()

    def _check_policy(self, profile: RiskProfile | None, trade: TradeIntent | None) -> tuple[bool, str]:
        if trade:
            allowed, reason = validate_trade(trade.asset, trade.action, trade.size)
            if not allowed:
                return False, reason
        if profile:
            allowed, reason = validate_profile(profile)
            if not allowed:
                return False, reason
        return True, "ok"

    def _decode_call_data(self, call_data: str | None) -> tuple[bytes, str | None]:
        if not call_data:
            return b"", None
        data = call_data[2:] if call_data.startswith("0x") else call_data
        if len(data) % 2 != 0:
            return b"", "invalid-call-data"
        try:
            return bytes.fromhex(data), None
        except ValueError:
            return b"", "invalid-call-data"

    def _is_valid_address(self, address: str | None) -> bool:
        if not address:
            return False
        if address.lower() == ZERO_ADDRESS:
            return False
        return bool(ADDRESS_RE.match(address))

    def ingest_wallet(self, address: str) -> dict[str, Any]:
        if DATA_PROVIDER == "bitquery":
            client = BitqueryClient()
            events = client.fetch_wallet_activity(address)
        else:
            client = BscScanClient()
            events = client.fetch_wallet_activity(address)

        stored = []
        for event in events:
            if not event.get("tx_hash"):
                continue
            stored_event = self.data_agent.ingest(
                event["tx_hash"],
                event["payload"],
                "bnb",
                from_address=event.get("from_address"),
                to_address=event.get("to_address"),
                value=event.get("value"),
                block_number=event.get("block_number"),
                tags=event.get("tags"),
            )
            stored.append(stored_event.tx_hash)
        return {"stored": stored, "count": len(stored)}

    def advise(self, profile: RiskProfile, objective: str, user_id: str | None) -> dict[str, Any]:
        recommendation, rationale, signals, risk_score, allocation, confidence = self.advisor_agent.recommend(
            profile, objective, user_id=user_id
        )
        context = self.advisor_agent.last_personalization or {}
        llm_rec, llm_rationale = self.llm_advisor.recommend(
            profile,
            objective,
            signals,
            risk_score,
            allocation,
            user_context=context.get("summary"),
        )
        return {
            "recommendation": recommendation,
            "rationale": rationale,
            "signals": signals,
            "risk_score": risk_score,
            "allocation": allocation,
            "confidence": confidence,
            "llm_recommendation": llm_rec,
            "llm_rationale": llm_rationale,
            "personalization": context or None,
        }

    def execute(self, trade: TradeIntent) -> dict[str, Any]:
        if POLICY_MODE == "read_only":
            return {"status": "rejected", "reason": "read-only"}
        plan = self.exec_agent.build_plan(trade.strategy_id, trade.asset, trade.action, trade.size)
        if plan.estimated_gas > MAX_GAS or plan.slippage_bps > MAX_SLIPPAGE_BPS:
            return {"status": "rejected", "reason": "gas-or-slippage-limit"}

        call_data, error = self._decode_call_data(trade.call_data)
        if error:
            return {"status": "rejected", "reason": error}
        if trade.to_address:
            if not self._is_valid_address(trade.to_address):
                return {"status": "rejected", "reason": "invalid-to-address"}
        elif EXECUTE_LIVE:
            return {"status": "rejected", "reason": "missing-to-address"}
        if not call_data and trade.value_wei == 0 and EXECUTE_LIVE:
            return {"status": "rejected", "reason": "missing-call-data"}

        if POLICY_MODE == "paper_trade":
            result = None
            status = "paper-trade"
        else:
            result = self.exec_client.submit(
                to_address=trade.to_address or "",
                data=call_data,
                value_wei=trade.value_wei,
            )
            status = "submitted" if result.status == "submitted" else result.status
        return {
            "status": status,
            "plan": {
                "plan_id": plan.plan_id,
                "estimated_gas": plan.estimated_gas,
                "slippage_bps": plan.slippage_bps,
                "gas_strategy": plan.gas_strategy,
                "deadline_sec": plan.deadline_sec,
                "safety_checks": plan.safety_checks,
            },
            "tx_hash": "" if result is None else result.tx_hash,
        }

    def route(
        self,
        route: str,
        profile: RiskProfile | None,
        trade: TradeIntent | None,
        payload: dict,
        user_id: str | None,
    ) -> dict[str, Any]:
        allowed, reason = self._check_policy(profile, trade)
        if not allowed:
            self._log_decision(route, "rejected", reason, payload)
            return {"status": "rejected", "detail": reason}

        if route == "ingest":
            address = payload.get("address", "")
            try:
                data = self.ingest_wallet(address)
            except RuntimeError as exc:
                self._log_decision(route, "rejected", "ingest-provider-missing", payload)
                return {"status": "rejected", "detail": str(exc)}
            self._log_decision(route, "accepted", "ingested", payload)
            return {"status": "accepted", "detail": "ingested", "data": data}
        if route == "advise":
            if not profile:
                self._log_decision(route, "rejected", "missing-profile", payload)
                return {"status": "rejected", "detail": "missing-profile"}
            data = self.advise(profile, payload.get("objective", "balanced"), user_id)
            self._log_decision(route, "accepted", "advised", payload)
            return {"status": "accepted", "detail": "advised", "data": data}
        if route == "execute":
            if not trade:
                self._log_decision(route, "rejected", "missing-trade", payload)
                return {"status": "rejected", "detail": "missing-trade"}
            data = self.execute(trade)
            status = data.get("status", "unknown")
            self._log_decision(route, status, "executed", payload)
            return {"status": status, "detail": "executed", "data": data}

        self._log_decision(route, "rejected", "unknown-route", payload)
        return {"status": "rejected", "detail": "unknown-route"}
