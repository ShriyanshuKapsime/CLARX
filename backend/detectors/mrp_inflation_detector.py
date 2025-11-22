"""
MRP Inflation Detector
Detects if the listed MRP appears to be inflated compared to the selling price.
"""


def detect_mrp_inflation(price, mrp):
    """
    Detect if MRP is inflated compared to the selling price.
    
    Args:
        price: Current selling price (float or None)
        mrp: Listed MRP (float or None)
    
    Returns:
        dict with detection results
    """
    # If no MRP provided, cannot detect inflation
    if not mrp or mrp is None:
        return {
            "type": "mrp_inflation",
            "detected": False,
            "inflation_level": "none",
            "mrp": None,
            "price": price,
            "message": "MRP not provided on this product."
        }
    
    # If no price provided, cannot compare
    if not price or price is None:
        return {
            "type": "mrp_inflation",
            "detected": False,
            "inflation_level": "none",
            "mrp": mrp,
            "price": None,
            "message": "Price not available for comparison."
        }
    
    # Calculate price difference ratio
    ratio = mrp / price if price > 0 else 0
    
    # Determine inflation level
    if ratio >= 1.5:
        # MRP is 50%+ higher than price - likely inflated
        detected = True
        inflation_level = "high"
        message = "The MRP on this product seems significantly inflated. Actual value may be lower than listed MRP."
    elif ratio >= 1.3:
        # MRP is 30-50% higher - possibly inflated
        detected = True
        inflation_level = "medium"
        message = "The MRP on this product may be inflated. Actual value may be lower than listed MRP."
    else:
        # MRP is less than 30% higher - appears genuine
        detected = False
        inflation_level = "none"
        message = "MRP appears genuine compared to the selling price."
    
    return {
        "type": "mrp_inflation",
        "detected": detected,
        "inflation_level": inflation_level,
        "mrp": float(mrp),
        "price": float(price),
        "ratio": round(ratio, 2),
        "message": message
    }

