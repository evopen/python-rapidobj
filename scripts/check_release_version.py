"""Validate tag, project version, and PyPI publishability for releases."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tomllib
import urllib.error
import urllib.request


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    ref = os.environ.get("GITHUB_REF", "")

    if not (event_name == "push" and ref.startswith("refs/tags/v")):
        print("Skipping release version check outside tag push context.")
        return 0

    tag_version = ref.removeprefix("refs/tags/v")
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data["project"]
    package_name = project["name"]
    project_version = project["version"]

    print(f"Package: {package_name}")
    print(f"Tag version: {tag_version}")
    print(f"pyproject.toml version: {project_version}")

    if project_version != tag_version:
        return fail(
            "Tag version does not match pyproject.toml version "
            f"({tag_version} != {project_version})."
        )

    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url) as response:
            pypi_data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("Package does not exist on PyPI yet; version is publishable.")
            return 0
        raise

    releases = pypi_data.get("releases", {})
    latest = pypi_data.get("info", {}).get("version", "<unknown>")
    print(f"Latest version on PyPI: {latest}")

    if tag_version in releases and releases[tag_version]:
        return fail(f"Version {tag_version} is already published on PyPI.")

    print(f"Version {tag_version} is not yet published on PyPI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
