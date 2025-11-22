import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def extract_price_and_mrp(html, url=None):
    """
    Extract product price and MRP from HTML.
    Returns tuple (price, mrp) for backward compatibility.
    """
    result = extract_price_and_mrp_detailed(html, url)
    if result:
        return result.get("selling_price"), result.get("mrp")
    return None, None


def extract_price_and_mrp_detailed(html, url=None):
    """
    Extract product price and MRP from HTML using comprehensive multi-layer approach.
    
    Returns structured output:
    {
        "selling_price": 1599,
        "mrp": 3490,
        "mrp_source": "onsite | inferred | cross_site",
        "benchmark_mrp": 3200,
        "inflation_factor": 1.09,
        "confidence": "high | medium | low",
        "message": "User-friendly explanation"
    }
    """
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'lxml')
    domain = urlparse(url).netloc.lower() if url else ""
    
    print("[PRICE DEBUG] Starting comprehensive price extraction...")
    
    # ============================================
    # STEP 1: Detect Selling Price
    # ============================================
    selling_price = _detect_selling_price(soup, domain)
    print(f"[PRICE DEBUG] Selling price: {selling_price}")
    
    # ============================================
    # STEP 2: Detect MRP (High Confidence)
    # ============================================
    mrp_onsite = _detect_mrp_onsite(soup, domain)
    mrp_source = "onsite"
    confidence = "high"
    
    # ============================================
    # STEP 3: Detect MRP from Strikethrough (Medium Confidence)
    # ============================================
    if not mrp_onsite:
        mrp_onsite = _detect_mrp_strikethrough(soup)
        if mrp_onsite:
            mrp_source = "onsite"
            confidence = "medium"
            print(f"[PRICE DEBUG] MRP from strikethrough: {mrp_onsite}")
    
    # ============================================
    # STEP 4: Infer MRP from Discount Formula (Low-Medium Confidence)
    # ============================================
    if not mrp_onsite and selling_price:
        mrp_inferred = _infer_mrp_from_discount(soup, selling_price)
        if mrp_inferred:
            mrp_onsite = mrp_inferred
            mrp_source = "inferred"
            confidence = "low"
            print(f"[PRICE DEBUG] MRP inferred from discount: {mrp_onsite}")
    
    # ============================================
    # STEP 5: Cross-Site MRP Verification (Market Confidence)
    # ============================================
    benchmark_mrp = None
    if url and selling_price:
        product_title = _extract_product_title(soup, url)
        if product_title and len(product_title) > 20:
            benchmark_mrp = _get_cross_site_mrp(product_title, url)
            if benchmark_mrp:
                print(f"[PRICE DEBUG] Benchmark MRP from cross-site: {benchmark_mrp}")
                # If we have benchmark but no onsite MRP, use benchmark
                if not mrp_onsite:
                    mrp_onsite = benchmark_mrp
                    mrp_source = "cross_site"
                    confidence = "medium"
                # If we have both, use the higher one as benchmark
                elif benchmark_mrp > mrp_onsite:
                    benchmark_mrp = max(mrp_onsite, benchmark_mrp)
    
    # Final MRP
    final_mrp = mrp_onsite or benchmark_mrp
    
    # Calculate inflation factor
    inflation_factor = None
    if final_mrp and benchmark_mrp and benchmark_mrp > 0:
        inflation_factor = round(final_mrp / benchmark_mrp, 2)
    elif final_mrp and selling_price and final_mrp > selling_price * 1.4:
        # If no benchmark but MRP is much higher than price, calculate relative inflation
        inflation_factor = round(final_mrp / selling_price, 2)
    
    # Generate message
    message = _generate_mrp_message(final_mrp, selling_price, mrp_source, inflation_factor, benchmark_mrp)
    
    # Return structured result
    return {
        "selling_price": float(selling_price) if selling_price else None,
        "mrp": float(final_mrp) if final_mrp else None,
        "mrp_source": mrp_source if final_mrp else None,
        "benchmark_mrp": float(benchmark_mrp) if benchmark_mrp else None,
        "inflation_factor": inflation_factor,
        "confidence": confidence if final_mrp else None,
        "message": message
    }


