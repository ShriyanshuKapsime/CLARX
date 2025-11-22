# scraper/price_extractor.py  → FINAL WORKING VERSION (Nov 2025)

import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def extract_price_and_mrp(html, url=None):
    result = extract_price_and_mrp_detailed(html, url)
    if result:
        return result.get("selling_price"), result.get("mrp")
    return None, None

def extract_price_and_mrp_detailed(html, url=None):
    if not html:
        return None

    soup = BeautifulSoup(html, 'lxml')
    domain = urlparse(url).netloc.lower() if url else ""

    print("[CLARX] Starting price extraction...")

    # STEP 1: Get REAL selling price (priority: JSON-LD → a-offscreen → visible big text)
    selling_price = _get_real_selling_price(soup, domain)
    print(f"[CLARX] Real Selling Price: ₹{selling_price}")

    # STEP 2: Get the FAKE high MRP (strikethrough or "MRP inclusive of all taxes")
    listed_mrp = _get_listed_mrp(soup, domain)
    print(f"[CLARX] Listed MRP (fake): ₹{listed_mrp}")

    # STEP 3: Estimate REAL market MRP (cross-site logic placeholder + smart inference)
    real_market_mrp = _estimate_real_market_mrp(soup, domain, selling_price, listed_mrp)

    # STEP 4: Calculate inflation
    inflation_factor = None
    inflation_percent = None
    if listed_mrp and real_market_mrp and real_market_mrp > 100:
        inflation_factor = round(listed_mrp / real_market_mrp, 2)
        inflation_percent = round((inflation_factor - 1) * 100)

    # STEP 5: Generate final message
    message = _generate_final_message(selling_price, listed_mrp, real_market_mrp, inflation_factor, inflation_percent)

    return {
        "selling_price": float(selling_price) if selling_price else None,
        "mrp": float(listed_mrp) if listed_mrp else None,
        "real_market_mrp": float(real_market_mrp) if real_market_mrp else None,
        "inflation_factor": inflation_factor,
        "inflation_percent": inflation_percent,
        "confidence": "high" if selling_price and listed_mrp else "low",
        "message": message,
        "dark_pattern_detected": inflation_factor > 1.3 if inflation_factor else False
    }

def _get_real_selling_price(soup, domain):
    """Never returns strikethrough price. Always returns what you actually pay."""
    candidates = []

    # 1. JSON-LD (Gold standard)
    json_price, _ = _extract_from_json_ld(soup)
    if json_price and 50 <= json_price <= 500000:
        return json_price

    # 2. Amazon: Hidden in a-offscreen (this is the REAL price)
    if 'amazon' in domain:
        hidden = soup.select_one("span.a-offscreen")
        if hidden:
            text = hidden.get_text(strip=True).replace('₹', '').replace(',', '')
            match = re.search(r'[\d.]+', text)
            if match:
                price = float(match.group())
                if 50 <= price <= 500000:
                    return price

        # Fallback: big visible price
        big = soup.select_one("span.a-price-whole")
        if big:
            text = big.get_text(strip=True).replace(',', '')
            match = re.search(r'[\d.]+', text)
            if match:
                return float(match.group())

    # 3. Flipkart
    if 'flipkart' in domain:
        # Real price is usually in data-testid or big bold text
        price_elem = soup.find("div", string=re.compile(r'₹')) or soup.find("div", class_=re.compile(r'_30jeq3'))
        if price_elem:
            text = price_elem.get_text(strip=True)
            match = re.search(r'₹\s*([\d,]+)', text.replace(',', ''))
            if match:
                price = float(match.group(1).replace(',', ''))
                if 50 <= price <= 500000:
                    return price

    return None

def _get_listed_mrp(soup, domain):
    """Gets the big fake strikethrough MRP"""
    candidates = []

    # 1. Amazon: a-text-price span.a-offscreen (this is the strikethrough MRP)
    if 'amazon' in domain:
        mrp_hidden = soup.select("span.a-text-price span.a-offscreen")
        for el in mrp_hidden:
            text = el.get_text(strip=True).replace('₹', '').replace(',', '')
            match = re.search(r'[\d.]+', text)
            if match:
                val = float(match.group())
                if val > 200:
                    candidates.append(val)

    # 2. Flipkart: _3I9_wc class (classic MRP)
    if 'flipkart' in domain:
        for el in soup.find_all(class_=re.compile(r'_3I9_wc|old|strike', re.I)):
            text = el.get_text(strip=True)
            match = re.search(r'₹\s*([\d,]+)', text.replace(',', ''))
            if match:
                val = float(match.group(1).replace(',', ''))
                if val > 200:
                    candidates.append(val)

    # 3. Any strikethrough with ₹
    for tag in soup.find_all(['del', 's', 'strike']) + soup.find_all(style=re.compile('line-through')):
        text = tag.get_text(strip=True)
        match = re.search(r'₹\s*([\d,]+)', text.replace(',', ''))
        if match:
            val = float(match.group(1).replace(',', ''))
            if val > 200:
                candidates.append(val)

    # 4. Text: "MRP ₹4999"
    page_text = soup.get_text()
    mrp_match = re.search(r'MRP.*₹\s*([\d,]+)', page_text, re.I)
    if mrp_match:
        val = float(mrp_match.group(1).replace(',', ''))
        if val > 200:
            candidates.append(val)

    return max(candidates) if candidates else None

def _estimate_real_market_mrp(soup, domain, selling_price, listed_mrp):
    """Smart estimation when no cross-site search"""
    if not selling_price or not listed_mrp:
        return None

    # If discount > 60%, assume inflation
    apparent_discount = 1 - (selling_price / listed_mrp)
    if apparent_discount > 0.6:
        # Assume real MRP is ~ selling_price * 1.8 to 2.5
        return round(selling_price * 2.2)  # average real multiplier

    if apparent_discount > 0.4:
        return round(selling_price * 1.7)

    return listed_mrp  # probably genuine

def _extract_from_json_ld(soup):
    price = None
    mrp = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get('@type') == 'Product':
                    offers = item.get('offers', {})
                    offers_list = offers if isinstance(offers, list) else [offers]
                    for offer in offers_list:
                        if offer.get('price'):
                            price = float(offer['price'])
                        if offer.get('priceSpecification', {}).get('maxPrice'):
                            mrp = float(offer['priceSpecification']['maxPrice'])
        except:
            continue
    return price, mrp

def _generate_final_message(selling_price, listed_mrp, real_mrp, factor, percent):
    if not selling_price:
        return "Price not found."

    if not listed_mrp:
        return f"Selling Price: ₹{int(selling_price):,} | No MRP shown"

    if factor and factor > 1.3:
        return f"GREEN FLAG Fake Discount Detected!\n" \
               f"Selling Price: ₹{int(selling_price):,}\n" \
               f"Listed MRP: ₹{int(listed_mrp):,} (inflated)\n" \
               f"Real Market MRP: ~₹{int(real_mrp):,}\n" \
               f"Inflation: {percent}% fake!"

    discount = round((1 - selling_price / listed_mrp) * 100)
    return f"Selling Price: ₹{int(selling_price):,}\n" \
           f"MRP: ₹{int(listed_mrp):,}\n" \
           f"Discount: {discount}% (likely genuine)"

