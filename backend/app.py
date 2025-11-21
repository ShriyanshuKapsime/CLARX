from flask import Flask, request
from backend.scraper.html_fetcher import fetch_html
from backend.scraper.price_extractor import extract_price_and_mrp
from backend.detectors.run_all import run_all_detectors
from backend.price_tracker.track_price import PriceTracker

app = Flask(__name__)
tracker = PriceTracker()


@app.route('/test', methods=['GET'])
def test():
    return {"message": "Backend running successfully!"}


@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return {"error": "URL not provided"}, 400

    url = data["url"]
    html = fetch_html(url)
    return {"length": len(html)}


from backend.price_tracker.track_price import PriceTracker
tracker = PriceTracker()

@app.route('/test/save_price', methods=['POST'])
def test_save_price():
    data = request.get_json(silent=True)
    if not data:
        return {"error": "No JSON provided"}, 400

    url = data.get("url")
    price = data.get("price")
    mrp = data.get("mrp", None)

    if not url or price is None:
        return {"error": "url and price required"}, 400

    result = tracker.save_price(url, float(price), float(mrp) if mrp else None)
    return result


@app.route('/test/get_history', methods=['POST'])
def test_get_history():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return {"error": "url required"}, 400

    url = data["url"]
    result = tracker.get_history(url)
    return result


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return {"error": "URL not provided"}, 400

    url = data["url"]
    html = fetch_html(url)

    price, mrp = extract_price_and_mrp(html)

    if price:
        tracker.save_price(url, price, mrp)

    detections = run_all_detectors(html, url=url)

    detections["price_info"] = {"price": price, "mrp": mrp}

    detections["price_history"] = tracker.get_history(url)["history"]

    return {"detections": detections}


if __name__ == "__main__":
    print("[FLASK] Starting server on http://127.0.0.1:5000")
    app.run(debug=True)

