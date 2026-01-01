from collections import Counter
from datetime import datetime, timedelta
from typing import List

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OnChainEvent, UserHolding, UserTrade
from app.schemas import RiskProfile, UserHoldingIn, UserTradeIn


class AdvisorAgent:
    def __init__(self, db: Session):
        self.db = db
        self.last_personalization: dict | None = None

    def _extract_signals(self, events: List[OnChainEvent]) -> List[str]:
        tokens: List[str] = []
        stopwords = {
            "the",
            "and",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "from",
            "value",
            "block",
            "tx",
            "hash",
            "bnb",
        }
        for event in events:
            words = re.findall(r"[a-z0-9]+", event.payload.lower())
            tokens.extend([word for word in words if len(word) > 2 and word not in stopwords])
        common = Counter(tokens).most_common(6)
        return [f"{word}:{count}" for word, count in common]

    def _risk_score(self, profile: RiskProfile, data_confidence: float) -> float:
        score = 0.5 * profile.risk_tolerance + 0.3 * (1 - profile.max_drawdown) + 0.2 * min(1.0, 365 / profile.horizon_days)
        return round(min(1.0, max(0.0, score * (0.8 + 0.2 * data_confidence))), 2)

    def _allocation(self, risk_score: float) -> dict[str, int]:
        if risk_score < 0.35:
            return {"blue_chip": 60, "yield": 25, "growth": 10, "speculative": 5}
        if risk_score < 0.7:
            return {"blue_chip": 45, "yield": 20, "growth": 25, "speculative": 10}
        return {"blue_chip": 25, "yield": 15, "growth": 35, "speculative": 25}

    def record_trades(self, user_id: str, trades: List[UserTradeIn]) -> tuple[int, int]:
        inserted = 0
        skipped = 0
        normalized_user = user_id.strip()
        for trade in trades:
            external_id = trade.external_id.strip() if trade.external_id else None
            if external_id:
                existing = self.db.execute(
                    select(UserTrade).where(
                        UserTrade.user_id == normalized_user,
                        UserTrade.external_id == external_id,
                    )
                ).scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue
            side = trade.side.strip().lower()
            if side not in {"buy", "sell"}:
                side = "other"
            row = UserTrade(
                user_id=normalized_user,
                asset=trade.asset.strip().upper(),
                side=side,
                size=trade.size,
                price=trade.price,
                external_id=external_id,
                executed_at=trade.executed_at or datetime.utcnow(),
            )
            self.db.add(row)
            inserted += 1
        self.db.commit()
        return inserted, skipped

    def record_holdings(self, user_id: str, holdings: List[UserHoldingIn]) -> int:
        upserted = 0
        normalized_user = user_id.strip()
        for holding in holdings:
            asset = holding.asset.strip().upper()
            existing = self.db.execute(
                select(UserHolding).where(UserHolding.user_id == normalized_user, UserHolding.asset == asset)
            ).scalar_one_or_none()
            if existing:
                existing.quantity = holding.quantity
                existing.avg_cost = holding.avg_cost
                existing.updated_at = holding.updated_at or datetime.utcnow()
            else:
                row = UserHolding(
                    user_id=normalized_user,
                    asset=asset,
                    quantity=holding.quantity,
                    avg_cost=holding.avg_cost,
                    updated_at=holding.updated_at or datetime.utcnow(),
                )
                self.db.add(row)
            upserted += 1
        self.db.commit()
        return upserted

    def _user_context(self, user_id: str | None) -> tuple[dict | None, float, List[str], str | None]:
        if not user_id:
            return None, 0.0, [], None
        normalized_user = user_id.strip()
        since = datetime.utcnow() - timedelta(days=30)
        trades = (
            self.db.execute(
                select(UserTrade).where(UserTrade.user_id == normalized_user, UserTrade.executed_at >= since)
            )
            .scalars()
            .all()
        )
        holdings = (
            self.db.execute(select(UserHolding).where(UserHolding.user_id == normalized_user))
            .scalars()
            .all()
        )
        trade_count = len(trades)
        if not trade_count and not holdings:
            return None, 0.0, [], None
        buy_count = sum(1 for trade in trades if trade.side.lower() == "buy")
        sell_count = sum(1 for trade in trades if trade.side.lower() == "sell")
        buy_ratio = round(buy_count / trade_count, 2) if trade_count else None
        trade_assets = [trade.asset for trade in trades]
        top_traded_asset = Counter(trade_assets).most_common(1)[0][0] if trade_assets else None

        holding_assets = {holding.asset: abs(holding.quantity) for holding in holdings}
        total_qty = sum(holding_assets.values())
        top_holding_asset = max(holding_assets, key=holding_assets.get) if holding_assets else None
        top_holding_share = round(holding_assets.get(top_holding_asset, 0) / total_qty, 2) if total_qty else None

        notes: List[str] = []
        adjustment = 0.0
        if trade_count >= 10:
            notes.append("active-trading-style")
            adjustment += 0.03
        elif trade_count <= 2:
            notes.append("light-trading-activity")
            adjustment -= 0.02
        if top_holding_share is not None and top_holding_share >= 0.6:
            notes.append("portfolio-concentration")
            adjustment -= 0.05
        if trade_count and sell_count / trade_count >= 0.6:
            notes.append("recent-de-risking")
            adjustment -= 0.03

        context = {
            "user_id": normalized_user,
            "trade_count_30d": trade_count,
            "buy_ratio": buy_ratio,
            "top_traded_asset": top_traded_asset,
            "holdings_count": len(holdings),
            "top_holding_asset": top_holding_asset,
            "top_holding_share": top_holding_share,
            "notes": notes,
        }
        if trade_count >= 10:
            activity = "active"
        elif trade_count >= 3:
            activity = "moderate"
        else:
            activity = "light"
        context["activity"] = activity

        summary_parts = []
        if trade_count:
            summary_parts.append(f"30d trades={trade_count}")
        if buy_ratio is not None:
            summary_parts.append(f"buy ratio={buy_ratio:.2f}")
        if top_traded_asset:
            summary_parts.append(f"top traded={top_traded_asset}")
        if top_holding_asset and top_holding_share is not None:
            summary_parts.append(f"top holding={top_holding_asset} {top_holding_share:.0%}")
        summary = ", ".join(summary_parts) if summary_parts else None
        if summary:
            context["summary"] = summary
        return context, adjustment, notes, summary

    def recommend(self, profile: RiskProfile, objective: str, *, user_id: str | None = None) -> tuple[str, str, List[str], float, dict, float]:
        events = (
            self.db.execute(select(OnChainEvent).order_by(OnChainEvent.created_at.desc()).limit(80))
            .scalars()
            .all()
        )
        signals = self._extract_signals(events) if events else ["low-data"]
        data_confidence = min(1.0, len(events) / 50) if events else 0.2

        if profile.risk_tolerance < 0.35:
            recommendation = "Focus on high-liquidity blue-chip assets and short-term yield strategies."
        elif profile.risk_tolerance < 0.7:
            recommendation = "Balance spot positions with selective momentum trades on trending assets."
        else:
            recommendation = "Pursue higher beta opportunities with tight risk limits and rapid rebalancing."

        risk_score = self._risk_score(profile, data_confidence)
        context, adjustment, notes, summary = self._user_context(user_id)
        if context:
            risk_score = round(min(1.0, max(0.0, risk_score + adjustment)), 2)
        allocation = self._allocation(risk_score)
        rationale = (
            f"Objective '{objective}' with horizon {profile.horizon_days}d and max drawdown {profile.max_drawdown:.2f}. "
            f"Signals: {', '.join(signals[:4])}."
        )
        if summary:
            rationale = f"{rationale} User context: {summary}."
        if notes:
            signals = signals + [f"user:{note}" for note in notes]
        self.last_personalization = context
        return recommendation, rationale, signals, risk_score, allocation, round(data_confidence, 2)
