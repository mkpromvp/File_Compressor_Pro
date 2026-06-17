import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    import privatebinapi  # type: ignore
except Exception:
    privatebinapi = None

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

ARCHIVE_EXTS = (".zip", ".rar", ".7z", ".iso", ".tar", ".gz", ".xz", ".bz2", ".001")
URL_RE = re.compile(r'https?://[^\s\]\[\)\(}"\'<>,]+', re.IGNORECASE)
DOWNLOAD_HOST_HINTS = (
    "mediafire.com",
    "gofile.io",
    "pixeldrain.com",
    "1fichier.com",
    "qiwi.gg",
    "fuckingfast.co",
    "multiup.io",
    "megaup.net",
    "krakenfiles.com",
    "buzzheavier.com",
    "drop.download",
    "rapidgator.net",
    "ddownload.com",
)


def _extract_urls_from_text(text: str) -> list[str]:
    urls = []
    for match in URL_RE.findall(text):
        cleaned = match.rstrip("\"'.,);]}")
        if cleaned:
            urls.append(cleaned)
    return urls


def _is_likely_download_link(url: str) -> bool:
    lowered = url.lower()
    return any(ext in lowered for ext in ARCHIVE_EXTS) or any(h in lowered for h in DOWNLOAD_HOST_HINTS)


def _looks_like_privatebin(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.fragment and parsed.query) and "paste" in parsed.netloc


def _extract_from_privatebin(url: str) -> list[str]:
    if privatebinapi is None:
        return []

    try:
        result = privatebinapi.get(url)
        text = result.get("text", "") if isinstance(result, dict) else ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        return _extract_urls_from_text(text)
    except Exception as err:
        print(f"PrivateBin decode failed for {url}: {err}")
        return []


def main() -> int:
    raw_path = "raw_links.txt"
    out_path = "direct_links.txt"

    with open(raw_path, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("No URLs provided")
        return 1

    found = []
    queue = list(links)
    seen = set()
    max_to_process = 300

    while queue and len(seen) < max_to_process:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        print(f"Checking: {url}")
        try:
            if _looks_like_privatebin(url):
                pb_links = _extract_from_privatebin(url)
                if pb_links:
                    print(f"PrivateBin links found: {len(pb_links)}")
                    for candidate in pb_links:
                        if candidate not in seen and candidate not in queue:
                            queue.append(candidate)

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
                if not href:
                    continue

                candidate = href if href.startswith("http") else urljoin(final_url, href)
                if _is_likely_download_link(candidate):
                    page_hit = True
                    if any(ext in candidate.lower() for ext in ARCHIVE_EXTS):
                        found.append(candidate)
                    elif candidate not in seen and candidate not in queue:
                        queue.append(candidate)

            for text_link in _extract_urls_from_text(soup.get_text("\n", strip=True)):
                if any(ext in text_link.lower() for ext in ARCHIVE_EXTS):
                    found.append(text_link)
                    page_hit = True
                elif _is_likely_download_link(text_link) and text_link not in seen and text_link not in queue:
                    queue.append(text_link)
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
