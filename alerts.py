# alerts.py - ClickUp alerting for failures

import requests
from datetime import datetime
from config import logger, CLICKUP_API_KEY, CLICKUP_WORKSPACE_ID, CLICKUP_CHANNEL_ID, current_log_file


def send_clickup_alert(alert_type, message, keyword=None, page=None, error=None):
    """Send alert to ClickUp Chat for failures
    
    Args:
        alert_type: "cloudflare" or "pipeline_crash"
        message: Alert message body
        keyword: Kickstarter keyword (if applicable)
        page: Pagination page number (if applicable)
        error: Error message/exception (if applicable)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not CLICKUP_API_KEY or not CLICKUP_WORKSPACE_ID or not CLICKUP_CHANNEL_ID:
        logger.warning("[ALERT] ClickUp API not configured, alert not sent locally")
        return False
    
    try:
        # Build alert message with context
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        alert_body = f"""🚨 Kickstarter Monitor Alert

**Alert Type:** {alert_type.upper()}
**Time:** {timestamp}
**Log File:** {current_log_file}

**Details:**
{message}
"""
        
        if keyword:
            alert_body += f"\n**Keyword:** {keyword}"
        
        if page:
            alert_body += f"\n**Page:** {page}"
        
        if error:
            alert_body += f"\n**Error:** {error}"
        
        # Send to ClickUp Chat API
        # Using workspaces/chat/channels endpoint to send message to channel
        url = f"https://api.clickup.com/api/v3/workspaces/{CLICKUP_WORKSPACE_ID}/chat/channels/{CLICKUP_CHANNEL_ID}/messages"
        
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        payload = {
            "type": "message",
            "content": alert_body,
            "content_format": "text/md"
        }
        
        logger.debug("[ALERT] Sending ClickUp alert...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            logger.info(f"[ALERT] ✅ ClickUp alert sent ({alert_type})")
            return True
        else:
            logger.warning(f"[ALERT] ⚠️  ClickUp alert failed with status {response.status_code}")
            logger.debug(f"[ALERT] Response: {response.text}")
            return False
    
    except Exception as e:
        # Never crash the pipeline due to alert failure
        logger.warning(f"[ALERT] ⚠️  ClickUp alert error: {e}")
        return False


def send_cloudflare_alert(keyword, page, retry_attempt):
    """Send alert when Cloudflare blocks exhaust retries
    
    Args:
        keyword: Kickstarter keyword being searched
        page: Page number that triggered max retries
        retry_attempt: Current retry attempt number
    """
    message = f"Max Cloudflare retries ({retry_attempt}) exceeded while searching keyword."
    error = f"Keyword '{keyword}' skipped after {retry_attempt} failed attempts on page {page}"
    
    return send_clickup_alert(
        alert_type="cloudflare",
        message=message,
        keyword=keyword,
        page=page,
        error=error
    )


def send_pipeline_crash_alert(error_message, phase=None):
    """Send alert when pipeline crashes with unhandled error
    
    Args:
        error_message: Exception message
        phase: Pipeline phase where crash occurred (optional)
    """
    message = "Unhandled exception during pipeline execution."
    
    return send_clickup_alert(
        alert_type="pipeline_crash",
        message=message,
        error=error_message
    )
