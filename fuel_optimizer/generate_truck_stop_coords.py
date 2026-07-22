import csv
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(Path(r"C:\Users\Fazz Com 03364446969\Desktop\Assessment\fuel_optimizer\.env"))

api_key = os.getenv("ROUTING_API_KEY", "")
source_path = Path(r"C:\Users\Fazz Com 03364446969\Desktop\Assessment\fuel_optimizer\routing\data\truck_stops.csv")
out_path = Path(r"C:\Users\Fazz Com 03364446969\Desktop\Assessment\fuel_optimizer\routing\data\truck_stops_with_coordinates.csv")

if not api_key:
    raise SystemExit("ROUTING_API_KEY missing")


def build_query(row):
    address = (row.get("Address") or "").strip()
    city = (row.get("City") or "").strip()
    state = (row.get("State") or "").strip()
    return " ".join(part for part in [address, city, state] if part).strip()


def has_coordinates(row):
    return bool((row.get("latitude") or "").strip() and (row.get("longitude") or "").strip())


def geocode(query, max_retries=8):
    url = f"https://api.geoapify.com/v1/geocode/search?text={quote(query)}&apiKey={api_key}&limit=1"
    payload = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.ConnectionError, requests.Timeout) as exc:
            wait = min(2 ** attempt, 30)
            if attempt == max_retries - 1:
                raise exc
            print(f"Network error, retrying in {wait}s ({attempt + 1}/{max_retries})...")
            time.sleep(wait)
        except requests.HTTPError:
            if response.status_code == 429 and attempt < max_retries - 1:
                wait = min(2 ** (attempt + 1), 30)
                print(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise

    if payload is None:
        return "", ""

    features = payload.get("features", [])
    if not features:
        return "", ""

    props = features[0].get("properties", {})
    lat = props.get("lat")
    lon = props.get("lon")
    return (lat if lat is not None else "", lon if lon is not None else "")


def write_output(fieldnames, output_rows):
    with out_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)


with source_path.open(newline="", encoding="utf-8") as infile:
    rows = list(csv.DictReader(infile))

existing_rows = []
if out_path.exists():
    with out_path.open(newline="", encoding="utf-8") as infile:
        existing_rows = list(csv.DictReader(infile))

fieldnames = list(rows[0].keys()) + ["latitude", "longitude"] if rows else ["latitude", "longitude"]
output_rows = []
geocoded_count = 0
skipped_count = 0

for index, row in enumerate(rows, start=1):
    base_row = {key: row.get(key, "") for key in rows[0].keys()}

    if index <= len(existing_rows) and has_coordinates(existing_rows[index - 1]):
        enriched = {**base_row, "latitude": existing_rows[index - 1]["latitude"], "longitude": existing_rows[index - 1]["longitude"]}
        output_rows.append(enriched)
        skipped_count += 1
        continue

    query = build_query(row)
    try:
        latitude, longitude = geocode(query)
        if not latitude or not longitude:
            city = (row.get("City") or "").strip()
            state = (row.get("State") or "").strip()
            fallback_query = ", ".join(part for part in [city, state] if part)
            if fallback_query:
                latitude, longitude = geocode(fallback_query)
    except requests.RequestException as exc:
        write_output(fieldnames, output_rows)
        print(f"Failed at row {index}: {exc}")
        raise SystemExit(1) from exc

    enriched = {**base_row, "latitude": latitude, "longitude": longitude}
    output_rows.append(enriched)
    geocoded_count += 1
    print(f"{index}/{len(rows)} {query} -> {latitude},{longitude}")

    if geocoded_count % 10 == 0:
        write_output(fieldnames, output_rows)

    time.sleep(0.2)

write_output(fieldnames, output_rows)
print(f"Skipped {skipped_count} rows with existing coordinates")
print(f"Geocoded {geocoded_count} rows")
print(f"Wrote {len(output_rows)} rows to {out_path}")
