"""Prepare a release by bumping version, committing, and tagging in one step."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
import tomllib


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
PYPROJECT_VERSION_RE = re.compile(r'(?m)^version = "([^"]+)"$')


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        check=False,
        text=True,
        capture_output=capture,
    )
    if result.returncode != 0:
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)
    return result.stdout if capture else ""


def parse_version(version: str) -> tuple[int, int, int]:
    if not VERSION_RE.fullmatch(version):
        raise SystemExit(fail(f"Invalid version '{version}'. Expected X.Y.Z."))
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def read_project_version(pyproject: Path) -> str:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data["project"]["version"]


def ensure_clean_tree() -> None:
    status = run("git", "status", "--short", capture=True).strip()
    if status:
        raise SystemExit(
            fail("Git working tree is not clean. Commit or stash changes first.")
        )


def ensure_no_existing_tag(tag: str) -> None:
    existing = run("git", "tag", "--list", tag, capture=True).strip()
    if existing:
        raise SystemExit(fail(f"Tag {tag} already exists locally."))


def update_pyproject_version(pyproject: Path, target_version: str) -> None:
    text = pyproject.read_text(encoding="utf-8")
    matches = PYPROJECT_VERSION_RE.findall(text)
    if len(matches) != 1:
        raise SystemExit(
            fail("Expected exactly one top-level version entry in pyproject.toml.")
        )
    updated = PYPROJECT_VERSION_RE.sub(f'version = "{target_version}"', text, count=1)
    pyproject.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump pyproject version, commit it, and create a matching tag."
    )
    parser.add_argument("version", help="Target release version in X.Y.Z format.")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Also push HEAD and the new tag to origin.",
    )
    args = parser.parse_args()

    pyproject = Path("pyproject.toml")
    target_version = args.version
    target_tuple = parse_version(target_version)
    current_version = read_project_version(pyproject)
    current_tuple = parse_version(current_version)
    tag = f"v{target_version}"

    print(f"Current version: {current_version}")
    print(f"Target version:  {target_version}")

    if target_tuple <= current_tuple:
        return fail(
            "Target version must be greater than current version "
            f"({target_version} <= {current_version})."
        )

    ensure_clean_tree()
    ensure_no_existing_tag(tag)

    update_pyproject_version(pyproject, target_version)
    updated_version = read_project_version(pyproject)
    if updated_version != target_version:
        return fail(
            "pyproject.toml update did not persist the expected version "
            f"({updated_version} != {target_version})."
        )

    commit_message = f"chore(release): {target_version}"
    tag_message = f"Release {target_version}"

    run("git", "add", "pyproject.toml")
    run("git", "commit", "-m", commit_message)
    run("git", "tag", "-a", tag, "-m", tag_message)

    print(f"Created commit: {commit_message}")
    print(f"Created tag:    {tag}")

    if args.push:
        run("git", "push", "origin", "HEAD")
        run("git", "push", "origin", tag)
        print("Pushed commit and tag to origin.")
    else:
        print("Next step:")
        print(f"  git push origin HEAD {tag}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
