from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    ALLOWED_ACTIONS,
    ALLOWED_ASSETS,
    DATA_PROVIDER,
    EMBED_PROVIDER,
    EXECUTE_LIVE,
    LLM_PROVIDER,
    MAX_GAS,
    MAX_POSITION_SIZE,
    MAX_SLIPPAGE_BPS,
    POLICY_MODE,
    RPC_URL,
)
from app.models import OnChainEvent, UserHolding, UserTrade


@dataclass
class ScoreCategory:
    score: float
    confidence: float
    notes: list[str]


class Scorecard:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _event_stats(self) -> dict:
        total = self.db.execute(select(func.count(OnChainEvent.id))).scalar_one()
        has_structured = (
            self.db.execute(
                select(func.count(OnChainEvent.id)).where(
                    OnChainEvent.from_address.isnot(None),
                    OnChainEvent.to_address.isnot(None),
                    OnChainEvent.block_number.isnot(None),
                )
            ).scalar_one()
            > 0
        )
        tagged = (
            self.db.execute(select(func.count(OnChainEvent.id)).where(OnChainEvent.tags.isnot(None))).scalar_one()
        )
        return {"total": total, "has_structured": has_structured, "tagged": tagged}

    def data_agent(self) -> ScoreCategory:
        stats = self._event_stats()
        score = 5.0
        notes: list[str] = []
        if stats["total"] > 0:
            score += 2
        else:
            notes.append("No on-chain events ingested yet.")
        if stats["tagged"] > 0:
            score += 1
        else:
            notes.append("Tag extraction needs real transactions for richer insights.")
        if EMBED_PROVIDER in {"openai", "ollama"}:
            score += 1
        if DATA_PROVIDER in {"bscscan", "bitquery"}:
            score += 1
        if stats["has_structured"]:
            score += 1
        score = min(10.0, score)
        confidence = min(1.0, stats["total"] / 60) if stats["total"] else 0.2
        return ScoreCategory(score=round(score, 2), confidence=round(confidence, 2), notes=notes)

    def advisor_agent(self) -> ScoreCategory:
        stats = self._event_stats()
        score = 5.0
        notes: list[str] = []
        if stats["total"] >= 20:
            score += 2
        else:
            notes.append("Advisor confidence improves with more historical events.")
        user_trades = self.db.execute(select(func.count(UserTrade.id))).scalar_one()
        user_holdings = self.db.execute(select(func.count(UserHolding.id))).scalar_one()
        if user_trades or user_holdings:
            score += 1
        else:
            notes.append("Add user trade history/holdings to enable personalization.")
        if LLM_PROVIDER != "none":
            score += 2
        else:
            notes.append("Enable LLM_PROVIDER for richer strategy rationale.")
        score += 1
        score = min(10.0, score)
        confidence = min(1.0, stats["total"] / 50) if stats["total"] else 0.3
        return ScoreCategory(score=round(score, 2), confidence=round(confidence, 2), notes=notes)

    def execution_agent(self) -> ScoreCategory:
        score = 5.0
        notes: list[str] = []
        if POLICY_MODE == "read_only":
            notes.append("Execution policy is read_only; live execution disabled.")
        elif POLICY_MODE == "paper_trade":
            notes.append("Execution policy is paper_trade; live execution disabled.")
        if RPC_URL:
            score += 2
        else:
            notes.append("Set RPC_URL to validate execution path against BNB Chain.")
        if EXECUTE_LIVE:
            score += 1
        else:
            notes.append("Execution currently runs in dry-run mode.")
        if MAX_GAS and MAX_SLIPPAGE_BPS:
            score += 1
        if MAX_POSITION_SIZE:
            score += 1
        if ALLOWED_ASSETS and ALLOWED_ACTIONS:
            score += 1
        score = min(10.0, score)
        confidence = 0.6 if RPC_URL else 0.4
        return ScoreCategory(score=round(score, 2), confidence=round(confidence, 2), notes=notes)

    def overall(self) -> tuple[float, float]:
        data_score = self.data_agent()
        advisor_score = self.advisor_agent()
        exec_score = self.execution_agent()
        overall_score = round((data_score.score + advisor_score.score + exec_score.score) / 3, 2)
        overall_confidence = round((data_score.confidence + advisor_score.confidence + exec_score.confidence) / 3, 2)
        return overall_score, overall_confidence
