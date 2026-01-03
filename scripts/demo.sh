#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.venv/bin/activate"
else
  echo "Missing ${ROOT_DIR}/.venv/bin/activate. Create a venv in the repo root." >&2
  exit 1
fi
set -a
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
elif [[ -f "${ROOT_DIR}/.env.development" ]]; then
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env.development"
else
  echo "Missing .env or .env.development in ${ROOT_DIR}" >&2
  exit 1
fi
set +a

python "${ROOT_DIR}/cli.py" demo

python "${ROOT_DIR}/cli.py" mcp-route --route advise --user-id user-1 --intent portfolio \
  --profile-json '{"risk_tolerance":0.45,"horizon_days":120,"max_drawdown":0.2}' \
  --payload-json '{"objective":"income"}'
