import argparse
import json
import sys

import httpx


def _request(method: str, base_url: str, path: str, payload: dict | None = None) -> None:
    url = f"{base_url.rstrip('/')}{path}"
    response = httpx.request(method, url, json=payload, timeout=20)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="BNB Chain AI Trading MVP CLI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check API health")
    subparsers.add_parser("demo", help="Run ingest -> search -> advise -> execute demo flow")
    subparsers.add_parser("insights", help="Show recent data insights")
    subparsers.add_parser("scorecard", help="Show judging criteria scorecard")

    ingest = subparsers.add_parser("ingest", help="Ingest on-chain data")
    ingest.add_argument("--tx-hash", required=True)
    ingest.add_argument("--payload", required=True)
    ingest.add_argument("--chain", default="bnb")

    search = subparsers.add_parser("search", help="Search embedded data")
    search.add_argument("--query", required=True)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--chain")
    search.add_argument("--probes", type=int)

    advise = subparsers.add_parser("advise", help="Get advisor recommendation")
    advise.add_argument("--risk", type=float, required=True)
    advise.add_argument("--horizon", type=int, required=True)
    advise.add_argument("--max-drawdown", type=float, required=True)
    advise.add_argument("--objective", default="balanced growth")
    advise.add_argument("--user-id")

    user_trades = subparsers.add_parser("user-trades", help="Record user trade history")
    user_trades.add_argument("--user-id", required=True)
    user_trades.add_argument("--trades-json", required=True, help="JSON array of trades")

    user_holdings = subparsers.add_parser("user-holdings", help="Record user holdings")
    user_holdings.add_argument("--user-id", required=True)
    user_holdings.add_argument("--holdings-json", required=True, help="JSON array of holdings")

    execute = subparsers.add_parser("execute", help="Create execution plan")
    execute.add_argument("--asset", required=True)
    execute.add_argument("--action", required=True)
    execute.add_argument("--size", type=float, required=True)
    execute.add_argument("--strategy-id", required=True)
    execute.add_argument("--to-address")
    execute.add_argument("--call-data")
    execute.add_argument("--value-wei", type=int)

    mcp = subparsers.add_parser("mcp-route", help="Route via MCP orchestrator")
    mcp.add_argument("--route", required=True, choices=["ingest", "advise", "execute"])
    mcp.add_argument("--user-id", required=True)
    mcp.add_argument("--intent", default="portfolio")
    mcp.add_argument("--profile-json", help="JSON string for risk profile")
    mcp.add_argument("--trade-json", help="JSON string for trade intent")
    mcp.add_argument("--payload-json", default="{}", help="JSON string for extra payload")

    args = parser.parse_args()
    base_url = args.base_url

    try:
        if args.command == "health":
            _request("GET", base_url, "/health")
            return
        if args.command == "demo":
            print("Step 1: ingest sample data")
            _request(
                "POST",
                base_url,
                "/data/ingest",
                {"tx_hash": "0xdemo001", "payload": "nft mint volume rising on bnb", "chain": "bnb"},
            )
            print("Step 2: data insights")
            _request("GET", base_url, "/data/insights")
            print("Step 3: search similar events")
            _request(
                "POST",
                base_url,
                "/data/search",
                {"query": "nft volume trend", "top_k": 3},
            )
            print("Step 4: advisor recommendation")
            _request(
                "POST",
                base_url,
                "/advisor/recommend",
                {
                    "profile": {"risk_tolerance": 0.55, "horizon_days": 120, "max_drawdown": 0.25},
                    "objective": "balanced growth",
                },
            )
            print("Step 5: execution plan (dry run)")
            _request(
                "POST",
                base_url,
                "/execute/plan",
                {"asset": "BNB", "action": "swap", "size": 5.0, "strategy_id": "demo-strat"},
            )
            print("Step 6: scorecard")
            _request("GET", base_url, "/scorecard")
            return
        if args.command == "insights":
            _request("GET", base_url, "/data/insights")
            return
        if args.command == "scorecard":
            _request("GET", base_url, "/scorecard")
            return
        if args.command == "ingest":
            _request(
                "POST",
                base_url,
                "/data/ingest",
                {"tx_hash": args.tx_hash, "payload": args.payload, "chain": args.chain},
            )
            return
        if args.command == "search":
            payload = {"query": args.query, "top_k": args.top_k}
            if args.chain:
                payload["chain"] = args.chain
            if args.probes is not None:
                payload["probes"] = args.probes
            _request("POST", base_url, "/data/search", payload)
            return
        if args.command == "advise":
            payload = {
                "profile": {
                    "risk_tolerance": args.risk,
                    "horizon_days": args.horizon,
                    "max_drawdown": args.max_drawdown,
                },
                "objective": args.objective,
            }
            if args.user_id:
                payload["user_id"] = args.user_id
            _request(
                "POST",
                base_url,
                "/advisor/recommend",
                payload,
            )
            return
        if args.command == "user-trades":
            trades = json.loads(args.trades_json)
            _request(
                "POST",
                base_url,
                f"/advisor/users/{args.user_id}/trades",
                {"trades": trades},
            )
            return
        if args.command == "user-holdings":
            holdings = json.loads(args.holdings_json)
            _request(
                "POST",
                base_url,
                f"/advisor/users/{args.user_id}/holdings",
                {"holdings": holdings},
            )
            return
        if args.command == "execute":
            payload = {
                "asset": args.asset,
                "action": args.action,
                "size": args.size,
                "strategy_id": args.strategy_id,
            }
            if args.to_address:
                payload["to_address"] = args.to_address
            if args.call_data:
                payload["call_data"] = args.call_data
            if args.value_wei is not None:
                payload["value_wei"] = args.value_wei
            _request(
                "POST",
                base_url,
                "/execute/plan",
                payload,
            )
            return
        if args.command == "mcp-route":
            profile = json.loads(args.profile_json) if args.profile_json else None
            trade = json.loads(args.trade_json) if args.trade_json else None
            payload = json.loads(args.payload_json)
            _request(
                "POST",
                base_url,
                "/mcp/route",
                {
                    "route": args.route,
                    "user_id": args.user_id,
                    "intent": args.intent,
                    "profile": profile,
                    "trade": trade,
                    "payload": payload,
                },
            )
            return
    except httpx.HTTPError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
