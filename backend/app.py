"""
Flask backend API for ClearBuy/ClearCart/TruthLens
"""
from flask import Flask, request, jsonify
try:
    from flask_cors import CORS
except ImportError:
    # Fallback if flask-cors not installed
    class CORS:
        def __init__(self, app):
            @app.after_request
            def after_request(response):
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
                response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                return response
from datetime import datetime
import uuid
from functools import wraps
from collections import defaultdict
import time

from models import Database
from scraper import Scraper
from detector import DarkPatternDetector

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize database
db = Database()

# Rate limiting (simple in-memory)
rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 60  # seconds


def rate_limit(f):
    """Simple rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP (or use session ID in production)
        client_id = request.remote_addr or 'default'
        now = time.time()

        # Clean old entries
        rate_limit_store[client_id] = [
            req_time for req_time in rate_limit_store[client_id]
            if now - req_time < RATE_LIMIT_WINDOW
        ]

        # Check limit
        if len(rate_limit_store[client_id]) >= RATE_LIMIT_REQUESTS:
            return jsonify({
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Limit: {RATE_LIMIT_REQUESTS} per {RATE_LIMIT_WINDOW} seconds."
            }), 429

        # Add current request
        rate_limit_store[client_id].append(now)

        return f(*args, **kwargs)
    return decorated_function


@app.route('/test', methods=['GET'])
def test():
    """Health check endpoint"""
    return jsonify({"message": "Backend running successfully!", "status": "ok"})


@app.route('/analyze', methods=['POST'])
@rate_limit
def analyze():
    """
    Main analysis endpoint
    POST /analyze
    Body: {"url": "https://..."}
    """
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"error": "url_required", "message": "URL not provided"}), 400

    url = data['url'].strip()
    if not url.startswith(('http://', 'https://')):
        return jsonify({"error": "invalid_url", "message": "URL must start with http:// or https://"}), 400

    # Create job
    job_id = db.create_job(url)
    db.update_job(job_id, 'running')

    scraper = None
    try:
        # Scrape the page
        scraper = Scraper(headless=True, wait_time=3)
        scraper_result = scraper.scrape(url)

        # Check for scraping errors
        if 'error' in scraper_result:
            db.update_job(job_id, 'failed', error_message=scraper_result.get('message', 'Scraping failed'))
            return jsonify({
                "error": scraper_result['error'],
                "message": scraper_result.get('message', 'Failed to scrape URL'),
                "job_id": job_id
            }), 422

        html = scraper_result['html']
        soup = scraper_result['soup']
        price_data = scraper_result.get('price', {})
        timer_analysis = scraper_result.get('timer_analysis', {})

        # Run detectors
        detector = DarkPatternDetector()
        violations = detector.detect_all(html, soup, scraper_result)

        # Calculate trust score
        trust_data = detector.calculate_trust_score(violations)

        # Store price in database
        if price_data.get('current'):
            db.insert_price(url, price_data['current'])
            db.update_url_scraped(url)

        # Get price history
        price_history = db.get_price_history(url, limit=30)

        # Calculate price stats
        if price_history:
            prices = [p['price'] for p in price_history]
            current_price = price_data.get('current') or prices[-1] if prices else None
            highest_price = max(prices) if prices else current_price
            lowest_price = min(prices) if prices else current_price
        else:
            current_price = price_data.get('current')
            highest_price = current_price
            lowest_price = current_price

        # Calculate MRP (simplified - in production, compare with external APIs)
        site_mrp = price_data.get('mrp') or current_price
        fair_mrp = current_price * 0.85 if current_price else None  # Simplified calculation
        inflation_pct = ((site_mrp - fair_mrp) / fair_mrp * 100) if (site_mrp and fair_mrp) else 0

        # Build response
        result = {
            "job_id": job_id,
            "url": url,
            "trust_grade": trust_data['grade'],
            "trust_summary": trust_data['summary'],
            "violations": violations,
            "price": {
                "current": current_price,
                "highest": highest_price,
                "lowest": lowest_price,
                "trend_window": "7 days",
                "history": [
                    {"ts": p['ts'], "price": p['price']}
                    for p in price_history[-7:]  # Last 7 days
                ]
            },
            "mrp": {
                "site_mrp": site_mrp,
                "fair_mrp": fair_mrp,
                "inflation_pct": round(inflation_pct, 1) if inflation_pct else 0,
                "note": "Fair MRP is median price across trusted sellers"
            },
            "timer_analysis": timer_analysis,
            "meta": {
                "scraped_at": datetime.now().isoformat(),
                "source": scraper_result.get('domain', 'unknown'),
                "notes": "scraped with selenium"
            }
        }

        # Update job as done
        db.update_job(job_id, 'done', result_json=result)

        return jsonify(result), 200

    except Exception as e:
        db.update_job(job_id, 'failed', error_message=str(e))
        return jsonify({
            "error": "analysis_failed",
            "message": f"Analysis failed: {str(e)}",
            "job_id": job_id
        }), 500

    finally:
        if scraper:
            scraper.close()


@app.route('/history', methods=['GET'])
def get_history():
    """
    Get price history for a URL
    GET /history?url=https://...
    """
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "url_required", "message": "URL parameter required"}), 400

    limit = int(request.args.get('limit', 30))
    history = db.get_price_history(url, limit=limit)

    return jsonify({
        "url": url,
        "history": [
            {"ts": p['ts'], "price": p['price']}
            for p in history
        ]
    }), 200


@app.route('/job/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """
    Get job status and result
    GET /job/{job_id}
    """
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "job_not_found", "message": f"Job {job_id} not found"}), 404

    response = {
        "id": job['id'],
        "url": job['url'],
        "status": job['status'],
        "created_at": job['created_at'],
        "finished_at": job['finished_at'],
    }

    if job['status'] == 'done' and job['result']:
        response['result'] = job['result']
    elif job['status'] == 'failed' and job['error_message']:
        response['error'] = job['error_message']

    return jsonify(response), 200


# Serve static files (optional - for development)
@app.route('/')
def index():
    from flask import send_from_directory
    import os
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    return send_from_directory(frontend_path, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    from flask import send_from_directory
    import os
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    return send_from_directory(frontend_path, filename)


if __name__ == '__main__':
    print("Starting ClearBuy backend server...")
    print("Make sure chromedriver is installed and in PATH")
    print("Server running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
