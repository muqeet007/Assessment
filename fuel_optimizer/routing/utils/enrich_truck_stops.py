import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routing.services.routing_service import RoutingService


BASE_DIR = ROOT / "routing"
INPUT_PATH = BASE_DIR / "data" / "truck_stops.csv"
OUTPUT_PATH = BASE_DIR / "data" / "truck_stops_with_coordinates.csv"


def build_query(row):
    parts = [
        row.get("Address", "").strip(),
        row.get("City", "").strip(),
        row.get("State", "").strip(),
    ]
    query = ", ".join(part for part in parts if part)
    return query or row.get("City", "").strip() or row.get("State", "").strip()


def geocode_point(service, query):
    if not query:
        return "", ""

    try:
        coord = service._geocode(query)
        lat_str, lon_str = coord.split(",", 1)
        return lat_str.strip(), lon_str.strip()
    except Exception:
        return "", ""


def enrich_truck_stops():
    service = RoutingService()

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as infile:
        rows = list(csv.DictReader(infile))

    fieldnames = list(rows[0].keys()) if rows else []
    fieldnames.extend(["latitude", "longitude"])

    enriched_rows = []
    for index, row in enumerate(rows, start=1):
        query = build_query(row)
        latitude, longitude = geocode_point(service, query)
        if not latitude or not longitude:
            fallback_query = f"{row.get('City','').strip()}, {row.get('State','').strip()}"
            latitude, longitude = geocode_point(service, fallback_query)

        enriched_rows.append({**row, "latitude": latitude, "longitude": longitude})
        if index % 25 == 0:
            time.sleep(0.2)

    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"Wrote {len(enriched_rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    enrich_truck_stops()
