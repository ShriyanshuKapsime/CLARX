# Implementation Notes

## Files Created/Updated

### Backend Files

1. **backend/app.py** - Main Flask application
   - POST `/analyze` - Main analysis endpoint
   - GET `/history?url={url}` - Price history endpoint
   - GET `/job/{job_id}` - Job status endpoint
   - Rate limiting (5 requests per 60 seconds)
   - CORS enabled for frontend
   - Static file serving for development

2. **backend/models.py** - SQLite database models
   - `Database` class with methods for:
     - URL management
     - Price history storage
     - Job tracking
   - Tables: `urls`, `prices`, `jobs`

3. **backend/scraper.py** - Enhanced Selenium scraper
   - Headless Chrome scraping
   - Price extraction (site-specific + regex fallback)
   - Timer detection and analysis
   - Cloudflare/Access Denied detection
   - User-agent spoofing for bot detection avoidance

4. **backend/detector.py** - Dark pattern detection
   - `detect_fake_scarcity()` - Scarcity messaging detection
   - `detect_drip_pricing()` - Hidden fees detection
   - `detect_pre_ticked_addons()` - Pre-selected add-ons
   - `detect_confirm_shaming()` - Manipulative language
   - `calculate_trust_score()` - A-F grade calculation

5. **backend/db_init.py** - Database initialization helper

6. **backend/requirements.txt** - Updated dependencies

### Frontend Files

1. **frontend/index.html** - Landing page
   - URL input form
   - Redirects to results page with URL parameter

2. **frontend/2ndPage.html** - Results page (updated)
   - Integrated API calls
   - Dynamic UI updates:
     - Trust grade and risk pill
     - Dark pattern violations grid
     - Price statistics and chart
     - MRP analysis
     - Timer manipulation detection
   - Loading and error states

### Documentation

1. **README.md** - Comprehensive setup and usage guide
2. **IMPLEMENTATION_NOTES.md** - This file

### Scripts

1. **start.sh** - Linux/Mac startup script
2. **start.bat** - Windows startup script

## API Contract

### POST /analyze
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
  "violations": [
    {
      "type": "fake_scarcity",
      "title": "Fake Scarcity",
      "severity": "high",
      "confidence": "high",
      "explanation": "...",
      "snippet": ""
    }
  ],
  "price": {
    "current": 18499,
    "highest": 21999,
    "lowest": 17299,
    "trend_window": "7 days",
    "history": [
      {"ts": "2025-11-21T19:12:33+05:30", "price": 18499}
    ]
  },
  "mrp": {
    "site_mrp": 24999,
    "fair_mrp": 21200,
    "inflation_pct": 17.9,
    "note": "..."
  },
  "timer_analysis": {
    "present": true,
    "resets_on_refresh": true,
    "client_side_only": true,
    "fake_timer": true,
    "confidence": "high",
    "reasons": [...]
  },
  "meta": {...}
}
```

## Frontend-Backend Integration

### URL Flow
1. User enters URL on `index.html`
2. Form submits to `2ndPage.html?url={encoded_url}`
3. `2ndPage.html` reads URL parameter
4. Calls `POST /analyze` with URL
5. Updates UI with response data

### UI Update Functions
- `updateUI(result)` - Main update function
- `updateViolations(violations)` - Dark pattern cards
- `updatePriceStats(priceData)` - Price statistics
- `updatePriceChart(priceData)` - Chart.js update
- `updateMRPStats(mrpData)` - MRP analysis
- `updateTimerAnalysis(timerData)` - Timer detection

## Database Schema

### urls
- id (INTEGER PRIMARY KEY)
- url (TEXT UNIQUE)
- domain (TEXT)
- last_scraped_at (TIMESTAMP)
- created_at (TIMESTAMP)

### prices
- id (INTEGER PRIMARY KEY)
- url_id (INTEGER FOREIGN KEY)
- price (REAL)
- timestamp (TIMESTAMP)

### jobs
- id (INTEGER PRIMARY KEY)
- url (TEXT)
- status (TEXT) - pending/running/done/failed
- created_at (TIMESTAMP)
- finished_at (TIMESTAMP)
- result_json (TEXT)
- error_message (TEXT)

## Trust Score Calculation

Weights:
- Pre-ticked add-ons: 2
- Fake timer: 2
- Drip pricing: 1
- Fake scarcity: 1
- Confirm shaming: 1

Severity multipliers:
- High: 1.5x
- Medium: 1.0x
- Low: 0.5x

Grade mapping:
- 0 violations: A (Low Risk)
- ≤2 score: B (Moderate Risk)
- ≤4 score: C (High Manipulation)
- ≤6 score: D (High Manipulation)
- >6 score: F (Critical Manipulation)

## Error Handling

### Scraping Errors
- Cloudflare/Access Denied → 422 with `site_protected` error
- Scraping failure → 422 with error message
- Network errors → 500 with error details

### Rate Limiting
- 429 status code
- 5 requests per 60 seconds per IP

## Configuration Needed

1. **ChromeDriver**: Must be in PATH or use webdriver-manager
2. **Port**: Default 5000 (change in app.py if needed)
3. **API URL**: Auto-detected in frontend (localhost:5000 for local)

## Testing

### Manual Testing
```bash
# Test API
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.flipkart.com/example"}'

# Test health
curl http://localhost:5000/test
```

### Example URLs to Test
- Flipkart product pages
- Amazon.in product pages
- Myntra product pages

## Known Limitations

1. **MRP Calculation**: Currently simplified (85% of current price). In production, integrate with external price comparison APIs.

2. **Timer Detection**: Basic implementation. Could be enhanced with:
   - Multiple refresh cycles
   - Network request monitoring
   - JavaScript execution analysis

3. **Site-Specific Parsing**: Limited to Flipkart, Amazon, Myntra. Regex fallback for others.

4. **Bot Protection**: Some sites may block Selenium. Consider:
   - undetected-chromedriver
   - Proxy rotation
   - CAPTCHA solving services

## Future Enhancements

1. **Price Comparison APIs**: Integrate with external APIs for fair MRP calculation
2. **Review Analysis**: Detect review manipulation
3. **Image Analysis**: Detect fake product images
4. **Historical Data**: Longer price history tracking
5. **User Accounts**: Save analysis history per user
6. **Export Reports**: PDF/CSV export of analysis

## Deployment Checklist

- [ ] Install ChromeDriver on server
- [ ] Set environment variables if needed
- [ ] Configure CORS for production domain
- [ ] Set up database backups
- [ ] Configure rate limiting for production
- [ ] Add logging
- [ ] Set up monitoring
- [ ] Test with real product URLs
- [ ] Add error tracking (Sentry, etc.)

