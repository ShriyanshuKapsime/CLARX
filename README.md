# ClearBuy / ClearCart / TruthLens

A full-stack web application that analyzes e-commerce product pages for dark patterns, fake discounts, price manipulation, and timer authenticity.

## Features

- **Dark Pattern Detection**: Identifies fake scarcity, drip pricing, fake timers, pre-ticked add-ons, and confirm shaming
- **Price Tracking**: Tracks price history and detects inflation
- **Timer Analysis**: Validates countdown timers for authenticity
- **Trust Score**: Generates A-F grade based on detected manipulations
- **Real-time Analysis**: Scrapes product pages using Selenium and provides instant results

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Database**: SQLite
- **Scraping**: Selenium WebDriver
- **Charts**: Chart.js

## Prerequisites

- Python 3.8+
- Chrome browser
- ChromeDriver (must be in PATH or install via webdriver-manager)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd CLARX
```

### 2. Create virtual environment

```bash
python -m venv venv
```

### 3. Activate virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 5. Install ChromeDriver

**Option A: Using webdriver-manager (Recommended)**
```bash
pip install webdriver-manager
```

Then update `backend/scraper.py` to use:
```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
```

**Option B: Manual installation**
1. Download ChromeDriver from https://chromedriver.chromium.org/
2. Extract and add to PATH
3. Or place in project root directory

## Running the Application

### 1. Start the backend server

```bash
cd backend
python app.py
```

The server will start on `http://localhost:5000`

### 2. Open the frontend

**Option A: Direct file access**
- Open `frontend/index.html` in your browser

**Option B: Using Flask static serving (Recommended)**
- Update `backend/app.py` to serve static files:
```python
from flask import send_from_directory

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)
```

Then access at `http://localhost:5000`

## Usage

1. Open the application in your browser
2. Paste a product URL from Flipkart, Amazon, Myntra, etc.
3. Click "Analyze Now"
4. View the analysis results including:
   - Trust Score (A-F grade)
   - Dark Pattern Violations
   - Price History and Trends
   - MRP Analysis
   - Timer Manipulation Detection

## API Endpoints

### POST /analyze
Analyze a product URL

**Request:**
```json
{
  "url": "https://www.flipkart.com/product-url"
}
```

**Response:**
```json
{
  "job_id": 1,
  "url": "...",
  "trust_grade": "B",
  "trust_summary": "Moderate Risk",
  "violations": [...],
  "price": {...},
  "mrp": {...},
  "timer_analysis": {...}
}
```

### GET /history?url={url}
Get price history for a URL

### GET /job/{job_id}
Get job status and result

## Project Structure

```
CLARX/
├── backend/
│   ├── app.py              # Flask application
│   ├── models.py           # Database models
│   ├── scraper.py          # Selenium scraper
│   ├── detector.py         # Dark pattern detectors
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Landing page
│   └── 2ndPage.html        # Results page
└── README.md
```

## Database

SQLite database (`clarx.db`) is automatically created on first run. It contains:

- **urls**: Product URLs and metadata
- **prices**: Price history records
- **jobs**: Analysis job tracking

## Configuration

### Rate Limiting
Default: 5 requests per 60 seconds per IP
Modify in `backend/app.py`:
```python
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 60
```

### Scraping Settings
Modify in `backend/scraper.py`:
```python
scraper = Scraper(headless=True, wait_time=3)
```

## Troubleshooting

### ChromeDriver not found
- Ensure ChromeDriver is in PATH
- Or use webdriver-manager (see Installation step 5)

### Cloudflare/Access Denied errors
- Some sites have bot protection
- Try different URLs or increase wait_time in scraper

### Port already in use
- Change port in `backend/app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
python backend/app.py
```

### Testing

Test the API:
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.flipkart.com/example-product"}'
```

## Security & Legal Notes

- This tool is for educational and consumer research purposes
- Scraping is user-initiated only (no background crawling)
- Respect robots.txt and terms of service
- Rate limiting is implemented to prevent abuse
- Data stored is limited to price history and analysis results

## Deployment

### Heroku

1. Create `Procfile`:
```
web: python backend/app.py
```

2. Add buildpack for Chrome:
```
heroku buildpacks:add heroku/google-chrome
heroku buildpacks:add heroku/chromedriver
```

3. Deploy:
```bash
git push heroku main
```

### Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "backend/app.py"]
```

## License

This project is for educational purposes.

## Support

For issues or questions, please open an issue on the repository.
