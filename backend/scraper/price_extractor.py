import re

def extract_price_and_mrp(html):
    """
    Extract price and MRP from HTML.
    Works for Flipkart, Amazon, and general Indian sites.
    """

    # Convert HTML to lowercase for consistency
    text = html.lower()

    # Regex for amounts like ₹12,999 or 12999
    price_regex = r"₹\s?([\d,]+)"

    prices = re.findall(price_regex, html)

    if not prices:
        return None, None

    # Normalize numbers (remove commas)
    cleaned_prices = [int(p.replace(",", "")) for p in prices]

    # Heuristic:
    # Usually first is discounted price, second is MRP
    price = cleaned_prices[0] if len(cleaned_prices) > 0 else None
    mrp = cleaned_prices[1] if len(cleaned_prices) > 1 else None

    return price, mrp

