from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def get_page_source(url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    time.sleep(2)  # Let page load

    html = driver.page_source
    driver.quit()
    return html

