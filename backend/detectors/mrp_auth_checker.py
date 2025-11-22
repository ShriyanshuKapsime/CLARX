"""
MRP Authenticity Checker
Checks if listed MRP is inflated by comparing against official sources and market norms.
"""
import re
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def check_mrp_authenticity(html, url, listed_mrp=None, price=None):
    """
    Check MRP authenticity using multiple methods:
    1. Official brand website (if available)
    2. Trusted marketplace comparison
    3. Historical discount estimation
    
    Args:
        html: Page HTML
        url: Product URL
        listed_mrp: MRP found on the page
        price: Current selling price
    
    Returns:
        dict with MRP authenticity check results
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # Extract product info
    product_title = _extract_product_title(soup, url)
    brand = _extract_brand(product_title, soup)
    
    # If no MRP provided, try to extract it from page
    if not listed_mrp:
        listed_mrp = _extract_mrp_from_page(soup, url)
        # Also try JSON-LD
        if not listed_mrp:
            _, json_ld_mrp = _extract_from_json_ld(soup)
            if json_ld_mrp:
                listed_mrp = json_ld_mrp
    
    # If no price provided, try to extract it from page
    if not price:
        price = _extract_price_from_page(soup, url)
    
    result = {
        "official_mrp": None,
        "market_mrp": None,
        "estimated_mrp": None,
        "listed_mrp": float(listed_mrp) if listed_mrp else None,
        "price": float(price) if price else None,
        "inflation_percent": None,
        "inflated": False,
        "message": "",
        "source": "estimation"
    }
    
    # If no MRP found, return early
    if not listed_mrp:
        result["message"] = "MRP not provided on website. Could not verify authenticity."
        return result
    
    if not price:
        result["message"] = "Price not available for comparison."
        return result
    
    # Calculate discount percentage
    discount_pct = ((listed_mrp - price) / listed_mrp * 100) if listed_mrp > 0 else 0
    
    # Method 1: Try official brand website (placeholder - would need actual scraping)
    # For now, we'll use estimation as primary method
    official_mrp = _check_official_website(brand, product_title)
    if official_mrp:
        result["official_mrp"] = official_mrp
        result["source"] = "official"
        inflation = ((listed_mrp - official_mrp) / official_mrp * 100) if official_mrp > 0 else 0
        result["inflation_percent"] = round(inflation, 1)
        result["inflated"] = inflation > 10  # More than 10% difference
        
        if result["inflated"]:
            result["message"] = f"⚠️ MRP might be inflated. Listed MRP differs from official brand website by {abs(result['inflation_percent'])}%."
        else:
            result["message"] = "✔ Official MRP verified. No signs of price inflation."
        return result
    
    # Method 2: Estimate realistic MRP based on discount norms
    estimated_mrp = _estimate_realistic_mrp(price, discount_pct)
    result["estimated_mrp"] = estimated_mrp
    result["source"] = "estimation"
    
    # Calculate inflation
    if estimated_mrp:
        inflation = ((listed_mrp - estimated_mrp) / estimated_mrp * 100) if estimated_mrp > 0 else 0
        result["inflation_percent"] = round(inflation, 1)
        result["inflated"] = inflation > 15  # More than 15% difference suggests inflation
        
        # Generate user-friendly message
        if result["inflated"]:
            result["message"] = f"⚠️ MRP might be inflated. Listed MRP: ₹{int(listed_mrp):,}. Realistic MRP: ₹{int(estimated_mrp):,}. Inflation detected: {abs(result['inflation_percent'])}%."
        elif discount_pct > 70:
            result["message"] = "⚠️ Discount seems unusually high (>70%). MRP may be manipulated to show false savings."
            result["inflated"] = True
        else:
            result["message"] = f"✔ MRP appears reasonable. Listed MRP: ₹{int(listed_mrp):,}. Estimated realistic range: ₹{int(estimated_mrp * 0.9):,} - ₹{int(estimated_mrp * 1.1):,}."
    else:
        result["message"] = "Could not estimate realistic MRP. Listed MRP: ₹{:,}.".format(int(listed_mrp))
    
    return result


def _extract_product_title(soup, url):
    """Extract product title from page"""
    # Try various title selectors
    title = None
    
    # JSON-LD
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'Product':
                title = data.get('name')
                if title:
                    return title
        except:
            pass
    
    # Meta tags
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title.get('content')
    
    # Page title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Clean up title (remove site name)
        title = re.sub(r'\s*[-|]\s*(Amazon|Flipkart|Myntra).*', '', title, flags=re.I)
        return title
    
    # H1 tag
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    
    return "Unknown Product"


def _extract_brand(product_title, soup):
    """Extract brand name from product title or page"""
    # Common brand patterns in titles
    # "boAt Stone 352 Speaker" -> "boAt"
    # "Samsung Galaxy S21" -> "Samsung"
    
    # Try to find brand in title (usually first word or known brands)
    words = product_title.split()
    if words:
        # Check if first word is a known brand
        first_word = words[0]
        known_brands = [
            'boat', 'samsung', 'apple', 'oneplus', 'xiaomi', 'realme', 'oppo', 'vivo',
            'sony', 'lg', 'panasonic', 'philips', 'hp', 'dell', 'lenovo', 'asus',
            'nike', 'adidas', 'puma', 'reebok', 'woodland', 'redtape', 'sparx'
        ]
        if first_word.lower() in known_brands:
            return first_word
    
    # Try to find brand in JSON-LD
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                brand = data.get('brand', {}).get('name') if isinstance(data.get('brand'), dict) else data.get('brand')
                if brand:
                    return brand
        except:
            pass
    
    # Try meta tags
    brand_meta = soup.find('meta', property='product:brand')
    if brand_meta:
        return brand_meta.get('content')
    
    return None


def _extract_mrp_from_page(soup, url):
    """Extract MRP from the current page using multiple patterns"""
    domain = urlparse(url).netloc.lower() if url else ""
    
    # Amazon MRP selectors
    if 'amazon' in domain:
        mrp_selectors = [
            ('span', {'class': 'a-price a-text-price'}),
            ('span', {'id': 'priceblock_saleprice'}),
            ('span', {'class': re.compile(r'.*strike.*', re.I)}),
        ]
        for tag, attrs in mrp_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text(strip=True)
                # Try multiple patterns
                patterns = [
                    r'₹\s*([\d,]+)',
                    r'M\.?R\.?P\.?\s*:?\s*₹\s*([\d,]+)',
                    r'MRP\s*:?\s*₹\s*([\d,]+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        try:
                            return float(match.group(1).replace(',', ''))
                        except:
                            pass
    
    # Flipkart MRP selector
    elif 'flipkart' in domain:
        mrp_selectors = [
            ('div', {'class': '_3I9_wc'}),
            ('span', {'class': '_3I9_wc'}),
            ('div', {'class': re.compile(r'.*mrp.*', re.I)}),
        ]
        for tag, attrs in mrp_selectors:
            mrp_elem = soup.find(tag, attrs)
            if mrp_elem:
                text = mrp_elem.get_text(strip=True)
                # Try multiple patterns
                patterns = [
                    r'₹\s*([\d,]+)',
                    r'M\.?R\.?P\.?\s*:?\s*₹\s*([\d,]+)',
                    r'MRP\s*:?\s*₹\s*([\d,]+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        try:
                            return float(match.group(1).replace(',', ''))
                        except:
                            pass
    
    # Fallback: search for MRP patterns in page text
    page_text = soup.get_text()
    mrp_patterns = [
        r'M\.?R\.?P\.?\s*:?\s*₹\s*([\d,]+)',
        r'MRP\s*:?\s*₹\s*([\d,]+)',
        r'Maximum\s+Retail\s+Price\s*:?\s*₹\s*([\d,]+)',
    ]
    
    for pattern in mrp_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace(',', ''))
                if 100 <= value <= 10000000:  # Reasonable range
                    return value
            except:
                pass
    
    return None


def _extract_from_json_ld(soup):
    """Extract price and MRP from JSON-LD structured data"""
    price = None
    mrp = None
    
    # Find all script tags with type="application/ld+json"
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            
            # Handle both single objects and arrays
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') == 'Product':
                        offers = item.get('offers', {})
                        if isinstance(offers, list) and len(offers) > 0:
                            offers = offers[0]
                        
                        if 'price' in offers:
                            try:
                                price = float(offers['price'])
                            except:
                                pass
                        
                        if 'priceSpecification' in offers:
                            ps = offers['priceSpecification']
                            if 'maxPrice' in ps:
                                try:
                                    mrp = float(ps['maxPrice'])
                                except:
                                    pass
            elif isinstance(data, dict):
                if data.get('@type') == 'Product':
                    offers = data.get('offers', {})
                    if isinstance(offers, list) and len(offers) > 0:
                        offers = offers[0]
                    
                    if 'price' in offers:
                        try:
                            price = float(offers['price'])
                        except:
                            pass
                    
                    if 'priceSpecification' in offers:
                        ps = offers['priceSpecification']
                        if 'maxPrice' in ps:
                            try:
                                mrp = float(ps['maxPrice'])
                            except:
                                pass
        except:
            continue
    
    return price, mrp


def _extract_price_from_page(soup, url):
    """Extract current price from page"""
    domain = urlparse(url).netloc.lower() if url else ""
    
    # Amazon price selectors
    if 'amazon' in domain:
        price_selectors = [
            ('span', {'id': 'priceblock_ourprice'}),
            ('span', {'id': 'priceblock_dealprice'}),
            ('span', {'class': 'a-price-whole'}),
        ]
        for tag, attrs in price_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text(strip=True)
                match = re.search(r'₹?\s*([\d,]+)', text.replace(',', ''))
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except:
                        pass
    
    # Flipkart price selector
    elif 'flipkart' in domain:
        price_elem = soup.find('div', class_='_30jeq3') or soup.find('span', class_='_30jeq3')
        if price_elem:
            text = price_elem.get_text(strip=True)
            match = re.search(r'₹?\s*([\d,]+)', text.replace(',', ''))
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except:
                    pass
    
    return None


def _check_official_website(brand, product_title):
    """
    Check official brand website for MRP.
    This is a placeholder - in production, would need actual web scraping.
    """
    if not brand:
        return None
    
    # Load brand sites mapping
    brand_sites_path = os.path.join(os.path.dirname(__file__), '..', '..', 'brand_sites.json')
    brand_sites = {}
    
    if os.path.exists(brand_sites_path):
        try:
            with open(brand_sites_path, 'r') as f:
                brand_sites = json.load(f)
        except:
            pass
    
    # For now, return None (would need actual scraping implementation)
    # In production, this would:
    # 1. Look up brand domain from brand_sites.json
    # 2. Search for product on official site
    # 3. Extract MRP
    # 4. Return it
    
    return None


def _estimate_realistic_mrp(price, discount_pct):
    """
    Estimate realistic MRP based on price and typical discount norms.
    
    Rules:
    - If discount > 70% → likely fake MRP
    - If price < 500 → typical discount = 30-50%
    - If price > 2000 → typical discount = 10-25%
    - If price 500-2000 → typical discount = 20-40%
    """
    if not price or price <= 0:
        return None
    
    # If discount is suspiciously high (>70%), MRP is likely inflated
    if discount_pct > 70:
        # Estimate based on reasonable discount (30-40%)
        return price / 0.65  # Assume 35% discount
    
    # Estimate based on price range and typical discount norms
    if price < 500:
        # Low price items: 30-50% discount typical
        # Use 40% as median
        return price / 0.6
    elif price > 2000:
        # High price items: 10-25% discount typical
        # Use 15% as median
        return price / 0.85
    else:
        # Mid-range: 20-40% discount typical
        # Use 30% as median
        return price / 0.7

