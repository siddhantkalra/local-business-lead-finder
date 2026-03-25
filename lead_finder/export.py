import csv
from pathlib import Path
from typing import List, Dict, Any


COLUMNS = [
    "lead_score",
    "reason_for_targeting",
    "business_name",
    "category_query",
    "address",
    "phone",
    "website",
    "maps_url",
    "rating",
    "review_count",
    "price_level",
    "types",
    # Website signals
    "website_reachable",
    "website_https",
    "website_has_viewport",
    "website_booking_detected",
    "website_error",
    # GBP signals
    "gbp_has_hours",
    "gbp_photo_count",
    "gbp_has_description",
    # Outreach
    "outreach_opener",
]


def export_csv(leads: List[Dict[str, Any]], out_path: Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow({col: lead.get(col, "") for col in COLUMNS})
