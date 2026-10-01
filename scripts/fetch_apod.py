import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic/?per_page=1&api_key={}"
OUTPUT_FILE = "data.json"
MAX_ATTEMPTS = 5
BASE_DELAY = 10


def fetch(api_key):
    url = API_URL.format(api_key)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def valid(data):
    return (
        isinstance(data, list)
        and len(data) > 0
        and isinstance(data[0], dict)
        and ("url" in data[0] or "hdurl" in data[0])
    )


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
            if valid(data):
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(data[0], f)
                print(f"Success on attempt {attempt}")
                return
            print(f"Unexpected response: {data}", file=sys.stderr)
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
