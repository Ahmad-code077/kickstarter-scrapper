# session_utils.py - Session creation with global proxy and impersonate settings

from curl_cffi.requests import Session
from config import logger, PROXY_URL


def create_session_with_proxy(impersonate="chrome", timeout=30):
    """Create a curl_cffi Session with global proxy and impersonate settings
    
    This ensures EVERY request through this session automatically uses:
    - Proxy configured in .env (PROXY_IP, PROXY_PORT, PROXY_USER, PROXY_PASS)
    - Chrome impersonation to avoid detection
    
    Args:
        impersonate (str): Browser to impersonate. Default: "chrome"
        timeout (int): Request timeout in seconds. Default: 30
    
    Returns:
        Session: Configured curl_cffi Session with proxy and impersonate settings
    
    Example:
        >>> session = create_session_with_proxy()
        >>> response = session.get("https://www.kickstarter.com/...")
        >>> # Proxy is automatically applied! No need to pass proxies= parameter
    """
    session = Session(impersonate=impersonate, timeout=timeout)
    
    if PROXY_URL:
        # Apply proxy globally to all requests through this session
        # Format: http://user:password@ip:port
        session.proxies = {
            "http": PROXY_URL,
            "https": PROXY_URL,
        }
        logger.debug(f"[SESSION] Proxy configured for session: http://***:***@{PROXY_URL.split('@')[1]}")
    else:
        logger.debug("[SESSION] No proxy configured, requests will go directly")
    
    return session


def create_session(impersonate="chrome", timeout=30):
    """Create a session, automatically choosing proxy vs no-proxy based on .env

    If a proxy is configured in .env (PROXY_URL is set), the session routes all
    requests through that proxy IP. Otherwise it falls back to a direct (no-proxy)
    session. This is the single entry point the pipeline should use so the
    proxy/no-proxy decision lives in exactly one place.

    Args:
        impersonate (str): Browser to impersonate. Default: "chrome"
        timeout (int): Request timeout in seconds. Default: 30

    Returns:
        Session: Proxied session if PROXY_URL is set, else a direct session
    """
    if PROXY_URL:
        return create_session_with_proxy(impersonate=impersonate, timeout=timeout)
    return create_session_no_proxy(impersonate=impersonate, timeout=timeout)


def create_session_no_proxy(impersonate="chrome", timeout=30):
    """Create a curl_cffi Session WITHOUT proxy (for debugging or optional use)
    
    Args:
        impersonate (str): Browser to impersonate. Default: "chrome"
        timeout (int): Request timeout in seconds. Default: 30
    
    Returns:
        Session: Configured curl_cffi Session (no proxy)
    
    Example:
        >>> session = create_session_no_proxy()
        >>> response = session.get("https://www.example.com")
    """
    session = Session(impersonate=impersonate, timeout=timeout)
    logger.debug("[SESSION] Created session without proxy")
    return session
