import requests
import time
import csv
import os

API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
BASE_URL = "https://api.apify.com/v2"

# ---- EDIT THESE TWO LINES ----
CITIES = ["Derby", "Leicester", "Sheffield"]
NICHES = ["plumbers", "builders", "cleaners", "restaurants", "takeaways"]
# -------------------------------

OUTPUT_PATH = os.path.expanduser("~/Desktop/uk_businesses.csv")

NO_REAL_WEBSITE_PATTERNS = [
    "google.com/maps", "facebook.com", "instagram.com", "tiktok.com",
    "twitter.com", "business.site", "booksy.com", "fresha.com",
    "setmore.com", "nearcut.com", "6map.top",
]


def has_real_website(url):
    if not url:
        return False
    u = url.lower()
    return not any(p in u for p in NO_REAL_WEBSITE_PATTERNS)


def run_scraper(search_query, location):
    actor_id = "compass~crawler-google-places"
    url = f"{BASE_URL}/acts/{actor_id}/runs"
    payload = {
        "searchStringsArray": [search_query],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": 80,
        "language": "en",
        "countryCode": "gb",
    }
    params = {"token": API_TOKEN}
    print(f"Scraping: {search_query} in {location}")
    resp = requests.post(url, json=payload, params=params)
    resp.raise_for_status()
    run = resp.json()["data"]
    run_id = run["id"]

    while True:
        s = requests.get(f"{BASE_URL}/actor-runs/{run_id}", params=params).json()["data"]["status"]
        if s in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        time.sleep(10)
    if s != "SUCCEEDED":
        print(f"  Failed: {s}")
        return []
    items = requests.get(f"{BASE_URL}/datasets/{run['defaultDatasetId']}/items",
                         params={"token": API_TOKEN, "format": "json"}).json()
    return items


def main():
    if not API_TOKEN:
        print("Set APIFY_API_TOKEN first:  export APIFY_API_TOKEN='your_token'")
        return

    rows = []
    for city in CITIES:
        for niche in NICHES:
            try:
                items = run_scraper(f"{niche} in {city}", city)
                print(f"  {len(items)} results")
                for it in items:
                    website = it.get("website") or ""
                    phone = it.get("phone") or it.get("phoneUnformatted") or "N/A"
                    priority = "" if has_real_website(website) else "PRIORITY"
                    rows.append({
                        "Business Name": it.get("title", "N/A"),
                        "Phone Number": phone,
                        "Website": website if website else "None",
                        "Address": it.get("address", "N/A"),
                        "Category": niche.title(),
                        "City": city,
                        "Priority": priority,
                    })
            except Exception as e:
                print(f"  Error: {e}")

    rows.sort(key=lambda r: (0 if r["Priority"] == "PRIORITY" else 1, r["City"], r["Category"]))
    fields = ["Business Name", "Phone Number", "Website", "Address", "Category", "City", "Priority"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    pri = sum(1 for r in rows if r["Priority"] == "PRIORITY")
    print(f"\nDone! {len(rows)} businesses, {pri} PRIORITY (no website)")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
