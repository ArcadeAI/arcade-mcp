#!/usr/bin/env python3
"""Upsert toolkits-fix-pr trailer in a PR body."""

from __future__ import annotations

import argparse
import pathlib
import re


def _upsert_trailer(body: str, trailer_key: str, url: str) -> str:
    trailer_line = f"{trailer_key}: {url}"
    pattern = re.compile(rf"(?im)^\s*{re.escape(trailer_key)}\s*:.*$", re.MULTILINE)

    if pattern.search(body):
        return pattern.sub(trailer_line, body, count=1)

    normalized = body.rstrip()
    if normalized:
        return f"{normalized}\n\n{trailer_line}\n"
    return f"{trailer_line}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, help="Path to file containing PR body")
    parser.add_argument("--trailer-key", required=True, help="Trailer key, e.g. toolkits-fix-pr")
    parser.add_argument("--url", required=True, help="PR URL to insert")
    args = parser.parse_args()

    body = pathlib.Path(args.body_file).read_text(encoding="utf-8")
    print(_upsert_trailer(body, args.trailer_key, args.url), end="")


if __name__ == "__main__":
    main()
