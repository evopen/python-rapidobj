#!/usr/bin/env python3
"""Sample textured points from an OBJ file using rapidobj and pure PyTorch (no pytorch3d dependency)."""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import torch
import torch.nn.functional as F
import typer
import torchvision.io as tvio

# Try to import safetensors
try:
    from safetensors.numpy import save_file as save_safetensors
    SAFETENSORS_AVAILABLE = True
except ImportError:
    SAFETENSORS_AVAILABLE = False

# Import rapidobj_ext
try:
    from rapidobj_ext import parse_obj
except ImportError:
    print("Error: rapidobj_ext not found. Please ensure it is installed.")
    sys.exit(1)


app = typer.Typer(help="Sample textured points from an OBJ file", pretty_exceptions_enable=False)


class SamplingError(Exception):
    pass



def srgb_to_linear(x: torch.Tensor) -> torch.Tensor:
    """Convert sRGB to linear space."""
    return torch.where(x <= 0.04045, x / 12.92, torch.pow((x + 0.055) / 1.055, 2.4))


def linear_to_srgb(x: torch.Tensor) -> torch.Tensor:
    """Convert linear space to sRGB."""
    return torch.where(x <= 0.0031308, x * 12.92, 1.055 * torch.pow(x, 1.0 / 2.4) - 0.055)


def compute_face_areas(v0: torch.Tensor, v1: torch.Tensor, v2: torch.Tensor) -> torch.Tensor:
    """Compute area of triangles (N, 3)."""
    # Cross product of two edges
    # Area = 0.5 * |(v1 - v0) x (v2 - v0)|
    e1 = v1 - v0
    e2 = v2 - v0
    # torch.cross is deprecated for 1D, but we use linalg.cross or manual
    cross = torch.linalg.cross(e1, e2, dim=1)
    return 0.5 * torch.linalg.norm(cross, dim=1)


