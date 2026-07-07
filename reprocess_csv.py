import csv
import os
import sys

NO_REAL_WEBSITE_PATTERNS = [
    "google.com/maps",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "twitter.com",
    "business.site",
    "booksy.com",
    "fresha.com",
    "setmore.com",
    "nearcut.com",
    "6map.top",
]


def has_real_website(url):
    if not url or url == "None":
        return False
    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in NO_REAL_WEBSITE_PATTERNS)


def main():
    input_path = os.path.expanduser("~/Desktop/nottingham_businesses.csv")
    output_path = os.path.expanduser("~/Desktop/nottingham_businesses_flagged.csv")

    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    rows = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            website = row.get("Website", "")
            row["Priority"] = "" if has_real_website(website) else "PRIORITY"
            rows.append(row)

    rows.sort(key=lambda r: (0 if r["Priority"] == "PRIORITY" else 1, r.get("Category", "")))

    fieldnames = ["Business Name", "Phone Number", "Website", "Address", "Category", "Priority"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    priority_count = sum(1 for r in rows if r["Priority"] == "PRIORITY")
    print(f"Done! {total} businesses, {priority_count} flagged as PRIORITY (no real website)")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
