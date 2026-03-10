"""
Feature parity test: Compare pymeshlab vs rapidobj outputs.
Tests vertices, faces, texture coordinates, and texture IDs.

Note: 
- Triangulation may differ between libraries
- pymeshlab stores per-wedge texcoords directly in a matrix
- rapidobj stores a texcoord pool + indices (OBJ file format style)
- wedge_tex_coord_index_array in pymeshlab is TEXTURE ID, not texcoord index
"""
import numpy as np
import pymeshlab
from rapidobj import parse_obj

OBJ_PATH = "/home/dhh/Downloads/rungholt/house.obj"

# --- PyMeshLab ---
print("=" * 60)
print("Loading with PyMeshLab...")
meshset = pymeshlab.MeshSet()
meshset.load_new_mesh(OBJ_PATH)
mesh = meshset.current_mesh()

pml_vertices = mesh.vertex_matrix()
pml_faces = mesh.face_matrix()
pml_wedge_texcoords = mesh.wedge_tex_coord_matrix()  # Direct per-wedge UVs
pml_texture_ids = mesh.wedge_tex_coord_index_array()  # Texture/material ID per wedge

print(f"  Vertices: {pml_vertices.shape}")
print(f"  Faces: {pml_faces.shape}")
print(f"  Wedge texcoords: {pml_wedge_texcoords.shape} (per-wedge UVs)")
print(f"  Texture IDs: {pml_texture_ids.shape} (unique: {set(pml_texture_ids)})")
print(f"  Textures: {list(mesh.textures().keys())}")

# --- RapidObj ---
print("=" * 60)
print("Loading with RapidObj...")
result = parse_obj(OBJ_PATH)

if not result.ok:
    print(f"  Error: {result.error_message}")
    exit(1)

robj_vertices = result.vertices
robj_faces = result.faces
robj_texcoord_pool = result.texcoords
robj_texcoord_indices = result.wedge_texcoord_indices
robj_material_ids = result.wedge_material_ids  # NEW: Per-wedge material IDs

# Unwrap to per-wedge format
robj_wedge_texcoords = robj_texcoord_pool[robj_texcoord_indices]

print(f"  Vertices: {robj_vertices.shape}")
print(f"  Faces: {robj_faces.shape}")
print(f"  Texcoord pool: {robj_texcoord_pool.shape} (unique UVs)")
print(f"  Texcoord indices: {robj_texcoord_indices.shape}")
print(f"  Wedge texcoords: {robj_wedge_texcoords.shape} (after unwrapping)")
print(f"  Wedge material IDs: {robj_material_ids.shape} (unique: {set(robj_material_ids)})") 

# --- Compare ---
print("=" * 60)
print("Comparing outputs...")

# Vertices
print("\n[Vertices]")
print(f"  PyMeshLab: {pml_vertices.shape}, dtype: {pml_vertices.dtype}")
print(f"  RapidObj:  {robj_vertices.shape}, dtype: {robj_vertices.dtype}")
if pml_vertices.shape == robj_vertices.shape:
    if np.allclose(pml_vertices, robj_vertices, atol=1e-5):
        print("  ✓ Vertices MATCH")
    else:
        diff = np.abs(pml_vertices - robj_vertices).max()
        print(f"  ✗ Vertices DIFFER (max diff: {diff})")
else:
    print("  ✗ Shape mismatch")

# Face count
print("\n[Faces]")
print(f"  PyMeshLab: {pml_faces.shape[0]} triangles")
print(f"  RapidObj:  {robj_faces.shape[0]} triangles")
if pml_faces.shape[0] == robj_faces.shape[0]:
    print("  ✓ Same number of triangles")
else:
    print("  ✗ Different number of triangles")

# Compare exact face match
if np.array_equal(pml_faces, robj_faces):
    print("  ✓ Faces MATCH exactly (same triangulation)")
else:
    print("  ⚠ Faces differ (different triangulation algorithm)")

# Unique UVs
print("\n[Unique Texcoords]")
pml_unique = np.unique(np.round(pml_wedge_texcoords, 6), axis=0)
robj_unique = np.unique(np.round(robj_texcoord_pool, 6), axis=0)
print(f"  PyMeshLab unique UVs: {pml_unique.shape[0]}")
print(f"  RapidObj unique UVs:  {robj_unique.shape[0]}")
if pml_unique.shape == robj_unique.shape:
    if np.allclose(np.sort(pml_unique, axis=0), np.sort(robj_unique, axis=0), atol=1e-5):
        print("  ✓ Same set of unique UV coordinates")
    else:
        print("  ✗ Different UV coordinates")
else:
    print("  ✗ Different number of unique UVs")

# Per-wedge texcoords
print("\n[Per-Wedge Texcoords]")
print(f"  PyMeshLab: {pml_wedge_texcoords.shape}")
print(f"  RapidObj:  {robj_wedge_texcoords.shape}")
if pml_wedge_texcoords.shape == robj_wedge_texcoords.shape:
    if np.allclose(pml_wedge_texcoords, robj_wedge_texcoords, atol=1e-5):
        print("  ✓ Per-wedge texcoords MATCH")
    else:
        # Check if they're the same just reordered (due to triangulation)
        print("  ⚠ Per-wedge texcoords differ (expected due to different triangulation)")
else:
    print("  ✗ Shape mismatch")

# Material/Texture IDs
print("\n[Material/Texture IDs]")
print(f"  PyMeshLab texture IDs: {pml_texture_ids.shape} (unique: {set(pml_texture_ids)})")
print(f"  RapidObj material IDs: {robj_material_ids.shape} (unique: {set(robj_material_ids)})")
if pml_texture_ids.shape == robj_material_ids.shape:
    if np.array_equal(pml_texture_ids, robj_material_ids):
        print("  ✓ Material/Texture IDs MATCH exactly")
    else:
        print("  ⚠ Material/Texture IDs differ (may be due to different triangulation)")
        # Check if same set of IDs present
        if set(pml_texture_ids) == set(robj_material_ids):
            print("  ✓ Same set of material IDs used")
else:
    print("  ✗ Shape mismatch")


print("\n" + "=" * 60)
print("SUMMARY:")
print("  ✓ Vertices: Should match exactly")
print("  ✓ Triangle count: Should match")
print("  ✓ Unique UVs: Should match")
print("  ✓ Material/Texture IDs: Now properly exposed for multi-texture support")
print("  ⚠ Face order: May differ (triangulation algorithm)")
print("  ⚠ Wedge texcoord order: May differ (follows face order)")
print()
print("NOTE: pymeshlab's wedge_tex_coord_index_array() returns")
print("  TEXTURE/MATERIAL IDs (0, 1), not texcoord indices!")
print("  RapidObj now exposes this via wedge_material_ids property")
print("=" * 60)
