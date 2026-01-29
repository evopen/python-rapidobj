#include "rapidobj.hpp"

#include <iostream>

// define the result struct
struct ObjParseStats {
  bool ok;
  int vertex_count;
  int normal_count;
  int uv_count;
  int shape_count;
  int material_count;
};

static ObjParseStats parse_rapidobj(const char *filename) {
  ObjParseStats res;
  auto m = rapidobj::ParseFile(filename);
  res.ok = !m.error;

  if (res.ok) {
    res.vertex_count = (int)(m.attributes.positions.size() / 3);
    res.normal_count = (int)(m.attributes.normals.size() / 3);
    res.uv_count = (int)(m.attributes.texcoords.size() / 2);
    res.shape_count = (int)m.shapes.size();
    res.material_count = (int)m.materials.size();
  }

  return res;
}

int main() {
  auto res = parse_rapidobj("/home/dhh/Downloads/rungholt/rungholt.obj");

  if (!res.ok) {
    std::cout << "Failed to parse OBJ file" << '\n';
    return EXIT_FAILURE;
  }

  std::cout << "Vertices:  " << res.vertex_count << '\n';
  std::cout << "Normals:   " << res.normal_count << '\n';
  std::cout << "UVs:       " << res.uv_count << '\n';
  std::cout << "Shapes:    " << res.shape_count << '\n';
  std::cout << "Materials: " << res.material_count << '\n';

  return EXIT_SUCCESS;
}