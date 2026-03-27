from __future__ import annotations

from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

Float32Array: TypeAlias = NDArray[np.float32]
IntArray: TypeAlias = NDArray[np.int_]


class ObjParseResult:
    @property
    def ok(self) -> bool: ...

    @property
    def error_message(self) -> str: ...

    @property
    def vertex_count(self) -> int: ...

    @property
    def normal_count(self) -> int: ...

    @property
    def uv_count(self) -> int: ...

    @property
    def shape_count(self) -> int: ...

    @property
    def material_count(self) -> int: ...

    @property
    def texture_paths(self) -> list[str]: ...

    @property
    def vertices(self) -> Float32Array: ...

    @property
    def faces(self) -> IntArray: ...

    @property
    def texcoords(self) -> Float32Array: ...

    @property
    def wedge_texcoord_indices(self) -> IntArray: ...

    @property
    def wedge_material_ids(self) -> IntArray: ...


def parse_obj(filename: str) -> ObjParseResult: ...
