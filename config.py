# config.py - Configuration, logging, and environment variables

from dotenv import load_dotenv
import os
import sys
import logging
from datetime import datetime, timedelta
import glob
from supabase import create_client

# =========================
# LOAD .env FILE
# =========================
load_dotenv()


# =========================
# LOGGING SETUP
# =========================

def setup_logging(log_level):
    """Configure logging with console and file handlers"""
    log_format = "%(asctime)s - [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(console_handler)
    
    # File handler (create logs/ directory if not exists)
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    log_file = os.path.join(logs_dir, f"kickstarter-monitor-{timestamp}.log")
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(file_handler)
    
    return logger, log_file


def cleanup_old_logs(retention_days):
    """Delete log files older than retention_days"""
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_count = 0
    
    for log_file in glob.glob(os.path.join(logs_dir, "kickstarter-monitor-*.log")):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
        
        if file_mtime < cutoff_date:
            try:
                os.remove(log_file)
                print(f"🗑️  Deleted old log: {os.path.basename(log_file)}")
                deleted_count += 1
            except Exception as e:
                print(f"⚠️  Failed to delete {os.path.basename(log_file)}: {e}")
    
    if deleted_count > 0:
        print(f"🧹 Cleanup complete: Deleted {deleted_count} log files older than {retention_days} days")


def get_env(var_name, default=None, required=False):
    """Get environment variable from .env or system env"""
    value = os.getenv(var_name, default)
    
    if required and not value:
        logger.error(f"'{var_name}' is required but not set!")
        logger.error(f"Please add it to your .env file: {var_name}=your_value")
        sys.exit(1)
    
    return value


# =========================
# INITIALIZE LOGGER & CLEANUP
# =========================

LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS = int(get_env("LOG_RETENTION_DAYS", "30"))

# Cleanup old logs before setup
cleanup_old_logs(LOG_RETENTION_DAYS)

# Setup logger with file and console handlers
logger, current_log_file = setup_logging(LOG_LEVEL)


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
# Note: CSRF token is now extracted from project page HTML, not from .env
# Cookies are handled automatically by curl_cffi.Session

BASE_URL = "https://www.kickstarter.com/discover/advanced"
GRAPHQL_URL = "https://www.kickstarter.com/graph"


# =========================
# ENVIRONMENT VARIABLES - CLICKUP
# =========================

CLICKUP_WORKSPACE_ID = get_env("CLICKUP_WORKSPACE_ID", required=False)
CLICKUP_CHANNEL_ID = get_env("CLICKUP_CHANNEL_ID", required=False)
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
logger.info(f"📁 Log file: {current_log_file}")
logger.info(f"🧹 Log retention: {LOG_RETENTION_DAYS} days")
logger.info("=" * 80)
