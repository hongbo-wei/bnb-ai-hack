# BNB Chain AI Trading MVP Whitepaper

## Problem
On-chain markets move quickly, but most traders and protocols lack a safe, explainable, and policy-aware system that can turn raw on-chain data into actionable decisions. Existing tools are fragmented (data dashboards, signal bots, execution scripts) and do not provide end-to-end risk controls or auditable decision routing.

## Solution
BNB Chain AI Trading MVP provides an agentic system with three specialized agents and a policy-gated orchestrator:
- **Data Agent** collects and embeds on-chain events for semantic search and trend detection.
- **Advisor Agent** transforms signals into risk-aware recommendations with allocations and confidence.
- **Execution Agent** produces deterministic, gas-aware execution plans with safety checks.

The result is a transparent pipeline from signal ingestion to decision output, with optional on-chain execution.

## Design Architecture
- **FastAPI API** exposes ingestion, search, insights, advisory, execution, and scoring endpoints.
- **MCP Orchestrator** routes requests, enforces policy (gas, slippage, allowed assets/actions), and logs decisions.
- **Postgres + pgvector** store on-chain events and embeddings for similarity search.
- **BNB RPC** enables optional live execution through existing token/DEX contracts.

## Innovation
- End-to-end, policy-gated AI trading flow from data to execution.
- Deterministic execution planning with explicit safety gates (no opaque auto-trading).
- Embedding-driven on-chain signal search with measurable query timing.
- Audit-friendly MCP decision logging for traceability.

## Market Potential
- **Retail and pro traders** who want explainable, risk-aware AI trading guidance.
- **Wallets and frontends** that need safe trade intent generation and compliance controls.
- **Protocols and funds** seeking an audit-friendly automation layer for strategy execution.

## Competitive Advantage
- Tight integration with BNB Chain data sources.
- Clear separation of data, advisory, and execution responsibilities.
- Lightweight deployment with minimal infrastructure requirements.

## Roadmap Summary
See `docs/roadmap-6-month.md` for the six-month plan and milestone details.
