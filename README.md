**CLARX — Consumer Lens & Analysis for Retail eXposure**
A transparency tool that protects online shoppers from dark patterns, fake discounts, and MRP manipulation.
🚀 About the Project

CLARX is a consumer-protection web tool designed to identify manipulative tactics on e-commerce websites such as Amazon, Flipkart, Myntra, and others.

It analyzes any product link and reveals:

1. Fake discounts 
2. Hidden dark patterns
3. Price authenticity
4. Scarcity tricks (“Only 1 left!”)
5. Suspicious timers / urgency triggers
And more.

The goal is simple:
👉 Empower consumers to make smarter, transparent buying decisions.

⚠️ Why CLARX? — The Problem

In 2023, the Government of India officially banned "dark patterns" used by online retailers to manipulate buyers.

But…

--> Fake “Hurry! Only 2 left!” messages

--> Inflated MRP tricking users

--> False timers resetting on every refresh

--> Misleading discount percentages

--> Hidden charges

…are still commonly found on major shopping sites.

Most consumers do not notice these patterns, leading to overspending and misinformed buying decisions.

There is no simple tool to automatically check whether a product page is genuine or manipulative.

✅ Our Solution

CLARX acts as your shopping truth detector.

Paste any product link → CLARX analyzes the entire webpage and returns a clear, readable explanation of all manipulative patterns found.

🧠 What CLARX Analyzes
✔ Dark Pattern Detection

Fake scarcity (“Only 1 left!”)

Suspicious countdown timers

Pre-ticked add-ons

Drip pricing (hidden fees revealed later)

✔ MRP Authenticity Checker

Detects inflated MRPs

Estimates real MRP using price logic

Fetches structured data (JSON-LD) when available

Compares discounts with realistic market norms

✔ Price Extraction

Accurate selling price extraction

Accurate MRP extraction

Supports Amazon, Flipkart, Myntra

Cross-checks multiple selectors

✔ Easy-to-Read UI

Trust grade (A–F)

Color-coded risk meter

Detailed breakdown of violations

Price authenticity card

User-friendly explanations

🏗️ Tech Stack
Frontend

HTML, CSS, JavaScript

Lucide Icons

Chart.js

Responsive UI components

Backend

Python

Flask

BeautifulSoup (HTML parsing)

Regex-based heuristic detectors

SQLite for price logs

CORS enabled

Architecture
Frontend (HTML/CSS/JS)
        ↓ sends URL
Backend (Flask API)
        ↓ fetches HTML
Scraper → Detectors → MRP Checker
        ↓ returns JSON
Frontend renders results

📦 Features
Feature	Description
🔍 Dark Pattern Scanner	Detects fake scarcity, timers, add-ons, hidden fees
🧠 Trust Score	A–F grade with risk color indicators
💰 Price Checker	Extracts selling price & MRP accurately
⚖️ MRP Authenticity	Checks if MRP is inflated or manipulated
📊 Result Dashboard	Clean UI with cards, colors, explanations
💾 Local Result Storage	Displays last analysis instantly
🌐 Works Across Sites	Amazon, Flipkart, Myntra support
🖼️ Screenshots

(Add your images here if needed.)
Example sections:

Home Page

Result Page

Violation Cards

Price & MRP section

🧪 How to Run Locally
1. Clone repo
git clone https://github.com/yourusername/CLARX.git
cd CLARX

2. Setup backend
cd backend
pip install -r requirements.txt
python app.py


Backend runs at:
➡️ http://127.0.0.1:5000

3. Run frontend

Open the frontend/index.html directly or use Live Server.

📜 API Endpoints
Endpoint	Method	Description
/analyze	POST	Analyzes a product page
/test	GET	Checks if backend is running
/scrape	POST	Returns raw HTML length
/test/get_history	POST	(optional) Retrieves price logs
📌 Output Format (JSON)
{
  "detections": {
    "scarcity": {...},
    "timer": {...},
    "addons": {...},
    "drip_pricing": {...},
    "price_info": {
      "price": 799,
      "mrp": 1499
    },
    "mrp_authenticity": {...}
  }
}

🧩 Future Enhancements

Browser extension for real-time warnings

Multisite comparison feature

AI-based text classifier for fake scarcity

Better official MRP detection

User history dashboard

🛡️ Disclaimer

CLARX analyzes publicly available data for educational and research purposes.
We are not affiliated with any e-commerce platform.

👨‍💻 Team

Built with passion by
**Team — Protostars**
