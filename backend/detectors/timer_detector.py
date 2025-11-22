import re
from backend.scraper.timer_refresh_checker import check_timer_reset

# Countdown timer HTML class patterns (must be exact matches in class/id attributes)
TIMER_CLASSES = [
    "countdown", "timer", "expiry-timer", "deal-timer", 
    "countdown-timer", "timer-container"
]

# JavaScript countdown function patterns (must include date math or countdown logic)
JS_TIMER_PATTERNS = [
    r"setInterval\s*\([^)]*countdown",
    r"setInterval\s*\([^)]*timer",
    r"setInterval\s*\([^)]*Date\s*[+-]",
    r"startTimer\s*\(",
    r"updateTimer\s*\(",
    r"countdown\s*\([^)]*Date",
    r"new\s+Date\s*\([^)]*\)\s*[-+]\s*\d+",  # Date math for countdown
]


def detect_fake_timer(html, url=None):
    """
    Detect countdown timers ONLY if actual timer elements exist.
    Does NOT rely on keywords like "offer", "deal", "limited" - requires REAL countdown evidence.
    
    Strict detection rules:
    - Must have countdown digits (00:30, HH:MM:SS) OR
    - Must have timer-specific DOM elements (class/id="countdown", data-countdown) OR
    - Must have JavaScript countdown functions with date math
    """
    text = html.lower()
    matches = []
    flags = {
        "reset_on_refresh": False,
        "frontend_only": False,
        "missing_tnc": False
    }

    # Detection Rule 1: Check for countdown digit patterns
    # Must be strict patterns that indicate actual countdown (not prices or other numbers)
    # Patterns like "00:30", "12:59:59" - but NOT "₹1,234" or "10% off"
    countdown_regex = [
        r"\b\d{1,2}:\d{2}:\d{2}\b",  # HH:MM:SS (strict word boundaries)
        r"\b\d{1,2}:\d{2}\b(?!\s*[ap]m)",  # HH:MM but not time of day (exclude AM/PM)
        r"\d{1,2}h\s+\d{1,2}m\s+\d{1,2}s",  # 3h 14m 30s
        r"\d{1,2}h\s+\d{1,2}m(?!\s*[ap]m)",  # 3h 14m (not time of day)
    ]
    
    has_countdown_digits = False
    found_pattern = None
    for pattern in countdown_regex:
        # Additional check: make sure it's not part of a price or percentage
        matches_found = re.finditer(pattern, html, re.IGNORECASE)
        for match in matches_found:
            # Check context - should not be near currency symbols or percentages
            start = max(0, match.start() - 10)
            end = min(len(html), match.end() + 10)
            context = html[start:end].lower()
            # Exclude if it's part of price (₹, $, etc.) or percentage
            if not re.search(r'[₹$€£%]|price|discount|off', context):
                has_countdown_digits = True
                found_pattern = pattern
                matches.append(f"Countdown pattern: {pattern}")
                break
        if has_countdown_digits:
            break

    # Detection Rule 2: Check for countdown HTML classes and IDs
    has_timer_classes = False
    found_classes = []
    
    # Check class attributes
    for class_name in TIMER_CLASSES:
        class_pattern = rf'class=["\'][^"\']*{re.escape(class_name)}[^"\']*["\']'
        if re.search(class_pattern, html, re.IGNORECASE):
            has_timer_classes = True
            found_classes.append(f"class={class_name}")
    
    # Check id attributes (specifically id="countdown" or id="timer")
    id_patterns = [
        r'id=["\']countdown["\']',
        r'id=["\']timer["\']',
        r'id=["\']countdown-timer["\']',
    ]
    for pattern in id_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            has_timer_classes = True
            found_classes.append(f"id={pattern}")
    
    if found_classes:
        matches.append(f"Timer DOM elements: {', '.join(found_classes)}")

    # Detection Rule 3: Check for data-countdown attributes
    has_data_countdown = False
    data_countdown_patterns = [
        r'data-countdown=["\'][^"\']+["\']',
        r'data-timer=["\'][^"\']+["\']',
        r'data-end-time=["\'][^"\']+["\']',
        r'data-expiry=["\'][^"\']+["\']',
    ]
    for pattern in data_countdown_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            has_data_countdown = True
            matches.append(f"Data attribute: {pattern}")
            break

    # Detection Rule 4: Check for JavaScript countdown functions with date math
    has_js_timer = False
    found_js_patterns = []
    for pattern in JS_TIMER_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            has_js_timer = True
            clean_pattern = pattern.replace(r"\s*", "").replace("\\", "").replace("(", "")
            found_js_patterns.append(clean_pattern)
    
    if found_js_patterns:
        matches.append(f"JS countdown functions: {', '.join(found_js_patterns)}")

    # ONLY detect timer if at least one actual timer element exists
    timer_detected = has_countdown_digits or has_timer_classes or has_data_countdown or has_js_timer

    if not timer_detected:
        return {
            "detected": False,
            "type": "fake_timer"
        }

    # Timer was detected - now analyze if it's suspicious
    # 2) Reset checker (only if URL provided)
    if url:
        flags["reset_on_refresh"] = check_timer_reset(url)

    # 3) JS-driven timer (frontend-only)
    if has_js_timer:
        # Check if there's server-side timestamp evidence
        has_server_timestamp = bool(
            re.search(r'data-expiry|data-end-time|expires-at|end-time|data-timestamp', html, re.I) or
            re.search(r'/api/.*timer|/api/.*expiry|/api/.*countdown', html, re.I)
        )
        if not has_server_timestamp:
            flags["frontend_only"] = True

    # 4) Missing expiry or terms & conditions
    if not re.search(r"valid|until|expiry|terms|conditions|t&c|expires", text):
        flags["missing_tnc"] = True

    # Calculate confidence based on suspicious flags
    suspicious_count = sum(flags.values())
    confidence = (
        "low" if suspicious_count == 0 else
        "medium" if suspicious_count == 1 else
        "high"
    )

    return {
        "detected": True,
        "type": "fake_timer",
        "friendly_msg": "This product appears to use a countdown timer to increase urgency. Please verify if the timer resets or is legitimate.",
        "matches": matches,
        "flags": flags,
        "confidence": confidence
    }
