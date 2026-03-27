#!/usr/bin/env python3
"""Minimal error handling example."""

from __future__ import annotations

from rapidobj import parse_obj


def main() -> int:
    result = parse_obj("does-not-exist.obj")
    if result.ok:
        print("Unexpected success")
        return 1

    print("Expected parse failure")
    print(result.error_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
