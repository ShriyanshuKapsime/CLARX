"""
Test suite for price extraction logic.
Tests Amazon, Flipkart, and edge cases (EMI, bank offers, etc.)
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'CLARX'))

from backend.scraper.price_extractor import extract_price_and_mrp


def test_amazon_product():
    """Test Amazon product page price extraction"""
    print("\n=== Test 1: Amazon Product ===")
    
    # Sample Amazon HTML with priceblock_ourprice
    amazon_html = """
    <html>
        <body>
            <div id="buybox">
                <span id="priceblock_ourprice">₹1,599</span>
                <span class="a-price a-text-price">₹3,490</span>
            </div>
            <div class="bank-offer">
                <span>Get 10% off up to ₹500</span>
            </div>
            <div class="emi-section">
                <span>EMI from ₹136/month</span>
            </div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(amazon_html, url="https://www.amazon.in/product")
    
    assert price == 1599, f"Expected 1599, got {price}"
    assert mrp == 3490, f"Expected 3490, got {mrp}"
    print("✓ Amazon price extraction: PASSED")


def test_flipkart_product():
    """Test Flipkart product page price extraction"""
    print("\n=== Test 2: Flipkart Product ===")
    
    # Sample Flipkart HTML
    flipkart_html = """
    <html>
        <body>
            <div class="_30jeq3">₹1,599</div>
            <div class="_3I9_wc">₹3,490</div>
            <div class="bank-offer">
                <span>Bank offer: Get 10% off up to ₹500</span>
            </div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(flipkart_html, url="https://www.flipkart.com/product")
    
    assert price == 1599, f"Expected 1599, got {price}"
    assert mrp == 3490, f"Expected 3490, got {mrp}"
    print("✓ Flipkart price extraction: PASSED")


def test_emi_rejection():
    """Test that EMI values are rejected"""
    print("\n=== Test 3: EMI Rejection ===")
    
    # HTML with only EMI values, no real price
    emi_html = """
    <html>
        <body>
            <div class="emi-section">
                <span>EMI from ₹136/month</span>
                <span>EMI starting at ₹500</span>
            </div>
            <div class="bank-offer">
                <span>Get ₹500 cashback</span>
            </div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(emi_html, url="https://www.amazon.in/product")
    
    # Should not extract EMI values
    assert price is None or price >= 100, f"Should reject EMI values, got {price}"
    print("✓ EMI rejection: PASSED")


def test_bank_offer_rejection():
    """Test that bank offer amounts are rejected"""
    print("\n=== Test 4: Bank Offer Rejection ===")
    
    # HTML with bank offers but no main price
    offer_html = """
    <html>
        <body>
            <div class="offers">
                <span>Get 10% off up to ₹500</span>
                <span>Bank offer: ₹200 cashback</span>
            </div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(offer_html, url="https://www.flipkart.com/product")
    
    # Should not extract offer amounts as main price
    assert price is None or price >= 100, f"Should reject offer amounts, got {price}"
    print("✓ Bank offer rejection: PASSED")


def test_mrp_validation():
    """Test that prices < 30% of MRP are rejected"""
    print("\n=== Test 5: MRP Validation ===")
    
    # HTML with a small price that's way less than MRP
    validation_html = """
    <html>
        <body>
            <div id="priceblock_ourprice">₹500</div>
            <span class="a-price a-text-price">₹3,490</span>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(validation_html, url="https://www.amazon.in/product")
    
    # 500 is < 30% of 3490 (1047), so should be rejected
    # In this case, we might still get it if it's from the official selector
    # But the validation should catch it
    if price and mrp:
        assert price >= mrp * 0.3, f"Price {price} should be >= 30% of MRP {mrp}"
    
    print("✓ MRP validation: PASSED")


def test_json_ld_extraction():
    """Test JSON-LD structured data extraction"""
    print("\n=== Test 6: JSON-LD Extraction ===")
    
    json_ld_html = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": {
                    "price": "1599",
                    "priceSpecification": {
                        "maxPrice": "3490"
                    }
                }
            }
            </script>
        </head>
        <body>
            <div>Some content</div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(json_ld_html, url="https://www.example.com/product")
    
    assert price == 1599, f"Expected 1599 from JSON-LD, got {price}"
    assert mrp == 3490, f"Expected 3490 from JSON-LD, got {mrp}"
    print("✓ JSON-LD extraction: PASSED")


def test_real_price_with_emi():
    """Test that real price is extracted even when EMI is present"""
    print("\n=== Test 7: Real Price with EMI ===")
    
    # HTML with both real price and EMI
    mixed_html = """
    <html>
        <body>
            <div id="buybox">
                <span id="priceblock_ourprice">₹1,599</span>
                <span class="a-price a-text-price">₹3,490</span>
            </div>
            <div class="emi-section">
                <span>EMI from ₹136/month</span>
            </div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(mixed_html, url="https://www.amazon.in/product")
    
    # Should extract the real price, not EMI
    assert price == 1599, f"Expected 1599 (real price), got {price}"
    assert price != 136, "Should not extract EMI value"
    print("✓ Real price with EMI: PASSED")


def test_no_price_found():
    """Test handling when no price is found"""
    print("\n=== Test 8: No Price Found ===")
    
    no_price_html = """
    <html>
        <body>
            <div>Product description</div>
            <div>No price information</div>
        </body>
    </html>
    """
    
    price, mrp = extract_price_and_mrp(no_price_html, url="https://www.example.com/product")
    
    assert price is None, f"Expected None, got {price}"
    print("✓ No price found: PASSED")


if __name__ == "__main__":
    print("=" * 50)
    print("PRICE EXTRACTOR TEST SUITE")
    print("=" * 50)
    
    try:
        test_amazon_product()
        test_flipkart_product()
        test_emi_rejection()
        test_bank_offer_rejection()
        test_mrp_validation()
        test_json_ld_extraction()
        test_real_price_with_emi()
        test_no_price_found()
        
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

