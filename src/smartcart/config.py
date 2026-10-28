import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "db" / "ecommerce.db"))
MODELS_DIR = Path(os.environ.get("MODELS_DIR", ROOT / "models"))
SESSION_GAP_MS = 30 * 60 * 1000
DAY_MS = 86_400_000
HYBRID_WEIGHTS = {"ctx": 3.0, "cf": 1.0, "pop": 0.5}
RRF_K = 60
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000").split(",")

CUT_EVENTS = 3
HISTORY_DAYS = 30
MAX_CTX_EVENTS = 300
TOP_N_ITEMS = 10_000
MAX_USER_ITEMS = 100
N_PER_SOURCE = 50
POP_WINDOW_DAYS = 7
HALF_LIFE_DAYS = 3
SESSION_BOOST = 3.0
UNSEEN_DAYS = 365.0
EVENT_WEIGHTS = {"view": 1.0, "addtocart": 3.0, "transaction": 5.0}
SIM_TOP_NEIGHBORS = 200
DATABASE_URL = os.environ.get("DATABASE_URL")

APP_DATABASE_PATH = Path(os.environ.get("APP_DATABASE_PATH", ROOT / "data" / "db" / "app.db"))
APP_DATABASE_URL = os.environ.get("APP_DATABASE_URL")
SESSION_COOKIE = "sc_session"
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "168"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "8"))
LOGIN_WINDOW_S = int(os.environ.get("LOGIN_WINDOW_S", "300"))
REGISTER_MAX_PER_HOUR = int(os.environ.get("REGISTER_MAX_PER_HOUR", "10"))
CHAT_MAX_PER_MINUTE = int(os.environ.get("CHAT_MAX_PER_MINUTE", "20"))
CHAT_MAX_CHARS = 500
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none").lower()
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "15"))
