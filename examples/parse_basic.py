#!/usr/bin/env python3
"""Minimal rapidobj parsing example."""

from __future__ import annotations

import sys

from rapidobj import parse_obj


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mesh.obj>")
        return 1

    result = parse_obj(sys.argv[1])
    if not result.ok:
        print(f"Parse error: {result.error_message}")
        return 2

    print(f"vertices: {result.vertices.shape}")
    print(f"faces: {result.faces.shape}")
    print(f"texcoords: {result.texcoords.shape}")
    print(f"materials: {result.material_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
