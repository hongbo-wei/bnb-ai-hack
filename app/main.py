import time

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import INGEST_ENABLED, IVFFLAT_LISTS, IVFFLAT_PROBES, RESET_VECTOR_DIM_MISMATCH, VECTOR_DIM
from app.db import ENGINE, SessionLocal
from app.models import Base
from app.schemas import (
    AdvisorRequest,
    AdvisorResponse,
    ExecutionRequest,
    ExecutionResponse,
    IngestRequest,
    IngestResponse,
    MCPRouteRequest,
    MCPRouteResponse,
    SearchRequest,
    SearchResponse,
    SearchHit,
    InsightsResponse,
    ScorecardResponse,
    UserHoldingsRequest,
    UserHoldingsResponse,
    UserTradesRequest,
    UserTradesResponse,
)
from app.services.advisor_agent import AdvisorAgent
from app.services.data_agent import DataAgent
from app.services.execution_agent import ExecutionAgent
from app.services.ingest_scheduler import IngestScheduler
from app.services.mcp_orchestrator import MCPOrchestrator
from app.services.policy import validate_trade
from app.services.scorecard import Scorecard

app = FastAPI(title="BNB Chain AI Trading MVP")
ingest_scheduler: IngestScheduler | None = None


@app.on_event("startup")
def startup() -> None:
    with ENGINE.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        current_dim = None
        try:
            current_dim = conn.execute(
                text(
                    "SELECT atttypmod FROM pg_attribute "
                    "WHERE attrelid='onchain_events'::regclass AND attname='embedding'"
                )
            ).scalar_one_or_none()
        except Exception:
            current_dim = None
        if current_dim is not None and current_dim >= 0:
            current_dim = current_dim - 4
        if current_dim and current_dim != VECTOR_DIM and RESET_VECTOR_DIM_MISMATCH:
            conn.execute(text("DROP TABLE IF EXISTS onchain_events"))
    Base.metadata.create_all(bind=ENGINE)
    with ENGINE.begin() as conn:
        columns = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='onchain_events'"
            )
        ).fetchall()
        existing = {row[0] for row in columns}
        if "from_address" not in existing:
            conn.execute(text("ALTER TABLE onchain_events ADD COLUMN from_address VARCHAR(64)"))
        if "to_address" not in existing:
            conn.execute(text("ALTER TABLE onchain_events ADD COLUMN to_address VARCHAR(64)"))
        if "value" not in existing:
            conn.execute(text("ALTER TABLE onchain_events ADD COLUMN value DOUBLE PRECISION"))
        if "block_number" not in existing:
            conn.execute(text("ALTER TABLE onchain_events ADD COLUMN block_number INTEGER"))
        if "tags" not in existing:
            conn.execute(text("ALTER TABLE onchain_events ADD COLUMN tags TEXT"))
        index_lists = max(1, IVFFLAT_LISTS)
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS onchain_events_embedding_idx "
                f"ON onchain_events USING ivfflat (embedding vector_cosine_ops) WITH (lists={index_lists})"
            )
        )
        conn.execute(text("ANALYZE onchain_events"))
    if INGEST_ENABLED:
        global ingest_scheduler
        ingest_scheduler = IngestScheduler(SessionLocal)
        ingest_scheduler.start()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("shutdown")
def shutdown() -> None:
    if ingest_scheduler:
        ingest_scheduler.stop()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/data/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    agent = DataAgent(db)
    event = agent.ingest(
        request.tx_hash,
        request.payload,
        request.chain,
        from_address=request.from_address,
        to_address=request.to_address,
        value=request.value,
        block_number=request.block_number,
        tags=request.tags,
    )
    return IngestResponse(id=event.id, tx_hash=event.tx_hash)


