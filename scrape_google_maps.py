import requests
import time
import csv
import os
import json

API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
BASE_URL = "https://api.apify.com/v2"

NICHES = ["restaurants", "builders", "beauty salons", "barbers", "takeaways", "plumbers", "cleaners"]
LOCATION = "Nottingham"

OUTPUT_PATH = os.path.expanduser("~/Desktop/nottingham_businesses.csv")


def run_scraper(search_query):
    """Run the Apify Google Maps Scraper actor for a given query."""
    actor_id = "compass~crawler-google-places"
    url = f"{BASE_URL}/acts/{actor_id}/runs"

    payload = {
        "searchStringsArray": [search_query],
        "locationQuery": LOCATION,
        "maxCrawledPlacesPerSearch": 100,
        "language": "en",
        "countryCode": "gb",
    }

    headers = {"Content-Type": "application/json"}
    params = {"token": API_TOKEN}

    print(f"Starting scrape for: {search_query}")
    resp = requests.post(url, json=payload, headers=headers, params=params)
    resp.raise_for_status()
    run_data = resp.json()["data"]
    run_id = run_data["id"]
    print(f"  Run ID: {run_id}")

    # Poll until finished
    while True:
        status_resp = requests.get(f"{BASE_URL}/actor-runs/{run_id}", params={"token": API_TOKEN})
        status_resp.raise_for_status()
        status = status_resp.json()["data"]["status"]
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        print(f"  Status: {status}, waiting...")
        time.sleep(10)

    if status != "SUCCEEDED":
        print(f"  Run failed with status: {status}")
        return []

    # Fetch results from default dataset
    dataset_id = run_data["defaultDatasetId"]
    items_resp = requests.get(
        f"{BASE_URL}/datasets/{dataset_id}/items",
        params={"token": API_TOKEN, "format": "json"},
    )
    items_resp.raise_for_status()
    return items_resp.json()


def extract_fields(items, category):
    """Extract relevant fields from raw Apify results."""
    rows = []
    for item in items:
        website = item.get("website") or item.get("url") or None
        website_display = website if website else "None"

        # Flag as PRIORITY if no website
        priority = "" if website else "PRIORITY"

        rows.append({
            "Business Name": item.get("title") or item.get("name", "N/A"),
            "Phone Number": item.get("phone") or item.get("phoneUnformatted") or "N/A",
            "Website": website_display,
            "Address": item.get("address") or item.get("street") or "N/A",
            "Category": category,
            "Priority": priority,
        })
    return rows


def main():
    if not API_TOKEN:
        print("Error: Set APIFY_API_TOKEN environment variable.")
        print("  export APIFY_API_TOKEN='your_apify_api_token_here'")
        return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    all_rows = []

    for niche in NICHES:
        query = f"{niche} in {LOCATION}"
        try:
            items = run_scraper(query)
            print(f"  Got {len(items)} results for {niche}")
            rows = extract_fields(items, niche.title())
            all_rows.extend(rows)
        except Exception as e:
            print(f"  Error scraping {niche}: {e}")

    # Sort so PRIORITY rows come first
    all_rows.sort(key=lambda r: (0 if r["Priority"] == "PRIORITY" else 1, r["Category"]))

    # Write CSV
    fieldnames = ["Business Name", "Phone Number", "Website", "Address", "Category", "Priority"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    total = len(all_rows)
    priority_count = sum(1 for r in all_rows if r["Priority"] == "PRIORITY")
    print(f"\nDone! Wrote {total} businesses to {OUTPUT_PATH}")
    print(f"{priority_count} flagged as PRIORITY (no website)")


if __name__ == "__main__":
    main()
