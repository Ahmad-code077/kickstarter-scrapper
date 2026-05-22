# config.py - Configuration, logging, and environment variables

from dotenv import load_dotenv
import os
import sys
import logging
from supabase import create_client

# =========================
# LOAD .env FILE
# =========================
load_dotenv()


# =========================
# LOGGING SETUP
# =========================

def setup_logging(log_level):
    """Configure logging with INFO and DEBUG levels"""
    log_format = "%(asctime)s - [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format
    )
    return logging.getLogger(__name__)


def get_env(var_name, default=None, required=False):
    """Get environment variable from .env or system env"""
    value = os.getenv(var_name, default)
    
    if required and not value:
        logger.error(f"'{var_name}' is required but not set!")
        logger.error(f"Please add it to your .env file: {var_name}=your_value")
        sys.exit(1)
    
    return value


# =========================
# INITIALIZE LOGGER
# =========================

LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
logger = setup_logging(LOG_LEVEL)


# =========================
# ENVIRONMENT VARIABLES - KICKSTARTER
# =========================

keywords_env = get_env("KICKSTARTER_KEYWORDS", required=True)
KEYWORDS = [k.strip() for k in keywords_env.split("|") if k.strip()]

if not KEYWORDS:
    logger.error("KICKSTARTER_KEYWORDS is set but empty!")
    sys.exit(1)

DAYS_BACK = int(get_env("KICKSTARTER_DAYS_BACK", "14"))
MAX_PAGES = int(get_env("KICKSTARTER_MAX_PAGES", "10"))
REQUEST_DELAY = float(get_env("KICKSTARTER_REQUEST_DELAY", "1"))
KICKSTARTER_CSRF_TOKEN = get_env("KICKSTARTER_CSRF_TOKEN", required=False)
KICKSTARTER_COOKIES = get_env("KICKSTARTER_COOKIE_STRING", required=False)

BASE_URL = "https://www.kickstarter.com/discover/advanced"
GRAPHQL_URL = "https://www.kickstarter.com/graph"


# =========================
# ENVIRONMENT VARIABLES - CLICKUP
# =========================

CLICKUP_WORKSPACE_ID = get_env("CLICKUP_WORKSPACE_ID", required=False)
CLICKUP_VOICE_DOC_ID = get_env("CLICKUP_VOICE_DOC_ID", required=False)
CLICKUP_VOICE_PAGE_ID = get_env("CLICKUP_VOICE_PAGE_ID", required=False)
CLICKUP_SOP_EXTRACTION_DOC_ID = get_env("CLICKUP_SOP_EXTRACTION_DOC_ID", required=False)
CLICKUP_SOP_EXTRACTION_PAGE_ID = get_env("CLICKUP_SOP_EXTRACTION_PAGE_ID", required=False)
CLICKUP_API_KEY = get_env("CLICKUP_API_KEY", required=False)


# =========================
# ENVIRONMENT VARIABLES - OPENAI
# =========================

OPENAI_API_KEY = get_env("OPENAI_API_KEY", required=False)


# =========================
# ENVIRONMENT VARIABLES - SUPABASE
# =========================

SUPABASE_URL = get_env("SUPABASE_URL", required=False)
SUPABASE_KEY = get_env("SUPABASE_KEY", required=False)

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized")


# =========================
# PRINT CONFIGURATION
# =========================

logger.info("=" * 80)
logger.info("🎯 KICKSTARTER MONITOR - Complete Pipeline")
logger.info("=" * 80)
logger.info(f"📌 Keywords: {', '.join(KEYWORDS)}")
logger.info(f"📅 Days back: {DAYS_BACK}")
logger.info(f"📊 Log level: {LOG_LEVEL}")
logger.info("=" * 80)
