
import os
from pathlib import Path


# Load .env from the DocuMind AI project root.
# No third-party dotenv dependency is required.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_env_file():
    if not ENV_FILE.is_file():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Remove matching quotes around values.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        else:
            # Remove inline comments for unquoted values.
            value = value.split(" #", 1)[0].rstrip()

        if key:
            os.environ.setdefault(key, value)


load_env_file()


def env(k, d=None):
    return os.getenv(k, d)


def flag(k, d="false"):
    return env(k, d).strip().lower() == "true"


# Database and storage
DATABASE_URL = env("DATABASE_URL", "sqlite:///./documind.db")
STORAGE_DIR = env("STORAGE_DIR", "./storage")

MAX_UPLOAD = int(env("MAX_UPLOAD_BYTES", 10_000_000))
MAX_PAGES = int(env("MAX_PAGES", 300))
CHUNK_WORDS = int(env("CHUNK_WORDS", 180))
CHUNK_OVERLAP = int(env("CHUNK_OVERLAP", 30))

# Authentication and application settings
COOKIE_SECURE = flag("COOKIE_SECURE")
SESSION_DAYS = int(env("SESSION_DAYS", 7))

CORS_ORIGINS = [
    origin.strip()
    for origin in env("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

JOBS_SYNC = flag("JOBS_SYNC")
AUTO_CREATE_TABLES = flag("AUTO_CREATE_TABLES")
DEV_RETURN_RESET_TOKEN = flag("DEV_RETURN_RESET_TOKEN")

# Embeddings
EMBED_PROVIDER = env("EMBED_PROVIDER", "hash")  # hash | sbert
EMBED_MODEL = env(
    "EMBED_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# Language model
LLM_PROVIDER = env("LLM_PROVIDER", "none").strip().lower()
LLM_MODEL = env("LLM_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
GEMINI_API_KEY = env("GEMINI_API_KEY")

# GitHub integration and retrieval settings
GITHUB_TOKEN = env("GITHUB_TOKEN")
MIN_VECTOR_SIM = float(env("MIN_VECTOR_SIM", 0.30))
MAX_JOB_ATTEMPTS = int(env("MAX_JOB_ATTEMPTS", 2))
