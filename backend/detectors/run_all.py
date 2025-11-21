from .scarcity_detector import detect_scarcity
from .timer_detector import detect_fake_timer
from .drip_pricing_detector import detect_drip_pricing



def run_all_detectors(html, url=None):
    results = {}

    results["scarcity"] = detect_scarcity(html)
    results["timer"] = detect_fake_timer(html, url=url)
    results["drip_pricing"] = detect_drip_pricing(html)

    return results

