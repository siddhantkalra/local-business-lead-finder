import os
import math
from typing import Dict, Generator, List, Optional, Any
import requests

from .utils import jitter_sleep


class PlacesClient:
    """Google Places API (New) client."""

    TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
    DETAILS_BASE_URL = "https://places.googleapis.com/v1/places"

    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("Missing GOOGLE_PLACES_API_KEY")
        self.session = session or requests.Session()

    def _post_text_search(self, payload: Dict[str, Any], field_mask: str) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }
        r = self.session.post(self.TEXT_SEARCH_URL, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()

    def _get_place(self, place_id: str, field_mask: str) -> Dict[str, Any]:
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }
        url = f"{self.DETAILS_BASE_URL}/{place_id}"
        r = self.session.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()

    def get_city_center(self, city_query: str) -> Optional[Dict[str, float]]:
        payload = {"textQuery": city_query, "maxResultCount": 1}
        data = self._post_text_search(payload, "places.location")
        places = data.get("places", [])
        if not places:
            return None
        loc = places[0].get("location", {})
        lat, lng = loc.get("latitude"), loc.get("longitude")
        if lat is None or lng is None:
            return None
        return {"lat": float(lat), "lng": float(lng)}

    @staticmethod
    def grid_points(
        center_lat: float,
        center_lng: float,
        span_km: float,
        step_km: float,
    ) -> List[Dict[str, float]]:
        """Generate a regular grid of lat/lng points covering a square area.

        span_km  — half-width of the area to cover (e.g. 20 → 40×40 km box)
        step_km  — distance between adjacent grid points
        """
        # 1 degree lat ≈ 111 km everywhere
        # 1 degree lng ≈ 111 km × cos(lat)
        lat_step = step_km / 111.0
        lng_step = step_km / (111.0 * math.cos(math.radians(center_lat)))

        steps = math.ceil(span_km / step_km)
        points = []
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                points.append({
                    "lat": center_lat + i * lat_step,
                    "lng": center_lng + j * lng_step,
                })
        return points

    def nearby_search(
        self,
        *,
        lat: float,
        lng: float,
        radius_km: float,
        keyword: str,
    ) -> Generator[Dict[str, Any], None, None]:
        payload = {
            "textQuery": keyword,
            "maxResultCount": 20,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_km * 1000,
                }
            },
        }
        field_mask = "places.id,places.displayName,places.formattedAddress,places.location"
        data = self._post_text_search(payload, field_mask)

        for item in data.get("places", []):
            place_id = item.get("id")
            if place_id:
                yield {
                    "place_id": place_id,
                    "name": item.get("displayName", {}).get("text"),
                    "formatted_address": item.get("formattedAddress"),
                }
            jitter_sleep(0.05, 0.05)

    def place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        field_mask = (
            "id,displayName,formattedAddress,nationalPhoneNumber,internationalPhoneNumber,"
            "websiteUri,googleMapsUri,rating,userRatingCount,priceLevel,types,"
            "regularOpeningHours,photos,editorialSummary,businessStatus"
        )
        data = self._get_place(place_id, field_mask)
        if not data:
            return None

        return {
            "name": data.get("displayName", {}).get("text"),
            "formatted_address": data.get("formattedAddress"),
            "vicinity": data.get("formattedAddress"),
            "formatted_phone_number": data.get("nationalPhoneNumber"),
            "international_phone_number": data.get("internationalPhoneNumber"),
            "website": data.get("websiteUri"),
            "url": data.get("googleMapsUri"),
            "rating": data.get("rating"),
            "user_ratings_total": data.get("userRatingCount"),
            "price_level": data.get("priceLevel"),
            "types": data.get("types", []),
            # GBP signals
            "has_hours": bool(data.get("regularOpeningHours")),
            "photo_count": len(data.get("photos", [])),
            "has_description": bool(data.get("editorialSummary", {}).get("text")),
            "business_status": data.get("businessStatus", "OPERATIONAL"),
        }
