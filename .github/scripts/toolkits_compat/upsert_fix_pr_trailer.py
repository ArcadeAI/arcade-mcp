#!/usr/bin/env python3
"""Upsert toolkits-fix-pr trailer in a PR body."""

from __future__ import annotations

import argparse
import pathlib
import re


def _upsert_trailer(body: str, trailer_key: str, url: str) -> str:
    trailer_line = f"{trailer_key}: {url}"
    pattern = re.compile(
        rf"^\s*{re.escape(trailer_key)}\s*:.*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    filtered_lines = [line for line in body.splitlines() if not pattern.match(line)]
    normalized = "\n".join(filtered_lines).rstrip()
    if normalized:
        return f"{normalized}\n\n{trailer_line}\n"
    return f"{trailer_line}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, help="Path to file containing PR body")
    parser.add_argument("--trailer-key", required=True, help="Trailer key, e.g. toolkits-fix-pr")
    parser.add_argument("--url", required=True, help="PR URL to insert")
    args = parser.parse_args()
    url = args.url.strip()
    if not url:
        raise SystemExit("--url must be non-empty")

    body = pathlib.Path(args.body_file).read_text(encoding="utf-8")
    print(_upsert_trailer(body, args.trailer_key, url), end="")


if __name__ == "__main__":
    main()
