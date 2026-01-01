import os


DATABASE_URL = os.getenv("DATABASE_URL", "")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "384"))
IVFFLAT_LISTS = int(os.getenv("IVFFLAT_LISTS", "100"))
IVFFLAT_PROBES = int(os.getenv("IVFFLAT_PROBES", "10"))

DATA_PROVIDER = os.getenv("DATA_PROVIDER", "bscscan")
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY", "")
BITQUERY_ENDPOINT = os.getenv("BITQUERY_ENDPOINT", "https://streaming.bitquery.io/graphql")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
BSCSCAN_ENDPOINT = os.getenv("BSCSCAN_ENDPOINT", "https://api.bscscan.com/api")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "local")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_API_BASE = os.getenv("EMBED_API_BASE", "https://api.openai.com/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")

INGEST_ENABLED = os.getenv("INGEST_ENABLED", "false").lower() == "true"
INGEST_INTERVAL_SEC = int(os.getenv("INGEST_INTERVAL_SEC", "300"))
INGEST_WALLET = os.getenv("INGEST_WALLET", "")

RESET_VECTOR_DIM_MISMATCH = os.getenv("RESET_VECTOR_DIM_MISMATCH", "false").lower() == "true"

RPC_URL = os.getenv("RPC_URL", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
EXECUTE_LIVE = os.getenv("EXECUTE_LIVE", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()
POLICY_MODE = os.getenv("POLICY_MODE")
if not POLICY_MODE:
    POLICY_MODE = "paper_trade" if ENVIRONMENT == "production" else "paper_trade"
if POLICY_MODE not in {"read_only", "paper_trade", "execute_enabled"}:
    raise RuntimeError("POLICY_MODE must be one of: read_only, paper_trade, execute_enabled")

MAX_GAS = int(os.getenv("MAX_GAS", "300000"))
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "25"))
MAX_SLIPPAGE_BPS = int(os.getenv("MAX_SLIPPAGE_BPS", "100"))
ALLOWED_ASSETS = [item.strip().upper() for item in os.getenv("ALLOWED_ASSETS", "BNB,BUSD,USDT").split(",") if item.strip()]
ALLOWED_ACTIONS = [item.strip().lower() for item in os.getenv("ALLOWED_ACTIONS", "swap,transfer").split(",") if item.strip()]

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set (see .env.example)")
