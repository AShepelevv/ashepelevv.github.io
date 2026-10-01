import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic/?per_page=1&api_key={}"
SITE_URL = "https://science.nasa.gov/"
OUTPUT_FILE = "data.json"
MAX_ATTEMPTS = 5
BASE_DELAY = 10
MEDIA_TAGS = {"img", "video", "source", "iframe"}
EXPLANATION_LABEL = re.compile(r"^Explanation\s*:\s*")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append(" ")

    def handle_data(self, data):
        self.parts.append(data)


class MediaFinder(HTMLParser):
    """APOD Basic HTML keeps the legacy APOD page layout: the media of the day
    is the first image, video or iframe inside the leading <center> block."""

    def __init__(self):
        super().__init__()
        self.src = None
        self.searching = True

    def handle_starttag(self, tag, attrs):
        src = dict(attrs).get("src")
        if self.searching and tag in MEDIA_TAGS and src:
            self.src = src
            self.searching = False

    def handle_endtag(self, tag):
        if tag == "center":
            self.searching = False


def to_text(fragment):
    parser = TextExtractor()
    parser.feed(fragment or "")
    parser.close()
    return " ".join("".join(parser.parts).split())


def find_media_src(page):
    finder = MediaFinder()
    finder.feed(page or "")
    finder.close()
    return finder.src


def fetch(api_key):
    url = API_URL.format(api_key)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def to_legacy_format(entry):
    src = find_media_src(entry.get("basic_html"))
    return {
        "date": entry.get("date"),
        "title": to_text(entry.get("title")),
        "explanation": EXPLANATION_LABEL.sub("", to_text(entry.get("explanation"))),
        "media_type": entry.get("media_type") if src else "image",
        "url": urllib.parse.urljoin(SITE_URL, src) if src else entry.get("hdurl"),
        "hdurl": entry.get("hdurl"),
        "permalink": entry.get("permalink"),
    }


def latest_apod(data):
    if isinstance(data, list) and data and isinstance(data[0], dict):
        apod = to_legacy_format(data[0])
        if apod["url"]:
            return apod
    return None


def main():
    api_key = os.environ.get("NASA_API_KEY")
    if not api_key:
        print("NASA_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    delay = BASE_DELAY
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Attempt {attempt} of {MAX_ATTEMPTS}...")
        try:
            data = fetch(api_key)
            apod = latest_apod(data)
            if apod:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(apod, f)
                print(f"Success on attempt {attempt}")
                return
            print(f"Unexpected response: {str(data)[:1000]}", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

        if attempt < MAX_ATTEMPTS:
            print(f"Waiting {delay}s before next attempt...")
            time.sleep(delay)
            delay *= 2

    print(f"All {MAX_ATTEMPTS} attempts failed", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
