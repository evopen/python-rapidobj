# Release Checklist

## Versioning

Use semantic version tags: `vX.Y.Z`.

## Build and Validate

1. Clean old artifacts.
   - `rm -rf dist/`
2. Build distributions.
   - `uv build`
3. Validate metadata and artifacts.
   - `uvx --from twine twine check dist/*`
4. Smoke test wheel in a clean environment.
   - Install wheel from `dist/`
   - Import `rapidobj`
   - Parse a small `.obj` file and assert `result.ok`

## GitHub Source Release

1. Push commit to `main`.
2. Create and push tag.
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
3. Create GitHub release from the tag and include changelog notes.

## PyPI Publish

1. Upload validated artifacts:
   - `uvx --from twine twine upload dist/*`
2. Verify package page metadata and install command.
