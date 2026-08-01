#!/usr/bin/env python3
"""Pull the curated real photo for each day from Wikimedia Commons.

Titles are picked by hand (see the `PHOTOS` list below) rather than an
automated "first result" search, because that would risk a portrait crop,
a watermark, or a photo full of identifiable strangers. Each one was checked
for license and orientation before being added here.

For every entry this:
  1. asks the Commons API for the current image URL + license metadata
     (never trust a cached URL — files get renamed/deleted)
  2. downloads it and centre-crops/resizes to a 1600x640 banner
  3. re-encodes as WebP under ~145KB
  4. writes images/CREDITS.md with photographer, license and source link

Only CC0, public-domain, or CC-BY / CC-BY-SA licensed files are accepted —
the script hard-fails on anything else so a bad pick can't slip in silently.

    python3 tools/fetch_day_photos.py
"""
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images"
API = "https://commons.wikimedia.org/w/api.php"
UA = "trip-site-personal-use/1.0 (static GitHub Pages itinerary; contact via repo)"

ALLOWED_LICENSE_PREFIXES = ("CC0", "Public domain", "CC BY")
BANNER_W, BANNER_H = 1600, 640
MAX_BYTES = 148 * 1024

PHOTOS = json.loads(Path("/tmp/day_photos.json").read_text(encoding="utf-8"))


def with_retry(fn, tries=6):
    delay = 5
    for attempt in range(tries):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            print(f"   429 — waiting {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 60)


def api_get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    def go():
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    return with_retry(go)


def imageinfo(title):
    data = api_get({
        "action": "query", "titles": title, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": "2000", "format": "json"
    })
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    if "missing" in page:
        raise SystemExit(f"not found on Commons: {title}")
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    return {
        "url": info.get("thumburl") or info["url"],
        "license": meta.get("LicenseShortName", {}).get("value", "?"),
        "artist": strip_html(meta.get("Artist", {}).get("value", "")),
        "credit": strip_html(meta.get("Credit", {}).get("value", "")),
        "descriptionurl": info.get("descriptionurl", ""),
    }


def strip_html(s):
    import re
    return re.sub(r"<[^>]+>", "", s or "").strip()


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    def go():
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    return with_retry(go)


def to_banner_webp(raw):
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    src_w, src_h = img.size
    target_ratio = BANNER_W / BANNER_H
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        x0 = (src_w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        y0 = (src_h - new_h) // 2
        img = img.crop((0, y0, src_w, y0 + new_h))
    img = img.resize((BANNER_W, BANNER_H), Image.LANCZOS)

    best = None
    for quality in range(78, 19, -6):
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=quality, method=6)
        best = (buf.getvalue(), quality)
        if buf.tell() <= MAX_BYTES:
            break
    return best


def main():
    OUT.mkdir(exist_ok=True)
    credits = ["# קרדיטים לתמונות\n",
               "כל תמונה הורדה מ‑Wikimedia Commons תחת רישיון פתוח, וקוצצה/נדחסה ל‑WebP למען האתר.\n"]
    total = 0
    for item in PHOTOS:
        title = item["title"]
        out = OUT / f"day-{item['iso']}.webp"
        skip_download = out.exists() and "--redo" not in sys.argv

        print(f"{'↷' if skip_download else '→'} {item['iso']}  {title}")
        info = imageinfo(title)  # always fetched, so CREDITS.md is complete even on a resumed run
        if not info["license"].startswith(ALLOWED_LICENSE_PREFIXES):
            raise SystemExit(f"REJECTED — license not allowed: {info['license']} ({title})")

        if not skip_download:
            raw = download(info["url"])
            webp, quality = to_banner_webp(raw)
            out.write_bytes(webp)
            print(f"   {info['license']:16} q{quality:<3} {len(webp)/1024:5.1f} KB  {info['artist'] or info['credit']}")
        total += out.stat().st_size

        credits.append(f"## {item['iso']} — `day-{item['iso']}.webp`\n")
        credits.append(f"- מקור: [{title}]({info['descriptionurl']})\n")
        credits.append(f"- צלם/ת: {info['artist'] or info['credit'] or 'לא צוין'}\n")
        credits.append(f"- רישיון: {info['license']}\n\n")

        time.sleep(2.5)  # be polite to the API

    (OUT / "CREDITS.md").write_text("".join(credits), encoding="utf-8")
    print(f"\n{len(PHOTOS)} photos, {total/1024:.0f} KB total")


if __name__ == "__main__":
    main()
