## rapidobj

`rapidobj` is a fast Wavefront OBJ parser exposed as a Python extension module
using nanobind. It returns NumPy views for mesh data so parsing and data access
stay efficient.

## Requirements

- Python 3.12+
- CMake 3.18+
- A C++17 compiler

## Install

From PyPI:

```bash
python -m pip install rapidobj
```

From source:

```bash
uv sync
uv build --wheel --python 3.12 --no-sources
python -m pip install dist/rapidobj-0.1.3-cp312-cp312-*.whl
```

For release builds, GitHub Actions is the authoritative wheel pipeline. Pull
requests validate the package, and version tags build Linux and Windows wheels
for CPython 3.12, 3.13, and 3.14. Tag builds publish the validated artifacts
to PyPI via Trusted Publishing after a strict version check.

For releases, use the helper script so the package version and tag stay in
lockstep:

```bash
uv run python scripts/release.py X.Y.Z
git push origin HEAD vX.Y.Z
```

## Minimal Usage

```python
from rapidobj import parse_obj

result = parse_obj("mesh.obj")
if not result.ok:
    raise RuntimeError(result.error_message)

print(result.vertices.shape)  # (V, 3)
print(result.faces.shape)     # (F, 3)
print(result.texcoords.shape) # (T, 2)
```

See `examples/` for runnable scripts.

## API

- `parse_obj(filename: str) -> ObjParseResult`
- `ObjParseResult.ok: bool`
- `ObjParseResult.error_message: str`
- `ObjParseResult.vertex_count: int`
- `ObjParseResult.normal_count: int`
- `ObjParseResult.uv_count: int`
- `ObjParseResult.shape_count: int`
- `ObjParseResult.material_count: int`
- `ObjParseResult.texture_paths: list[str]`
- `ObjParseResult.vertices: np.ndarray`
- `ObjParseResult.faces: np.ndarray`
- `ObjParseResult.texcoords: np.ndarray`
- `ObjParseResult.wedge_texcoord_indices: np.ndarray`
- `ObjParseResult.wedge_material_ids: np.ndarray`

## Release Notes

Release workflow and checklist are documented in `RELEASE.md`.
