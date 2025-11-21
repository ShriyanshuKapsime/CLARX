from .selenium_driver import get_page_source
import time
import re

def extract_timer_value(html):
    match = re.search(r"(\d{1,2}:\d{2}:\d{2})", html)  
    if match:
        return match.group(1)
    return None

def check_timer_reset(url):
    # Scrape once
    html1 = get_page_source(url)
    t1 = extract_timer_value(html1)

    time.sleep(2)

    # Scrape again
    html2 = get_page_source(url)
    t2 = extract_timer_value(html2)

    # If timer resets or jumps backwards → suspicious
    if t1 and t2:
        return t2 > t1  

    return False

