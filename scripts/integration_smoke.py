#!/usr/bin/env python
import argparse
import json
import sys
import uuid

import httpx


def request(method: str, base_url: str, path: str, payload: dict | None = None) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    response = httpx.request(method, url, json=payload, timeout=20)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = json.dumps(response.json(), indent=2)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{method} {path} failed: {detail}") from exc
    if response.content:
        return response.json()
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run API integration smoke checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()

    base_url = args.base_url
    tx_hash = f"0x{uuid.uuid4().hex}"

    health = request("GET", base_url, "/health")
    if health.get("status") != "ok":
        raise RuntimeError(f"Health check failed: {health}")

    ingest = request(
        "POST",
        base_url,
        "/data/ingest",
        {"tx_hash": tx_hash, "payload": "nft mint volume rising on bnb", "chain": "bnb"},
    )
    if "tx_hash" not in ingest:
        raise RuntimeError(f"Ingest response missing tx_hash: {ingest}")

    insights = request("GET", base_url, "/data/insights")
    if "total_events" not in insights:
        raise RuntimeError(f"Insights response missing total_events: {insights}")

    search = request("POST", base_url, "/data/search", {"query": "nft volume trend", "top_k": 3})
    if "hits" not in search:
        raise RuntimeError(f"Search response missing hits: {search}")

    advisor = request(
        "POST",
        base_url,
        "/advisor/recommend",
        {
            "profile": {"risk_tolerance": 0.55, "horizon_days": 120, "max_drawdown": 0.25},
            "objective": "balanced growth",
        },
    )
    if "recommendation" not in advisor:
        raise RuntimeError(f"Advisor response missing recommendation: {advisor}")

    plan = request(
        "POST",
        base_url,
        "/execute/plan",
        {"asset": "BNB", "action": "swap", "size": 5.0, "strategy_id": "smoke-strat"},
    )
    if "plan" not in plan:
        raise RuntimeError(f"Plan response missing plan: {plan}")

    mcp_advise = request(
        "POST",
        base_url,
        "/mcp/route",
        {
            "route": "advise",
            "user_id": "smoke-user",
            "intent": "portfolio",
            "profile": {"risk_tolerance": 0.4, "horizon_days": 90, "max_drawdown": 0.2},
            "payload": {"objective": "income"},
        },
    )
    if mcp_advise.get("status") != "accepted":
        raise RuntimeError(f"MCP advise failed: {mcp_advise}")

    mcp_execute = request(
        "POST",
        base_url,
        "/mcp/route",
        {
            "route": "execute",
            "user_id": "smoke-user",
            "intent": "trade",
            "trade": {"asset": "BNB", "action": "swap", "size": 1.0, "strategy_id": "smoke-strat"},
            "payload": {},
        },
    )
    if "data" not in mcp_execute:
        raise RuntimeError(f"MCP execute failed: {mcp_execute}")

    scorecard = request("GET", base_url, "/scorecard")
    if "overall_score" not in scorecard:
        raise RuntimeError(f"Scorecard response missing overall_score: {scorecard}")

    print("Integration smoke checks passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Smoke check failed: {exc}", file=sys.stderr)
        sys.exit(1)
