from flask import Flask, request, jsonify
from flask_cors import CORS  # ← ADDED
from backend.scraper.html_fetcher import fetch_html
from backend.scraper.price_extractor import extract_price_and_mrp, extract_price_and_mrp_detailed
from backend.detectors.run_all import run_all_detectors
from backend.detectors.mrp_auth_checker import check_mrp_authenticity
from backend.price_tracker.track_price import PriceTracker

app = Flask(__name__)
CORS(app)  # ← ADDED - Enable CORS for all routes
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
    try:  # ← ADDED error handling
        data = request.get_json(silent=True)
        if not data or "url" not in data:
            return {"error": "URL not provided"}, 400

        url = data["url"]
        
        # Fetch and analyze
        html = fetch_html(url)
        
        # Extract price and MRP with detailed information
        price_data = extract_price_and_mrp_detailed(html, url=url)
        price = price_data.get("selling_price") if price_data else None
        mrp = price_data.get("mrp") if price_data else None

        # Save price history
        if price:
            tracker.save_price(url, price, mrp)

        # Run detectors (pass price and mrp for MRP inflation check)
        detections = run_all_detectors(html, url=url, price=price, mrp=mrp)
        
        # MRP Authenticity Check
        detections["mrp_check"] = check_mrp_authenticity(html, url, listed_mrp=mrp, price=price)
        
        # Add price info
        detections["price_info"] = {"price": price, "mrp": mrp}
        detections["price_history"] = tracker.get_history(url)["history"]
        
        # Add MRP Reality Check section
        if price_data:
            detections["mrp_reality_check"] = {
                "listed_mrp": price_data.get("mrp"),
                "benchmark_mrp": price_data.get("benchmark_mrp"),
                "inflation_factor": price_data.get("inflation_factor"),
                "mrp_source": price_data.get("mrp_source"),
                "confidence": price_data.get("confidence"),
                "message": price_data.get("message", "MRP information not available.")
            }

        return jsonify({"detections": detections}), 200
        
    except Exception as e:  # ← ADDED error handling
        print(f"[ERROR] {str(e)}")  # Log error
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("[FLASK] Starting server on http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)  # ← host='0.0.0.0' allows external access
