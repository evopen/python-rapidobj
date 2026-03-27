# Release Checklist

## Versioning

Use semantic version tags: `vX.Y.Z`.

Production releases must satisfy all of the following:
- the Git tag is `vX.Y.Z`
- `[project].version` in `pyproject.toml` is `X.Y.Z`
- `X.Y.Z` is not already published on PyPI

Do not bump `pyproject.toml` and create tags as separate manual steps. Use the
release script so the version bump, commit, and tag come from the same commit:

```bash
uv run python scripts/release.py X.Y.Z
git push origin HEAD vX.Y.Z
```

Or let the script push both:

```bash
uv run python scripts/release.py X.Y.Z --push
```

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

1. Run the release script from a clean working tree.
   - `uv run python scripts/release.py X.Y.Z`
2. Push the release commit and tag.
   - `git push origin HEAD vX.Y.Z`
3. Wait for the release workflow to finish and download the generated artifacts if needed.
4. Create GitHub release from the tag and include changelog notes.

## PyPI Publish

1. Configure a Trusted Publisher for the repository on PyPI.
2. Run the release script so `pyproject.toml` and the tag are created together.
3. Push the resulting commit and matching version tag (`vX.Y.Z`).
4. Wait for the `Release Artifacts` workflow to finish.
5. Verify the package page and an install from PyPI.
