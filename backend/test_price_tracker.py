from price_tracker.tracker_price import PriceTracker


tracker = PriceTracker()

url = "https://www.flipkart.com/sample-product"

tracker.save_price(url, price=1499, mrp=2999)

history = tracker.get_history(url)
print(history)
