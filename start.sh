#!/bin/bash
# Lead Finder — start script
# Run this once to launch the web app. Keep the terminal window open.

set -e
cd "$(dirname "$0")"

echo "──────────────────────────────────────"
echo "  Lead Finder"
echo "──────────────────────────────────────"

# Activate venv
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
  echo "✓ Virtual environment activated"
else
  echo "✗ No .venv found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# Install/update dependencies silently
pip install fastapi "uvicorn[standard]" --quiet

# Check API key
if grep -q "your_real_api_key" .env 2>/dev/null; then
  echo "⚠  Warning: GOOGLE_PLACES_API_KEY looks like a placeholder in .env"
fi

echo "✓ Starting server at http://localhost:8000"
echo "  Press Ctrl+C to stop."
echo "──────────────────────────────────────"

# Open browser after short delay
(sleep 1.5 && open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null || true) &

exec uvicorn app:app --host 127.0.0.1 --port 8000
