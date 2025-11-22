from .selenium_driver import get_page_source
import time
import re

def extract_timer_value(html):
    """
    Extract timer value from HTML. Returns time in seconds for comparison.
    Supports formats: HH:MM:SS, HH:MM, and "Xh Ym Zs" patterns.
    """
    # Try HH:MM:SS format
    match = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", html)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    
    # Try HH:MM format (assume 0 seconds)
    match = re.search(r"(\d{1,2}):(\d{2})(?!\d)", html)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours * 3600 + minutes * 60
    
    # Try "Xh Ym Zs" format
    match = re.search(r"(\d+)\s*h[ours]*\s*(\d+)\s*m[inutes]*\s*(\d+)\s*s[econds]*", html, re.I)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    
    # Try "Xh Ym" format
    match = re.search(r"(\d+)\s*h[ours]*\s*(\d+)\s*m[inutes]*", html, re.I)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours * 3600 + minutes * 60
    
    return None

def check_timer_reset(url):
    """
    Check if timer resets on refresh by comparing timer values from two page loads.
    Returns True if timer increased (reset) or jumped backwards, indicating fake timer.
    """
    try:
        # Scrape once
        html1 = get_page_source(url)
        t1 = extract_timer_value(html1)

        time.sleep(2)

        # Scrape again
        html2 = get_page_source(url)
        t2 = extract_timer_value(html2)

        # If timer resets or jumps backwards → suspicious
        # Timer should decrease over time, so if t2 > t1 (or significantly different), it's suspicious
        if t1 is not None and t2 is not None:
            # If timer increased, it reset (suspicious)
            if t2 > t1:
                return True
            # If timer decreased by more than expected (more than 10 seconds in 2 seconds), suspicious
            if t1 - t2 > 10:
                return True
            # If timer is exactly the same after 2 seconds, also suspicious (should have decreased)
            if abs(t1 - t2) < 1:
                return True

        return False
    except Exception:
        # If we can't check, return False (not suspicious)
        return False

