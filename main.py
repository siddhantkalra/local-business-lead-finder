import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv

from lead_finder.places import PlacesClient
from lead_finder.website_checks import analyze_website
from lead_finder.scoring import score_lead, make_outreach_opener
from lead_finder.export import export_csv


def run(config_path: str, out_dir: str) -> None:
    load_dotenv()

    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    city = cfg["city"]
    categories = cfg.get("categories", [])

    radius_km = float(cfg.get("radius_km", 20))

    checks_cfg = cfg.get("website_checks", {})
    scoring_cfg = cfg.get("scoring", {})
    min_score = int(cfg.get("min_lead_score", 6))

    places = PlacesClient()

    center = places.get_city_center(city)
    if center is None:
        raise SystemExit(f"Could not resolve city center for: {city}")

    lat, lng = center["lat"], center["lng"]
    print(f"Searching near: {city} ({lat:.4f}, {lng:.4f}), radius {radius_km}km")
    print(f"{len(categories)} categories × 20 results = up to {len(categories) * 20} raw results")

    leads = []
    seen = set()

    for cat in categories:
        cat_count = 0
        for place in places.nearby_search(lat=lat, lng=lng, radius_km=radius_km, keyword=cat):
            place_id = place.get("place_id")
            if not place_id or place_id in seen:
                continue
            seen.add(place_id)

            details = places.place_details(place_id)
            if not details:
                continue

            if details.get("business_status") not in ("OPERATIONAL", None, ""):
                continue

            website = details.get("website")
            website_analysis = (
                analyze_website(
                    website_url=website,
                    timeout_s=int(checks_cfg.get("timeout_seconds", 8)),
                    user_agent=str(checks_cfg.get("user_agent", "LocalLeadFinder/1.0")),
                    booking_keywords=list(checks_cfg.get("booking_keywords", [])),
                )
                if website
                else None
            )

            lead = {
                "business_name": details.get("name"),
                "category_query": cat,
                "types": ",".join(details.get("types", [])) if isinstance(details.get("types"), list) else "",
                "address": details.get("formatted_address") or details.get("vicinity"),
                "phone": details.get("formatted_phone_number") or details.get("international_phone_number"),
                "website": website,
                "maps_url": details.get("url"),
                "rating": details.get("rating"),
                "review_count": details.get("user_ratings_total"),
                "price_level": details.get("price_level"),
                "gbp_has_hours": details.get("has_hours"),
                "gbp_photo_count": details.get("photo_count", 0),
                "gbp_has_description": details.get("has_description"),
            }

            if website_analysis:
                lead.update({
                    "website_reachable": website_analysis["reachable"],
                    "website_https": website_analysis["https"],
                    "website_has_viewport": website_analysis["has_viewport"],
                    "website_booking_detected": website_analysis["booking_detected"],
                    "website_error": website_analysis["error"],
                })
            else:
                lead.update({
                    "website_reachable": None,
                    "website_https": None,
                    "website_has_viewport": None,
                    "website_booking_detected": None,
                    "website_error": None,
                })

            score, reason = score_lead(lead, scoring_cfg)
            lead["lead_score"] = score
            lead["reason_for_targeting"] = reason
            lead["outreach_opener"] = (
                make_outreach_opener(lead)
                if score >= int(scoring_cfg.get("min_score_for_outreach_message", 7))
                else ""
            )

            leads.append(lead)
            cat_count += 1

        print(f"  [{cat}] {cat_count} unique businesses found")

    # Filter to only actionable leads
    actionable = [l for l in leads if l["lead_score"] >= min_score]
    actionable.sort(key=lambda l: l["lead_score"], reverse=True)

    export_csv(actionable, out_path / "digital_opportunity_leads.csv")
    print(f"\nTotal unique businesses scraped: {len(leads)}")
    print(f"Actionable leads (score >= {min_score}): {len(actionable)}")
    print(f"Output: {out_path / 'digital_opportunity_leads.csv'}")


def main():
    parser = argparse.ArgumentParser(description="Local business lead finder")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--out", required=True, help="Output folder")
    args = parser.parse_args()
    run(args.config, args.out)


if __name__ == "__main__":
    main()
