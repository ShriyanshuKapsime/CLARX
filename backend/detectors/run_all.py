from .scarcity_detector import detect_scarcity
from .timer_detector import detect_fake_timer
from .drip_pricing_detector import detect_drip_pricing
from .addon_detector import detect_addons
from .mrp_inflation_detector import detect_mrp_inflation

def run_all_detectors(html, url=None, price=None, mrp=None):
    results = {}

    results["scarcity"] = detect_scarcity(html)
    results["timer"] = detect_fake_timer(html, url=url)
    results["drip_pricing"] = detect_drip_pricing(html)
    results["addons"] = detect_addons(html)
    
    # MRP inflation check (requires price and mrp)
    results["mrp_inflation"] = detect_mrp_inflation(price, mrp)

    return results

