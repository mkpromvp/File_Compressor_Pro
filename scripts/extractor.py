import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

ARCHIVE_EXTS = (".zip", ".rar", ".7z", ".iso", ".tar", ".gz", ".xz", ".bz2", ".001")


def main() -> int:
    raw_path = "raw_links.txt"
    out_path = "direct_links.txt"

    with open(raw_path, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("No URLs provided")
        return 1

    found = []

    for url in links:
        print(f"Checking: {url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            content_type = (r.headers.get("content-type") or "").lower()
            final_url = r.url

            if (
                "application/octet-stream" in content_type
                or "application/zip" in content_type
                or "application/x-rar" in content_type
                or any(final_url.lower().endswith(ext) for ext in ARCHIVE_EXTS)
            ):
                found.append(final_url)
                continue

            soup = BeautifulSoup(r.text, "lxml")
            btn = soup.find("a", {"id": "downloadButton"})
            if btn and btn.get("href"):
                found.append(btn.get("href"))
                continue

            page_hit = False
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if any(ext in href.lower() for ext in ARCHIVE_EXTS):
                    direct = href if href.startswith("http") else urljoin(final_url, href)
                    found.append(direct)
                    page_hit = True

            if not page_hit and "gofile.io" in final_url.lower():
                found.append(final_url)

        except Exception as err:
            print(f"Error processing {url}: {err}")

    unique_links = list(dict.fromkeys(found))
    if not unique_links:
        print("No downloadable links found")
        return 1

    with open(out_path, "w", encoding="utf-8") as f:
        for item in unique_links:
            f.write(item + "\n")

    print("Final links:")
    for item in unique_links:
        print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
