from .scarcity_detector import detect_scarcity
from .timer_detector import detect_fake_timer


def run_all_detectors(html, url=None):
    results = {}

    results["scarcity"] = detect_scarcity(html)
    results["timer"] = detect_fake_timer(html, url=url)

    return results

