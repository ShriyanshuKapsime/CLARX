def detect_scarcity(html):
    keywords = [
        "only", 
        "left in stock", 
        "hurry",
        "selling fast",
        "limited stock"
    ]

    text = html.lower()
    found = []

    for k in keywords:
        if k in text:
            found.append(k)

    if found:
        return {
            "detected": True,
            "matches": found,
            "confidence": "medium",
            "type": "scarcity"
        }

    return {
        "detected": False,
        "type": "scarcity"
    }

