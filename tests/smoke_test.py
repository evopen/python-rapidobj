"""Minimal wheel smoke test for CI and release validation."""

from __future__ import annotations

from pathlib import Path
import tempfile

from rapidobj import parse_obj


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        obj_path = Path(tmpdir) / "tri.obj"
        obj_path.write_text(
            "v 0.0 0.0 0.0\n"
            "v 1.0 0.0 0.0\n"
            "v 0.0 1.0 0.0\n"
            "f 1 2 3\n",
            encoding="utf-8",
        )

        result = parse_obj(str(obj_path))
        if not result.ok:
            raise RuntimeError(result.error_message)

        assert result.vertices.shape == (3, 3)
        assert result.faces.shape == (1, 3)


if __name__ == "__main__":
    main()
