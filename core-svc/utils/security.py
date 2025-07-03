"""
Security Utilities - Phase 1
URL validation and security checks as recommended by expert analysis
"""

import re
from urllib.parse import urlparse
from typing import List
import ipaddress
import structlog

logger = structlog.get_logger()

# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}

# Blocked IP ranges (RFC 1918 private networks, localhost, etc.)
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),    # Localhost
    ipaddress.ip_network("10.0.0.0/8"),     # Private class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private class B
    ipaddress.ip_network("192.168.0.0/16"), # Private class C
    ipaddress.ip_network("169.254.0.0/16"), # Link-local
    ipaddress.ip_network("224.0.0.0/4"),    # Multicast
    ipaddress.ip_network("::1/128"),        # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),       # IPv6 private
]

# Allowed domains for video URLs
ALLOWED_DOMAINS = {
    "youtube.com", 
    "youtu.be", 
    "storage.googleapis.com",
    "s3.amazonaws.com",
    "amazonaws.com"
}


def validate_video_url(url: str) -> bool:
    """
    Validate video URL to prevent SSRF attacks
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is safe, False otherwise
        
    Raises:
        ValueError: If URL is invalid or unsafe
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            logger.warning("Invalid URL scheme", url=url, scheme=parsed.scheme)
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        
        # Check if domain is allowed
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL must have a hostname")
        
        # Check against allowed domains
        domain_allowed = False
        for allowed_domain in ALLOWED_DOMAINS:
            if hostname == allowed_domain or hostname.endswith(f".{allowed_domain}"):
                domain_allowed = True
                break
        
        if not domain_allowed:
            logger.warning("Domain not allowed", url=url, hostname=hostname)
            raise ValueError(f"Domain not allowed: {hostname}")
        
        # Check for IP address in hostname (prevent direct IP access)
        try:
            ip = ipaddress.ip_address(hostname)
            # If we get here, hostname is an IP address
            for blocked_range in BLOCKED_IP_RANGES:
                if ip in blocked_range:
                    logger.warning("Blocked IP address", url=url, ip=str(ip))
                    raise ValueError(f"Access to IP address not allowed: {ip}")
        except ValueError:
            # hostname is not an IP address, which is good
            pass
        
        logger.info("URL validation passed", url=url)
        return True
        
    except Exception as e:
        logger.error("URL validation failed", url=url, error=str(e))
        raise


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove path traversal attempts
    sanitized = re.sub(r'\.\.', '', sanitized)
    
    # Limit length
    sanitized = sanitized[:100]
    
    # Ensure not empty
    if not sanitized.strip():
        sanitized = "untitled"
    
    logger.debug("Filename sanitized", original=filename, sanitized=sanitized)
    return sanitized


def validate_clip_title(title: str) -> str:
    """
    Validate and sanitize clip title
    
    Args:
        title: Original title
        
    Returns:
        Sanitized title
    """
    if not title or not title.strip():
        return "Untitled Clip"
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>&"\'\\]', '', title)
    
    # Limit length
    sanitized = sanitized[:200]
    
    return sanitized.strip()


def get_safe_storage_path(base_path: str, project_id: str, filename: str) -> str:
    """
    Generate safe storage path preventing directory traversal
    
    Args:
        base_path: Base storage directory
        project_id: Project UUID
        filename: Sanitized filename
        
    Returns:
        Safe file path
    """
    # Sanitize all components
    safe_project_id = re.sub(r'[^a-zA-Z0-9\-_]', '', str(project_id))
    safe_filename = sanitize_filename(filename)
    
    # Construct path
    safe_path = f"{base_path.rstrip('/')}/{safe_project_id}/{safe_filename}"
    
    logger.debug("Safe storage path generated", 
                project_id=project_id, 
                filename=filename, 
                safe_path=safe_path)
    
    return safe_path