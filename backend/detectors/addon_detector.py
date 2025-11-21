import re

ADDON_KEYWORDS = [
    r"warranty",
    r"extended warranty",
    r"damage protection",
    r"screen protection",
    r"insurance",
    r"protection plan",
    r"add[- ]?on",
    r"add to your order",
    r"buy together",
    r"frequently bought together",
    r"you may also need",
    r"recommended accessories",
    r"complete your order",
    r"include for",
    r"add for"
]

CHECKBOX_PATTERN = r"<input[^>]+checked[^>]*>"

def detect_addons(html):
    detected_matches = []

    lower_html = html.lower()

    for kw in ADDON_KEYWORDS:
        if re.search(kw, lower_html):
            detected_matches.append(kw)

    if re.search(CHECKBOX_PATTERN, lower_html):
        detected_matches.append("pre_ticked_checkbox")

    return {
        "type": "add_on",
        "detected": len(detected_matches) > 0,
        "matches": detected_matches
    }

