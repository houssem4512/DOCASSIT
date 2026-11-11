from pathlib import Path
import os

# Load environment variables from backend/.env if it exists.
# This is where you put your API keys (GROQ_API_KEY, OPENAI_API_KEY, etc.)
# without having to `export` them in every terminal session.
# Copy backend/.env.example to backend/.env and fill in your keys.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed yet — env vars must be set manually

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework.authtoken", "corsheaders",
    "apps.accounts", "apps.documents", "apps.notifications", "apps.core",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages"]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_USER_MODEL = "accounts.User"
LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Tunis"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024

CORS_ALLOW_ALL_ORIGINS = True  # restrict in production

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

# ---- RAG integration point -------------------------------------------------
# Dotted path to your engine class (see backend/rag/engine.py).
# Default = the real trilingual RAG engine you implement in rag/my_engine.py.
# Set RAG_ENGINE=rag.engine.PlaceholderEngine to fall back to the demo stub.
RAG_ENGINE = os.environ.get("RAG_ENGINE", "rag.my_engine.MyRAGEngine")
MAX_UPLOAD_MB = 50
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg"]

# ---- AI layer configuration (NEW) -----------------------------------------
# All of these are read by the modules in backend/rag/ and backend/mcp_server/.
# Override any of them in your environment (e.g. .env or `export VAR=...`).

# Multilingual embedding model. Default = small + fast + trilingual (ar/fr/en).
# For higher quality swap to "intfloat/multilingual-e5-small".
# After fine-tuning, point this at the local path, e.g. "./models/docassist-ft".
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# LLM provider: "none" (retrieval only), "groq" (free cloud, recommended),
# "openai", or "ollama" (local).
# "none" lets you run the full project with zero API keys — search and
# ingestion work, the chat returns the retrieved context with a notice.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

# Groq — free cloud LLM with a generous free tier (30 req/min, 14k req/day).
# Get a key at https://console.groq.com/keys (no credit card required).
# Recommended models for trilingual (ar/fr/en):
#   - "llama-3.3-70b-versatile"  (best quality)
#   - "qwen-2.5-32b"             (excellent for Arabic)
#   - "llama-3.1-8b-instant"     (fastest)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Vector store: Chroma persistent client rooted here. Zero setup.
CHROMA_DIR = os.environ.get("CHROMA_DIR", str(BASE_DIR / "chroma_db"))

# Whether to route chat answers through the LangGraph state machine.
# False = use the plain LangChain chain (simpler, faster, easier to debug).
# True  = use the LangGraph agent with explicit nodes + tool calling.
USE_LANGGRAPH = os.environ.get("USE_LANGGRAPH", "1") == "1"

# Whether the LLM is allowed to call tools (search_by_language) before answering.
# Requires LLM_PROVIDER != "none".
ENABLE_TOOL_CALLING = os.environ.get("ENABLE_TOOL_CALLING", "1") == "1"
