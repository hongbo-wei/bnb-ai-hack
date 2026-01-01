import hashlib
from dataclasses import dataclass


@dataclass
class ExecutionPlan:
    plan_id: str
    estimated_gas: int
    slippage_bps: int
    gas_strategy: str
    deadline_sec: int
    safety_checks: list[str]
    status: str


class ExecutionAgent:
    def build_plan(self, strategy_id: str, asset: str, action: str, size: float) -> ExecutionPlan:
        if size <= 0:
            raise ValueError("size must be positive")
        seed = f"{strategy_id}:{asset}:{action}:{size}".encode("utf-8")
        plan_id = hashlib.sha256(seed).hexdigest()[:12]
        action_lower = action.lower()
        if action_lower == "swap":
            base_gas = 120_000
        elif action_lower == "approve":
            base_gas = 55_000
        else:
            base_gas = 80_000
        estimated_gas = int(base_gas * (1 + min(size, 50) / 100))
        slippage_bps = 20 if size < 5 else 35 if size < 20 else 60
        gas_strategy = "economy" if size < 10 else "fast"
        deadline_sec = 120
        safety_checks = [
            "nonce-free",
            "allowance-verified",
            "slippage-within-bounds",
            "size-within-policy",
        ]
        return ExecutionPlan(
            plan_id=plan_id,
            estimated_gas=estimated_gas,
            slippage_bps=slippage_bps,
            gas_strategy=gas_strategy,
            deadline_sec=deadline_sec,
            safety_checks=safety_checks,
            status="ready",
        )
