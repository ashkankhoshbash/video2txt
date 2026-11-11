"""Download one supported video into a caller-owned temporary directory."""

import json
import re
import shutil
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def download_aparat(path, directory):
    """Fetch a single Aparat video using its public metadata endpoint."""
    match = re.fullmatch(
        r"/(?:v|video/video/embed/videohash)/([a-zA-Z0-9]+)/?", path
    )
    if not match:
        raise ValueError("Enter a link to a single Aparat video.")
    endpoint = (
        "https://www.aparat.com/api/fa/v1/video/video/show/videohash/"
        + match[1]
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    with urlopen(Request(endpoint, headers=headers), timeout=20) as response:
        data = json.load(response)
    attributes = (data.get("data") or {}).get("attributes") or {}
    sources = []
    for item in attributes.get("file_link_all") or []:
        quality = re.fullmatch(r"(\d+)p", item.get("profile") or "")
        height = int(quality[1]) if quality else float("inf")
        sources.extend(
            (height, url) for url in (item.get("urls") or [])
            if url.startswith("https://")
        )
    if not sources:
        raise RuntimeError("Aparat did not return a downloadable video.")

    media = directory / "media.mp4"
    for _, url in sorted(sources):
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                with media.open("wb") as output:
                    shutil.copyfileobj(response, output)
        except OSError as error:
            last_error = error
        else:
            return media
    raise RuntimeError(f"Aparat download failed: {last_error}")


def download_audio(url, directory):
    """Download the best available single audio or video stream."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if parsed.scheme not in ("http", "https") or not (
        host == "aparat.com" or host.endswith(".aparat.com")
    ):
        raise ValueError("Enter an Aparat video link.")
    return download_aparat(parsed.path, directory)
