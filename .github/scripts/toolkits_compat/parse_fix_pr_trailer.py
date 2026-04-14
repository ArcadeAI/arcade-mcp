#!/usr/bin/env python3
"""Parse toolkits-fix-pr trailer from a PR body."""

from __future__ import annotations

import argparse
import pathlib
import re
from typing import Final


def _extract_fix_pr_url(body: str, trailer_key: str, repo: str) -> str:
    escaped_key = re.escape(trailer_key)
    escaped_repo = re.escape(repo)
    pattern: Final[re.Pattern[str]] = re.compile(
        rf"(?im)^\s*{escaped_key}\s*:\s*(https://github\.com/{escaped_repo}/pull/\d+)\s*$"
    )
    matches = pattern.findall(body)
    return matches[-1] if matches else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, help="Path to file containing PR body")
    parser.add_argument("--trailer-key", required=True, help="Trailer key, e.g. toolkits-fix-pr")
    parser.add_argument("--repo", required=True, help="Expected repo slug, e.g. ArcadeAI/monorepo")
    parser.add_argument("--output-file", help="Path to GITHUB_OUTPUT-compatible file")
    parser.add_argument("--print-url", action="store_true", help="Print parsed URL and exit")
    args = parser.parse_args()

    body = pathlib.Path(args.body_file).read_text(encoding="utf-8")
    url = _extract_fix_pr_url(body, args.trailer_key, args.repo)

    if args.print_url:
        print(url)
        return

    if args.output_file:
        output_path = pathlib.Path(args.output_file)
        with output_path.open("a", encoding="utf-8") as fh:
            fh.write(f"linked_fix_pr_url={url}\n")


if __name__ == "__main__":
    main()
