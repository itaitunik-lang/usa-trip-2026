#!/usr/bin/env python3
"""Pull money amounts out of raw Gmail message JSON dumps.

The sync agent fetches each message in the `USA TRIP` Gmail label with the
Gmail MCP tool. Those bodies are ~100KB of HTML each, so they land on disk
instead of in the conversation. This script strips the markup and reports
every currency amount with its surrounding words, which is enough to decide
what the booking actually cost.

    python3 tools/extract_receipts.py <file-or-dir> [...]
"""
import html
import json
import re
import sys
from pathlib import Path

AMOUNT = re.compile(
    r"(?:USD|ILS|NIS|EUR|\$|₪|€)\s?\d[\d,]*(?:\.\d{2})?"
    r"|\d[\d,]*(?:\.\d{2})?\s?(?:USD|ILS|NIS|EUR|\$|₪|€)"
)
# Words that mark an amount as the one actually charged, rather than a
# strikethrough "was" price or an unrelated fee table entry.
TOTAL_HINT = re.compile(
    r"total|price now|amount paid|grand total|charged|סה.?כ|לתשלום|סכום",
    re.IGNORECASE,
)


def plain_text(payload: str) -> str:
    """Best-effort text extraction from a Gmail message JSON dump."""
    try:
        msg = json.loads(payload)
    except json.JSONDecodeError:
        msg = {}
    body = ""
    if isinstance(msg, dict):
        body = msg.get("plaintextBody") or msg.get("htmlBody") or ""
    if not body:
        body = payload
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body)
    text = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def header(payload: str, field: str) -> str:
    try:
        return json.loads(payload).get(field, "") or ""
    except (json.JSONDecodeError, AttributeError):
        return ""


def report(path: Path) -> None:
    payload = path.read_text(encoding="utf-8", errors="replace")
    text = plain_text(payload)

    print(f"\n=== {path.name}")
    for field in ("subject", "sender", "date"):
        value = header(payload, field)
        if value:
            print(f"  {field}: {value}")

    seen = set()
    for match in AMOUNT.finditer(text):
        window = text[max(0, match.start() - 90) : match.end() + 30]
        key = (match.group(), window[:40])
        if key in seen:
            continue
        seen.add(key)
        flag = "*" if TOTAL_HINT.search(window) else " "
        print(f"  {flag} {match.group():>14}  …{window}…")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    for arg in argv:
        target = Path(arg)
        files = sorted(target.glob("*.txt")) if target.is_dir() else [target]
        for path in files:
            report(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
