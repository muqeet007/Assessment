import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.structures import CaseInsensitiveDict

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class RoutingService:
    """Routing service that uses Geoapify to return distance, duration, and geometry."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ROUTING_API_KEY", "")

    def _geocode(self, place):
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        encoded_place = requests.utils.quote(place)
        url = f"https://api.geoapify.com/v1/geocode/search?text={encoded_place}&apiKey={self.api_key}"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()

        features = payload.get("features", [])
        if not features:
            raise ValueError(f"No geocoding results for {place}")

        properties = features[0].get("properties", {})
        lat = properties.get("lat")
        lon = properties.get("lon")
        if lat is None or lon is None:
            raise ValueError(f"Missing coordinates for {place}")

        return f"{lat},{lon}"

    def get_route(self, start, destination):
        if not self.api_key:
            return {
                "distance": None,
                "duration": None,
                "geometry": None,
                "error": "Missing routing API key.",
            }

        try:
            start_point = self._geocode(start)
            destination_point = self._geocode(destination)
        except Exception as exc:
            return {
                "distance": None,
                "duration": None,
                "geometry": None,
                "error": str(exc),
            }

        url = (
            "https://api.geoapify.com/v1/routing?"
            f"waypoints={start_point}|{destination_point}&mode=drive&apiKey={self.api_key}"
        )

        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return {
                "distance": None,
                "duration": None,
                "geometry": None,
                "error": str(exc),
            }

        if not payload.get("features"):
            return {
                "distance": None,
                "duration": None,
                "geometry": None,
                "error": "No route found.",
            }

        feature = payload["features"][0]
        properties = feature.get("properties", {})
        return {
            "distance": properties.get("distance"),
            "duration": properties.get("time"),
            "geometry": feature.get("geometry"),
        }
