# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common commands

All commands are intended to be run from the project root (`CLARX/CLARX`).

### Environment setup

- Create virtualenv (optional but recommended):
  - Windows (PowerShell): `python -m venv venv; .\venv\Scripts\Activate.ps1`
  - macOS/Linux (bash): `python -m venv venv && source venv/bin/activate`
- Install backend dependencies (preferred): `cd backend && pip install -r requirements.txt`
- Alternative (root) dependencies: `pip install -r requirements.txt` (includes overlapping libs for scraping/backend work).

### Run the backend API

- Directly via Flask app:
  - From project root: `cd backend && python app.py`
  - Or use helper scripts from project root:
    - Windows: `start.bat`
    - macOS/Linux: `./start.sh`
- The API listens on `http://127.0.0.1:5000` by default (see `backend/app.py`).

### Initialize/inspect databases

There are two SQLite databases used in different parts of the code:

- Price history DB used by `PriceTracker` (current `/analyze` implementation):
  - File: `backend/database/price_history.sqlite`
  - Schema: `backend/database/schema.sql`.
- Legacy/general DB used by `models.Database` (job-based API that is not currently wired into `app.py`):
  - File: `clarx.db` (created by `Database` in `backend/models.py` when run in that working directory).

Useful commands:

- Initialize the legacy `clarx.db` schema (if you use the `Database` class):
  - From `backend/`: `python db_init.py`
- Inspect a SQLite DB (example on Unix): `sqlite3 backend/database/price_history.sqlite`.

### Manual API testing

From the project root, with backend running on `http://127.0.0.1:5000`:

- Basic health check:
  - `curl http://127.0.0.1:5000/test`
- Analyze a product URL (replace with a real product page):
  - `curl -X POST http://127.0.0.1:5000/analyze -H "Content-Type: application/json" -d '{"url": "https://www.flipkart.com/example-product"}'`
- Price-history debug endpoints (exercise `PriceTracker`):
  - Save a price sample:
    - `curl -X POST http://127.0.0.1:5000/test/save_price -H "Content-Type: application/json" -d '{"url": "https://www.flipkart.com/example-product", "price": 1499, "mrp": 2999}'`
  - Fetch history for that URL:
    - `curl -X POST http://127.0.0.1:5000/test/get_history -H "Content-Type: application/json" -d '{"url": "https://www.flipkart.com/example-product"}'`

### Frontend usage

No build step is required for the frontend; it is static HTML/CSS/JS.

- After the backend is running, open `frontend/index.html` directly in a browser.
- The landing page script (`frontend/js/index.js`) POSTs to `http://127.0.0.1:5000/analyze`, stores the response in `localStorage`, and navigates to `frontend/results.html`.
- `frontend/js/results.js` reads the stored `detections` object (or falls back to `?url=` in the query string) and renders charts and dark-pattern cards.

### Ad-hoc/diagnostic scripts

- `backend/test_price_tracker.py` is a small script intended to exercise the price history flow. It is currently out of sync with the module name (`PriceTracker` lives in `backend/price_tracker/track_price.py`), so running it may require fixing the import before use.

## High-level architecture

### Overall flow

- This is a small full-stack app that analyzes e-commerce product pages for dark patterns.
- The typical user flow is:
  1. User opens `frontend/index.html` and enters a product URL.
  2. Frontend POSTs `{ "url": "..." }` to `/analyze` on the Flask backend.
  3. Backend scrapes the page with Selenium, extracts price/MRP, runs several rule-based detectors, and persists price history.
  4. Backend responds with a `detections` object that includes detector outputs, price info, and price history.
  5. Frontend stores the result and `results.html` visualizes trust grade, violations, and price history.

### Backend structure

Key modules under `backend/`:

- `app.py`
  - Entrypoint for the Flask app.
  - Enables CORS globally (for local file-based frontend access).
  - Creates a single `PriceTracker` instance for DB access.
  - Routes:
    - `GET /test` — simple health check.
    - `POST /scrape` — low-level HTML fetch diagnostic, returning only the HTML length.
    - `POST /test/save_price` and `POST /test/get_history` — direct price-history debug endpoints that wrap `PriceTracker.save_price` and `.get_history`.
    - `POST /analyze` — main analysis endpoint:
      - Validates JSON body and `url` field.
      - Calls `backend.scraper.html_fetcher.fetch_html(url)` to get raw HTML via Selenium.
      - Calls `backend.scraper.price_extractor.extract_price_and_mrp(html)` to derive `(price, mrp)`.
      - Uses `PriceTracker` to persist the price and fetch historical data from `backend/database/price_history.sqlite`.
      - Calls `backend.detectors.run_all.run_all_detectors(html, url=url)` to run rule-based detectors.
      - Augments the `detections` dict with `price_info` and `price_history` and returns it as JSON.
  - On direct execution, runs the dev server on `0.0.0.0:5000` with debug enabled.

