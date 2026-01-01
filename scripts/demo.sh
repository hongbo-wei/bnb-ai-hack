#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
set -a
source .env
set +a

python cli.py demo

python cli.py mcp-route --route advise --user-id user-1 --intent portfolio \
  --profile-json '{"risk_tolerance":0.45,"horizon_days":120,"max_drawdown":0.2}' \
  --payload-json '{"objective":"income"}'
