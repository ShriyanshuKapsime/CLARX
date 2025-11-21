"""
Enhanced scraper with Selenium, timer detection, and price extraction
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, Optional, List
from urllib.parse import urlparse


class Scraper:
    def __init__(self, headless: bool = True, wait_time: int = 3):
        self.headless = headless
        self.wait_time = wait_time
        self.driver = None

    def _init_driver(self):
        """Initialize Chrome driver"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("window-size=1920,1080")

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            raise Exception(f"Failed to initialize Chrome driver: {str(e)}. Make sure chromedriver is installed and in PATH.")

    def scrape(self, url: str) -> Dict:
        """
        Main scraping function that returns HTML, price, and timer analysis
        """
        if not self.driver:
            self._init_driver()

        try:
            # Navigate to URL
            self.driver.get(url)
            time.sleep(self.wait_time)

            # Check for Cloudflare/Access Denied
            page_text = self.driver.page_source.lower()
            if any(blocker in page_text for blocker in ['cloudflare', 'access denied', 'checking your browser', 'please wait']):
                return {
                    "error": "site_protected",
                    "message": "Site is protected (Cloudflare/Access Denied). Please try a different URL."
                }

            # Get page source
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # Extract price
            price_data = self._extract_price(soup, url)

            # Analyze timer
            timer_analysis = self._analyze_timer(soup, url)

            # Get domain
            domain = urlparse(url).netloc

            return {
                "html": html,
                "soup": soup,
                "price": price_data,
                "timer_analysis": timer_analysis,
                "domain": domain,
                "url": url
            }

        except Exception as e:
            return {
                "error": "scraping_failed",
                "message": f"Failed to scrape URL: {str(e)}"
            }

    def _extract_price(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract price from page using site-specific selectors and regex fallback"""
        domain = urlparse(url).netloc.lower()
        price = None
        mrp = None

        # Site-specific selectors
        selectors = {
            'flipkart.com': [
                ('span', {'class': re.compile(r'.*price.*', re.I)}),
                ('div', {'class': re.compile(r'.*price.*', re.I)}),
                ('span', {'class': '_30jeq3'}),
                ('div', {'class': '_30jeq3'}),
            ],
            'amazon.in': [
                ('span', {'class': 'a-price-whole'}),
                ('span', {'id': 'priceblock_dealprice'}),
                ('span', {'id': 'priceblock_ourprice'}),
            ],
            'myntra.com': [
                ('span', {'class': re.compile(r'.*price.*', re.I)}),
                ('span', {'class': 'pdp-price'}),
            ]
        }

        # Try site-specific selectors first
        for site, site_selectors in selectors.items():
            if site in domain:
                for tag, attrs in site_selectors:
                    elements = soup.find_all(tag, attrs)
                    for elem in elements:
                        price_text = elem.get_text(strip=True)
                        price_match = re.search(r'₹?\s*([\d,]+)', price_text.replace(',', ''))
                        if price_match:
                            try:
                                price = float(price_match.group(1).replace(',', ''))
                                break
                            except:
                                pass
                    if price:
                        break
                if price:
                    break

        # Fallback: regex search across entire page
        if not price:
            page_text = soup.get_text()
            price_patterns = [
                r'₹\s*([\d,]+)',
                r'Rs\.?\s*([\d,]+)',
                r'INR\s*([\d,]+)',
            ]
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    try:
                        # Take the first reasonable price (between 100 and 10,000,000)
                        for match in matches:
                            p = float(match.replace(',', ''))
                            if 100 <= p <= 10000000:
                                price = p
                                break
                    except:
                        pass
                if price:
                    break

        # Try to find MRP (strikethrough price)
        mrp_selectors = [
            ('span', {'class': re.compile(r'.*mrp.*', re.I)}),
            ('span', {'class': re.compile(r'.*strike.*', re.I)}),
            ('span', {'style': re.compile(r'.*text-decoration.*line-through', re.I)}),
        ]
        for tag, attrs in mrp_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                mrp_text = elem.get_text(strip=True)
                mrp_match = re.search(r'₹?\s*([\d,]+)', mrp_text.replace(',', ''))
                if mrp_match:
                    try:
                        mrp = float(mrp_match.group(1).replace(',', ''))
                        break
                    except:
                        pass
            if mrp:
                break

        return {
            "current": price,
            "mrp": mrp if mrp else price  # Fallback to current price if MRP not found
        }

    def _analyze_timer(self, soup: BeautifulSoup, url: str) -> Dict:
        """
        Analyze timer elements for fake timer detection
        """
        html = str(soup)
        page_text = soup.get_text()

        # Look for timer patterns
        timer_patterns = [
            r'(\d{1,2}):(\d{2}):(\d{2})',  # HH:MM:SS
            r'(\d{1,2}):(\d{2})',  # MM:SS
            r'(\d+)\s*(?:hours?|hrs?|h)\s*(\d+)\s*(?:minutes?|mins?|m)',  # X hours Y minutes
        ]

        timer_found = False
        timer_elements = []

        # Search in text
        for pattern in timer_patterns:
            matches = re.findall(pattern, page_text, re.I)
            if matches:
                timer_found = True
                timer_elements.extend(matches)
                break

        # Search in HTML for timer-related classes/ids
        timer_keywords = ['countdown', 'timer', 'offer-ends', 'deal-ends', 'limited-time', 'expires']
        for keyword in timer_keywords:
            if keyword.lower() in html.lower():
                timer_found = True
                break

        if not timer_found:
            return {
                "present": False,
                "resets_on_refresh": False,
                "client_side_only": False,
                "fake_timer": False,
                "confidence": "low",
                "reasons": []
            }

        # Check if timer resets on refresh
        resets_on_refresh = False
        if self.driver:
            try:
                # Get initial timer value
                initial_timer = self._get_timer_value(soup)
                if initial_timer:
                    # Reload page
                    self.driver.refresh()
                    time.sleep(2)
                    new_soup = BeautifulSoup(self.driver.page_source, 'lxml')
                    new_timer = self._get_timer_value(new_soup)

                    # If timer increased or reset, it's suspicious
                    if new_timer and (new_timer > initial_timer or abs(new_timer - initial_timer) > 300):
                        resets_on_refresh = True
            except:
                pass

        # Check for client-side only timer
        client_side_only = False
        js_indicators = ['setInterval', 'setTimeout', 'countdown', 'timer']
        has_js_timer = any(indicator in html for indicator in js_indicators)

        # Check for server-side timestamp (API calls, data attributes)
        has_server_timestamp = bool(
            re.search(r'data-expiry|data-end-time|expires-at|end-time', html, re.I) or
            re.search(r'/api/.*timer|/api/.*expiry', html, re.I)
        )

        if has_js_timer and not has_server_timestamp:
            client_side_only = True

        # Determine if fake
        fake_timer = resets_on_refresh or client_side_only
        confidence = "high" if (resets_on_refresh and client_side_only) else ("medium" if fake_timer else "low")

        reasons = []
        if resets_on_refresh:
            reasons.append("Countdown resets on every reload within the same session.")
        if client_side_only:
            reasons.append("No server-side timestamp — logic is entirely client scripted.")
        if fake_timer and not reasons:
            reasons.append("Timer detected but validation checks suggest it may be manipulated.")

        return {
            "present": True,
            "resets_on_refresh": resets_on_refresh,
            "client_side_only": client_side_only,
            "has_tnc": False,  # Could be enhanced
            "fake_timer": fake_timer,
            "confidence": confidence,
            "reasons": reasons
        }

    def _get_timer_value(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract timer value in seconds"""
        page_text = soup.get_text()
        match = re.search(r'(\d{1,2}):(\d{2}):(\d{2})', page_text)
        if match:
            hours, minutes, seconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds
        return None

    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

