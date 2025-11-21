from .selenium_driver import get_page_source

def fetch_html(url):
    return get_page_source(url)

