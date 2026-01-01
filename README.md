# BNB Chain AI Trading MVP

BNB Hack main track submission for the AI track (DeFi category). This project builds three AI agents and an orchestrator that turn on-chain data into actionable, policy-safe trade intent.

## Submission snapshot
- **Main track**: AI
- **Category**: DeFi
- **Technical solution**: BSC (configurable RPC for testnet or mainnet)
- **Environment config**: `.env.development` (no secrets)
- **Smart contracts**: `chain/contracts/DecisionLog.sol` deployed on BSC mainnet at `0x74B9CFd32552630B0bfEF0976Fc1d8198f830242`
- **Status**: Live on BSC mainnet (2026-01-01)

## Project details
AI-driven trading intelligence that combines on-chain signal retrieval, personalized risk profiling, and policy-gated execution planning. The system provides explainable recommendations, a deterministic execution plan, and a safety-first orchestration layer suitable for compliance-friendly automation.

## User journey diagram
```text
User
  |
CLI / REST
  |
FastAPI API
  |
MCP Orchestrator (policy + routing)
  |        |          |
Data Agent Advisor Agent Execution Agent
  |        |          |
Postgres + pgvector   BNB RPC (optional live exec)
```

## Architecture
- **API layer**: FastAPI endpoints for ingest, search, advice, execution planning, and scoring.
- **Orchestrator**: MCP-style router that enforces policy gates and logs decisions.
- **Data Agent**: On-chain ingestion (BscScan/Bitquery) + embeddings in pgvector.
- **Advisor Agent**: Risk-aware recommendations with allocations and confidence scoring.
- **Execution Agent**: Gas-aware, policy-gated execution plans with dry-run support.
- **Storage**: Postgres + pgvector for events, user trades/holdings, and decisions.

## Open-source dependencies
- fastapi, uvicorn
- sqlalchemy, psycopg, pgvector
- pydantic, numpy, httpx
- web3
- hardhat, ethers

## Deployment instructions
1. Copy and review `.env.development` (no secrets).
2. Start Postgres with pgvector: `docker compose up -d`
3. Install dependencies and run the API:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
4. (Optional) Enable live execution on BSC by setting `RPC_URL`, `PRIVATE_KEY`, `EXECUTE_LIVE=true`, and `POLICY_MODE=execute_enabled`.

## On-chain deployment (BSC testnet or mainnet)
1. Install node deps (once): `npm install`
2. Create `.env.hardhat` from `.env.hardhat.example` and set `DEPLOYER_PRIVATE_KEY` plus `BSC_TESTNET_RPC_URL` or `BSC_MAINNET_RPC_URL`.
3. Compile: `npx hardhat compile`
4. Deploy (testnet): `npx hardhat run chain/scripts/deploy.js --network bscTestnet`
5. Deploy (mainnet): `npx hardhat run chain/scripts/deploy.js --network bscMainnet`
6. Log two transactions (required by submission):  
   `CONTRACT_ADDRESS=<DEPLOYED_CONTRACT> npx hardhat run chain/scripts/log-twice.js --network <bscTestnet|bscMainnet>`
7. (Optional) Verify contract on BscScan:  
   `BSCSCAN_API_KEY=<API_KEY> npx hardhat verify --network <bscTestnet|bscMainnet> <DEPLOYED_CONTRACT>`

## BNB Hack alignment

**Agents we built**
- **On-Chain Data Agent**: Stores, queries, and analyzes BNB Chain data in a vector database (pgvector) to surface trends and similar events.
- **Investor Advisor Agent**: Combines user risk profile + recent signals to generate personalized recommendations with risk scoring and allocations.
- **Execution Agent**: Produces gas‑aware, policy‑gated execution plans (dry‑run by default) with explicit safety checks.

**Objectives → Implementation**
- **Data handling**: Vector embeddings + similarity search (`/data/ingest`, `/data/search`) with pgvector; structured metadata extraction and insights (`/data/insights`).
- **Strategy generation**: Risk‑aware recommendations with risk score, allocation mix, and confidence (`/advisor/recommend`) + optional LLM via Ollama.
- **Execution automation**: Deterministic execution planning + gas strategy + policy checks (`/execute/plan`, MCP gate).

