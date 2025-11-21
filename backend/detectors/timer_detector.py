import re
from ..scraper.timer_refresh_checker import check_timer_reset

# keywords or HTML patterns where timers commonly appear
TIMER_KEYWORDS = [
    "countdown",
    "timer",
    "offer ends",
    "ends in",
    "deal ends",
    "limited time",
    "flash sale"
]

def detect_fake_timer(html, url=None):
    text = html.lower()
    flags = {
        "reset_on_refresh": False,
        "frontend_only": False,
        "missing_tnc": False
    }

    # 1️⃣ Looks for timer indicators in HTML
    found_keywords = [k for k in TIMER_KEYWORDS if k in text]

    if not found_keywords:
        return {
            "detected": False,
            "type": "fake_timer"
        }

    # 2️⃣ Check if timer resets (MOST powerful test)
    if url:
        reset = check_timer_reset(url)
        flags["reset_on_refresh"] = reset

    # 3️⃣ Check if timer is driven by JS only (frontend manipulated)
    if re.search(r"setInterval|countdown|timer_js|startTimer", html):
        flags["frontend_only"] = True

    # 4️⃣ Check if “T&C” or expiry info is missing → suspicious
    if not re.search(r"valid|until|expiry|terms|conditions|t&c", text):
        flags["missing_tnc"] = True

    # 5️⃣ Decide confidence score
    suspicious_count = sum(flags.values())

    if suspicious_count == 0:
        confidence = "low"
    elif suspicious_count == 1:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "detected": True,
        "type": "fake_timer",
        "matches": found_keywords,
        "flags": flags,
        "confidence": confidence
    }

