import re

def detect_drip_pricing(html):
    text = html.lower()

    flags = {
        "delivery_fee": False,
        "convenience_fee": False,
        "packaging_fee": False,
        "plus_price_pattern": False,
        "hidden_charges_terms": False
    }

    # 1️⃣ Detect common fee keywords
    if "delivery fee" in text or "delivery charge" in text or "shipping fee" in text:
        flags["delivery_fee"] = True

    if "convenience fee" in text or "platform fee" in text:
        flags["convenience_fee"] = True

    if "packaging fee" in text or "handling fee" in text:
        flags["packaging_fee"] = True

    # 2️⃣ Detect “₹ X + ₹ Y” patterns (classic hidden fee)
    plus_price_pattern = re.search(r"₹\s?\d[\d,]*\s?\+\s?₹\s?\d[\d,]*", html)
    if plus_price_pattern:
        flags["plus_price_pattern"] = True

    # 3️⃣ Detect hidden charges terms
    if "additional charges" in text or "extra charges" in text:
        flags["hidden_charges_terms"] = True

    # Count suspicious flags
    suspicious_count = sum(flags.values())

    if suspicious_count == 0:
        return {
            "detected": False,
            "type": "drip_pricing"
        }

    # Confidence scoring
    if suspicious_count == 1:
        confidence = "medium"
    elif suspicious_count == 2:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "detected": True,
        "type": "drip_pricing",
        "flags": flags,
        "confidence": confidence
    }