**Judging criteria mapping**
- **Query efficiency**: pgvector similarity search + `timing_ms` reported in `/data/search`.
- **AI‑driven insights**: token/tag trend extraction + optional LLM rationale.
- **BNB compatibility**: BscScan/BitQuery ingestion, BNB‑chain payloads, and optional RPC execution.
- **Strategy accuracy / risk precision**: profile‑driven scoring, allocations, and confidence.
- **UX**: single CLI demo, insights route, and scorecard endpoint.
- **Execution success / gas / security**: gas strategy, slippage limits, allowed asset/action gates, and safety checks.

## What this includes
- On-chain data agent backed by a vector database (pgvector + Postgres)
- Investor advisor agent that generates risk-aware recommendations with confidence and allocations
- Execution agent that produces gas-aware dry-run plans with safety checks
- MCP-style orchestrator that routes requests, enforces policy, and logs decisions
- Scorecard endpoint that evaluates judging-criteria readiness

## Quick start

1. Start Postgres with pgvector:

```bash
docker compose up -d
```

2. Create a `.env` file (recommended for judges):

```bash
cp .env.development .env
```

3. Install dependencies and run the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API runs at `http://127.0.0.1:8000`.

## CLI

Run commands through the lightweight CLI:

```bash
source .venv/bin/activate
python cli.py demo
python cli.py health
python cli.py ingest --tx-hash 0xabc --payload "nft mint volume rising" --chain bnb
python cli.py insights
python cli.py search --query "nft volume trend" --top-k 3
python cli.py advise --risk 0.6 --horizon 180 --max-drawdown 0.2 --objective growth
python cli.py user-trades --user-id user-1 --trades-json '[{"asset":"BNB","side":"buy","size":2.5,"price":580.0}]'
python cli.py user-holdings --user-id user-1 --holdings-json '[{"asset":"BNB","quantity":12.0,"avg_cost":540.0}]'
python cli.py execute --asset BNB --action swap --size 5 --strategy-id strat-001
python cli.py scorecard
python cli.py mcp-route --route advise --user-id user-1 --intent portfolio \
  --profile-json '{"risk_tolerance":0.4,"horizon_days":120,"max_drawdown":0.2}' \
  --payload-json '{"objective":"income"}'
```

## Demo flow

Run the full demo (ingest → insights → search → advise → execute → scorecard + MCP routing):

```bash
./scripts/demo.sh
```

## Sample requests

Ingest data:

```bash
curl -X POST http://127.0.0.1:8000/data/ingest \
  -H 'Content-Type: application/json' \
  -d '{"tx_hash":"0xabc","payload":"nft mint volume rising","chain":"bnb"}'
```

Search data:

```bash
curl -X POST http://127.0.0.1:8000/data/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"nft volume trend","top_k":3,"probes":10}'
```

Insights:

```bash
curl http://127.0.0.1:8000/data/insights
```

Advisor recommendation:

```bash
curl -X POST http://127.0.0.1:8000/advisor/recommend \
  -H 'Content-Type: application/json' \
  -d '{"profile":{"risk_tolerance":0.6,"horizon_days":180,"max_drawdown":0.2},"objective":"growth","user_id":"user-1"}'
```

Execution plan:

```bash
curl -X POST http://127.0.0.1:8000/execute/plan \
  -H 'Content-Type: application/json' \
  -d '{"asset":"BNB","action":"swap","size":5.0,"strategy_id":"strat-001"}'
```

Live execution (MCP route + calldata; requires `EXECUTE_LIVE=true`, `RPC_URL`, `PRIVATE_KEY`):

```bash
python scripts/encode_erc20_transfer.py \
  --to 0x1111111111111111111111111111111111111111 \
  --amount 1000000
```

Use the printed hex as `call_data` and send to the token contract:

```bash
curl -X POST http://127.0.0.1:8000/mcp/route \
  -H 'Content-Type: application/json' \
  -d '{"route":"execute","user_id":"user-1","intent":"trade","trade":{"asset":"USDT","action":"transfer","size":1.0,"strategy_id":"strat-001","to_address":"0x2222222222222222222222222222222222222222","call_data":"0xa9059cbb...","value_wei":0},"payload":{}}'
```

MCP route (orchestrator/policy gate):