def _detect_selling_price(soup, domain):
    """Detect selling price - lowest non-strikethrough price on page"""
    candidates = []
    
    # Site-specific selectors
    if 'amazon' in domain:
        selectors = [
            ('span', {'id': 'priceblock_ourprice'}),
            ('span', {'id': 'priceblock_dealprice'}),
            ('span', {'class': 'a-price-whole'}),
        ]
        for tag, attrs in selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text(strip=True)
                match = re.search(r'₹?\s*([\d,]+)', text.replace(',', ''))
                if match:
                    try:
                        price = float(match.group(1).replace(',', ''))
                        candidates.append(price)
                    except:
                        pass
    
    elif 'flipkart' in domain:
        price_elem = soup.find('div', class_='_30jeq3') or soup.find('span', class_='_30jeq3')
        if price_elem:
            text = price_elem.get_text(strip=True)
            match = re.search(r'₹?\s*([\d,]+)', text.replace(',', ''))
            if match:
                try:
                    price = float(match.group(1).replace(',', ''))
                    candidates.append(price)
                except:
                    pass
    
    # JSON-LD
    json_ld_price, _ = _extract_from_json_ld(soup)
    if json_ld_price:
        candidates.append(json_ld_price)
    
    # Regex fallback - find all prices, exclude strikethrough
    if not candidates:
        html_str = str(soup)
        page_text = soup.get_text()
        
        # Find all price patterns
        for match in re.finditer(r'₹\s*([\d,]+)', html_str):
            try:
                value = float(match.group(1).replace(',', ''))
                if 100 <= value <= 10000000:
                    # Check if in strikethrough context
                    start = max(0, match.start() - 50)
                    end = min(len(html_str), match.end() + 50)
                    context = html_str[start:end].lower()
                    
                    if any(tag in context for tag in ['<del', '<s', 'strike', 'text-decoration']):
                        continue
                    
                    candidates.append(value)
            except:
                pass
    
    # Return lowest price (selling price is usually the lowest)
    return min(candidates) if candidates else None


def _detect_mrp_onsite(soup, domain):
    """Detect MRP using common patterns: MRP, List Price, Regular Price, etc."""
    # Pattern: (MRP|List Price|Regular Price|Price:|Maximum Retail Price)[^0-9]*([0-9,]+)
    page_text = soup.get_text()
    
    mrp_patterns = [
        r'(?:MRP|M\.R\.P\.?)\s*:?\s*₹\s*([\d,]+)',
        r'List\s+Price\s*:?\s*₹\s*([\d,]+)',
        r'Regular\s+Price\s*:?\s*₹\s*([\d,]+)',
        r'Maximum\s+Retail\s+Price\s*:?\s*₹\s*([\d,]+)',
        r'Original\s+Price\s*:?\s*₹\s*([\d,]+)',
    ]
    
    for pattern in mrp_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace(',', ''))
                if 100 <= value <= 10000000:
                    return value
            except:
                pass
    
    # Site-specific MRP selectors
    if 'amazon' in domain:
        mrp_selectors = [
            ('span', {'class': 'a-price a-text-price'}),
            ('span', {'id': 'priceblock_saleprice'}),
        ]
        for tag, attrs in mrp_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text(strip=True)
                match = re.search(r'₹\s*([\d,]+)', text.replace(',', ''))
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except:
                        pass
    
    elif 'flipkart' in domain:
        mrp_elem = soup.find('div', class_='_3I9_wc') or soup.find('span', class_='_3I9_wc')
        if mrp_elem:
            text = mrp_elem.get_text(strip=True)
            match = re.search(r'₹\s*([\d,]+)', text.replace(',', ''))
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except:
                    pass
    
    # JSON-LD
    _, json_ld_mrp = _extract_from_json_ld(soup)
    if json_ld_mrp:
        return json_ld_mrp
    
    return None