- `scraper/` (current Selenium-based HTML and signal acquisition)
  - `selenium_driver.py` — minimal helper that spins up a headless Chrome `webdriver`, loads a URL, sleeps briefly, returns `page_source`, and quits.
  - `html_fetcher.py` — thin wrapper that exposes `fetch_html(url)` by delegating to `selenium_driver.get_page_source`.
  - `price_extractor.py` — regex-based parser that finds all `₹`-prefixed amounts in the HTML and heuristically interprets the first as current price and the second as MRP.
  - `timer_refresh_checker.py` — utility that calls `get_page_source` twice for the same URL and compares parsed timer strings to see if a countdown appears to reset between loads (used by the timer detector).
  - There is also a more advanced but currently unused `scraper.py` module that encapsulates scraping, price extraction, and timer analysis in a `Scraper` class. It represents an alternative design that is not wired into `app.py`.

- `detectors/` (rule-based detection of dark patterns)
  - `scarcity_detector.py` — scans raw HTML for scarcity-related keywords (e.g., "only", "left in stock", "limited stock"). Returns a dict with `detected`, `matches`, and a medium-confidence flag when patterns are found.
  - `timer_detector.py` — looks for timer/flash-sale wording and JS patterns; optionally uses `timer_refresh_checker.check_timer_reset(url)` to see if the timer resets on refresh; exposes a `fake_timer`-type detection with `flags` (e.g., `reset_on_refresh`, `frontend_only`, `missing_tnc`) and a confidence score.
  - `drip_pricing_detector.py` — searches for fee-related phrases (delivery, convenience, packaging fees) and `₹ X + ₹ Y` patterns indicating split pricing, plus generic "additional charges" terms.
  - `addon_detector.py` — regexes for warranty/insurance/add-on phrasing and the presence of checked checkboxes to detect pre-ticked upsells.
  - `run_all.py` — orchestrator that accepts raw HTML and optional `url`, runs each detector, and returns a dictionary like:
    - `{ "scarcity": {...}, "timer": {...}, "drip_pricing": {...}, "addons": {...} }`.

- `price_tracker/track_price.py`
  - Implements a lightweight `PriceTracker` around the `backend/database/price_history.sqlite` file.
  - Identifies products by an MD5 hash of the URL so repeated analysis of the same URL shares a `product_id`.
  - `save_price(url, price, mrp)` inserts into the `price_history` table and returns a small status payload.
  - `get_history(url)` returns `{ "product_id": ..., "history": [{"price", "mrp", "timestamp"}, ...] }` for use by `/analyze` and the debug endpoints.

- `models.py` and `db_init.py` (legacy/alternate job-based backend)
  - `models.Database` defines a different schema (`urls`, `prices`, `jobs`) stored in `clarx.db`, with helper methods for URL management, price history, and asynchronous job tracking.
  - `db_init.py` bootstraps this DB.
  - These are referenced heavily in `IMPLEMENTATION_NOTES.md` and describe a job-queue-based `/analyze` API that returns `job_id` and separate `/job/{job_id}` queries. The current `app.py` instead exposes a single synchronous `/analyze` endpoint.
  - When modifying the backend, be aware that there are effectively two designs in the tree: the current synchronous `PriceTracker` + detectors pipeline, and the older job-based `Database` design. Prefer the currently wired path in `app.py` unless you are explicitly reviving the job-based flow.

### Frontend structure

Key files under `frontend/`:

- `index.html` + `js/index.js`
  - Landing page where the user pastes a product URL.
  - `analyze()` reads the URL, does basic validation, disables the CTA, and POSTs to `http://127.0.0.1:5000/analyze`.
  - On success, it stores the raw JSON response under `localStorage["analysis_result"]` and redirects to `results.html`.

- `results.html` + `js/results.js`
  - On `DOMContentLoaded`, attempts to read `analysis_result` from `localStorage`; if not available, falls back to a `?url=` query-param-based call to the backend.
  - Normalizes both old and new backend payload shapes (direct `detections` vs. entire response) and then:
    - Computes a coarse-grained risk score from detector outputs and maps it to a trust grade (A–F).
    - Renders a set of violation cards based on scarcity/timer/add-on/drip-pricing detections and any explicit `violations` array returned by the backend.
    - Renders price statistics (current price, MRP, count of history points, last-timestamp) and a detailed history list from `price_history`.
    - Uses Chart.js to render a line chart of price over time in the `priceChart` canvas.
    - Visualizes timer-related findings, including confidence and detailed reasons or underlying flags.

- `css/index.css`, `css/results.css`
  - Styling for the two main pages, including cards, risk pill, and chart layout.

### External dependencies and environment nuances

- The backend relies on Chrome + ChromeDriver for Selenium. Ensure ChromeDriver is installed and on the PATH, or swap to a `webdriver-manager`-based setup as outlined in `README.md`.
- The frontend JS currently points explicitly at `http://127.0.0.1:5000` when running from local files; if you change the backend host/port or deploy behind a different origin, update `frontend/js/index.js` and, if necessary, the `API_BASE` logic in `frontend/js/results.js`.
- Rate limiting and other production-hardening mentioned in `README.md`/`IMPLEMENTATION_NOTES.md` are not fully wired into the current `app.py`; consider this when adding new endpoints or refactoring.
