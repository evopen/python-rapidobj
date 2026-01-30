#include "rapidobj.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <iostream>
#include <vector>

namespace nb = nanobind;

// Internal storage struct using std::vector
struct ObjData {
  bool ok = false;
  std::string error_message;
  int vertex_count = 0;
  int normal_count = 0;
  int uv_count = 0;
  int shape_count = 0;
  int material_count = 0;
  std::vector<std::string> texture_paths;
  std::vector<float> vertices;             // flat: [x0,y0,z0, x1,y1,z1, ...]
  std::vector<int> faces;                  // flat: [v0,v1,v2, v0,v1,v2, ...]
  std::vector<float> texcoords;            // flat: [u0,v0, u1,v1, ...]
  std::vector<int> wedge_texcoord_indices; // per-wedge index into texcoords
};

static ObjData parse_obj_internal(const std::string &filename) {
  ObjData data;
  auto m = rapidobj::ParseFile(filename);
  data.ok = !m.error;

  if (!data.ok) {
    data.error_message = m.error.code.message();
    return data;
  }

  data.vertex_count = static_cast<int>(m.attributes.positions.size() / 3);
  data.normal_count = static_cast<int>(m.attributes.normals.size() / 3);
  data.uv_count = static_cast<int>(m.attributes.texcoords.size() / 2);
  data.shape_count = static_cast<int>(m.shapes.size());
  data.material_count = static_cast<int>(m.materials.size());

  for (const auto &material : m.materials) {
    data.texture_paths.push_back(material.diffuse_texname);
  }

  // Copy vertices
  data.vertices.assign(m.attributes.positions.begin(),
                       m.attributes.positions.end());

  // Triangulate first
  rapidobj::Triangulate(m);

  // Copy texcoords
  data.texcoords.assign(m.attributes.texcoords.begin(),
                        m.attributes.texcoords.end());

  // Copy face indices and wedge texcoord indices
  for (const auto &shape : m.shapes) {
    for (const auto &index : shape.mesh.indices) {
      data.faces.push_back(index.position_index);
      data.wedge_texcoord_indices.push_back(index.texcoord_index);
    }
  }

  return data;
}

// Python-exposed class that wraps ObjData and returns ndarrays
class ObjParseResult {
public:
  ObjData data;

  ObjParseResult(ObjData &&d) : data(std::move(d)) {}

  bool ok() const { return data.ok; }
  std::string error_message() const { return data.error_message; }
  int vertex_count() const { return data.vertex_count; }
  int normal_count() const { return data.normal_count; }
  int uv_count() const { return data.uv_count; }
  int shape_count() const { return data.shape_count; }
  int material_count() const { return data.material_count; }
  const std::vector<std::string> &texture_paths() const {
    return data.texture_paths;
  }

  // Return vertices as numpy array with shape (N, 3)
  nb::ndarray<nb::numpy, float, nb::shape<-1, 3>> vertices() {
    size_t n_vertices = data.vertices.size() / 3;
    return nb::ndarray<nb::numpy, float, nb::shape<-1, 3>>(
        data.vertices.data(), {n_vertices, 3},
        nb::handle() // no owner - prevent deallocation
    );
  }

  // Return faces as numpy array with shape (N, 3)
  nb::ndarray<nb::numpy, int, nb::shape<-1, 3>> faces() {
    size_t n_faces = data.faces.size() / 3;
    return nb::ndarray<nb::numpy, int, nb::shape<-1, 3>>(
        data.faces.data(), {n_faces, 3}, nb::handle());
  }

  // Return texcoords as numpy array with shape (N, 2)
  nb::ndarray<nb::numpy, float, nb::shape<-1, 2>> texcoords() {
    size_t n_texcoords = data.texcoords.size() / 2;
    return nb::ndarray<nb::numpy, float, nb::shape<-1, 2>>(
        data.texcoords.data(), {n_texcoords, 2}, nb::handle());
  }

  // Return wedge texcoord indices as numpy array with shape (N*3,)
  nb::ndarray<nb::numpy, int, nb::shape<-1>> wedge_texcoord_indices() {
    return nb::ndarray<nb::numpy, int, nb::shape<-1>>(
        data.wedge_texcoord_indices.data(),
        {data.wedge_texcoord_indices.size()}, nb::handle());
  }
};

ObjParseResult parse_obj(const std::string &filename) {
  return ObjParseResult(parse_obj_internal(filename));
}

NB_MODULE(rapidobj_ext, m) {
  m.doc() = "Fast OBJ file parser using rapidobj";

  nb::class_<ObjParseResult>(m, "ObjParseResult")
      .def_prop_ro("ok", &ObjParseResult::ok)
      .def_prop_ro("error_message", &ObjParseResult::error_message)
      .def_prop_ro("vertex_count", &ObjParseResult::vertex_count)
      .def_prop_ro("normal_count", &ObjParseResult::normal_count)
      .def_prop_ro("uv_count", &ObjParseResult::uv_count)
      .def_prop_ro("shape_count", &ObjParseResult::shape_count)
      .def_prop_ro("material_count", &ObjParseResult::material_count)
      .def_prop_ro("texture_paths", &ObjParseResult::texture_paths)
      .def_prop_ro("vertices", &ObjParseResult::vertices,
                   nb::rv_policy::reference_internal)
      .def_prop_ro("faces", &ObjParseResult::faces,
                   nb::rv_policy::reference_internal)
      .def_prop_ro("texcoords", &ObjParseResult::texcoords,
                   nb::rv_policy::reference_internal)
      .def_prop_ro("wedge_texcoord_indices",
                   &ObjParseResult::wedge_texcoord_indices,
                   nb::rv_policy::reference_internal);

  m.def("parse_obj", &parse_obj, nb::arg("filename"),
        "Parse an OBJ file and return the result");
}
