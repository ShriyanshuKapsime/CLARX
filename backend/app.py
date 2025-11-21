from flask import Flask, request
from scraper.html_fetcher import fetch_html
from detectors.run_all import run_all_detectors

app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test():
    return {"message": "Backend running successfully!"}

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json(silent=True)

    if not data or 'url' not in data:
        return {"error": "URL not provided"}, 400
    
    url = data['url']
    html = fetch_html(url)

    return {"length": len(html)}


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return {"error": "URL not provided"}, 400

    url = data["url"]
    html = fetch_html(url)

    detections = run_all_detectors(html, url=url)

    return {"detections": detections}

if __name__ == '__main__':
    app.run(debug=True)

