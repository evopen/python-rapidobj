#include "rapidobj.hpp"
#include <nanobind/ndarray.h>

#include <iostream>

namespace nb = nanobind;

// define the result struct
struct ObjParseStats {
  bool ok;
  int vertex_count;
  int normal_count;
  int uv_count;
  int shape_count;
  int material_count;
  std::vector<std::string> texture_paths;
  // vertex_matrix
  nb::ndarray<float, nb::numpy, nb::shape<-1, 3>, nb::f_contig> vertex_matrix;
  // face_matrix
  nb::ndarray<int, nb::numpy, nb::shape<-1, 3>, nb::f_contig> face_matrix;
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

    for (const auto &material : m.materials) {
      res.texture_paths.push_back(material.diffuse_texname);
    }

    // copy vertex matrix
    res.vertex_matrix.assign(m.attributes.positions.begin(),
                             m.attributes.positions.end());

    // copy face matrix
    for (const auto &shape : m.shapes) {
      for (const auto &index : shape.mesh.indices) {
        res.face_matrix.push_back(index.position_index);
        res.face_matrix.push_back(index.normal_index);
        res.face_matrix.push_back(index.texcoord_index);
      }
    }
  }

  return res;
}

int main(int argc, char **argv) {
  auto res = parse_rapidobj(argv[1]);

  if (!res.ok) {
    std::cout << "Failed to parse OBJ file" << '\n';
    return EXIT_FAILURE;
  }

  std::cout << "Vertices:  " << res.vertex_count << '\n';
  std::cout << "Normals:   " << res.normal_count << '\n';
  std::cout << "UVs:       " << res.uv_count << '\n';
  std::cout << "Shapes:    " << res.shape_count << '\n';
  std::cout << "Materials: " << res.material_count << '\n';

  // print the textures paths
  for (const auto &texture_path : res.texture_paths) {
    std::cout << "Texture:   " << texture_path << '\n';
  }

  // print vertex matrix
  for (const auto &vertex : res.vertex_matrix) {
    std::cout << vertex << ' ';
  }
  std::cout << '\n';

  // print face matrix
  for (const auto &face : res.face_matrix) {
    std::cout << face << ' ';
  }
  std::cout << '\n';

  return EXIT_SUCCESS;
}