def sample_points(
    vertices: torch.Tensor,
    faces: torch.Tensor,
    texcoords: torch.Tensor,
    wedge_indices: torch.Tensor,
    material_ids: torch.Tensor,
    textures: list[torch.Tensor],
    num_samples: int,
    device: torch.device
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Sample points from the mesh.
    Returns: (points_xyz, face_ids, colors_linear) as Tensors on cpu/device
    """
    
    # 1. Compute areas
    # Get vertices for each face: (F, 3, 3)
    # faces is (F, 3) indices
    # vertices is (V, 3)
    
    f_v = vertices[faces] # (F, 3, 3)
    v0, v1, v2 = f_v[:, 0], f_v[:, 1], f_v[:, 2] # (F, 3)
    
    areas = compute_face_areas(v0, v1, v2) # (F,)
    total_area = areas.sum().item()
    
    if total_area <= 0:
        raise SamplingError("Mesh has zero surface area.")
        
    # 2. Sample Faces
    # multinomial requires positive weights
    # Add epsilon or handle zero areas if needed, but 0 area faces shouldn't be sampled
    
    # We use multinomial on areas directly
    # Note: multinomial expects float input
    
    sample_face_idxs = torch.multinomial(areas, num_samples, replacement=True) # (N,)
    
    # 3. Generate Barycentrics
    # r1 = sqrt(u), r2 = v
    # w0 = 1 - r1
    # w1 = r1 * (1 - r2)
    # w2 = r1 * r2
    
    u = torch.rand(num_samples, device=device)
    v = torch.rand(num_samples, device=device)
    u_sqrt = u.sqrt()
    
    w0 = 1.0 - u_sqrt
    w1 = u_sqrt * (1.0 - v)
    w2 = u_sqrt * v
    
    # 4. Interpolate Positions
    # Gather face vertices for sampled faces
    # sample_face_idxs is indices into faces
    
    # Selected vertices: (N, 3)
    s_v0 = v0[sample_face_idxs]
    s_v1 = v1[sample_face_idxs]
    s_v2 = v2[sample_face_idxs]
    
    # (N, 1) * (N, 3) -> (N, 3)
    pos = w0[:, None] * s_v0 + w1[:, None] * s_v1 + w2[:, None] * s_v2
    
    # 5. Interpolate UVs and Sample Colors
    
    # We need per-face material IDs to know which texture to sample.
    # material_ids is per-wedge (F*3).
    # Assuming standard OBJ, all wedges in a face assume same material.
    # wedge_indices is (F*3)
    
    # Reshape to (F, 3)
    mats_per_face = material_ids.reshape(-1, 3)
    face_mat_ids = mats_per_face[:, 0] # (F,)
    
    # Indices into texcoords array (F, 3)
    face_uv_inds = wedge_indices.reshape(-1, 3)
    
    # Sampled face properties
    s_mat_ids = face_mat_ids[sample_face_idxs] # (N,)
    s_uv_inds = face_uv_inds[sample_face_idxs] # (N, 3)
    
    # Get UV coordinates
    # texcoords: (V_uv, 2)
    # s_uv_inds: (N, 3)
    
    tc = texcoords[s_uv_inds] # (N, 3, 2)
    uv0, uv1, uv2 = tc[:, 0], tc[:, 1], tc[:, 2] # (N, 2)
    
    # Interpolate UVs
    uv = w0[:, None] * uv0 + w1[:, None] * uv1 + w2[:, None] * uv2 # (N, 2)
    
    # Now sample colors.
    # Group by material ID to handle different textures.
    
    # Prepare output colors
    colors = torch.zeros((num_samples, 3), dtype=torch.float32, device=device)
    
    # If no textures, return white or encoded info? The requirement assumes textures exist.
    if not textures:
         # Fallback to white?
         colors[:] = 1.0
    else:
        unique_mats = torch.unique(s_mat_ids)
        
        for mid in unique_mats:
            mid_val = mid.item()
            if mid_val < 0 or mid_val >= len(textures):
                continue
                
            # Mask for this material
            mask = (s_mat_ids == mid)
            
            # Extract UVs for this material
            # Note: OBJ UVs are usually 0..1 with V=0 at bottom (OpenGL style) or top?
            # grid_sample expects -1..1.
            # Usually: u -> (u * 2) - 1.
            # v: depending on convention.
            # TexturesUV (pytorch3d) does:
            #   pixel_uvs = torch.lerp([-1, 1], [1, -1], uv) if flip_y else ...
            #   It seems it flips Y by default (1 at V=0 -> -1, 0 at V=1 -> 1? No.)
            #   Standard UV: (0,0) is bottom-left. Image tensor (0,0) is top-left.
            #   So we usually flip V: v' = 1 - v.
            
            curr_uv = uv[mask] # (K, 2)
            
            # Map [0, 1] to [-1, 1]
            # grid_sample uses (x, y). u is x, v is y.
            
            # Flip V logic:
            # If image origin is top-left (torch convention), and UV origin is bottom-left.
            # V=0 -> bottom -> y=1 (in torch grid -1..1, y=1 is bottom)
            # V=1 -> top -> y=-1
            # So y = (1 - v) * 2 - 1 = 1 - 2v ?
            # Or map v to [1, -1].
            # Pytorch3d logic: lerp([-1, 1], [1, -1], uv)
            # This maps u: 0->-1, 1->1. v: 0->1, 1->-1.
            # Exactly.
            
            grid = curr_uv.clone()
            grid[:, 0] = grid[:, 0] * 2.0 - 1.0       # u: 0..1 -> -1..1
            grid[:, 1] = (1.0 - grid[:, 1]) * 2.0 - 1.0 # v: 0..1 -> 1..-1 (flip y)
            
            # Prepare grid for grid_sample: (N, H, W, 2)
            # We have list of points (K, 2). treat as (1, 1, K, 2) or (K, 1, 1, 2) if batching.
            # Texture is (C, H, W). grid_sample expects (N, C, H, W).
            # We can treat each point as a separate "image" in batch? No.
            # We treat the list of points as a grid of size (1, K) or (K, 1).
            
            # Shape: (1, 1, K, 2)
            grid = grid.view(1, 1, -1, 2) 
            
            tex = textures[mid_val] # (C, H, W)
            # Add batch dim
            img_batch = tex.unsqueeze(0) # (1, C, H, W)
            
            # Sample
            # mode='bilinear', padding_mode='border' or 'zeros'
            # Reference script used TexturesUV default which is border?
            # Actually reference script (pytorch3d) uses border by default.
            
            sampled = F.grid_sample(
                img_batch, 
                grid, 
                mode='bilinear', 
                padding_mode='border', 
                align_corners=False # Standard usually False for UVs? Pytorch3d default is True.
                # Let's verify align_corners. Pytorch3d TexturesUV default is align_corners=True.
            )
            
            # Output: (1, C, 1, K)
            sampled = sampled.squeeze(0).squeeze(1).permute(1, 0) # (K, C)
            
            colors[mask] = sampled
            
    return pos, sample_face_idxs, colors


def _to_array_series(name: str, values: np.ndarray, dtype: pl.DataType) -> pl.Series:
    return pl.Series(name=name, values=values, dtype=dtype)


def build_samples_df(
    points_xyz: np.ndarray, colors: np.ndarray, face_ids: np.ndarray
) -> pl.DataFrame:
    if points_xyz.size == 0:
        return pl.DataFrame()

    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
        raise SamplingError("Point positions must be shaped (N, 3)")
    if colors.ndim != 2 or colors.shape[1] != 3:
        raise SamplingError("Point colors must be shaped (N, 3)")
    if face_ids.ndim != 1 or face_ids.shape[0] != points_xyz.shape[0]:
        raise SamplingError("Face indices must be shaped (N,)")

    points_xyz = np.asarray(points_xyz, dtype=np.float32, order="C")
    colors = np.asarray(colors, dtype=np.uint8, order="C")
    face_ids = np.asarray(face_ids, dtype=np.int64, order="C")

    return pl.DataFrame(
        {
            "pos": _to_array_series("pos", points_xyz, pl.Array(pl.Float32, 3)),
            "color": _to_array_series("color", colors, pl.Array(pl.UInt8, 3)),
            "face_index": pl.Series(
                "face_index",
                face_ids,
                dtype=pl.UInt32,
            ),
        }
    )


def write_samples_ipc(path: Path, samples: pl.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if samples.is_empty():
        # Write schema only? or just empty file. Polars handles empty df.
        pass
    samples.write_ipc(path)


def write_samples_safetensors(path: Path, samples: pl.DataFrame) -> None:
    if not SAFETENSORS_AVAILABLE:
        raise SamplingError("safetensors package is not installed.")
        
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if samples.is_empty():
        # Write empty dict
        save_safetensors({}, str(path))
        return

    pos = samples["pos"].to_numpy(allow_copy=False)
    color = samples["color"].to_numpy(allow_copy=False)
    face_index = samples["face_index"].to_numpy(allow_copy=False)
    tensors = {
        "pos": np.asarray(pos, dtype=np.float32, order="C"),
        "color": np.asarray(color, dtype=np.uint8, order="C"),
        "face_index": np.asarray(face_index, dtype=np.uint32, order="C"),
    }
    
    save_safetensors(tensors, str(path))


@app.command()
def main(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Input OBJ file.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        "-o",
        file_okay=True,
        dir_okay=False,
        writable=True,
        help="Output path for sampled points (.ipc or .safetensors).",
    ),
    points_per_m2: float = typer.Option(
        ...,
        "--points-per-m2",
        min=0.0,
        help="Target point density per square meter of surface area.",
    ),
    device: str = typer.Option(
        "auto",
        "--device",
        help="Torch device (e.g. cpu, cuda, cuda:0). Defaults to auto.",
    ),
) -> None:
    if points_per_m2 <= 0.0:
        raise typer.BadParameter("--points-per-m2 must be greater than 0")

    if output_path.suffix not in [".ipc", ".safetensors"]:
        raise typer.BadParameter("Output extension must be .ipc or .safetensors")

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_device = torch.device(device)
    
    start_time = time.perf_counter()
    
    # 1. Load OBJ
    print(f"Loading {input_path}...")
    obj_start = time.perf_counter()
    result = parse_obj(str(input_path))
    if not result.ok:
        raise SamplingError(f"Failed to load OBJ: {result.error_message}")
        
    obj_time = time.perf_counter() - obj_start
    print(f"Loaded OBJ in {obj_time:.3f}s")
    
    # 2. Load Textures
    texture_paths = result.texture_paths
    # Note: result.texture_paths might be empty if no materials/textures.
    
    print(f"Loading {len(texture_paths)} textures...")
    tex_start = time.perf_counter()
    texture_tensors = []
    
    obj_dir = input_path.parent
    
    for i, tp in enumerate(texture_paths):
        if not tp or (obj_dir / tp).is_dir():
             print(f"Warning: Empty or invalid texture path for material {i}: '{tp}'. Using white placeholder.")
             # 1x1 white texture (3, 1, 1)
             img = torch.ones((3, 1, 1), dtype=torch.float32, device=torch_device)
             texture_tensors.append(img)
             continue

        tpath = obj_dir / tp
        if not tpath.exists():
            # Try finding it in the same dir as OBJ even if path says otherwise? 
            # Standard rapidobj behavior is to give path as in MTL.
            # We assume relative to OBJ dir if relative.
            tpath = obj_dir / Path(tp).name
            if not tpath.exists():
                 print(f"Warning: Texture file not found: {tp} (tried {tpath}). Using white placeholder.")
                 # Use placeholder
                 img = torch.ones((3, 1, 1), dtype=torch.float32, device=torch_device)
                 texture_tensors.append(img)
                 continue

        try:
            # Read image: CHW, uint8
            img = tvio.read_image(str(tpath))
            if img.shape[0] == 1: 
                img = img.repeat(3, 1, 1)
            elif img.shape[0] == 4: 
                img = img[:3]
                
            img = img.float() / 255.0
            # Convert to linear space for correct interpolation
            img = srgb_to_linear(img)
            texture_tensors.append(img.to(torch_device))
        except Exception as e:
            print(f"Warning: Failed to load texture {tpath}: {e}. Using white placeholder.")
            img = torch.ones((3, 1, 1), dtype=torch.float32, device=torch_device)
            texture_tensors.append(img)
            
    tex_time = time.perf_counter() - tex_start
    print(f"Loaded textures in {tex_time:.3f}s")
    
    # 3. Prepare Data
    prep_start = time.perf_counter()
    
    verts = torch.from_numpy(result.vertices).to(torch_device)
    faces = torch.from_numpy(result.faces).to(torch_device).long()
    texcoords = torch.from_numpy(result.texcoords).to(torch_device)
    wedge_indices = torch.from_numpy(result.wedge_texcoord_indices).to(torch_device).long()
    material_ids = torch.from_numpy(result.wedge_material_ids).to(torch_device).long()
    

    
    # Let's do area calc here.
    f_v = verts[faces]
    v0, v1, v2 = f_v[:, 0], f_v[:, 1], f_v[:, 2]
    areas = compute_face_areas(v0, v1, v2)
    total_area = areas.sum().item()
    
    num_samples = int(math.ceil(total_area * points_per_m2))
    
    prep_time = time.perf_counter() - prep_start
    print(f"Prepared mesh in {prep_time:.3f}s. Area: {total_area:.2f} m2. Target samples: {num_samples}")
    
    if num_samples <= 0:
        print("Warning: No samples generated.")
        if output_path.suffix == ".ipc":
            write_samples_ipc(output_path, pl.DataFrame())
        else:
            write_samples_safetensors(output_path, pl.DataFrame())
        return

    sample_start = time.perf_counter()
    samples_xyz_t, sample_face_ids_t, sample_colors_linear_t = sample_points(
        verts, faces, texcoords, wedge_indices, material_ids, texture_tensors,
        num_samples=num_samples,
        device=torch_device
    )
    sample_time = time.perf_counter() - sample_start
    print(f"Sampled {samples_xyz_t.shape[0]} points in {sample_time:.3f}s")
    
    # 5. Save Output
    write_start = time.perf_counter()
    
    # Convert linear colors back to sRGB for storage/display
    # Clamp just in case (bicubic/bilinear undershoot/overshoot)
    sample_colors_srgb = linear_to_srgb(sample_colors_linear_t.clamp(0.0, 1.0))
    
    # Convert to numpy and uint8
    colors_u8 = (sample_colors_srgb * 255.0).round().clamp(0, 255).byte().cpu().numpy()
    samples_xyz = samples_xyz_t.cpu().numpy()
    sample_face_ids = sample_face_ids_t.cpu().numpy()
    
    samples_df = build_samples_df(samples_xyz, colors_u8, sample_face_ids)
    
    if output_path.suffix == ".ipc":
        write_samples_ipc(output_path, samples_df)
    else:
        write_samples_safetensors(output_path, samples_df)
        
    write_time = time.perf_counter() - write_start
    print(f"Wrote output to {output_path} in {write_time:.3f}s")
    
    total_time = time.perf_counter() - start_time
    print(f"Total time: {total_time:.3f}s")


if __name__ == "__main__":
    app()
