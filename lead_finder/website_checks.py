import requests
from bs4 import BeautifulSoup
from typing import List


def analyze_website(
    website_url: str,
    timeout_s: int = 8,
    user_agent: str = "LocalLeadFinder/1.0",
    booking_keywords: List[str] = None,
) -> dict:
    if booking_keywords is None:
        booking_keywords = ["book", "appointment", "schedule", "reserve"]

    result = {
        "reachable": False,
        "https": website_url.startswith("https://") if website_url else False,
        "has_viewport": False,
        "booking_detected": False,
        "error": None,
    }

    try:
        headers = {"User-Agent": user_agent}
        r = requests.get(website_url, timeout=timeout_s, headers=headers)
        r.raise_for_status()
        result["reachable"] = True

        soup = BeautifulSoup(r.text, "html.parser")

        result["has_viewport"] = bool(
            soup.find("meta", attrs={"name": "viewport"})
        )

        text = soup.get_text().lower()
        result["booking_detected"] = any(kw.lower() in text for kw in booking_keywords)

    except requests.exceptions.RequestException as e:
        result["error"] = str(e)

    return result
