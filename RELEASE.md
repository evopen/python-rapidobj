# Release Checklist

## Versioning

Use semantic version tags: `vX.Y.Z`.

Production releases must satisfy all of the following:
- the Git tag is `vX.Y.Z`
- `[project].version` in `pyproject.toml` is `X.Y.Z`
- `X.Y.Z` is not already published on PyPI

## Local Validation

1. Clean old artifacts.
   - `rm -rf dist/`
2. Build and validate the source distribution.
   - `uv build --sdist --no-sources`
3. Validate sdist metadata.
   - `uvx --from twine twine check dist/*.tar.gz`
4. Smoke test the sdist install path.
   - `uv run --isolated --no-project --with dist/*.tar.gz tests/smoke_test.py`
5. Optionally validate a local single-interpreter wheel.
   - `uv build --wheel --python 3.12 --no-sources`
6. Smoke test wheel in a clean environment.
   - Install wheel from `dist/`
   - Import `rapidobj`
   - Parse a small `.obj` file and assert `result.ok`

## GitHub CI

1. Pull requests run:
   - `pyright`
   - `sdist` build and smoke test
   - Linux and Windows wheel builds for CPython `3.12`, `3.13`, and `3.14`
2. Version tags (`vX.Y.Z`) run the release workflow:
   - verify that tag version, `pyproject.toml` version, and PyPI publishability match
   - build the `sdist`
   - build Linux and Windows wheel artifacts
   - run metadata checks and smoke tests
   - upload artifacts to GitHub Actions
   - publish those exact artifacts to PyPI via Trusted Publishing

## GitHub Source Release

1. Push commit to `main`.
2. Create and push tag.
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
3. Wait for the release workflow to finish and download the generated artifacts if needed.
4. Create GitHub release from the tag and include changelog notes.

## PyPI Publish

1. Configure a Trusted Publisher for the repository on PyPI.
2. Bump `[project].version` in `pyproject.toml`.
3. Push a matching version tag (`vX.Y.Z`).
4. Wait for the `Release Artifacts` workflow to finish.
5. Verify the package page and an install from PyPI.
