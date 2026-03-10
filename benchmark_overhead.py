"""
Benchmark to determine overhead sources:
1. Python startup time
2. Binding/data copy overhead
"""
import sys
import time

# Measure import time
import_start = time.perf_counter()
from rapidobj import parse_obj
import_elapsed = time.perf_counter() - import_start

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <obj_path> [iterations]")
    sys.exit(1)

obj_path = sys.argv[1]
iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5

print(f"Python import time: {import_elapsed*1000:.2f} ms")
print(f"Parsing: {obj_path}")
print(f"Iterations: {iterations}")
print("-" * 50)

times = []
for i in range(iterations):
    start = time.perf_counter()
    ret = parse_obj(obj_path)
    elapsed = time.perf_counter() - start
    times.append(elapsed * 1000)
    
    # Access the arrays to force any lazy evaluation
    _ = ret.vertices.shape
    _ = ret.faces.shape
    _ = ret.texcoords.shape
    _ = ret.wedge_texcoord_indices.shape

print(f"Parse times: {[f'{t:.2f}' for t in times]} ms")
print(f"Average: {sum(times)/len(times):.2f} ms")
print(f"Min: {min(times):.2f} ms")
print(f"Max: {max(times):.2f} ms")
print()
print(f"Vertices: {ret.vertices.shape}")
print(f"Faces: {ret.faces.shape}")