@app.post("/data/search", response_model=SearchResponse)
def search(request: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:
    agent = DataAgent(db)
    total_start = time.perf_counter()
    embed_start = time.perf_counter()
    query_vec = agent.embed(request.query)
    embed_ms = (time.perf_counter() - embed_start) * 1000
    probes = request.probes if request.probes is not None else IVFFLAT_PROBES
    if probes is not None and probes <= 0:
        probes = None
    db_start = time.perf_counter()
    hits = agent.search_by_vector(query_vec, request.top_k, request.chain, probes=probes)
    db_ms = (time.perf_counter() - db_start) * 1000
    elapsed_ms = (time.perf_counter() - total_start) * 1000
    response_hits = [
        SearchHit(tx_hash=event.tx_hash, payload=event.payload, chain=event.chain, score=score)
        for event, score in hits
    ]
    return SearchResponse(
        hits=response_hits,
        timing_ms=round(elapsed_ms, 2),
        total_hits=len(response_hits),
        embed_ms=round(embed_ms, 2),
        db_ms=round(db_ms, 2),
        probes=probes,
    )


@app.get("/data/insights", response_model=InsightsResponse)
def insights(db: Session = Depends(get_db)) -> InsightsResponse:
    agent = DataAgent(db)
    data = agent.insights()
    return InsightsResponse(**data)


@app.post("/advisor/recommend", response_model=AdvisorResponse)
def recommend(request: AdvisorRequest, db: Session = Depends(get_db)) -> AdvisorResponse:
    agent = AdvisorAgent(db)
    recommendation, rationale, signals, risk_score, allocation, confidence = agent.recommend(
        request.profile, request.objective, user_id=request.user_id
    )
    return AdvisorResponse(
        recommendation=recommendation,
        rationale=rationale,
        signals=signals,
        risk_score=risk_score,
        allocation=allocation,
        confidence=confidence,
        personalization=agent.last_personalization,
    )


@app.post("/advisor/users/{user_id}/trades", response_model=UserTradesResponse)
def record_trades(user_id: str, request: UserTradesRequest, db: Session = Depends(get_db)) -> UserTradesResponse:
    agent = AdvisorAgent(db)
    inserted, skipped = agent.record_trades(user_id, request.trades)
    return UserTradesResponse(inserted=inserted, skipped=skipped)


@app.post("/advisor/users/{user_id}/holdings", response_model=UserHoldingsResponse)
def record_holdings(user_id: str, request: UserHoldingsRequest, db: Session = Depends(get_db)) -> UserHoldingsResponse:
    agent = AdvisorAgent(db)
    upserted = agent.record_holdings(user_id, request.holdings)
    return UserHoldingsResponse(upserted=upserted)


@app.post("/execute/plan", response_model=ExecutionResponse)
def plan(request: ExecutionRequest) -> ExecutionResponse:
    agent = ExecutionAgent()
    allowed, reason = validate_trade(request.asset, request.action, request.size)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)
    try:
        plan = agent.build_plan(request.strategy_id, request.asset, request.action, request.size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecutionResponse(
        plan={
            "plan_id": plan.plan_id,
            "estimated_gas": plan.estimated_gas,
            "slippage_bps": plan.slippage_bps,
            "gas_strategy": plan.gas_strategy,
            "deadline_sec": plan.deadline_sec,
            "safety_checks": plan.safety_checks,
            "status": plan.status,
        },
        dry_run=True,
    )


@app.post("/mcp/route", response_model=MCPRouteResponse)
def route(request: MCPRouteRequest, db: Session = Depends(get_db)) -> MCPRouteResponse:
    orchestrator = MCPOrchestrator(db)
    result = orchestrator.route(request.route, request.profile, request.trade, request.payload, request.user_id)
    return MCPRouteResponse(
        status=result.get("status", "unknown"),
        decision=result.get("status", "unknown"),
        detail=result.get("detail", ""),
        data=result.get("data", {}),
    )


@app.get("/scorecard", response_model=ScorecardResponse)
def scorecard(db: Session = Depends(get_db)) -> ScorecardResponse:
    evaluator = Scorecard(db)
    data = evaluator.data_agent()
    advisor = evaluator.advisor_agent()
    execution = evaluator.execution_agent()
    overall_score, overall_confidence = evaluator.overall()
    return ScorecardResponse(
        data_agent={"score": data.score, "confidence": data.confidence, "notes": data.notes},
        advisor_agent={"score": advisor.score, "confidence": advisor.confidence, "notes": advisor.notes},
        execution_agent={"score": execution.score, "confidence": execution.confidence, "notes": execution.notes},
        overall_score=overall_score,
        overall_confidence=overall_confidence,
    )
