# MCP Contract

## Route
`POST /mcp/route`

## Request schema
```json
{
  "route": "ingest | advise | execute",
  "user_id": "user-1",
  "intent": "portfolio | trade | research",
  "profile": {"risk_tolerance": 0.5, "horizon_days": 120, "max_drawdown": 0.2},
  "trade": {
    "asset": "BNB",
    "action": "swap",
    "size": 5.0,
    "strategy_id": "strat-001",
    "to_address": "0x...",
    "call_data": "0x...",
    "value_wei": 0
  },
  "payload": {"objective": "income", "address": "0x..."}
}
```

## Response schema
```json
{
  "status": "accepted | rejected | submitted | dry-run | paper-trade | missing-credentials | invalid-target",
  "decision": "accepted | rejected | submitted | dry-run | paper-trade",
  "detail": "string",
  "data": {}
}
```

## Agent roles + allowed actions
- On-Chain Data Agent: `/data/ingest`, `/data/search`, `/data/insights`
- Investor Advisor Agent: `/advisor/recommend` (optional `user_id`)
- Execution Agent: `/execute/plan`, `/mcp/route` with `route=execute`
- Allowed actions are gated by `ALLOWED_ACTIONS`, `ALLOWED_ASSETS`, `MAX_POSITION_SIZE`, `MAX_GAS`, `MAX_SLIPPAGE_BPS`.

## Memory boundaries
- Persistent (Postgres): on-chain events, user trades/holdings, MCP decisions.
- Persistent (pgvector): embedding vectors in `onchain_events.embedding`.
- Ephemeral: LLM responses, execution plans, search results, policy decisions returned to caller.

## Policy gate layer
- `POLICY_MODE=read_only`: rejects execution.
- `POLICY_MODE=paper_trade`: returns plans but never submits transactions.
- `POLICY_MODE=execute_enabled`: allows execution when `EXECUTE_LIVE=true` and RPC/keys are set.
- In production, default is `paper_trade` unless explicitly set to `execute_enabled`.