```bash
curl -X POST http://127.0.0.1:8000/mcp/route \
  -H 'Content-Type: application/json' \
  -d '{"route":"advise","user_id":"user-1","intent":"portfolio","profile":{"risk_tolerance":0.4,"horizon_days":120,"max_drawdown":0.2},"payload":{"objective":"income"}}'
```

## Personalization (user history/holdings)

Record user trades:

```bash
curl -X POST http://127.0.0.1:8000/advisor/users/user-1/trades \
  -H 'Content-Type: application/json' \
  -d '{"trades":[{"asset":"BNB","side":"buy","size":2.5,"price":580.0,"external_id":"t-001"}]}'
```

Record user holdings:

```bash
curl -X POST http://127.0.0.1:8000/advisor/users/user-1/holdings \
  -H 'Content-Type: application/json' \
  -d '{"holdings":[{"asset":"BNB","quantity":12.0,"avg_cost":540.0}]}'
```

## MCP wiring
- Orchestrator route: `POST /mcp/route`
- Logs decisions in the `mcp_decisions` table
- Policy gates: `MAX_GAS`, `MAX_POSITION_SIZE`, `MAX_SLIPPAGE_BPS`, `ALLOWED_ASSETS`, `ALLOWED_ACTIONS`
- Ingestion provider: `DATA_PROVIDER` (`bscscan` or `bitquery`)

## MCP contract
Request (`POST /mcp/route`):

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

Response:

```json
{
  "status": "accepted | rejected | submitted | dry-run | paper-trade | missing-credentials | invalid-target",
  "decision": "accepted | rejected | submitted | dry-run | paper-trade",
  "detail": "string",
  "data": {}
}
```

## Agent roles + allowed actions
- **On-Chain Data Agent**: `/data/ingest`, `/data/search`, `/data/insights`
- **Investor Advisor Agent**: `/advisor/recommend` (optional `user_id` for personalization)
- **Execution Agent**: `/execute/plan`, `/mcp/route` with `route=execute`
- **Allowed actions**: `ALLOWED_ACTIONS`, `ALLOWED_ASSETS`, `MAX_POSITION_SIZE`, `MAX_GAS`, `MAX_SLIPPAGE_BPS`

## Agent memory boundaries
- **Postgres (persistent)**: on-chain events, user trades/holdings, MCP decisions.
- **pgvector (persistent)**: embedding vectors stored in `onchain_events.embedding`.
- **Ephemeral**: LLM responses, execution plans, search results, policy decisions returned to caller.

## Policy gate layer
- **`POLICY_MODE=read_only`**: rejects execution (`/mcp/route` with `route=execute`).
- **`POLICY_MODE=paper_trade`**: returns plans but never submits transactions.
- **`POLICY_MODE=execute_enabled`**: allows execution when `EXECUTE_LIVE=true` and RPC/keys are set.
- **Environment-driven**: in production, default is `paper_trade` unless explicitly set to `execute_enabled`.

## Scorecard
Returns a judging-criteria readiness snapshot:

```bash
curl http://127.0.0.1:8000/scorecard
```

## Integration smoke test
Run this after the API server is up:

```bash
python scripts/integration_smoke.py --base-url http://127.0.0.1:8000
```

## Notes
- Vector embeddings support Ollama (`EMBED_PROVIDER=ollama`) or local hashing (`EMBED_PROVIDER=local`).
- For Ollama, set `EMBED_MODEL` to an installed model and `VECTOR_DIM` to its embedding size.
- pgvector powers similarity search; the service creates the extension on startup.
- Tune vector search with `IVFFLAT_LISTS` (index build) and `IVFFLAT_PROBES` (query probes), or override probes per request.
- Set `LLM_PROVIDER=ollama` and `LLM_MODEL` to enable LLM-based advisor responses.
- To enable scheduled ingestion, set `INGEST_ENABLED=true`, `INGEST_WALLET`, and an API key for `DATA_PROVIDER`.
- If you change `VECTOR_DIM`, set `RESET_VECTOR_DIM_MISMATCH=true` once to recreate the embeddings table.
- Live execution requires a non-zero `trade.to_address` and `trade.call_data` (hex); `trade.value_wei` can be used for native transfers.

Ollama setup (recommended defaults):

```bash
ollama pull nomic-embed-text
ollama pull gpt-oss:20b-cloud
```
