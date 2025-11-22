import re


def detect_scarcity(html):
    """
    Detect stock-based scarcity messages ONLY.
    Does NOT trigger on generic words like "only", "hurry", "limited" alone.
    
    Requires strict patterns that include:
    - Numbers (quantities) AND
    - Stock-related keywords ("left", "remaining", "in stock", etc.)
    
    Examples that WILL trigger:
    - "Only 2 left in stock"
    - "Hurry! Only 1 remaining"
    - "Limited stock: 3 items left"
    - "Selling fast: only 5 left"
    
    Examples that will NOT trigger:
    - "Only ₹499" (no stock keyword)
    - "Hurry, offers on credit cards" (no stock keyword)
    - "Only on weekends" (no stock keyword)
    - "Limited edition design" (no stock keyword + number)
    """
    text = html.lower()
    matches = []
    confidence = None
    
    # Strict regex patterns that require numbers + stock-related keywords
    # Pattern 1: "Only X left" or "Only X remaining" or "Only X in stock"
    pattern1 = r"(only\s+\d+\s+(left|remaining|in\s+stock))"
    match1 = re.search(pattern1, text, re.IGNORECASE)
    if match1:
        matches.append(match1.group(0))
        confidence = "high"  # Exact quantity detected
    
    # Pattern 2: "X left" or "X remaining" or "X in stock" (without "only")
    pattern2 = r"(\d+\s+(left|remaining|in\s+stock))"
    match2 = re.search(pattern2, text, re.IGNORECASE)
    if match2:
        match = match2.group(0)
        # Avoid duplicates
        if match not in matches:
            matches.append(match)
            if confidence != "high":
                confidence = "high"  # Exact quantity detected
    
    # Pattern 3: "Few left" or "Few remaining" or "Few in stock"
    pattern3 = r"(few\s+(left|remaining|in\s+stock))"
    match3 = re.search(pattern3, text, re.IGNORECASE)
    if match3:
        match = match3.group(0)
        if match not in matches:
            matches.append(match)
            confidence = "medium"  # Generic but stock-related
    
    # Pattern 4: "Low stock" (must be standalone, not "low price")
    pattern4 = r"\b(low\s+stock)\b"
    match4 = re.search(pattern4, text, re.IGNORECASE)
    if match4:
        match = match4.group(0)
        if match not in matches:
            matches.append(match)
            if confidence != "high":
                confidence = "medium"  # Generic but stock-related
    
    # Pattern 5: "Selling fast" with stock context (must be near "left", "remaining", or numbers)
    # Only match if "selling fast" is followed by stock-related content within reasonable distance
    pattern5 = r"(selling\s+fast[^.]{0,80}?(only\s+\d+|few|low\s+stock|\d+\s+(left|remaining|in\s+stock)))"
    match5 = re.search(pattern5, text, re.IGNORECASE)
    if match5:
        # Additional check: ensure it's not "selling fast" in a different context
        match_text = match5.group(0)
        if "left" in match_text or "remaining" in match_text or "stock" in match_text or re.search(r'\d+', match_text):
            if match_text not in matches:
                matches.append(match_text)
                if confidence != "high":
                    confidence = "medium"  # Generic but stock-related
    
    # Pattern 6: "Hurry" with stock context (must be near "left", "remaining", or numbers)
    # Only match if "hurry" is followed by stock-related content
    pattern6 = r"(hurry[^.]{0,80}?(only\s+\d+|few|low\s+stock|\d+\s+(left|remaining|in\s+stock)))"
    match6 = re.search(pattern6, text, re.IGNORECASE)
    if match6:
        match_text = match6.group(0)
        # Additional check: ensure it's stock-related, not just "hurry" with any number
        if "left" in match_text or "remaining" in match_text or "stock" in match_text:
            if match_text not in matches:
                matches.append(match_text)
                if confidence != "high":
                    confidence = "medium"  # Generic but stock-related
    
    # Pattern 7: "Limited stock" with quantity or "left/remaining"
    # Must have "limited stock" followed by numbers or stock keywords
    pattern7 = r"(limited\s+stock[^.]{0,50}?(\d+|few|left|remaining))"
    match7 = re.search(pattern7, text, re.IGNORECASE)
    if match7:
        match_text = match7.group(0)
        # Additional validation: must have actual stock indicator
        if re.search(r'\d+|few|left|remaining', match_text):
            if match_text not in matches:
                matches.append(match_text)
                if confidence != "high":
                    confidence = "medium"  # Generic but stock-related
    
    # Pattern 8: "X items left" or "X units left"
    pattern8 = r"(\d+\s+(items?|units?)\s+(left|remaining))"
    match8 = re.search(pattern8, text, re.IGNORECASE)
    if match8:
        match = match8.group(0)
        if match not in matches:
            matches.append(match)
            confidence = "high"  # Exact quantity detected
    
    # Only return detected=True if we found actual stock-related patterns
    if matches:
        return {
            "detected": True,
            "type": "scarcity",
            "matches": matches,
            "confidence": confidence or "medium",
            "explanation": "This site shows low-stock messages such as: 'Only X left'. These are commonly used to create artificial urgency."
        }
    
    # No stock-related scarcity patterns found
    return {
        "detected": False,
        "type": "scarcity",
        "explanation": "No stock-related scarcity patterns found. Normal product details are safe."
    }

