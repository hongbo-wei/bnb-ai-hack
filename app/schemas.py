from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    tx_hash: str
    payload: str
    chain: str = "bnb"
    from_address: str | None = None
    to_address: str | None = None
    value: float | None = None
    block_number: int | None = None
    tags: List[str] | None = None


class IngestResponse(BaseModel):
    id: int
    tx_hash: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=25)
    chain: Optional[str] = None
    probes: int | None = Field(default=None, ge=1, le=200)


class SearchHit(BaseModel):
    tx_hash: str
    payload: str
    chain: str
    score: float


class SearchResponse(BaseModel):
    hits: List[SearchHit]
    timing_ms: float
    total_hits: int
    embed_ms: float | None = None
    db_ms: float | None = None
    probes: int | None = None


class InsightTag(BaseModel):
    tag: str
    count: int


class InsightTerm(BaseModel):
    term: str
    count: int


class InsightsResponse(BaseModel):
    total_events: int
    top_tags: List[InsightTag]
    top_terms: List[InsightTerm]
    total_value: float


class RiskProfile(BaseModel):
    risk_tolerance: float = Field(ge=0.0, le=1.0)
    horizon_days: int = Field(ge=1, le=3650)
    max_drawdown: float = Field(ge=0.0, le=1.0)


class AdvisorRequest(BaseModel):
    profile: RiskProfile
    objective: str = "balanced growth"
    user_id: str | None = None


class AdvisorResponse(BaseModel):
    recommendation: str
    rationale: str
    signals: List[str]
    risk_score: float
    allocation: dict
    confidence: float
    personalization: dict | None = None


class UserTradeIn(BaseModel):
    asset: str = Field(min_length=1)
    side: str = Field(min_length=1)
    size: float = Field(gt=0)
    price: float | None = Field(default=None, ge=0)
    executed_at: datetime | None = None
    external_id: str | None = None


class UserHoldingIn(BaseModel):
    asset: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    avg_cost: float | None = Field(default=None, ge=0)
    updated_at: datetime | None = None


class UserTradesRequest(BaseModel):
    trades: List[UserTradeIn]


class UserHoldingsRequest(BaseModel):
    holdings: List[UserHoldingIn]


class UserTradesResponse(BaseModel):
    inserted: int
    skipped: int


class UserHoldingsResponse(BaseModel):
    upserted: int


class ExecutionRequest(BaseModel):
    asset: str = Field(min_length=1)
    action: str = Field(min_length=1)
    size: float = Field(gt=0)
    strategy_id: str = Field(min_length=1)
    to_address: str | None = None
    call_data: str | None = None
    value_wei: int = Field(default=0, ge=0)


class ExecutionPlan(BaseModel):
    plan_id: str
    estimated_gas: int
    slippage_bps: int
    gas_strategy: str
    deadline_sec: int
    safety_checks: List[str]
    status: str


class ExecutionResponse(BaseModel):
    plan: ExecutionPlan
    dry_run: bool


class TradeIntent(BaseModel):
    asset: str = Field(min_length=1)
    action: str = Field(min_length=1)
    size: float = Field(gt=0)
    strategy_id: str = Field(min_length=1)
    to_address: str | None = None
    call_data: str | None = None
    value_wei: int = Field(default=0, ge=0)


class MCPRouteRequest(BaseModel):
    route: str
    user_id: str
    intent: str
    profile: RiskProfile | None = None
    trade: TradeIntent | None = None
    payload: dict = Field(default_factory=dict)


class MCPRouteResponse(BaseModel):
    status: str
    decision: str
    detail: str
    data: dict = Field(default_factory=dict)


class ScoreCategory(BaseModel):
    score: float
    confidence: float
    notes: List[str]


class ScorecardResponse(BaseModel):
    data_agent: ScoreCategory
    advisor_agent: ScoreCategory
    execution_agent: ScoreCategory
    overall_score: float
    overall_confidence: float