def _detect_mrp_strikethrough(soup):
    """Detect MRP from strikethrough prices: <del>, <s>, .strike, .price-old, .list-price"""
    mrp_candidates = []
    
    # HTML strikethrough patterns
    strikethrough_selectors = [
        ('del', {}),
        ('s', {}),
        ('span', {'class': re.compile(r'.*strike.*', re.I)}),
        ('span', {'class': re.compile(r'.*price-old.*', re.I)}),
        ('span', {'class': re.compile(r'.*list-price.*', re.I)}),
        ('div', {'class': re.compile(r'.*strike.*', re.I)}),
        ('div', {'class': re.compile(r'.*price-old.*', re.I)}),
    ]
    
    for tag, attrs in strikethrough_selectors:
        elements = soup.find_all(tag, attrs)
        for elem in elements:
            text = elem.get_text(strip=True)
            match = re.search(r'₹\s*([\d,]+)', text.replace(',', ''))
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    if 100 <= value <= 10000000:
                        mrp_candidates.append(value)
                except:
                    pass
    
    # CSS strikethrough (text-decoration: line-through)
    html_str = str(soup)
    for match in re.finditer(r'text-decoration\s*:\s*line-through[^>]*>.*?₹\s*([\d,]+)', html_str, re.IGNORECASE | re.DOTALL):
        try:
            value = float(match.group(1).replace(',', ''))
            if 100 <= value <= 10000000:
                mrp_candidates.append(value)
        except:
            pass
    
    # Return highest value (MRP is usually higher than selling price)
    return max(mrp_candidates) if mrp_candidates else None


def _infer_mrp_from_discount(soup, selling_price):
    """Infer MRP from discount formulas: 'Save 70%', '70% off', 'You save ₹1200'"""
    page_text = soup.get_text()
    
    # Pattern 1: "Save X%" or "X% off"
    discount_pct_match = re.search(r'(?:Save|off)\s+(\d+)%', page_text, re.IGNORECASE)
    if discount_pct_match:
        try:
            discount_pct = float(discount_pct_match.group(1)) / 100
            if 0 < discount_pct < 1:  # Valid discount range
                mrp = selling_price / (1 - discount_pct)
                if mrp > selling_price:  # MRP should be higher
                    return round(mrp)
        except:
            pass
    
    # Pattern 2: "You save ₹X"
    save_amount_match = re.search(r'(?:You\s+save|Save)\s*₹\s*([\d,]+)', page_text, re.IGNORECASE)
    if save_amount_match:
        try:
            save_amount = float(save_amount_match.group(1).replace(',', ''))
            if save_amount > 0:
                mrp = selling_price + save_amount
                if mrp > selling_price:
                    return round(mrp)
        except:
            pass
    
    return None


def _get_cross_site_mrp(product_title, url):
    """
    Get benchmark MRP from cross-site verification.
    This is a placeholder - in production would search Amazon, Flipkart, etc.
    """
    # For now, return None (would require actual web scraping or API)
    # In production, this would:
    # 1. Clean product title
    # 2. Search on Amazon, Flipkart, Croma, Reliance Digital, Decathlon
    # 3. Extract MRP from each
    # 4. Return highest/majority value
    
    # Placeholder implementation
    return None


def _extract_product_title(soup, url):
    """Extract product title from page"""
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
        title = re.sub(r'\s*[-|]\s*(Amazon|Flipkart|Myntra).*', '', title, flags=re.I)
        return title
    
    # H1
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    
    return None


def _extract_from_json_ld(soup):
    """Extract price and MRP from JSON-LD structured data"""
    price = None
    mrp = None
    
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            
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


def _generate_mrp_message(mrp, selling_price, mrp_source, inflation_factor, benchmark_mrp):
    """Generate user-friendly message about MRP"""
    if not mrp:
        return "MRP not provided. Could not verify authenticity."
    
    if not selling_price:
        return f"MRP: ₹{int(mrp):,}. Price information not available for comparison."
    
    if inflation_factor and inflation_factor > 1.3:
        return f"MRP may be inflated compared to market average. Inflation factor: {inflation_factor}x"
    
    if mrp_source == "inferred":
        return f"MRP inferred from discount information. Listed MRP: ₹{int(mrp):,}"
    
    return f"MRP: ₹{int(mrp):,}. Selling price: ₹{int(selling_price):,}"
