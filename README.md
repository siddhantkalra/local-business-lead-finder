# Local Business Lead Finder

A FastAPI-powered tool for finding and scoring local business leads. Point it at a city and industry, and it surfaces prospects with website status checks, contact signals, and a relevance score — ready to export.

---

## What It Does

- Searches for local businesses by category and location
- Checks each result for website presence, quality signals, and contact info gaps
- Scores leads by opportunity (businesses with weak or missing web presence = higher priority)
- Streams results live to the dashboard as they're found
- Exports the full list as CSV

Built originally to find leads for a local web services business — businesses that needed a website or had an outdated one.

---

## Stack

- **Backend**: Python / FastAPI with streaming responses (`StreamingResponse`)
- **Lead discovery**: Google Places API
- **Website checks**: `httpx` async requests
- **Frontend**: Vanilla JS — live log stream, sortable results table
- **Config**: `config.yaml` for search targets (city, categories, radius)

---

## Local Setup

```bash
# 1. Clone and install
git clone https://github.com/siddhantkalra/local-business-lead-finder.git
cd local-business-lead-finder
pip install -r requirements.txt

# 2. Add your API key
cp .env.example .env
# edit .env: GOOGLE_PLACES_API_KEY=your_key_here

# 3. Configure your search
# edit config.yaml: set city, categories, search radius

# 4. Run
python app.py
# or
./start.sh
```

Open [http://localhost:8000](http://localhost:8000).

---

## Project Structure

```
local-business-lead-finder/
├── app.py                    # FastAPI app + frontend
├── main.py                   # Entry point
├── config.yaml               # Search configuration
├── lead_finder/
│   ├── places.py             # Google Places API integration
│   ├── website_checks.py     # Website presence + quality checks
│   ├── scoring.py            # Lead scoring logic
│   ├── export.py             # CSV export
│   └── utils.py              # Shared utilities
├── static/
│   └── index.html            # Dashboard UI
├── requirements.txt
└── start.sh
```

---

## Output

Each lead includes: business name, address, phone, website URL, website status (live / missing / broken), and a numeric opportunity score. Export to CSV with one click.
