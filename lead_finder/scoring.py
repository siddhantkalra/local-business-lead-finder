from typing import Dict, Tuple, Any


def score_lead(lead: Dict[str, Any], scoring_cfg: Dict[str, Any]) -> Tuple[int, str]:
    high_max = int(scoring_cfg.get("high_opportunity_reviews_max", 20))
    mature_min = int(scoring_cfg.get("mature_reviews_min", 100))

    reviews = lead.get("review_count") or 0
    has_website = bool(lead.get("website"))

    reasons = []
    score = 5

    # ── Website signals ──────────────────────────────────────────────────────
    if not has_website:
        reasons.append("No website listed")
        score = 10 if reviews < 10 else 9
    else:
        if not lead.get("website_reachable"):
            reasons.append("Website unreachable/broken")
            score += 3
        if not lead.get("website_https"):
            reasons.append("No HTTPS")
            score += 1
        if not lead.get("website_has_viewport"):
            reasons.append("Not mobile-friendly")
            score += 1
        if not lead.get("website_booking_detected"):
            reasons.append("No booking/contact CTA")
            score += 1
        if lead.get("website_slow"):
            reasons.append("Slow website (>4s load)")
            score += 1

    # ── GBP signals ───────────────────────────────────────────────────────────
    if not lead.get("gbp_has_hours"):
        reasons.append("GBP: no hours set")
        score += 2
    if lead.get("gbp_photo_count", 0) == 0:
        reasons.append("GBP: no photos")
        score += 2
    elif lead.get("gbp_photo_count", 0) < 3:
        reasons.append("GBP: very few photos")
        score += 1
    if not lead.get("gbp_has_description"):
        reasons.append("GBP: no business description")
        score += 1
    if not lead.get("phone"):
        reasons.append("GBP: no phone number listed")
        score += 1

    # ── Review volume signals ─────────────────────────────────────────────────
    if reviews <= 0:
        reasons.append("No reviews")
        score += 1
    elif reviews <= high_max:
        reasons.append(f"Low review count ({reviews})")
        score += 1
    elif reviews >= mature_min:
        reasons.append(f"Mature listing ({reviews} reviews)")
        score -= 2

    score = max(1, min(10, score))

    if not reasons:
        reasons = ["Average opportunity"]

    return score, "; ".join(reasons)


def make_outreach_opener(lead: Dict[str, Any]) -> str:
    name = (lead.get("business_name") or "your business").strip()
    has_website = bool(lead.get("website") and lead.get("website_reachable"))
    poor_gbp = not lead.get("gbp_has_hours") or lead.get("gbp_photo_count", 0) < 3

    if not has_website and poor_gbp:
        return (
            f"Hi — I came across {name} on Google Maps. "
            "I noticed there's no website and the Google Business profile looks like it could use some attention. "
            "I help local businesses get a proper online presence — website, optimized Google listing, and a way for customers to reach you easily."
        )
    elif not has_website:
        return (
            f"Hi — I found {name} while searching locally. "
            "I noticed there's no website yet. "
            "I build simple, affordable websites for local businesses so customers can find and contact you online."
        )
    elif poor_gbp:
        return (
            f"Hi — I came across {name} on Google Maps. "
            "I noticed your Google Business Profile could be stronger — missing hours or photos can cost you customers. "
            "I help local businesses optimize their Google presence to show up better in local searches."
        )
    else:
        return (
            f"Hi — I came across {name} while searching locally. "
            "I noticed there may be some room to improve your online booking and contact flow. "
            "I help local businesses make it easier for customers to reach them online."
        )
