import sys
import time
from rapidobj import parse_obj


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <obj_path>")
        sys.exit(1)

    obj_path = sys.argv[1]
    print(f"Parsing: {obj_path}")

    start = time.perf_counter()
    ret = parse_obj(obj_path)
    elapsed = time.perf_counter() - start

    if not ret.ok:
        print(f"Error: {ret.error_message}")
        sys.exit(1)

    print(f"Time: {elapsed*1000:.2f} ms")
    print(f"Vertices: {ret.vertices.shape}")
    print(f"Faces: {ret.faces.shape}")
    print(f"Texcoords: {ret.texcoords.shape}")
    print(f"Wedge texcoord indices: {ret.wedge_texcoord_indices.shape}")


if __name__ == "__main__":
    main()
